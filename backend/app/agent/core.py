"""Shared Claude Agent SDK core -- used by both the FastAPI /api/chat endpoint
and the standalone agent_cli.py, so there is exactly one agent definition.

Requires the Claude Code CLI to be available (the Python claude_agent_sdk
communicates with it under the hood) plus ANTHROPIC_API_KEY -- see README."""

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    HookMatcher,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
    query,
)

from app.agent.security import ADMIN_ROLE, ALLOWED_TOOL_NAMES, make_pretool_hook
from app.agent.tools import clearview_server

MODEL = "claude-sonnet-5"

SYSTEM_PROMPT = """You are the Clearview Medical Group AI assistant, a Claude Code-style agent embedded in a \
revenue-cycle-management provider performance dashboard. All data you can access is 100% synthetic (no real \
patient or provider PHI) -- this is a demo dataset.

Use your tools to look up real data before answering questions about specific providers, claims, comparisons, \
or departments -- do not guess or invent numbers. When a question touches on WHY a denial happens or what payer \
policy applies, use search_policy_knowledge to retrieve and cite the relevant (synthetic) policy guidance.

You can also communicate on the practice's behalf: draft and send emails to providers, and schedule/book \
appointments with one provider or a group to discuss performance. Be a proactive partner -- if you notice \
something a provider or the practice should act on, offer to draft an email or propose a meeting, but only \
actually send an email or book a meeting once the user confirms (state clearly what you are about to send/book \
before doing it, unless the user's request was already explicit and specific).

Be concise, reference concrete figures and cited policy titles from tool results, and say plainly when something \
is outside the scope of provider performance / RCM data."""


def build_options(max_turns: int = 8, role: str = ADMIN_ROLE, system_prompt: str | None = None) -> ClaudeAgentOptions:
    return ClaudeAgentOptions(
        system_prompt=system_prompt or SYSTEM_PROMPT,
        mcp_servers={"clearview": clearview_server},
        allowed_tools=list(ALLOWED_TOOL_NAMES),
        hooks={"PreToolUse": [HookMatcher(hooks=[make_pretool_hook(role)])]},
        permission_mode="default",
        model=MODEL,
        max_turns=max_turns,
    )


def format_transcript(messages: list[dict]) -> str:
    """Turn a plain {role, content} history into a single prompt. Stateless
    per HTTP request -- no server-side session plumbing -- which keeps the
    existing frontend chat contract unchanged."""
    lines = []
    for m in messages[:-1]:
        role = "User" if m["role"] == "user" else "Assistant"
        lines.append(f"{role}: {m['content']}")
    transcript = "\n".join(lines)
    last = messages[-1]["content"]
    prefix = f"Conversation so far:\n{transcript}\n\n" if transcript else ""
    return f"{prefix}User: {last}\n\nRespond to this latest message, using tools as needed."


async def run_turn(messages: list[dict], role: str = ADMIN_ROLE) -> dict:
    prompt = format_transcript(messages)
    tool_calls: list[dict] = []
    reply = ""
    try:
        async for message in query(prompt=prompt, options=build_options(role=role)):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, ToolUseBlock):
                        short_name = block.name.rsplit("__", 1)[-1]
                        tool_calls.append({"tool": short_name, "input": block.input, "summary": f"Called {short_name}"})
            if isinstance(message, ResultMessage):
                reply = message.result or ""
    except Exception as exc:  # noqa: BLE001 -- SDK/CLI errors are wide (CLINotFoundError, process errors, etc.)
        return {
            "reply": f"The AI agent is unavailable right now ({exc}). Confirm the Claude Code CLI is installed and ANTHROPIC_API_KEY is set.",
            "toolCalls": tool_calls, "model": MODEL, "available": False,
        }
    return {"reply": reply, "toolCalls": tool_calls, "model": MODEL, "available": True}


async def run_structured_task(
    prompt: str, record_tool_name: str, role: str = ADMIN_ROLE, max_turns: int = 6,
    system_prompt: str | None = None,
) -> dict | None:
    """Run a single headless agent turn instructed to investigate using its
    tools and then call `record_tool_name` exactly once as its final step.
    Returns that tool call's structured input, or None if the agent never
    calls it or the SDK/CLI errors -- callers should treat None as "fall back
    to the next tier" (single-shot Claude, then rule-based)."""
    try:
        async for message in query(prompt=prompt, options=build_options(max_turns=max_turns, role=role, system_prompt=system_prompt)):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, ToolUseBlock) and block.name.rsplit("__", 1)[-1] == record_tool_name:
                        return block.input
    except Exception:  # noqa: BLE001 -- same wide SDK/CLI error surface as run_turn
        return None
    return None
