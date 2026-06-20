from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse  # 1. Import this

from schemas import ChatResponse, ProfileChatRequest, UserRepoChatRequest
from services import ask_profile_agent, ask_user_repo_agent


app = FastAPI(
    title="GitHub Intelligence Agents API",
    description="HTTP API for the Repository Intelligence and Profile Analyzer agents.",
    version="1.0.0",
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


# @app.post("/repository/chat", response_model=ChatResponse)
# async def repository_chat(payload: RepositoryChatRequest) -> ChatResponse:
#     try:
#         return await ask_repository_agent(
#             query=payload.query,
#             max_tool_rounds=payload.max_tool_rounds,
#         )
#     except RuntimeError as exc:
#         raise HTTPException(status_code=500, detail=str(exc)) from exc
#     except Exception as exc:
#         raise HTTPException(
#             status_code=502,
#             detail=f"Repository agent failed: {exc}",
#         ) from exc


# @app.post("/profile/chat", response_model=ChatResponse)
# async def profile_chat(payload: ProfileChatRequest) -> ChatResponse:
#     try:
#         return await ask_profile_agent(
#             username=payload.username,
#             query=payload.query,
#             max_tool_rounds=payload.max_tool_rounds,
#         )
#     except RuntimeError as exc:
#         raise HTTPException(status_code=500, detail=str(exc)) from exc
#     except Exception as exc:
#         raise HTTPException(
#             status_code=502,
#             detail=f"Profile analyzer agent failed: {exc}",
#         ) from exc


# 2. Change the response_class to PlainTextResponse
@app.post("/profile/chat", response_class=PlainTextResponse)
async def profile_chat(payload: ProfileChatRequest):
    try:
        # Get the ChatResponse object from your service
        chat_data = await ask_profile_agent(
            username=payload.username,
            query=payload.query,
            max_tool_rounds=payload.max_tool_rounds,
        )
        
        # 3. Extract the answer and return it as raw text
        return PlainTextResponse(content=chat_data.answer)

    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Profile analyzer agent failed: {exc}",
        ) from exc
    

@app.post("/user-repo/chat", response_class=PlainTextResponse)
async def user_repo_chat(payload: UserRepoChatRequest):
    try:
        chat_data = await ask_user_repo_agent(
            username=payload.username,
            repository=payload.repository,
            query=payload.query,
            max_tool_rounds=payload.max_tool_rounds,
        )
        return PlainTextResponse(content=chat_data.answer)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"User-Repo investigator agent failed: {exc}",
        ) from exc