import base64, hashlib, json, re, uuid
from datetime import datetime, timedelta, timezone
from cryptography.fernet import Fernet
from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer
from presidio_anonymizer import AnonymizerEngine
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from .config import settings
from .models import *

def canonical_hash(value: object) -> str: return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
def token_box() -> Fernet: return Fernet(settings().token_encryption_key.encode())
def encrypt(value: dict) -> str: return token_box().encrypt(json.dumps(value).encode()).decode()
def decrypt(value: str) -> dict: return json.loads(token_box().decrypt(value.encode()))

class Dlp:
    def __init__(self):
        self.analyzer=AnalyzerEngine(); self.analyzer.registry.add_recognizer(PatternRecognizer("AADHAAR", patterns=[Pattern("aadhaar", r"\b\d{4}[ -]?\d{4}[ -]?\d{4}\b", 0.7)])); self.analyzer.registry.add_recognizer(PatternRecognizer("API_KEY", patterns=[Pattern("api-key", r"\b(?:AIza[\w-]{35}|sk-[\w-]{20,})\b", 0.8)])); self.anonymizer=AnonymizerEngine()
    def sanitize(self, text: str) -> tuple[str, Classification, list[str]]:
        findings=self.analyzer.analyze(text=text, language="en")
        names=[x.entity_type for x in findings]
        if not findings: return text, Classification.INTERNAL, []
        return self.anonymizer.anonymize(text=text, analyzer_results=findings).text, Classification.CONFIDENTIAL, names
dlp=Dlp()

def policy(tool: str, artifacts: list[Artifact]) -> tuple[Decision,str]:
    if tool not in {"gmail_search_emails","gmail_get_message","gmail_get_thread","gmail_send_email","drive_search_files","drive_get_file_metadata","drive_read_file"}: return Decision.BLOCK,"unregistered tool"
    if tool == "gmail_send_email":
        if any(a.classification == Classification.RESTRICTED for a in artifacts): return Decision.BLOCK,"restricted artifact cannot be sent"
        return Decision.REQUIRE_APPROVAL,"email sends always require a human approval"
    return Decision.ALLOW,"authorized read-only operation"

async def audit(session: AsyncSession, user_id, invocation_id, event_type: str, details: dict): session.add(AuditEvent(user_id=user_id, invocation_id=invocation_id, event_type=event_type, details=details))
async def resolve_artifacts(session: AsyncSession, user_id, ids: list[str]) -> list[Artifact]:
    if not ids: return []
    parsed=[]
    try: parsed=[uuid.UUID(x) for x in ids]
    except ValueError: raise ValueError("invalid artifact id")
    items=(await session.scalars(select(Artifact).where(Artifact.user_id==user_id, Artifact.id.in_(parsed)))).all()
    if len(items)!=len(ids): raise PermissionError("unknown or foreign artifact")
    return list(items)
