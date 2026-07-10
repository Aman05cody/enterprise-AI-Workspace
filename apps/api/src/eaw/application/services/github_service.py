"""GitHub connector: connect, list repos, select, sync, intelligence helpers."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from eaw.application.ports.llm import ChatMessage, LLMPort
from eaw.application.services.audit_service import AuditService
from eaw.application.services.chat_service import ChatService
from eaw.application.services.document_service import DocumentService
from eaw.application.services.knowledge_service import KnowledgeService
from eaw.application.services.org_service import OrgService
from eaw.core.config import Settings
from eaw.domain.common.enums import (
    ConnectorStatus,
    ConnectorType,
    MembershipRole,
    SourceType,
    SyncJobStatus,
)
from eaw.domain.common.errors import ForbiddenError, NotFoundError, ValidationAppError
from eaw.domain.tenancy.policies import can_manage_knowledge_bases, require_role, role_at_least
from eaw.infrastructure.connectors.github_client import GitHubClient
from eaw.infrastructure.db.models.connectors import (
    Connector,
    ConnectorResource,
    ConnectorSyncJob,
)
from eaw.infrastructure.db.models.knowledge import KnowledgeBase
from eaw.infrastructure.security.crypto import decrypt_secret, encrypt_secret

logger = logging.getLogger(__name__)


class GitHubService:
    def __init__(
        self,
        db: Session,
        settings: Settings,
        org_service: OrgService,
        knowledge_service: KnowledgeService,
        document_service: DocumentService,
        llm: LLMPort,
        audit: AuditService,
        chat_service: Optional[ChatService] = None,
    ) -> None:
        self.db = db
        self.settings = settings
        self.org = org_service
        self.knowledge = knowledge_service
        self.documents = document_service
        self.llm = llm
        self.audit = audit
        self.chat = chat_service

    def _require_admin(self, org_id: UUID, user_id: UUID):
        mem = self.org.get_membership(org_id, user_id)
        if not role_at_least(mem.role, MembershipRole.ADMIN):
            raise ForbiddenError("Admin role required to manage connectors")
        return mem

    def _get_connector(self, connector_id: UUID) -> Connector:
        c = self.db.get(Connector, connector_id)
        if c is None or c.type != ConnectorType.GITHUB.value:
            raise NotFoundError("GitHub connector not found")
        return c

    def _client(self, connector: Connector) -> GitHubClient:
        if not connector.credentials_enc:
            raise ValidationAppError("Connector has no credentials")
        token = decrypt_secret(connector.credentials_enc)
        return GitHubClient(token, api_base=self.settings.github_api_base)

    def connect_with_pat(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        personal_access_token: str,
        display_name: Optional[str] = None,
    ) -> Connector:
        self._require_admin(organization_id, user_id)
        client = GitHubClient(
            personal_access_token, api_base=self.settings.github_api_base
        )
        profile = client.verify_token()
        login = profile.get("login") or "github"

        # Upsert single github connector per org for simplicity
        existing = self.db.scalar(
            select(Connector).where(
                Connector.organization_id == organization_id,
                Connector.type == ConnectorType.GITHUB.value,
            )
        )
        enc = encrypt_secret(personal_access_token.strip())
        if existing:
            existing.credentials_enc = enc
            existing.status = ConnectorStatus.CONNECTED.value
            existing.display_name = display_name or f"GitHub (@{login})"
            existing.config = {
                **(existing.config or {}),
                "login": login,
                "github_user_id": profile.get("id"),
            }
            connector = existing
        else:
            connector = Connector(
                organization_id=organization_id,
                type=ConnectorType.GITHUB.value,
                status=ConnectorStatus.CONNECTED.value,
                display_name=display_name or f"GitHub (@{login})",
                credentials_enc=enc,
                config={"login": login, "github_user_id": profile.get("id")},
                created_by=user_id,
            )
            self.db.add(connector)

        self.audit.log(
            action="connector.github.connected",
            actor_user_id=user_id,
            organization_id=organization_id,
            resource_type="connector",
            metadata={"login": login},
        )
        self.db.commit()
        self.db.refresh(connector)
        # Refresh resource catalog
        self.refresh_repo_catalog(connector_id=connector.id, user_id=user_id)
        self.db.refresh(connector)
        return connector

    def disconnect(self, *, connector_id: UUID, user_id: UUID) -> None:
        c = self._get_connector(connector_id)
        self._require_admin(c.organization_id, user_id)
        c.status = ConnectorStatus.DISCONNECTED.value
        c.credentials_enc = None
        self.audit.log(
            action="connector.github.disconnected",
            actor_user_id=user_id,
            organization_id=c.organization_id,
            resource_type="connector",
            resource_id=c.id,
        )
        self.db.commit()

    def list_connectors(self, *, organization_id: UUID, user_id: UUID) -> list[Connector]:
        self.org.get_membership(organization_id, user_id)
        return list(
            self.db.scalars(
                select(Connector).where(
                    Connector.organization_id == organization_id,
                    Connector.type == ConnectorType.GITHUB.value,
                )
            ).all()
        )

    def refresh_repo_catalog(self, *, connector_id: UUID, user_id: UUID) -> list[ConnectorResource]:
        c = self._get_connector(connector_id)
        self._require_admin(c.organization_id, user_id)
        if c.status != ConnectorStatus.CONNECTED.value:
            raise ValidationAppError("Connector is not connected")
        client = self._client(c)
        repos = client.list_repos()
        existing = {
            r.external_id: r
            for r in self.db.scalars(
                select(ConnectorResource).where(ConnectorResource.connector_id == c.id)
            ).all()
        }
        for repo in repos:
            ext = str(repo.id)
            meta = {
                "full_name": repo.full_name,
                "default_branch": repo.default_branch,
                "private": repo.private,
                "html_url": repo.html_url,
                "language": repo.language,
                "description": repo.description,
            }
            if ext in existing:
                existing[ext].name = repo.full_name
                existing[ext].metadata_ = meta
            else:
                self.db.add(
                    ConnectorResource(
                        connector_id=c.id,
                        organization_id=c.organization_id,
                        external_id=ext,
                        name=repo.full_name,
                        resource_type="repo",
                        sync_enabled=False,
                        metadata_=meta,
                    )
                )
        self.db.commit()
        return list(
            self.db.scalars(
                select(ConnectorResource)
                .where(ConnectorResource.connector_id == c.id)
                .order_by(ConnectorResource.name)
            ).all()
        )

    def list_resources(self, *, connector_id: UUID, user_id: UUID) -> list[ConnectorResource]:
        c = self._get_connector(connector_id)
        self.org.get_membership(c.organization_id, user_id)
        return list(
            self.db.scalars(
                select(ConnectorResource)
                .where(ConnectorResource.connector_id == c.id)
                .order_by(ConnectorResource.name)
            ).all()
        )

    def set_resource_selection(
        self,
        *,
        connector_id: UUID,
        user_id: UUID,
        resource_ids: list[UUID],
    ) -> list[ConnectorResource]:
        c = self._get_connector(connector_id)
        self._require_admin(c.organization_id, user_id)
        resources = list(
            self.db.scalars(
                select(ConnectorResource).where(ConnectorResource.connector_id == c.id)
            ).all()
        )
        selected = set(resource_ids)
        for r in resources:
            r.sync_enabled = r.id in selected
        self.db.commit()
        return [r for r in resources if r.sync_enabled]

    def sync_connector(
        self,
        *,
        connector_id: UUID,
        user_id: UUID,
        resource_id: Optional[UUID] = None,
    ) -> ConnectorSyncJob:
        c = self._get_connector(connector_id)
        self._require_admin(c.organization_id, user_id)
        job = ConnectorSyncJob(
            id=uuid4(),
            organization_id=c.organization_id,
            connector_id=c.id,
            resource_id=resource_id,
            status=SyncJobStatus.QUEUED.value,
            stats={},
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(job)
        c.status = ConnectorStatus.SYNCING.value
        self.db.commit()
        self.db.refresh(job)

        # Run sync inline (or enqueue). Prefer sync with optional celery later.
        try:
            from eaw.infrastructure.queue.enqueue import enqueue_github_sync

            task_id = enqueue_github_sync(job.id)
            if task_id:
                job.stats = {**(job.stats or {}), "celery_task_id": task_id}
                self.db.commit()
            else:
                self.db.refresh(job)
        except Exception:
            # fallback direct
            self.run_sync_job(job.id, actor_user_id=user_id)
            self.db.refresh(job)
        return job

    def run_sync_job(self, job_id: UUID, actor_user_id: Optional[UUID] = None) -> ConnectorSyncJob:
        job = self.db.get(ConnectorSyncJob, job_id)
        if job is None:
            raise NotFoundError("Sync job not found")
        connector = self._get_connector(job.connector_id)
        job.status = SyncJobStatus.RUNNING.value
        self.db.commit()

        client = self._client(connector)
        q = select(ConnectorResource).where(
            ConnectorResource.connector_id == connector.id,
            ConnectorResource.sync_enabled.is_(True),
        )
        if job.resource_id:
            q = q.where(ConnectorResource.id == job.resource_id)
        resources = list(self.db.scalars(q).all())
        if not resources:
            job.status = SyncJobStatus.FAILED.value
            job.error_message = "No repositories selected for sync"
            job.finished_at = datetime.now(timezone.utc)
            connector.status = ConnectorStatus.CONNECTED.value
            self.db.commit()
            return job

        actor = actor_user_id or connector.created_by
        if actor is None:
            # pick org owner-ish fallback: use first membership admin later; for now fail
            job.status = SyncJobStatus.FAILED.value
            job.error_message = "No actor user for sync"
            job.finished_at = datetime.now(timezone.utc)
            connector.status = ConnectorStatus.CONNECTED.value
            self.db.commit()
            return job

        total_files = 0
        total_docs = 0
        errors: list[str] = []

        try:
            for res in resources:
                meta = res.metadata_ or {}
                full_name = meta.get("full_name") or res.name
                if "/" not in full_name:
                    errors.append(f"Invalid repo name {full_name}")
                    continue
                owner, repo = full_name.split("/", 1)
                branch = meta.get("default_branch") or "main"
                kb = self._ensure_repo_kb(
                    organization_id=connector.organization_id,
                    user_id=actor,
                    full_name=full_name,
                    description=meta.get("description"),
                )
                res.knowledge_base_id = kb.id

                try:
                    tree = client.get_tree(owner, repo, branch)
                    paths = client.select_indexable_paths(
                        tree,
                        max_files=self.settings.github_sync_max_files,
                        max_file_bytes=self.settings.github_sync_max_file_bytes,
                    )
                except Exception as exc:  # noqa: BLE001
                    errors.append(f"{full_name}: {exc}")
                    continue

                for path in paths:
                    try:
                        text, _url = client.get_file_content(owner, repo, path, branch)
                        header = (
                            f"# File: {full_name}/{path}\n"
                            f"Repository: {full_name}\n"
                            f"Branch: {branch}\n\n"
                        )
                        doc = self.documents.ingest_text(
                            kb_id=kb.id,
                            user_id=actor,
                            title=f"{full_name}:{path}",
                            text=header + text,
                            source_type=SourceType.GITHUB.value,
                            source_path=path,
                            skip_duplicate=True,
                        )
                        total_files += 1
                        if doc:
                            total_docs += 1
                    except Exception as exc:  # noqa: BLE001
                        errors.append(f"{full_name}/{path}: {exc}")
                        logger.warning("GitHub file sync failed: %s", exc)

                res.last_synced_at = datetime.now(timezone.utc)

            job.status = SyncJobStatus.SUCCEEDED.value
            job.stats = {
                "resources": len(resources),
                "files_seen": total_files,
                "documents_upserted": total_docs,
                "errors": errors[:20],
            }
            job.error_message = None if not errors else f"{len(errors)} file errors"
            connector.last_synced_at = datetime.now(timezone.utc)
            connector.status = ConnectorStatus.CONNECTED.value
            job.finished_at = datetime.now(timezone.utc)
            self.audit.log(
                action="connector.github.synced",
                actor_user_id=actor,
                organization_id=connector.organization_id,
                resource_type="connector",
                resource_id=connector.id,
                metadata=job.stats,
            )
            self.db.commit()
        except Exception as exc:  # noqa: BLE001
            logger.exception("GitHub sync failed")
            job.status = SyncJobStatus.FAILED.value
            job.error_message = str(exc)[:2000]
            job.finished_at = datetime.now(timezone.utc)
            connector.status = ConnectorStatus.ERROR.value
            self.db.commit()
        self.db.refresh(job)
        return job

    def _ensure_repo_kb(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        full_name: str,
        description: Optional[str],
    ) -> KnowledgeBase:
        name = f"GitHub · {full_name}"[:200]
        existing = self.db.scalar(
            select(KnowledgeBase).where(
                KnowledgeBase.organization_id == organization_id,
                KnowledgeBase.name == name,
                KnowledgeBase.deleted_at.is_(None),
            )
        )
        if existing:
            return existing
        # create via service (requires manager+)
        try:
            return self.knowledge.create(
                organization_id=organization_id,
                user_id=user_id,
                name=name,
                description=description or f"Indexed repository {full_name}",
            )
        except Exception:
            # If name race, re-fetch
            existing = self.db.scalar(
                select(KnowledgeBase).where(
                    KnowledgeBase.organization_id == organization_id,
                    KnowledgeBase.name == name,
                    KnowledgeBase.deleted_at.is_(None),
                )
            )
            if existing:
                return existing
            raise

    def get_resource(self, resource_id: UUID) -> ConnectorResource:
        r = self.db.get(ConnectorResource, resource_id)
        if r is None:
            raise NotFoundError("Repository resource not found")
        return r

    # ── Intelligence features ────────────────────────────────

    def review_pull_request(
        self,
        *,
        connector_id: UUID,
        user_id: UUID,
        owner: str,
        repo: str,
        pull_number: int,
    ) -> dict:
        c = self._get_connector(connector_id)
        self.org.get_membership(c.organization_id, user_id)
        client = self._client(c)
        pr = client.get_pull(owner, repo, pull_number)
        files = client.get_pull_files(owner, repo, pull_number)
        diff = client.get_pull_diff(owner, repo, pull_number)
        file_summary = "\n".join(
            f"- {f.get('filename')} (+{f.get('additions')}/-{f.get('deletions')})"
            for f in files[:40]
        )
        system = (
            "You are a senior code reviewer. Review this pull request for bugs, "
            "security issues, missing tests, and design risks. Be specific. "
            "Use only the provided PR metadata and diff. If unclear, say so."
        )
        user = (
            f"PR #{pull_number}: {pr.get('title')}\n"
            f"Author: {(pr.get('user') or {}).get('login')}\n"
            f"Body:\n{pr.get('body') or ''}\n\n"
            f"Files:\n{file_summary}\n\n"
            f"Diff (truncated):\n{diff[:25000]}"
        )
        result = self.llm.complete(
            [
                ChatMessage(role="system", content=system),
                ChatMessage(role="user", content=user),
            ],
            temperature=0.2,
            max_tokens=1500,
        )
        return {
            "pull_number": pull_number,
            "title": pr.get("title"),
            "html_url": pr.get("html_url"),
            "review": result.content,
            "model": result.model,
            "files_count": len(files),
        }

    def explain_code(
        self,
        *,
        connector_id: UUID,
        user_id: UUID,
        owner: str,
        repo: str,
        path: str,
        ref: Optional[str] = None,
        focus: Optional[str] = None,
    ) -> dict:
        c = self._get_connector(connector_id)
        self.org.get_membership(c.organization_id, user_id)
        client = self._client(c)
        branch = ref or "main"
        text, url = client.get_file_content(owner, repo, path, branch)
        system = (
            "You are a staff engineer. Explain the code clearly: purpose, key functions, "
            "data flow, and risks. Do not invent APIs not present in the code."
        )
        user = (
            f"Repository: {owner}/{repo}\nPath: {path}\n"
            f"Focus: {focus or 'general explanation'}\n\n"
            f"```\n{text[:20000]}\n```"
        )
        result = self.llm.complete(
            [
                ChatMessage(role="system", content=system),
                ChatMessage(role="user", content=user),
            ],
            temperature=0.2,
        )
        return {
            "path": path,
            "url": url,
            "explanation": result.content,
            "model": result.model,
        }

    def generate_docs(
        self,
        *,
        connector_id: UUID,
        user_id: UUID,
        owner: str,
        repo: str,
        path: str,
        ref: Optional[str] = None,
    ) -> dict:
        c = self._get_connector(connector_id)
        self.org.get_membership(c.organization_id, user_id)
        client = self._client(c)
        branch = ref or "main"
        text, _ = client.get_file_content(owner, repo, path, branch)
        system = (
            "Generate clear technical documentation (Markdown) for the given source file: "
            "overview, public API, usage examples, and edge cases. Base only on the code."
        )
        result = self.llm.complete(
            [
                ChatMessage(role="system", content=system),
                ChatMessage(role="user", content=f"File {path}:\n```\n{text[:20000]}\n```"),
            ],
            temperature=0.3,
        )
        return {"path": path, "documentation": result.content, "model": result.model}

    def generate_tests(
        self,
        *,
        connector_id: UUID,
        user_id: UUID,
        owner: str,
        repo: str,
        path: str,
        ref: Optional[str] = None,
    ) -> dict:
        c = self._get_connector(connector_id)
        self.org.get_membership(c.organization_id, user_id)
        client = self._client(c)
        branch = ref or "main"
        text, _ = client.get_file_content(owner, repo, path, branch)
        system = (
            "Generate high-quality unit tests for the provided source code. "
            "Match the language/framework if obvious. Include happy path and edge cases."
        )
        result = self.llm.complete(
            [
                ChatMessage(role="system", content=system),
                ChatMessage(role="user", content=f"Source {path}:\n```\n{text[:20000]}\n```"),
            ],
            temperature=0.2,
        )
        return {"path": path, "tests": result.content, "model": result.model}

    def explain_architecture(
        self,
        *,
        resource_id: UUID,
        user_id: UUID,
    ) -> dict:
        res = self.get_resource(resource_id)
        self.org.get_membership(res.organization_id, user_id)
        if not res.knowledge_base_id:
            raise ValidationAppError("Repository has not been synced yet")
        if not self.chat:
            raise ValidationAppError("Chat service unavailable")

        conv = self.chat.create_conversation(
            kb_id=res.knowledge_base_id,
            user_id=user_id,
            title=f"Architecture · {res.name}",
        )
        result = self.chat.ask(
            conversation_id=conv.id,
            user_id=user_id,
            content=(
                "Explain the overall architecture of this repository based on indexed files. "
                "Cover modules, entrypoints, data flow, and notable patterns. "
                "Cite sources when possible."
            ),
            stream=False,
        )
        assert isinstance(result, dict)
        msg = result["message"]
        return {
            "conversation_id": str(conv.id),
            "knowledge_base_id": str(res.knowledge_base_id),
            "repository": res.name,
            "answer": msg.content,
            "confidence": msg.confidence,
            "citations": [
                {
                    "rank": c.rank,
                    "excerpt": c.excerpt,
                    "document_id": str(c.document_id) if c.document_id else None,
                }
                for c in (msg.citations or [])
            ],
            "insufficient_context": result.get("insufficient_context"),
        }

    def chat_with_repo(
        self,
        *,
        resource_id: UUID,
        user_id: UUID,
        question: str,
        conversation_id: Optional[UUID] = None,
    ) -> dict:
        res = self.get_resource(resource_id)
        self.org.get_membership(res.organization_id, user_id)
        if not res.knowledge_base_id:
            raise ValidationAppError("Repository has not been synced yet")
        if not self.chat:
            raise ValidationAppError("Chat service unavailable")
        if conversation_id:
            conv = self.chat.get_conversation(conversation_id, user_id)
        else:
            conv = self.chat.create_conversation(
                kb_id=res.knowledge_base_id,
                user_id=user_id,
                title=question[:80],
            )
        result = self.chat.ask(
            conversation_id=conv.id,
            user_id=user_id,
            content=question,
            stream=False,
        )
        assert isinstance(result, dict)
        msg = result["message"]
        return {
            "conversation_id": str(conv.id),
            "knowledge_base_id": str(res.knowledge_base_id),
            "answer": msg.content,
            "confidence": msg.confidence,
            "suggestions": result.get("suggestions") or [],
            "insufficient_context": result.get("insufficient_context"),
            "message_id": str(msg.id),
        }
