# IntelliBrowse

Agentic browser — describe tasks in plain English, the agent completes them autonomously.

## Quick Start

```bash
# 1. Activate the virtual environment
uv sync
source .venv/bin/activate

# 2. Install Playwright browser
playwright install chromium

# 3. Copy and fill in your API keys
cp .env.example .env
# Edit .env with your actual keys

# 4. Run the server
uvicorn intellibrowse.main:app --reload --host 0.0.0.0 --port 8000
```

## Usage
go to http://localhost:8000/

### HTTP (wait for result)
```bash
curl -X POST http://localhost:8000/task \
  -H "Content-Type: application/json" \
  -d '{"task": "Go to example.com and get the page title"}'
```

### WebSocket (stream step updates)
```python
import asyncio, json, websockets

async def main():
    async with websockets.connect("ws://localhost:8000/ws") as ws:
        await ws.send(json.dumps({"task": "Go to github.com and list my repos"}))
        async for msg in ws:
            data = json.loads(msg)
            print(data)

asyncio.run(main())
```
