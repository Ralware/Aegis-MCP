from .main import app
from .mcp_server import mcp
# mcp.streamable_http_app() owns the standard Streamable HTTP /mcp endpoint.
app.mount("/", mcp.streamable_http_app())
