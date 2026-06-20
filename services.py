import asyncio
import datetime
import json
import os
from typing import Any

from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mistralai.client import Mistral

from schemas import ChatResponse, ToolExecution


load_dotenv()

MODEL_NAME = os.getenv("MISTRAL_MODEL", "mistral-large-latest")


def _github_server_params() -> StdioServerParameters:
    return StdioServerParameters(
        command="docker",
        args=[
            "run",
            "-i",
            "--rm",
            "-e",
            f"GITHUB_PERSONAL_ACCESS_TOKEN={os.getenv('GITHUB_PERSONAL_ACCESS_TOKEN')}",
            "ghcr.io/github/github-mcp-server",
        ],
        env=None,
    )


def _validate_environment() -> None:
    missing = [
        key
        for key in ("GITHUB_PERSONAL_ACCESS_TOKEN", "MISTRAL_API_KEY")
        if not os.getenv(key)
    ]
    if missing:
        joined = ", ".join(missing)
        raise RuntimeError(f"Missing required environment variable(s): {joined}")


def _format_mistral_tools(tools: list[Any]) -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.inputSchema,
            },
        }
        for tool in tools
    ]


def _parse_tool_arguments(arguments: Any) -> dict[str, Any]:
    if isinstance(arguments, str):
        return json.loads(arguments) if arguments else {}
    if isinstance(arguments, dict):
        return arguments
    return {}


def _extract_tool_content(result: Any) -> str:
    if hasattr(result, "content") and result.content:
        return "\n".join(
            item.text for item in result.content if hasattr(item, "text")
        )
    return str(result)


async def _chat_complete(client: Mistral, **kwargs: Any) -> Any:
    return await asyncio.to_thread(client.chat.complete, **kwargs)


async def _run_chat(
    *,
    system_prompt: str,
    user_query: str,
    max_tool_rounds: int,
) -> ChatResponse:
    _validate_environment()

    mistral_client = Mistral(api_key=os.getenv("MISTRAL_API_KEY"))
    messages: list[Any] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_query},
    ]
    tool_executions: list[ToolExecution] = []

    async with stdio_client(_github_server_params()) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools_list = await session.list_tools()
            mistral_tools = _format_mistral_tools(tools_list.tools)

            for _ in range(max_tool_rounds):
                response = await _chat_complete(
                    mistral_client,
                    model=MODEL_NAME,
                    messages=messages,
                    tools=mistral_tools,
                    tool_choice="auto",
                )
                assistant_message = response.choices[0].message
                tool_calls = assistant_message.tool_calls

                if not tool_calls:
                    answer = assistant_message.content or ""
                    return ChatResponse(answer=answer)

                messages.append(assistant_message)

                for tool_call in tool_calls:
                    name = tool_call.function.name
                    args = _parse_tool_arguments(tool_call.function.arguments)
                    tool_call_id = getattr(tool_call, "id", None)

                    try:
                        result = await session.call_tool(name, arguments=args)
                        raw_content = _extract_tool_content(result)
                        tool_executions.append(
                            ToolExecution(
                                name=name,
                                arguments=args,
                                ok=True,
                                content=raw_content,
                            )
                        )
                    except Exception as exc:
                        raw_content = f"Error executing tool: {exc}"
                        tool_executions.append(
                            ToolExecution(
                                name=name,
                                arguments=args,
                                ok=False,
                                error=str(exc),
                            )
                        )

                    messages.append(
                        {
                            "role": "tool",
                            "name": name,
                            "content": raw_content,
                            "tool_call_id": tool_call_id,
                        }
                    )

            response = await _chat_complete(
                mistral_client,
                model=MODEL_NAME,
                messages=[
                    *messages,
                    {
                        "role": "user",
                        "content": "Return the best possible final answer with the information already gathered.",
                    },
                ],
            )
            answer = response.choices[0].message.content or ""
            return ChatResponse(answer=answer)


# async def ask_repository_agent(query: str, max_tool_rounds: int = 5) -> ChatResponse:
#     return await _run_chat(
#         system_prompt=(
#             "You are an expert GitHub assistant. You analyze repositories on demand "
#             "using your tools. Cite repositories, files, issues, pull requests, or "
#             "commits when they support your answer."
#         ),
#         user_query=query,
#         max_tool_rounds=max_tool_rounds,
#     )


