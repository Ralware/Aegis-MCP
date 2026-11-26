from backend.app.models import Artifact, Classification, Decision
from backend.app.security import canonical_hash, dlp, policy

def test_send_always_requires_approval(): assert policy("gmail_send_email",[])[0] == Decision.REQUIRE_APPROVAL
def test_unknown_tools_are_blocked(): assert policy("drop_database",[])[0] == Decision.BLOCK
def test_restricted_artifact_is_blocked():
    a=Artifact(provider="drive",source_id="x",content_hash="x",mime_type="text/plain",classification=Classification.RESTRICTED,provenance={},taint=[])
    assert policy("gmail_send_email",[a])[0] == Decision.BLOCK
def test_dlp_redacts_email_and_aadhaar():
    output, classification, findings=dlp.sanitize("contact me@example.com; Aadhaar 1234 5678 9012")
    assert "me@example.com" not in output and classification == Classification.CONFIDENTIAL and findings
def test_canonical_hash_is_stable(): assert canonical_hash({"b":1,"a":2}) == canonical_hash({"a":2,"b":1})
