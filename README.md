# ContextChat

An AI assistant that answers questions based **only** on documents, URLs, and MCP server data you provide — similar to ChatGPT but with a confined knowledge base.

## Features

- **Document Upload** — PDF, DOCX, TXT, MD, CSV, JSON
- **URL Scraping** — Add any web page as a knowledge source
- **MCP Server Integration** — Connect MCP servers (stdio or SSE) for product insights
- **Context-Aware Chat** — Answers are grounded in your uploaded content
- **Vector Search** — ChromaDB-powered semantic search over your documents

## Quick Start

```bash
# 1. Create a virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set your Groq API key
cp .env.example .env
# Edit .env and add your key

# 4. Run the server
make run
# Or: python run.py
```

Then open http://localhost:8000 in your browser.

## Environment Variables

| Variable | Description |
|----------|-------------|
| `GROQ_API_KEY` | Your Groq API key (required) |

## MCP Server Integration

You can connect MCP-compatible servers from the sidebar:

- **stdio transport**: Provide the command and arguments (e.g., `npx @modelcontextprotocol/server-example`)
- **SSE transport**: Provide the server URL endpoint

Once connected, the chat will automatically incorporate MCP server context into responses.

## Tech Stack

- **Backend**: FastAPI, LangChain, ChromaDB, Groq (LLaMA 3.3 70B)
- **Frontend**: Jinja2 + Vanilla JS + Custom CSS
- **Vector Store**: ChromaDB with local HuggingFace embeddings (all-MiniLM-L6-v2)