async def ask_profile_agent(
    username: str,
    query: str,
    max_tool_rounds: int = 5,
) -> ChatResponse:
    target_user = username.strip().lstrip("@")
    today_date = datetime.date.today().strftime("%B %d, %Y")
    return await _run_chat(
        system_prompt = (f"""You are an Expert GitHub Profile Analyst and Open-Source Auditor.
            Your exact target is the GitHub user: '{target_user}'.

            [TEMPORAL ANCHOR]
            The exact current date is {today_date}. Treat this as the absolute present. Anchor all relative time queries (e.g., "today", "last week", "recent") strictly against {today_date}. Do not treat this date as the future.

            [CONTRIBUTION SCOPE]
            When auditing user activity, you must actively search for and evaluate the full spectrum of GitHub contributions, including:
            1. Code: Commits, pushed branches, and releases.
            2. Collaboration: Pull Requests (opened, merged, and closed) and Code Reviews.
            3. Project Management: Issues (created, closed, and commented on) and Discussions.
            4. Ecosystem: Repositories created, forked, or starred.

            [INITIALIZATION SEQUENCE]
            When starting a session, build a profile of '{target_user}' by:
            1. Fetching their primary README from the '{target_user}/{target_user}' repository.
            2. Scanning their user bio, organizations, and pinned repositories.
            3. Fetching their recent public event stream to establish current activity levels.

            [CITATION RULES]
            Never hallucinate contributions. Every claim must be backed by data. You must explicitly cite the specific repository name, issue/PR number, or commit SHA where the activity occurred.

            [FORMATTING RULES]
            Strictly output plain text. Do not use Markdown, do not use tables, and do not use bolding. Separate items with a simple dash and use natural spacing. 

            """),
        user_query=query,
        max_tool_rounds=max_tool_rounds,
    )



async def ask_user_repo_agent(
    username: str,
    repository: str,
    query: str,
    max_tool_rounds: int = 5,
) -> ChatResponse:
    target_user = username.strip().lstrip("@")
    target_repo = repository.strip()
    today_date = datetime.date.today().strftime("%B %d, %Y")
    
    system_prompt = (f"""You are a specialized GitHub Forensics Investigator and User Activity Analyzer.
    Your exact objective is to comprehensively isolate and analyze all possible actions performed by a specific user within a targeted repository.

    [TARGET PARAMETERS]
    - Target User: '{target_user}'
    - Target Repository: '{target_repo}'

    [TEMPORAL ANCHOR]
    The exact current date is {today_date}. Treat this as the absolute present. Anchor all relative time queries strictly against this date.

    [EXECUTION STRATEGY]
    To fulfill the query, you must isolate the operations performed strictly by '{target_user}' within '{target_repo}'. Use your tools strategically across these five action vectors:

    1. Code & Contribution History:
    - Search commits authored by the target user: `repo:{target_repo} author:{target_user}`
    - Search pull requests created by the target user: `repo:{target_repo} type:pr author:{target_user}`

    2. Discussions & Issue Tracking:
    - Search issues authored or reported by the target user: `repo:{target_repo} type:issue author:{target_user}`
    - Search issues or PRs assigned to the target user: `repo:{target_repo} assignee:{target_user}`
    - Search general participation, mentions, or involvement: `repo:{target_repo} involves:{target_user}`

    3. Collaborative Feedback:
    - Search pull requests where the user acted as an official reviewer: `repo:{target_repo} type:pr reviewer:{target_user}`
    - Fetch timelines of specific PRs or Issues identified via the 'involves:' query to parse inline code comments, reactions, or discussion threads left by the user.

    4. Releases, Automations, & Packages:
    - Inspect the repository's Releases, Tags, Actions history, and Package registry to verify if '{target_user}' published versions, triggered workflows, or maintained automated deployments.

    5. Administrative & Moderation Actions (If Admin/Owner):
    - Check repository settings, branch protection rules, collaborator logs, and webhook configurations to identify governance actions performed by '{target_user}' (e.g., merging restricted PRs, changing visibility, or modifying team access).

    [CITATION & FORMATTING RULES]
    - Zero Hallucination: Every claim must be backed by data retrieved from your tools.
    - Mandatory Citations: You must explicitly cite Commit SHAs, Pull Request numbers, or Issue numbers for every operation you mention.
    - Link Enforcement: If you generate a 'Summary of Contributions' section, explicitly include the full URLs for any Pull Requests, Commits, or Issues referenced in that summary. Do not merely refer to them by their numbers.
    - Plain Text Output: Do not use Markdown tables, bolding, or headers. Output your findings as clean, readable plain text. Use standard spacing and simple dashes for lists.
    """)
    
    return await _run_chat(
        system_prompt=system_prompt,
        user_query=query,
        max_tool_rounds=max_tool_rounds,
    )