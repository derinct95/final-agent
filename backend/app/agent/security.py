"""Deny-by-default tool lockdown for the Claude Agent SDK.

Empirically confirmed (do not remove without re-testing): setting
`allowed_tools` on ClaudeAgentOptions alone does NOT prevent execution of
Claude Code's built-in tools (Bash/Read/Write/Edit/WebFetch/etc.) -- a request
to run a shell command still executed against the host in local testing even
with `allowed_tools` scoped to a single custom MCP tool. The actual
enforcement boundary is a `PreToolUse` hook that explicitly denies anything
outside our own whitelist. This hook is what makes it safe to expose the
agent through a web-facing endpoint.
"""

MCP_SERVER_NAME = "clearview"

_TOOL_BASENAMES = [
    "search_providers",
    "get_provider_claims",
    "compare_providers",
    "summarize_department",
    "search_policy_knowledge",
    "send_email",
    "schedule_appointment",
    # Output-only tools: a structured-data "return value" for headless agent
    # tasks (Proactive Insights, Practice Review, Root-Cause Explainer) --
    # see app/agent/core.py:run_structured_task. Read-only, no DB writes.
    "record_insights",
    "record_practice_review",
    "record_root_cause",
    "record_email_draft",
]

ALLOWED_TOOL_NAMES = {f"mcp__{MCP_SERVER_NAME}__{name}" for name in _TOOL_BASENAMES}

# Same write actions gated on the REST endpoints (app/auth_deps.py) -- gated
# here too because the agent's send_email/schedule_appointment tools call
# app/db/repo.py directly and do not go through those REST routes.
WRITE_TOOL_BASENAMES = {"send_email", "schedule_appointment"}
ADMIN_ROLE = "practice_admin"


def make_pretool_hook(role: str = ADMIN_ROLE):
    """Build a PreToolUse hook bound to the caller's role for this turn --
    denies anything outside the whitelist, and additionally denies the two
    write tools unless role is practice_admin."""

    async def _deny_unlisted_or_restricted_tools(input_data, tool_use_id, context):
        tool_name = input_data.get("tool_name")
        if tool_name not in ALLOWED_TOOL_NAMES:
            return {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": f"Tool '{tool_name}' is not permitted for the Clearview agent.",
                }
            }
        short_name = tool_name.rsplit("__", 1)[-1]
        if short_name in WRITE_TOOL_BASENAMES and role != ADMIN_ROLE:
            return {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": (
                        "This account (Clinical Analyst) cannot send emails or schedule appointments -- "
                        "Practice Administrator access is required."
                    ),
                }
            }
        return {}

    return _deny_unlisted_or_restricted_tools


# Kept for any external references expecting the old static hook name (defaults to admin/full access).
deny_unlisted_tools = make_pretool_hook(ADMIN_ROLE)
