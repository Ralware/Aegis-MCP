import base64, io, json, hashlib
from email.message import EmailMessage
from pypdf import PdfReader
from docx import Document
from openpyxl import load_workbook
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from .models import GoogleIntegration, User
from .security import decrypt, encrypt
from .config import settings

class GoogleProvider:
    def __init__(self, session: AsyncSession, user: User): self.session,self.user=session,user
    async def credentials(self):
        integration=await self.session.scalar(select(GoogleIntegration).where(GoogleIntegration.user_id==self.user.id, GoogleIntegration.revoked_at.is_(None)))
        if not integration: raise PermissionError("Google account is not connected")
        data=decrypt(integration.encrypted_credentials); creds=Credentials.from_authorized_user_info(data)
        if creds.expired and creds.refresh_token:
            from google.auth.transport.requests import Request
            creds.refresh(Request()); integration.encrypted_credentials=encrypt(json.loads(creds.to_json()))
        if not creds.valid: raise PermissionError("Google credentials are invalid or revoked")
        return creds
    async def gmail(self): return build("gmail","v1",credentials=await self.credentials(),cache_discovery=False)
    async def drive(self): return build("drive","v3",credentials=await self.credentials(),cache_discovery=False)
    async def gmail_search(self, query, page_token=None, limit=10):
        return (await self.gmail()).users().messages().list(userId="me",q=query,pageToken=page_token,maxResults=min(limit,100)).execute()
    def _email_body(self, payload):
        """Return text parts without rendering HTML or following remote content."""
        parts=[]
        def visit(part):
            mime=part.get("mimeType", "")
            data=part.get("body",{}).get("data")
            if data and mime in {"text/plain","text/html"}:
                parts.append(base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode("utf-8",errors="replace"))
            for child in part.get("parts",[]): visit(child)
        visit(payload); return "\n".join(parts)
    def _normalize_message(self, raw, include_attachments=False, service=None):
        headers={h["name"].lower():h["value"] for h in raw.get("payload",{}).get("headers",[])}
        result={"id":raw["id"],"thread_id":raw.get("threadId"),"from":headers.get("from"),"to":headers.get("to"),"subject":headers.get("subject"),"timestamp":raw.get("internalDate"),"body":self._email_body(raw.get("payload",{})),"attachments":[]}
        def visit(part):
            filename=part.get("filename")
            attachment_id=part.get("body",{}).get("attachmentId")
            if filename and attachment_id:
                item={"filename":filename,"mime_type":part.get("mimeType"),"attachment_id":attachment_id}
                if include_attachments and service:
                    blob=service.users().messages().attachments().get(userId="me",messageId=raw["id"],id=attachment_id).execute().get("data","")
                    item["sha256"]=hashlib.sha256(base64.urlsafe_b64decode(blob + "=" * (-len(blob) % 4))).hexdigest()
                result["attachments"].append(item)
            for child in part.get("parts",[]): visit(child)
        visit(raw.get("payload",{})); return result
    async def gmail_message(self, message_id, include_attachments=False):
        service=await self.gmail(); return self._normalize_message(service.users().messages().get(userId="me",id=message_id,format="full").execute(),include_attachments,service)
    async def gmail_thread(self, thread_id, include_attachments=False):
        service=await self.gmail(); raw=service.users().threads().get(userId="me",id=thread_id,format="full").execute()
        return {"id":raw["id"],"messages":[self._normalize_message(message,include_attachments,service) for message in raw.get("messages",[])]}
    async def gmail_send(self, args, attachments=[]):
        msg=EmailMessage(); msg["To"]=", ".join(args["to"]); msg["Subject"]=args["subject"]
        if args.get("cc"): msg["Cc"]=", ".join(args["cc"])
        if args.get("bcc"): msg["Bcc"]=", ".join(args["bcc"])
        msg.set_content(args["body"], subtype="html" if args.get("html") else "plain")
        for attachment in attachments:
            main, _, sub = attachment["mime_type"].partition("/")
            msg.add_attachment(attachment["content"], maintype=main, subtype=sub or "octet-stream", filename=attachment["filename"])
        raw=base64.urlsafe_b64encode(msg.as_bytes()).decode(); return (await self.gmail()).users().messages().send(userId="me",body={"raw":raw}).execute()
    async def artifact_attachment(self, artifact):
        if artifact.provider != "google-drive": raise ValueError("only inspected Google Drive artifacts can be attached")
        metadata=await self.drive_metadata(artifact.source_id)
        content=await self.drive_read(artifact.source_id,artifact.mime_type,settings().max_document_bytes)
        if hashlib.sha256(content).hexdigest()!=artifact.content_hash: raise ValueError("attachment content changed since retrieval")
        return {"content":content,"mime_type":artifact.mime_type,"filename":metadata["name"]}
    async def drive_search(self, query, page_token=None, limit=10): return (await self.drive()).files().list(q=query,pageToken=page_token,pageSize=min(limit,100),fields="nextPageToken,files(id,name,mimeType,modifiedTime,createdTime,size,owners(emailAddress,displayName),webViewLink)").execute()
    async def drive_metadata(self, file_id): return (await self.drive()).files().get(fileId=file_id,fields="id,name,mimeType,modifiedTime,createdTime,size,owners(emailAddress,displayName),exportLinks,webContentLink").execute()
    async def drive_read(self, file_id, mime_type, max_bytes):
        drive=await self.drive()
        metadata=drive.files().get(fileId=file_id,fields="size,mimeType,name").execute()
        if metadata.get("size") and int(metadata["size"]) > max_bytes: raise ValueError("file exceeds configured inspection limit")
        if not (mime_type.startswith("application/vnd.google-apps") or mime_type in {"text/plain","text/csv","application/pdf","application/vnd.openxmlformats-officedocument.wordprocessingml.document","application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}): raise ValueError("unsupported file type; raw content was withheld")
        request=drive.files().export_media(fileId=file_id,mimeType="text/plain") if mime_type.startswith("application/vnd.google-apps") else drive.files().get_media(fileId=file_id)
        buffer=io.BytesIO(); downloader=MediaIoBaseDownload(buffer,request)
        done=False
        while not done: _,done=downloader.next_chunk()
        value=buffer.getvalue()
        if len(value)>max_bytes: raise ValueError("download exceeds configured inspection limit")
        if mime_type == "application/pdf":
            return "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(value)).pages).encode()
        if mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            return "\n".join(p.text for p in Document(io.BytesIO(value)).paragraphs).encode()
        if mime_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
            book=load_workbook(io.BytesIO(value),read_only=True,data_only=True)
            return "\n".join("\t".join("" if cell is None else str(cell) for cell in row) for sheet in book.worksheets for row in sheet.iter_rows(values_only=True)).encode()
        # Google exports, TXT and CSV arrive as inspectable text. Binary/unsupported
        # formats were rejected above rather than passed uninspected to Gemini.
        return value
