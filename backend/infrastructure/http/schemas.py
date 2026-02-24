from pydantic import BaseModel, Field


class RunWorkflowRequest(BaseModel):
    owner: str = Field(..., min_length=1)
    repo: str = Field(..., min_length=1)
    issue_number: int = Field(..., gt=0)
    base_branch: str = Field(default="main", min_length=1)
    dry_run: bool = False


class RunWorkflowResponse(BaseModel):
    status: str
    message: str
    branch: str | None = None
    commit: str | None = None
    pr_title: str | None = None
    pr_url: str | None = None
