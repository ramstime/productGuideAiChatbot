import json
import subprocess
import asyncio
import httpx
from dataclasses import dataclass, field


@dataclass
class MCPServerConfig:
    name: str
    command: str = ""
    args: list[str] = field(default_factory=list)
    url: str = ""
    transport: str = "stdio"  # "stdio" or "sse"


class MCPClient:
    def __init__(self):
        self.servers: dict[str, MCPServerConfig] = {}
        self.server_tools: dict[str, list[dict]] = {}
        self.server_resources: dict[str, list[dict]] = {}

    def add_server(self, config: MCPServerConfig):
        self.servers[config.name] = config

    def remove_server(self, name: str):
        self.servers.pop(name, None)
        self.server_tools.pop(name, None)
        self.server_resources.pop(name, None)

    def list_servers(self) -> list[dict]:
        result = []
        for name, cfg in self.servers.items():
            result.append({
                "name": name,
                "transport": cfg.transport,
                "command": cfg.command,
                "url": cfg.url,
                "tools": self.server_tools.get(name, []),
                "resources": self.server_resources.get(name, []),
            })
        return result

    async def _stdio_request(self, config: MCPServerConfig, method: str, params: dict | None = None) -> dict:
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
        }
        if params:
            request["params"] = params

        cmd = [config.command] + config.args
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        input_data = json.dumps(request) + "\n"
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(input=input_data.encode()),
            timeout=30
        )

        output = stdout.decode().strip()
        if not output:
            raise RuntimeError(f"MCP server returned empty response. stderr: {stderr.decode()}")

        for line in output.splitlines():
            line = line.strip()
            if line.startswith("{"):
                return json.loads(line)

        raise RuntimeError(f"No valid JSON response from MCP server. Output: {output}")

    async def _sse_request(self, config: MCPServerConfig, method: str, params: dict | None = None) -> dict:
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
        }
        if params:
            request["params"] = params

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(config.url, json=request)
            resp.raise_for_status()
            return resp.json()

    async def _send_request(self, server_name: str, method: str, params: dict | None = None) -> dict:
        config = self.servers.get(server_name)
        if not config:
            raise ValueError(f"Server '{server_name}' not found")

        if config.transport == "stdio":
            return await self._stdio_request(config, method, params)
        elif config.transport == "sse":
            return await self._sse_request(config, method, params)
        else:
            raise ValueError(f"Unsupported transport: {config.transport}")

    async def initialize_server(self, server_name: str) -> dict:
        result = await self._send_request(server_name, "initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "product-sphere", "version": "1.0.0"}
        })
        return result

    async def discover_tools(self, server_name: str) -> list[dict]:
        try:
            result = await self._send_request(server_name, "tools/list")
            tools = result.get("result", {}).get("tools", [])
            self.server_tools[server_name] = tools
            return tools
        except Exception as e:
            return [{"error": str(e)}]

    async def discover_resources(self, server_name: str) -> list[dict]:
        try:
            result = await self._send_request(server_name, "resources/list")
            resources = result.get("result", {}).get("resources", [])
            self.server_resources[server_name] = resources
            return resources
        except Exception as e:
            return [{"error": str(e)}]

    async def call_tool(self, server_name: str, tool_name: str, arguments: dict | None = None) -> str:
        try:
            result = await self._send_request(server_name, "tools/call", {
                "name": tool_name,
                "arguments": arguments or {}
            })
            content = result.get("result", {}).get("content", [])
            text_parts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_parts.append(item["text"])
                elif isinstance(item, str):
                    text_parts.append(item)
            return "\n".join(text_parts) if text_parts else json.dumps(result)
        except Exception as e:
            return f"Error calling tool '{tool_name}': {str(e)}"

    async def read_resource(self, server_name: str, uri: str) -> str:
        try:
            result = await self._send_request(server_name, "resources/read", {"uri": uri})
            contents = result.get("result", {}).get("contents", [])
            text_parts = []
            for item in contents:
                if isinstance(item, dict):
                    text_parts.append(item.get("text", json.dumps(item)))
                else:
                    text_parts.append(str(item))
            return "\n".join(text_parts) if text_parts else json.dumps(result)
        except Exception as e:
            return f"Error reading resource '{uri}': {str(e)}"

    async def get_server_context(self, server_name: str) -> str:
        parts = []
        tools = self.server_tools.get(server_name, [])
        if tools:
            tool_desc = []
            for t in tools:
                if isinstance(t, dict) and "name" in t:
                    desc = t.get("description", "No description")
                    tool_desc.append(f"- {t['name']}: {desc}")
            if tool_desc:
                parts.append("Available MCP Tools:\n" + "\n".join(tool_desc))

        resources = self.server_resources.get(server_name, [])
        if resources:
            res_desc = []
            for r in resources:
                if isinstance(r, dict) and "uri" in r:
                    name = r.get("name", r["uri"])
                    res_desc.append(f"- {name}: {r['uri']}")
            if res_desc:
                parts.append("Available MCP Resources:\n" + "\n".join(res_desc))

        return "\n\n".join(parts) if parts else ""


mcp_client = MCPClient()
