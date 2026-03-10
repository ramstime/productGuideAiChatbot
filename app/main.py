import os
import json
from fastapi import FastAPI, Request, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.document_processor import process_uploaded_file, extract_text_from_url
from app.vector_store import add_documents, get_document_count, clear_all_documents, delete_documents_by_source
from app.chat_engine import chat, get_provider, set_provider
from app.mcp_client import mcp_client, MCPServerConfig
from app.source_store import add_source, get_all_sources, clear_all_sources, delete_source
from app.chat_store import get_chat_history, append_messages, clear_chat_history

app = FastAPI(title="ProductGuide - The AI Chatbot", version="1.0.0")

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

conversation_history: list[dict] = get_chat_history()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/chat")
async def api_chat(request: Request):
    body = await request.json()
    query = body.get("message", "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="Message is required")

    mcp_context = ""
    for server_name in mcp_client.servers:
        ctx = await mcp_client.get_server_context(server_name)
        if ctx:
            mcp_context += f"\n[Server: {server_name}]\n{ctx}\n"

    try:
        response = chat(query, conversation_history, mcp_context=mcp_context)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    conversation_history.append({"role": "user", "content": query})
    conversation_history.append({"role": "assistant", "content": response})
    append_messages(query, response)

    return JSONResponse({"response": response})


@app.post("/api/upload")
async def api_upload(files: list[UploadFile] = File(...)):
    results = []
    for file in files:
        try:
            content = await file.read()
            text, name = process_uploaded_file(file.filename, content)
            chunks_added = add_documents([text], [{"source": name, "type": "file"}])
            add_source(name=name, source_type="file", chunks=chunks_added)
            results.append({"filename": name, "chunks": chunks_added, "status": "success"})
        except Exception as e:
            results.append({"filename": file.filename, "status": "error", "error": str(e)})

    return JSONResponse({"results": results, "total_chunks": get_document_count()})


@app.post("/api/add-url")
async def api_add_url(request: Request):
    body = await request.json()
    url = body.get("url", "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")

    try:
        text, title = extract_text_from_url(url)
        chunks_added = add_documents([text], [{"source": url, "title": title, "type": "url"}])
        add_source(name=title or url, source_type="url", chunks=chunks_added, url=url)
        return JSONResponse({
            "title": title,
            "chunks": chunks_added,
            "total_chunks": get_document_count(),
            "status": "success",
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats")
async def api_stats():
    return JSONResponse({
        "document_chunks": get_document_count(),
        "conversation_length": len(conversation_history),
        "mcp_servers": len(mcp_client.servers),
        "llm_provider": get_provider(),
    })


@app.get("/api/provider")
async def api_get_provider():
    return JSONResponse({"provider": get_provider()})


@app.post("/api/provider")
async def api_set_provider(request: Request):
    body = await request.json()
    provider = body.get("provider", "").strip().lower()
    try:
        set_provider(provider)
        return JSONResponse({"provider": get_provider()})
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/sources")
async def api_sources():
    return JSONResponse({"sources": get_all_sources()})


@app.delete("/api/source/{source_name}")
async def api_delete_source(source_name: str):
    deleted = delete_source(source_name)
    if not deleted:
        raise HTTPException(status_code=404, detail="Source not found")
    delete_documents_by_source(source_name)
    return JSONResponse({"status": "deleted", "total_chunks": get_document_count()})


@app.post("/api/clear")
async def api_clear():
    global conversation_history
    conversation_history = []
    clear_all_documents()
    clear_all_sources()
    clear_chat_history()
    return JSONResponse({"status": "cleared"})


@app.get("/api/chat-history")
async def api_chat_history():
    return JSONResponse({"history": conversation_history})


@app.post("/api/clear-chat")
async def api_clear_chat():
    global conversation_history
    conversation_history = []
    clear_chat_history()
    return JSONResponse({"status": "chat_cleared"})


# ---- MCP Server Management Endpoints ----

@app.post("/api/mcp/add")
async def api_mcp_add(request: Request):
    body = await request.json()
    name = body.get("name", "").strip()
    transport = body.get("transport", "stdio").strip()

    if not name:
        raise HTTPException(status_code=400, detail="Server name is required")

    config = MCPServerConfig(
        name=name,
        command=body.get("command", ""),
        args=body.get("args", []),
        url=body.get("url", ""),
        transport=transport,
    )

    mcp_client.add_server(config)

    try:
        await mcp_client.initialize_server(name)
        await mcp_client.discover_tools(name)
        await mcp_client.discover_resources(name)
    except Exception as e:
        pass  # Server added but discovery may fail; tools/resources can be discovered later

    return JSONResponse({
        "status": "added",
        "server": {
            "name": name,
            "transport": transport,
            "tools": mcp_client.server_tools.get(name, []),
            "resources": mcp_client.server_resources.get(name, []),
        }
    })


@app.delete("/api/mcp/{server_name}")
async def api_mcp_remove(server_name: str):
    mcp_client.remove_server(server_name)
    return JSONResponse({"status": "removed"})


@app.get("/api/mcp/servers")
async def api_mcp_list():
    return JSONResponse({"servers": mcp_client.list_servers()})


@app.post("/api/mcp/{server_name}/call-tool")
async def api_mcp_call_tool(server_name: str, request: Request):
    body = await request.json()
    tool_name = body.get("tool", "")
    arguments = body.get("arguments", {})

    if not tool_name:
        raise HTTPException(status_code=400, detail="Tool name is required")

    result = await mcp_client.call_tool(server_name, tool_name, arguments)
    return JSONResponse({"result": result})


@app.post("/api/mcp/{server_name}/read-resource")
async def api_mcp_read_resource(server_name: str, request: Request):
    body = await request.json()
    uri = body.get("uri", "")

    if not uri:
        raise HTTPException(status_code=400, detail="Resource URI is required")

    result = await mcp_client.read_resource(server_name, uri)
    return JSONResponse({"result": result})


@app.post("/api/mcp/{server_name}/discover")
async def api_mcp_discover(server_name: str):
    tools = await mcp_client.discover_tools(server_name)
    resources = await mcp_client.discover_resources(server_name)
    return JSONResponse({"tools": tools, "resources": resources})
