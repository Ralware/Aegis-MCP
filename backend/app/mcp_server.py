"""Official MCP v2 Streamable HTTP server; every tool delegates to ExecutionService."""
import uuid
from mcp.server import MCPServer
from .db import SessionLocal
from .models import User
from .main import principal_context
from .services import ExecutionService

mcp=MCPServer("Trust Gate")
async def call(tool: str, args: dict):
    principal=principal_context.get()
    if not principal: raise PermissionError("authenticated principal required")
    async with SessionLocal() as session:
        user=await session.get(User,uuid.UUID(principal))
        return await ExecutionService(session,user,str(uuid.uuid4())).invoke(tool,args)
@mcp.tool()
async def gmail_search_emails(query: str, page_token: str|None=None, limit: int=10): return await call("gmail_search_emails",locals())
@mcp.tool()
async def gmail_get_message(id: str, include_attachments: bool=False): return await call("gmail_get_message",locals())
@mcp.tool()
async def gmail_get_thread(id: str, include_attachments: bool=False): return await call("gmail_get_thread",locals())
@mcp.tool()
async def drive_search_files(query: str, page_token: str|None=None, limit: int=10): return await call("drive_search_files",locals())
@mcp.tool()
async def drive_get_file_metadata(id: str): return await call("drive_get_file_metadata",locals())
@mcp.tool()
async def drive_read_file(id: str, mime_type: str): return await call("drive_read_file",locals())
@mcp.tool()
async def gmail_send_email(to: list[str], subject: str, body: str, cc: list[str]=[], bcc: list[str]=[], html: bool=False, attachment_ids: list[str]=[]): return await call("gmail_send_email",locals())
