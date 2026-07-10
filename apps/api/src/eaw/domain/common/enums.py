"""Shared domain enumerations."""

from enum import StrEnum


class MembershipRole(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    MANAGER = "manager"
    EMPLOYEE = "employee"
    GUEST = "guest"


class MembershipStatus(StrEnum):
    ACTIVE = "active"
    INVITED = "invited"
    DISABLED = "disabled"


class InviteStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    EXPIRED = "expired"
    REVOKED = "revoked"


class PlanTier(StrEnum):
    FREE = "free"
    TEAM = "team"
    BUSINESS = "business"
    ENTERPRISE = "enterprise"


class DocumentStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"
    DELETED = "deleted"


class SourceType(StrEnum):
    UPLOAD = "upload"
    GITHUB = "github"
    NOTION = "notion"
    GDRIVE = "gdrive"
    SLACK = "slack"
    JIRA = "jira"
    EMAIL = "email"


class StorageBackend(StrEnum):
    LOCAL = "local"
    S3 = "s3"


class IngestionJobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class IngestionStage(StrEnum):
    QUEUED = "queued"
    EXTRACT = "extract"
    CLEAN = "clean"
    CHUNK = "chunk"
    EMBED = "embed"
    INDEX = "index"
    FINALIZE = "finalize"


class ConnectorType(StrEnum):
    GITHUB = "github"
    NOTION = "notion"
    GDRIVE = "gdrive"
    SLACK = "slack"
    JIRA = "jira"


class ConnectorStatus(StrEnum):
    DISCONNECTED = "disconnected"
    CONNECTED = "connected"
    ERROR = "error"
    SYNCING = "syncing"


class SyncJobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


# Role hierarchy: higher index = more privilege
ROLE_RANK: dict[MembershipRole, int] = {
    MembershipRole.GUEST: 1,
    MembershipRole.EMPLOYEE: 2,
    MembershipRole.MANAGER: 3,
    MembershipRole.ADMIN: 4,
    MembershipRole.OWNER: 5,
}


def role_at_least(role: MembershipRole | str, minimum: MembershipRole) -> bool:
    r = MembershipRole(role)
    return ROLE_RANK[r] >= ROLE_RANK[minimum]
