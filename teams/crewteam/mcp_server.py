"""AgentCrew MCP Server — expose crew capabilities as MCP tools."""

import json
import asyncio
from http.server import HTTPServer, BaseHTTPRequestHandler


class MCPHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length else {}

        if self.path == "/tools/list":
            self.respond(200, {
                "tools": [
                    {
                        "name": "run_crew",
                        "description": "Run an AgentCrew with specified agents and tasks",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "agents": {"type": "array", "description": "List of agent specs"},
                                "tasks": {"type": "array", "description": "List of task specs"},
                                "inputs": {"type": "object", "description": "Input variables"},
                            },
                            "required": ["agents", "tasks"],
                        },
                    },
                    {
                        "name": "list_agents",
                        "description": "List available pre-built agents",
                        "inputSchema": {"type": "object", "properties": {}},
                    },
                ]
            })
        elif self.path == "/tools/call":
            tool = body.get("name")
            args = body.get("arguments", {})

            if tool == "run_crew":
                from agentcrew.sdk import Agent, Task, Crew
                agents = {a["name"]: Agent(**a) for a in args.get("agents", [])}
                tasks = [Task(description=t["description"], agent=agents[t["agent"]]) for t in args.get("tasks", [])]
                crew = Crew(agents=list(agents.values()), tasks=tasks, verbose=True)
                result = asyncio.run(crew.kickoff(args.get("inputs", {})))
                self.respond(200, {"content": [{"type": "text", "text": json.dumps(result)}]})
            elif tool == "list_agents":
                self.respond(200, {"content": [{"type": "text", "text": "Available: researcher, writer, reviewer, coder"}]})
            else:
                self.respond(404, {"error": f"Unknown tool: {tool}"})
        else:
            self.respond(404, {"error": "Not found"})

    def respond(self, code, data):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def log_message(self, format, *args):
        pass


def start_mcp(host="0.0.0.0", port=3000):
    server = HTTPServer((host, port), MCPHandler)
    print(f"AgentCrew MCP server on {host}:{port}")
    server.serve_forever()
