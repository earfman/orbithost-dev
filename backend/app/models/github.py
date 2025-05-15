from typing import List, Optional
from pydantic import BaseModel, HttpUrl

class GitHubUser(BaseModel):
    name: str
    email: str
    username: str

class GitHubRepository(BaseModel):
    id: int
    name: str
    full_name: str
    private: bool
    html_url: HttpUrl
    description: Optional[str] = None
    default_branch: str

class GitHubCommit(BaseModel):
    id: str
    message: str
    timestamp: str
    url: HttpUrl
    author: GitHubUser
    committer: GitHubUser

class GitHubPushEvent(BaseModel):
    ref: str
    before: str
    after: str
    repository: GitHubRepository
    pusher: GitHubUser
    sender: GitHubUser
    created: bool
    deleted: bool
    forced: bool
    commits: List[GitHubCommit]
    head_commit: GitHubCommit
