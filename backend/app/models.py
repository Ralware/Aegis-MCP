import enum, uuid
from datetime import datetime
from sqlalchemy import DateTime, Enum, ForeignKey, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase): pass
class Classification(str, enum.Enum): PUBLIC="PUBLIC"; INTERNAL="INTERNAL"; PERSONAL="PERSONAL"; CONFIDENTIAL="CONFIDENTIAL"; RESTRICTED="RESTRICTED"
class Decision(str, enum.Enum): ALLOW="ALLOW"; REQUIRE_APPROVAL="REQUIRE_APPROVAL"; BLOCK="BLOCK"
class ApprovalStatus(str, enum.Enum): PENDING="PENDING"; APPROVED="APPROVED"; REJECTED="REJECTED"; EXPIRED="EXPIRED"; CONSUMED="CONSUMED"; CANCELLED="CANCELLED"
class ExecutionState(str, enum.Enum): NOT_STARTED="NOT_STARTED"; EXECUTING="EXECUTING"; SUCCEEDED="SUCCEEDED"; FAILED="FAILED"; UNKNOWN="UNKNOWN"; RECONCILIATION_REQUIRED="RECONCILIATION_REQUIRED"

class User(Base):
    __tablename__="users"; id: Mapped[uuid.UUID]=mapped_column(primary_key=True, default=uuid.uuid4); google_subject: Mapped[str]=mapped_column(String(255), unique=True); email: Mapped[str]=mapped_column(String(320), unique=True); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), server_default=func.now())
class GoogleIntegration(Base):
    __tablename__="google_integrations"; id: Mapped[uuid.UUID]=mapped_column(primary_key=True, default=uuid.uuid4); user_id: Mapped[uuid.UUID]=mapped_column(ForeignKey("users.id"), unique=True); account_email: Mapped[str]=mapped_column(String(320)); encrypted_credentials: Mapped[str]=mapped_column(Text); scopes: Mapped[list]=mapped_column(JSON); revoked_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True)); updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
class Artifact(Base):
    __tablename__="artifacts"; id: Mapped[uuid.UUID]=mapped_column(primary_key=True, default=uuid.uuid4); user_id: Mapped[uuid.UUID]=mapped_column(ForeignKey("users.id")); provider: Mapped[str]=mapped_column(String(40)); source_id: Mapped[str]=mapped_column(String(512)); content_hash: Mapped[str]=mapped_column(String(64)); mime_type: Mapped[str]=mapped_column(String(255)); classification: Mapped[Classification]=mapped_column(Enum(Classification)); provenance: Mapped[dict]=mapped_column(JSON); taint: Mapped[list]=mapped_column(JSON, default=list); retrieved_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), server_default=func.now()); __table_args__=(UniqueConstraint("user_id","provider","source_id","content_hash"),)
class Invocation(Base):
    __tablename__="invocations"; id: Mapped[uuid.UUID]=mapped_column(primary_key=True, default=uuid.uuid4); user_id: Mapped[uuid.UUID]=mapped_column(ForeignKey("users.id")); tool: Mapped[str]=mapped_column(String(100)); arguments_hash: Mapped[str]=mapped_column(String(64)); decision: Mapped[Decision]=mapped_column(Enum(Decision)); state: Mapped[ExecutionState]=mapped_column(Enum(ExecutionState), default=ExecutionState.NOT_STARTED); correlation_id: Mapped[str]=mapped_column(String(64)); provider_id: Mapped[str|None]=mapped_column(String(512)); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), server_default=func.now())
class Approval(Base):
    __tablename__="approvals"; id: Mapped[uuid.UUID]=mapped_column(primary_key=True, default=uuid.uuid4); user_id: Mapped[uuid.UUID]=mapped_column(ForeignKey("users.id")); invocation_id: Mapped[uuid.UUID]=mapped_column(ForeignKey("invocations.id")); status: Mapped[ApprovalStatus]=mapped_column(Enum(ApprovalStatus), default=ApprovalStatus.PENDING); frozen_payload: Mapped[dict]=mapped_column(JSON); frozen_hash: Mapped[str]=mapped_column(String(64)); expires_at: Mapped[datetime]=mapped_column(DateTime(timezone=True)); decided_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True)); execution_state: Mapped[ExecutionState]=mapped_column(Enum(ExecutionState), default=ExecutionState.NOT_STARTED)
class AuditEvent(Base):
    __tablename__="audit_events"; id: Mapped[uuid.UUID]=mapped_column(primary_key=True, default=uuid.uuid4); user_id: Mapped[uuid.UUID|None]=mapped_column(ForeignKey("users.id")); invocation_id: Mapped[uuid.UUID|None]=mapped_column(ForeignKey("invocations.id")); event_type: Mapped[str]=mapped_column(String(100)); details: Mapped[dict]=mapped_column(JSON); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), server_default=func.now())
class OAuthState(Base):
    __tablename__="oauth_states"; state: Mapped[str]=mapped_column(String(128), primary_key=True); redirect_uri: Mapped[str]=mapped_column(String(2048)); expires_at: Mapped[datetime]=mapped_column(DateTime(timezone=True)); consumed_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
