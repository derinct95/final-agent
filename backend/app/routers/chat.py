from fastapi import APIRouter, Depends

from app.agent.core import run_turn
from app.auth_deps import get_current_role
from app.models import ChatRequest, ChatResponse, ToolCallLog

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(payload: ChatRequest, role: str = Depends(get_current_role)) -> ChatResponse:
    result = await run_turn([m.model_dump() for m in payload.messages], role=role)
    return ChatResponse(
        reply=result["reply"],
        toolCalls=[ToolCallLog(**tc) for tc in result["toolCalls"]],
        model=result["model"],
        available=result["available"],
    )
