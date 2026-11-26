import hashlib, json, uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from .models import *
from .security import audit, canonical_hash, dlp, policy, resolve_artifacts
from .providers import GoogleProvider
from .config import settings
from .gemini_security import security_analyzer

class ExecutionService:
    def __init__(self, session: AsyncSession, user: User, correlation_id: str): self.session,self.user,self.correlation_id=session,user,correlation_id
    async def invoke(self, tool: str, args: dict):
        artifacts=await resolve_artifacts(self.session,self.user.id,args.get("attachment_ids",[]))
        decision,reason=policy(tool,artifacts); inv=Invocation(user_id=self.user.id,tool=tool,arguments_hash=canonical_hash(args),decision=decision,correlation_id=self.correlation_id); self.session.add(inv); await self.session.flush(); await audit(self.session,self.user.id,inv.id,"POLICY_DECISION",{"decision":decision.value,"reason":reason,"arguments_hash":inv.arguments_hash})
        if decision is Decision.BLOCK: await self.session.commit(); raise PermissionError(reason)
        if decision is Decision.REQUIRE_APPROVAL:
            frozen={"tool":tool,"arguments":args,"artifact_hashes":{str(a.id):a.content_hash for a in artifacts}}
            approval=Approval(user_id=self.user.id,invocation_id=inv.id,frozen_payload=frozen,frozen_hash=canonical_hash(frozen),expires_at=datetime.now(timezone.utc)+timedelta(minutes=30)); self.session.add(approval); await audit(self.session,self.user.id,inv.id,"APPROVAL_CREATED",{"approval_id":str(approval.id),"reason":reason}); await self.session.commit(); return {"status":"PENDING_APPROVAL","approval_id":str(approval.id),"reason":reason}
        result=await self._execute(inv,tool,args); await self.session.commit(); return result
    async def _execute(self, inv, tool, args):
        inv.state=ExecutionState.EXECUTING; provider=GoogleProvider(self.session,self.user)
        try:
            operation={"gmail_search_emails":provider.gmail_search,"gmail_get_message":provider.gmail_message,"gmail_get_thread":provider.gmail_thread,"drive_search_files":provider.drive_search,"drive_get_file_metadata":provider.drive_metadata,"drive_read_file":provider.drive_read}[tool]
            if tool in {"gmail_get_message","gmail_get_thread"}: raw=await operation(args["id"],args.get("include_attachments",False))
            elif tool=="drive_get_file_metadata": raw=await operation(args["id"])
            elif tool=="drive_read_file": raw=await operation(args["id"],args["mime_type"],settings().max_document_bytes)
            elif tool in {"gmail_search_emails","drive_search_files"}: raw=await operation(args.get("query",""),args.get("page_token"),args.get("limit",10))
            else:
                attachments=[await provider.artifact_attachment(artifact) for artifact in await resolve_artifacts(self.session,self.user.id,args.get("attachment_ids",[]))]
                raw=await operation(args,attachments)
            if tool in {"gmail_get_message","gmail_get_thread"}:
                serialized=json.dumps(raw,ensure_ascii=False); sanitized,classification,findings=dlp.sanitize(serialized)
                threats=await security_analyzer.analyze(sanitized)
                blob=serialized.encode(); artifact=Artifact(user_id=self.user.id,provider="gmail",source_id=args["id"],content_hash=hashlib.sha256(blob).hexdigest(),mime_type="message/rfc822",classification=classification,provenance={"message_id":args["id"]},taint=findings); self.session.add(artifact)
                result={"artifact_id":str(artifact.id),"content":sanitized,"classification":classification.value,"redactions":findings,"threat_analysis":threats.model_dump()}
            elif isinstance(raw,bytes):
                text=raw.decode("utf-8",errors="replace"); sanitized,classification,findings=dlp.sanitize(text); threats=await security_analyzer.analyze(sanitized); artifact=Artifact(user_id=self.user.id,provider="google-drive",source_id=args["id"],content_hash=hashlib.sha256(raw).hexdigest(),mime_type=args["mime_type"],classification=classification,provenance={"file_id":args["id"]},taint=findings); self.session.add(artifact); result={"artifact_id":str(artifact.id),"content":sanitized,"classification":classification.value,"redactions":findings,"threat_analysis":threats.model_dump()}
            else:
                # Inspection is mandatory for *all* model-facing provider data, including
                # names, snippets and metadata returned by search/list APIs.
                def redact(value):
                    if isinstance(value,str): return dlp.sanitize(value)[0]
                    if isinstance(value,list): return [redact(item) for item in value]
                    if isinstance(value,dict): return {key:redact(item) for key,item in value.items()}
                    return value
                result=redact(raw)
            inv.state=ExecutionState.SUCCEEDED; await audit(self.session,self.user.id,inv.id,"EXECUTION_SUCCEEDED",{"tool":tool}); return result
        except Exception as exc:
            inv.state=ExecutionState.UNKNOWN if tool=="gmail_send_email" else ExecutionState.FAILED; await audit(self.session,self.user.id,inv.id,"EXECUTION_FAILED",{"tool":tool,"error_type":type(exc).__name__}); raise
