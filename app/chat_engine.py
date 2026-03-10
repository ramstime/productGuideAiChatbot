from openai import OpenAI
from app.config import (
    GROQ_API_KEY, GROQ_BASE_URL, GROQ_MODEL,
    OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL,
    LLM_PROVIDER,
)
from app.vector_store import search_documents, get_document_count

_active_provider = LLM_PROVIDER

groq_client = OpenAI(api_key=GROQ_API_KEY, base_url=GROQ_BASE_URL)
openai_client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)

SYSTEM_PROMPT = """You are a helpful assistant that answers questions based ONLY on the provided context documents. 

Rules:
1. Only answer based on the context provided below. If the context doesn't contain relevant information, say "I don't have enough information in the uploaded documents to answer that question."
2. Do NOT cite sources inline within your answer. Instead, add a single "Sources:" section at the very end listing the document names or URLs used.
3. Be concise and accurate.
4. If the user asks about something outside the uploaded context, politely redirect them to upload relevant documents or URLs first.
5. When MCP server insights are provided, incorporate them naturally into your response.
"""

NO_DOCS_PROMPT = """You are a helpful assistant. The user hasn't uploaded any documents or URLs yet. 
Politely inform them that they need to upload documents (PDF, DOCX, TXT) or provide URLs first, 
so you can answer questions based on that context. Also mention they can connect an MCP server for product insights."""


def get_provider():
    return _active_provider


def set_provider(provider: str):
    global _active_provider
    if provider not in ("openai", "groq"):
        raise ValueError(f"Unknown provider: {provider}. Use 'openai' or 'groq'.")
    _active_provider = provider


def _call_openai(messages: list[dict], temperature: float = 0.3, max_tokens: int = 2000) -> str:
    response = openai_client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content


def _call_groq(messages: list[dict], temperature: float = 0.3, max_tokens: int = 2000) -> str:
    response = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content


def build_context(query: str) -> str:
    docs = search_documents(query)
    if not docs:
        return ""

    context_parts = []
    for i, doc in enumerate(docs, 1):
        source = doc.metadata.get("source", "Unknown")
        context_parts.append(f"[Source {i}: {source}]\n{doc.page_content}")

    return "\n\n---\n\n".join(context_parts)


def chat(query: str, conversation_history: list[dict], mcp_context: str = "") -> str:
    doc_count = get_document_count()

    if doc_count == 0 and not mcp_context:
        system = NO_DOCS_PROMPT
        context_block = ""
    else:
        system = SYSTEM_PROMPT
        context_block = build_context(query)

    messages = [{"role": "system", "content": system}]

    if context_block:
        messages.append({
            "role": "system",
            "content": f"--- CONTEXT FROM UPLOADED DOCUMENTS ---\n\n{context_block}"
        })

    if mcp_context:
        messages.append({
            "role": "system",
            "content": f"--- CONTEXT FROM MCP SERVER ---\n\n{mcp_context}"
        })

    for msg in conversation_history[-10:]:
        messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({"role": "user", "content": query})

    if _active_provider == "openai":
        return _call_openai(messages)
    else:
        return _call_groq(messages)
