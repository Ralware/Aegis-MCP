from pydantic import BaseModel, Field
class SendEmail(BaseModel):
    to: list[str] = Field(min_length=1); cc: list[str]=[]; bcc: list[str]=[]; subject: str=Field(max_length=998); body: str; html: bool=False; attachment_ids: list[str]=[]
class ChatRequest(BaseModel): message: str
