import json
import os
import sys
import httpx

API_URL = os.environ.get("CONTEXT_LAYER_API_URL", "http://127.0.0.1:8000/v1/mcp")
MCP_TOKEN = os.environ.get("TRULIN_MCP_TOKEN", "")


def process_line(line: str, client: httpx.Client, token: str | None = None) -> None:
    line = line.strip()
    if not line:
        return
    try:
        req = json.loads(line)
    except Exception as e:
        err_res = {
            "jsonrpc": "2.0",
            "id": None,
            "error": {"code": -32700, "message": f"Parse error: {str(e)}"}
        }
        sys.stdout.write(json.dumps(err_res) + "\n")
        sys.stdout.flush()
        return

    # Forward to Context Trust Layer MCP endpoint
    headers = {}
    effective_token = token if token is not None else MCP_TOKEN
    if effective_token:
        headers["Authorization"] = f"Bearer {effective_token}"

    try:
        res = client.post(API_URL, json=req, headers=headers, timeout=30.0)
        if res.status_code == 200:
            response_data = res.json()
        else:
            response_data = {
                "jsonrpc": "2.0",
                "id": req.get("id"),
                "error": {
                    "code": -32603,
                    "message": f"Backend HTTP error {res.status_code}: {res.text}"
                }
            }
    except Exception as e:
        response_data = {
            "jsonrpc": "2.0",
            "id": req.get("id"),
            "error": {
                "code": -32603,
                "message": f"Cannot connect to Context Trust Layer at {API_URL}. Ensure FastAPI is running on port 8000. Error: {str(e)}"
            }
        }

    sys.stdout.write(json.dumps(response_data) + "\n")
    sys.stdout.flush()


def main():
    with httpx.Client() as client:
        for line in sys.stdin:
            process_line(line, client)


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, BrokenPipeError, SystemExit):
        pass
