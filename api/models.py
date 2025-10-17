from pydantic import BaseModel, HttpUrl
from typing import List, Optional

class Attachment(BaseModel):
    name: str
    url: str  # data: URIs supported

class TaskRequest(BaseModel):
    email: str
    secret: str
    task: str
    round: int
    nonce: str
    brief: str
    checks: List[str]
    evaluation_url: Optional[HttpUrl] = None
    attachments: List[Attachment] = []

class BuildResult(BaseModel):
    repo_url: str
    commit_sha: str
    pages_url: str

class TaskResponse(BuildResult):
    status: str
