from __future__ import annotations

import asyncio
import os

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main() -> None:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    parameters = StdioServerParameters(
        command=os.path.join(root, ".venv", "Scripts", "python.exe"),
        args=["-m", "windows_ui.server"],
        cwd=root,
        env={**os.environ, "WINDOWS_UI_ROOT": root},
    )
    async with stdio_client(parameters) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            await asyncio.wait_for(session.initialize(), 10)
            tools = await asyncio.wait_for(session.list_tools(), 10)
            print("TOOLS", [tool.name for tool in tools.tools], flush=True)
            status = await asyncio.wait_for(session.call_tool("desktop_control_status", {}), 10)
            print("STATUS", status.isError, status.content[0].text[:300], flush=True)
            windows = await asyncio.wait_for(session.call_tool("desktop_list_windows", {}), 10)
            print("WINDOWS", windows.isError, windows.content[0].text[:100], flush=True)
            shot = await asyncio.wait_for(session.call_tool("desktop_screenshot", {
                "target": "region",
                "region": {"left": 0, "top": 0, "width": 320, "height": 200},
                "format": "jpeg",
                "quality": 40,
            }), 10)
            print("SHOT", shot.isError, [(item.type, len(getattr(item, "data", "")) if item.type == "image" else len(item.text)) for item in shot.content], flush=True)


if __name__ == "__main__":
    asyncio.run(main())
