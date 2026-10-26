import argparse
import asyncio
import json
from typing import Any

from mcp import Client


async def call_tool(
    server_url: str,
    tool_name: str,
    arguments: dict[str, Any],
) -> None:
    async with Client(server_url) as client:
        result = await client.call_tool(tool_name, arguments)
    print(result.model_dump_json(indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Call a tool on a POC 3 HTTP server.")
    parser.add_argument("--url", default="http://127.0.0.1:8000/mcp")
    parser.add_argument("--tool", default="bmi")
    parser.add_argument(
        "--arguments",
        default='{"weight_kg":72,"height_m":1.75}',
        help="Tool arguments as a JSON object.",
    )
    args = parser.parse_args()
    try:
        arguments = json.loads(args.arguments)
    except json.JSONDecodeError as exc:
        parser.error(f"--arguments is not valid JSON: {exc}")
    if not isinstance(arguments, dict):
        parser.error("--arguments must decode to a JSON object.")
    asyncio.run(call_tool(args.url, args.tool, arguments))


if __name__ == "__main__":
    main()
