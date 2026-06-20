from typing import Any

from pydantic import BaseModel, Field


# class RepositoryChatRequest(BaseModel):
#     query: str = Field(..., min_length=1, description="Question or task for repository intelligence.")
#     max_tool_rounds: int = Field(
#         default=5,
#         ge=1,
#         le=10,
#         description="Maximum tool-calling rounds before returning an answer.",
#     )


class ProfileChatRequest(BaseModel):
    username: str = Field(..., min_length=1, description="GitHub username to analyze.")
    query: str = Field(..., min_length=1, description="Question about the target GitHub profile.")
    max_tool_rounds: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Maximum tool-calling rounds before returning an answer.",
    )


class ToolExecution(BaseModel):
    name: str
    arguments: dict[str, Any]
    ok: bool
    content: str | None = None
    error: str | None = None


class ChatResponse(BaseModel):
    answer: str
    # tool_executions: list[ToolExecution] = Field(default_factory=list)


class UserRepoChatRequest(BaseModel):
    username: str = Field(..., min_length=1, description="Target GitHub username.")
    repository: str = Field(..., min_length=1, description="Target repository in 'owner/repo' format.")
    query: str = Field(..., min_length=1, description="Question about the user's activity in the repository.")
    max_tool_rounds: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Maximum tool-calling rounds before returning an answer.",
    )
