"""Jira connector: projects/issues sync + sprint/story AI tools."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select

from eaw.application.ports.llm import ChatMessage, LLMPort
from eaw.application.services.audit_service import AuditService
from eaw.application.services.chat_service import ChatService
from eaw.application.services.connector_base import ConnectorServiceBase
from eaw.application.services.document_service import DocumentService
from eaw.application.services.knowledge_service import KnowledgeService
from eaw.application.services.org_service import OrgService
from eaw.core.config import Settings
from eaw.domain.common.enums import ConnectorStatus, ConnectorType, SourceType, SyncJobStatus
from eaw.domain.common.errors import NotFoundError, ValidationAppError
from eaw.infrastructure.connectors.jira_client import JiraClient
from eaw.infrastructure.db.models.connectors import Connector, ConnectorResource, ConnectorSyncJob
from eaw.infrastructure.security.crypto import encrypt_secret

logger = logging.getLogger(__name__)


class JiraService(ConnectorServiceBase):
    def __init__(
        self,
        db,
        settings: Settings,
        org_service: OrgService,
        knowledge_service: KnowledgeService,
        document_service: DocumentService,
        audit: AuditService,
        llm: LLMPort,
        chat_service: Optional[ChatService] = None,
    ) -> None:
        super().__init__(
            db,
            settings,
            org_service,
            knowledge_service,
            document_service,
            audit,
            ConnectorType.JIRA.value,
        )
        self.llm = llm
        self.chat = chat_service

    def _client(self, connector: Connector) -> JiraClient:
        raw = self.decrypt_token(connector)
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValidationAppError("Invalid Jira credentials blob") from exc
        return JiraClient(
            base_url=payload["base_url"],
            email=payload["email"],
            api_token=payload["api_token"],
        )

    def connect(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        base_url: str,
        email: str,
        api_token: str,
        display_name: Optional[str] = None,
    ) -> Connector:
        self.require_admin(organization_id, user_id)
        client = JiraClient(base_url=base_url, email=email, api_token=api_token)
        me = client.verify()
        display = me.get("displayName") or email
        secret = json.dumps(
            {
                "base_url": base_url.rstrip("/"),
                "email": email.strip(),
                "api_token": api_token.strip(),
            }
        )
        existing = self.db.scalar(
            select(Connector).where(
                Connector.organization_id == organization_id,
                Connector.type == ConnectorType.JIRA.value,
            )
        )
        enc = encrypt_secret(secret)
        if existing:
            existing.credentials_enc = enc
            existing.status = ConnectorStatus.CONNECTED.value
            existing.display_name = display_name or f"Jira · {display}"
            existing.config = {
                "base_url": base_url.rstrip("/"),
                "email": email,
                "account_id": me.get("accountId"),
            }
            connector = existing
        else:
            connector = Connector(
                organization_id=organization_id,
                type=ConnectorType.JIRA.value,
                status=ConnectorStatus.CONNECTED.value,
                display_name=display_name or f"Jira · {display}",
                credentials_enc=enc,
                config={
                    "base_url": base_url.rstrip("/"),
                    "email": email,
                    "account_id": me.get("accountId"),
                },
                created_by=user_id,
            )
            self.db.add(connector)
        self.audit.log(
            action="connector.jira.connected",
            actor_user_id=user_id,
            organization_id=organization_id,
            resource_type="connector",
            metadata={"email": email, "base_url": base_url},
        )
        self.db.commit()
        self.db.refresh(connector)
        self.refresh_catalog(connector_id=connector.id, user_id=user_id)
        self.db.refresh(connector)
        return connector

    def refresh_catalog(self, *, connector_id: UUID, user_id: UUID) -> list[ConnectorResource]:
        c = self.get_connector(connector_id)
        self.require_admin(c.organization_id, user_id)
        if c.status != ConnectorStatus.CONNECTED.value:
            raise ValidationAppError("Connector is not connected")
        client = self._client(c)
        projects = client.list_projects()
        existing = {
            r.external_id: r
            for r in self.db.scalars(
                select(ConnectorResource).where(ConnectorResource.connector_id == c.id)
            ).all()
        }
        for p in projects:
            meta = {
                "key": p.key,
                "name": p.name,
                "project_type": p.project_type,
                "style": p.style,
            }
            if p.id in existing:
                existing[p.id].name = f"{p.key} — {p.name}"
                existing[p.id].metadata_ = meta
            else:
                self.db.add(
                    ConnectorResource(
                        connector_id=c.id,
                        organization_id=c.organization_id,
                        external_id=p.id,
                        name=f"{p.key} — {p.name}",
                        resource_type="project",
                        sync_enabled=False,
                        metadata_=meta,
                    )
                )
        self.db.commit()
        return self.list_resources(connector_id=c.id, user_id=user_id)

    def sync(
        self,
        *,
        connector_id: UUID,
        user_id: UUID,
        resource_id: Optional[UUID] = None,
    ) -> ConnectorSyncJob:
        c = self.get_connector(connector_id)
        self.require_admin(c.organization_id, user_id)
        job = self.create_sync_job(connector=c, resource_id=resource_id)
        try:
            from eaw.infrastructure.queue.enqueue import enqueue_jira_sync

            task_id = enqueue_jira_sync(job.id)
            if task_id:
                job.stats = {**(job.stats or {}), "celery_task_id": task_id}
                self.db.commit()
            else:
                self.db.refresh(job)
        except Exception:
            self.run_sync_job(job.id, actor_user_id=user_id)
            self.db.refresh(job)
        return job

    def run_sync_job(
        self, job_id: UUID, actor_user_id: Optional[UUID] = None
    ) -> ConnectorSyncJob:
        job = self.db.get(ConnectorSyncJob, job_id)
        if job is None:
            raise NotFoundError("Sync job not found")
        connector = self.get_connector(job.connector_id)
        job.status = SyncJobStatus.RUNNING.value
        self.db.commit()

        actor = actor_user_id or connector.created_by
        if not actor:
            job.status = SyncJobStatus.FAILED.value
            job.error_message = "No actor user for sync"
            job.finished_at = datetime.now(timezone.utc)
            connector.status = ConnectorStatus.CONNECTED.value
            self.db.commit()
            return job

        resources = self.enabled_resources(connector.id, job.resource_id)
        if not resources:
            job.status = SyncJobStatus.FAILED.value
            job.error_message = "No Jira projects selected"
            job.finished_at = datetime.now(timezone.utc)
            connector.status = ConnectorStatus.CONNECTED.value
            self.db.commit()
            return job

        client = self._client(connector)
        kb = self.ensure_kb(
            organization_id=connector.organization_id,
            user_id=actor,
            name="Jira Workspace",
            description="Issues synced from Jira",
        )
        docs = 0
        issues_seen = 0
        errors: list[str] = []
        try:
            for res in resources:
                key = (res.metadata_ or {}).get("key")
                if not key:
                    errors.append(f"{res.name}: missing project key")
                    continue
                try:
                    issues = client.search_issues(
                        f'project = "{key}" ORDER BY updated DESC',
                        max_results=self.settings.jira_sync_max_issues,
                    )
                except Exception as exc:  # noqa: BLE001
                    errors.append(f"{key}: search failed: {exc}")
                    continue
                for issue in issues:
                    issues_seen += 1
                    try:
                        md = client.issue_to_markdown(issue)
                        ikey = issue.get("key") or "issue"
                        doc = self.documents.ingest_text(
                            kb_id=kb.id,
                            user_id=actor,
                            title=f"Jira · {ikey}",
                            text=md,
                            source_type=SourceType.JIRA.value,
                            source_path=ikey,
                            skip_duplicate=True,
                        )
                        if doc:
                            docs += 1
                    except Exception as exc:  # noqa: BLE001
                        errors.append(f"{issue.get('key')}: {exc}")
                res.knowledge_base_id = kb.id
                res.last_synced_at = datetime.now(timezone.utc)

            job.status = SyncJobStatus.SUCCEEDED.value
            job.stats = {
                "projects": len(resources),
                "issues_seen": issues_seen,
                "documents": docs,
                "errors": errors[:20],
                "knowledge_base_id": str(kb.id),
            }
            job.error_message = None if not errors else f"{len(errors)} issue errors"
            job.finished_at = datetime.now(timezone.utc)
            connector.last_synced_at = datetime.now(timezone.utc)
            connector.status = ConnectorStatus.CONNECTED.value
            self.audit.log(
                action="connector.jira.synced",
                actor_user_id=actor,
                organization_id=connector.organization_id,
                resource_type="connector",
                resource_id=connector.id,
                metadata=job.stats,
            )
            self.db.commit()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Jira sync failed")
            job.status = SyncJobStatus.FAILED.value
            job.error_message = str(exc)[:2000]
            job.finished_at = datetime.now(timezone.utc)
            connector.status = ConnectorStatus.ERROR.value
            self.db.commit()
        self.db.refresh(job)
        return job

    def explain_story(
        self, *, connector_id: UUID, user_id: UUID, issue_key: str
    ) -> dict:
        c = self.get_connector(connector_id)
        self.org.get_membership(c.organization_id, user_id)
        client = self._client(c)
        issue = client.get_issue(issue_key)
        md = client.issue_to_markdown(issue)
        result = self.llm.complete(
            [
                ChatMessage(
                    role="system",
                    content=(
                        "Explain this Jira story for an engineer and a PM: "
                        "goal, acceptance criteria if present, dependencies, risks, "
                        "and suggested next steps. Use only the issue content."
                    ),
                ),
                ChatMessage(role="user", content=md[:20000]),
            ],
            temperature=0.2,
        )
        return {
            "issue_key": issue_key,
            "summary": (issue.get("fields") or {}).get("summary"),
            "explanation": result.content,
            "model": result.model,
        }

    def issue_search(
        self, *, connector_id: UUID, user_id: UUID, jql: str, max_results: int = 20
    ) -> dict:
        c = self.get_connector(connector_id)
        self.org.get_membership(c.organization_id, user_id)
        client = self._client(c)
        issues = client.search_issues(jql, max_results=max_results)
        simplified = []
        for i in issues:
            f = i.get("fields") or {}
            simplified.append(
                {
                    "key": i.get("key"),
                    "summary": f.get("summary"),
                    "status": (f.get("status") or {}).get("name"),
                    "assignee": (f.get("assignee") or {}).get("displayName"),
                    "type": (f.get("issuetype") or {}).get("name"),
                }
            )
        # optional LLM overview
        overview = None
        if simplified:
            overview_result = self.llm.complete(
                [
                    ChatMessage(
                        role="system",
                        content="Summarize this Jira search result set for a manager.",
                    ),
                    ChatMessage(
                        role="user",
                        content=json.dumps(simplified, indent=2)[:15000],
                    ),
                ],
                temperature=0.2,
            )
            overview = overview_result.content
        return {"jql": jql, "count": len(simplified), "issues": simplified, "overview": overview}

    def sprint_summary(
        self,
        *,
        connector_id: UUID,
        user_id: UUID,
        project_key: str,
        board_id: Optional[int] = None,
    ) -> dict:
        c = self.get_connector(connector_id)
        self.org.get_membership(c.organization_id, user_id)
        client = self._client(c)
        boards = client.list_boards(project_key)
        if not boards and not board_id:
            # fallback: open issues in project
            issues = client.search_issues(
                f'project = "{project_key}" AND sprint in openSprints() ORDER BY rank',
                max_results=50,
            )
            payload = [client.issue_to_markdown(i) for i in issues[:30]]
            result = self.llm.complete(
                [
                    ChatMessage(
                        role="system",
                        content=(
                            "Create a sprint summary: goals, in-progress work, blockers, "
                            "completed items if any, and risks."
                        ),
                    ),
                    ChatMessage(
                        role="user",
                        content="\n\n---\n\n".join(payload)[:25000] or "No issues found.",
                    ),
                ],
                temperature=0.2,
            )
            return {
                "project_key": project_key,
                "mode": "jql_open_sprints",
                "issue_count": len(issues),
                "summary": result.content,
                "model": result.model,
            }

        bid = board_id or boards[0].get("id")
        sprints = client.list_sprints(bid)
        active = next((s for s in sprints if s.get("state") == "active"), None)
        if not active and sprints:
            active = sprints[0]
        if not active:
            raise ValidationAppError("No sprints found for board")
        issues = client.sprint_issues(active["id"], max_results=50)
        lines = []
        for i in issues:
            f = i.get("fields") or {}
            lines.append(
                f"- {i.get('key')}: {f.get('summary')} "
                f"[{(f.get('status') or {}).get('name')}] "
                f"({(f.get('assignee') or {}).get('displayName') or 'Unassigned'})"
            )
        result = self.llm.complete(
            [
                ChatMessage(
                    role="system",
                    content=(
                        "Write a concise sprint summary for leadership: theme, progress, "
                        "risks, and recommended focus. Use only the issue list."
                    ),
                ),
                ChatMessage(
                    role="user",
                    content=(
                        f"Sprint: {active.get('name')}\n"
                        f"Goal: {active.get('goal') or '—'}\n"
                        f"State: {active.get('state')}\n\n"
                        f"Issues:\n" + "\n".join(lines)
                    ),
                ),
            ],
            temperature=0.2,
        )
        return {
            "project_key": project_key,
            "board_id": bid,
            "sprint": {
                "id": active.get("id"),
                "name": active.get("name"),
                "state": active.get("state"),
                "goal": active.get("goal"),
            },
            "issue_count": len(issues),
            "summary": result.content,
            "model": result.model,
        }

    def ai_search(self, *, connector_id: UUID, user_id: UUID, query: str) -> dict:
        c = self.get_connector(connector_id)
        self.org.get_membership(c.organization_id, user_id)
        res = self.db.scalar(
            select(ConnectorResource).where(
                ConnectorResource.connector_id == c.id,
                ConnectorResource.knowledge_base_id.is_not(None),
            )
        )
        if not res or not res.knowledge_base_id:
            raise ValidationAppError("Sync at least one project before AI search")
        if not self.chat:
            raise ValidationAppError("Chat service unavailable")
        conv = self.chat.create_conversation(
            kb_id=res.knowledge_base_id,
            user_id=user_id,
            title=f"Jira search: {query[:60]}",
        )
        result = self.chat.ask(
            conversation_id=conv.id,
            user_id=user_id,
            content=query,
            stream=False,
        )
        assert isinstance(result, dict)
        msg = result["message"]
        return {
            "conversation_id": str(conv.id),
            "knowledge_base_id": str(res.knowledge_base_id),
            "answer": msg.content,
            "confidence": msg.confidence,
            "insufficient_context": result.get("insufficient_context"),
        }
