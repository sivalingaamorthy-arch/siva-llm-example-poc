"""How a calling agent should *use* structured errors: branch on the envelope.

Launches the server over stdio with a simulated outage, then:
  transient  -> back off and retry (bounded)
  validation -> fix the input (here: we just report it)
  anything else -> stop and explain

Run:  python examples/retry_client.py
"""

import asyncio
import os
import sys

from mcp import Client, StdioServerParameters

MAX_ATTEMPTS = 3


async def call_with_policy(client: Client, name: str, args: dict) -> None:
    for attempt in range(1, MAX_ATTEMPTS + 1):
        result = await client.call_tool(name, args)
        if not result.is_error:
            print(f"  ok after {attempt} attempt(s): {str(result.structured_content)[:90]}...")
            return
        error = (result.structured_content or {}).get("error", {})
        print(f"  attempt {attempt}: {error.get('errorCategory')} / {error.get('code')}")
        if error.get("isRetryable") and attempt < MAX_ATTEMPTS:
            await asyncio.sleep(error.get("retryAfterMs", 250) / 1000)
            continue
        print(f"  giving up -> {error.get('suggestion') or error.get('message')}")
        return


async def main() -> None:
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "health_content_mcp.server"],
        env={**os.environ, "HEALTH_MCP_FLAKY_CALLS": "2"},
    )
    async with Client(params) as client:
        print("get_article mental-01 (server is flaky for 2 calls):")
        await call_with_policy(client, "get_article", {"article_id": "mental-01"})
        print("get_article 'abc' (validation, never retried):")
        await call_with_policy(client, "get_article", {"article_id": "abc"})
        print("flag contraindicated article as editor (permission, escalate):")
        await call_with_policy(
            client,
            "flag_article",
            {"article_id": "physical-09", "reason": "intensity wording unclear", "reviewer_role": "editor"},
        )


if __name__ == "__main__":
    asyncio.run(main())
