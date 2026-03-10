import logging
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from app.config import (
    CHROMA_PERSIST_DIR, CHUNK_SIZE, CHUNK_OVERLAP, MAX_CONTEXT_DOCS
)

logging.getLogger("sentence_transformers").setLevel(logging.WARNING)

_embeddings = None
_vector_store = None


def get_embeddings():
    global _embeddings
    if _embeddings is None:
        _embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    return _embeddings


def get_vector_store():
    global _vector_store
    if _vector_store is None:
        _vector_store = Chroma(
            persist_directory=CHROMA_PERSIST_DIR,
            embedding_function=get_embeddings(),
            collection_name="user_documents",
        )
    return _vector_store


def add_documents(texts: list[str], metadatas: list[dict] | None = None):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )
    docs = []
    for i, text in enumerate(texts):
        meta = metadatas[i] if metadatas else {}
        chunks = splitter.split_text(text)
        for chunk in chunks:
            docs.append(Document(page_content=chunk, metadata=meta))

    if not docs:
        return 0

    store = get_vector_store()
    store.add_documents(docs)
    return len(docs)


def search_documents(query: str, k: int = MAX_CONTEXT_DOCS) -> list[Document]:
    store = get_vector_store()
    try:
        results = store.similarity_search(query, k=k)
    except Exception:
        results = []
    return results


def get_document_count() -> int:
    store = get_vector_store()
    try:
        collection = store._collection
        return collection.count()
    except Exception:
        return 0


def delete_documents_by_source(source_name: str) -> bool:
    store = get_vector_store()
    try:
        collection = store._collection
        results = collection.get(where={"source": source_name})
        ids = results["ids"]
        if ids:
            collection.delete(ids=ids)
        return True
    except Exception:
        return False


def clear_all_documents():
    store = get_vector_store()
    try:
        collection = store._collection
        ids = collection.get()["ids"]
        if ids:
            collection.delete(ids=ids)
        return True
    except Exception:
        return False
