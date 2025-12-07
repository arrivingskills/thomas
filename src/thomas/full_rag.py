import os
from pathlib import Path
from typing import List, Optional, Tuple
import re
import json
import http.client
from urllib.parse import urlparse
import http.client
from urllib.parse import urlparse

# ---------------- ChromaDB configuration (persistent by default) ----------------
# Defaults align to project root data/chroma, with optional env overrides.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PATH", str((_PROJECT_ROOT / "data" / "chroma").resolve()))
CHROMA_COLLECTION_NAME = os.getenv("CHROMA_COLLECTION", "documents")

def _get_chroma_client_and_collection():
    """
    Initialize a persistent Chroma client and return (client, collection).
    Uses CHROMA_PATH and CHROMA_COLLECTION env vars if set; otherwise defaults.
    """
    # Lazy import to keep optional dependency
    try:
        import chromadb  # type: ignore
        from chromadb.config import Settings  # type: ignore
    except Exception as ex:
        raise RuntimeError(
            "ChromaDB is required. Install with 'pip install chromadb' in your virtualenv.'"
        ) from ex

    Path(CHROMA_PERSIST_DIR).mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(
        path=CHROMA_PERSIST_DIR,
        settings=Settings(anonymized_telemetry=False)
    )
    # Prefer get_or_create_collection when available for robustness
    try:
        get_or_create = getattr(client, "get_or_create_collection")
        collection = get_or_create(name=CHROMA_COLLECTION_NAME, metadata={"hnsw:space": "cosine"})
    except Exception:
        try:
            collection = client.get_collection(CHROMA_COLLECTION_NAME)
        except Exception:
            collection = client.create_collection(name=CHROMA_COLLECTION_NAME, metadata={"hnsw:space": "cosine"})
    return client, collection

# ---------------- Ollama configuration (no env vars) ----------------
OLLAMA_BASE_URL = "http://127.0.0.1:11434"
# Use a valid published model tag. Common options: "llama3.1", "llama3.1:8b", "llama3.1:latest",
# "mistral:7b", "qwen2.5:7b", "phi3:3.8b".
OLLAMA_MODEL = "llama3.1"  # changed from "llama3.1:8b-instruct" which does not exist
OLLAMA_ENABLED = False
OLLAMA_TIMEOUT_SECONDS = 600

def discover_source_files(root_path: str) -> List[str]:
    allowed_exts = {".doc", ".docx", ".pdf", ".txt", ".rtf"}

    root = Path(root_path).expanduser().resolve()
    if not root.exists():
        raise ValueError(f"Path does not exist: {root_path}")
    if not root.is_dir():
        raise ValueError(f"Path is not a directory: {root_path}")

    results: List[str] = []

    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        for name in filenames:
            ext = Path(name).suffix.lower()
            if ext in allowed_exts:
                full_path = Path(dirpath) / name
                try:
                    abs_path = full_path.resolve(strict=False)
                except Exception:
                    abs_path = full_path.absolute()
                results.append(str(abs_path))

    return results


def _extract_text_from_pdf(path: str) -> str:
    """Extract text from a PDF using available backends.

    We attempt pypdf first (modern fork of PyPDF2), then PyPDF2 if available.
    If neither is installed, we raise a clear error explaining how to install.
    """
    try:
        from pypdf import PdfReader  # type: ignore

        text_parts: List[str] = []
        reader = PdfReader(path)
        for i, page in enumerate(reader.pages):
            try:
                page_text = page.extract_text() or ""
            except Exception:
                page_text = ""
            if page_text:
                text_parts.append(page_text)
        return "\n".join(text_parts).strip()
    except Exception:
        pass

    try:
        from PyPDF2 import PdfReader  # type: ignore

        text_parts2: List[str] = []
        reader2 = PdfReader(path)
        for i, page in enumerate(reader2.pages):
            try:
                page_text2 = page.extract_text() or ""
            except Exception:
                page_text2 = ""
            if page_text2:
                text_parts2.append(page_text2)
        return "\n".join(text_parts2).strip()
    except Exception as e:
        raise RuntimeError(
            "No PDF parser available. Install 'pypdf' (preferred) or 'PyPDF2'."
        ) from e


def _default_input_dir() -> Path:
    module_dir = Path(__file__).resolve().parent
    project_root = module_dir.parent.parent
    return (project_root / "data" / "input").resolve()

def _clean_extracted_text(text: str, keep_punctuation: bool = True) -> str:
    t = text.replace("\r\n", "\n").replace("\r", "\n")
    t = t.replace("\u00AD", "").replace("\u200B", "").replace("\u200C", "").replace("\u200D", "")
    t = re.sub(r"-\s*\n\s*", "", t)
    t = t.replace("\n\n", "<P>")
    t = re.sub(r"[ \t]*\n[ \t]*", " ", t)

    def _collapse_spaces(m: re.Match) -> str:
        return re.sub(r"\s+", "", m.group(0))

    t = re.sub(r"(h\s*t\s*t\s*p\s*s?\s*:\s*/\s*/[^ \t<>)]+)", _collapse_spaces, t, flags=re.IGNORECASE)
    t = re.sub(r"(d\s*o\s*i\s*[:.]?\s*10\.[^ \t<>)]+)", _collapse_spaces, t, flags=re.IGNORECASE)
    t = re.sub(r"(10\.\d{4,}/[^ \t<>)]+)", _collapse_spaces, t)
    t = re.sub(r"([A-Za-z0-9-]+\s*\.\s*[A-Za-z0-9.-]+\s*/[^ \t<>)]*)", _collapse_spaces, t)

    t = re.sub(r"[ \t]+", " ", t).strip()
    # Replace preserved paragraph markers with a single space to remove all newlines
    t = t.replace("<P>", " ")

    if not keep_punctuation:
        t = re.sub(r"[^\w\s]", " ", t)
        t = re.sub(r"\s+", " ", t)
        t = re.sub(r"(\s*\n\s*)+", "\n", t).strip()

    return t



def _ollama_request(method: str, path: str, body: Optional[dict] = None) -> Tuple[int, str]:
    """Minimal HTTP client for Ollama without external deps."""
    url = urlparse(OLLAMA_BASE_URL)
    conn_cls = http.client.HTTPSConnection if url.scheme == "https" else http.client.HTTPConnection
    conn = conn_cls(url.hostname, url.port or (443 if url.scheme == "https" else 80), timeout=OLLAMA_TIMEOUT_SECONDS)
    try:
        payload = None
        headers = {"Content-Type": "application/json"}
        if body is not None:
            payload = json.dumps(body).encode("utf-8")
        conn.request(method, path, body=payload, headers=headers)
        resp = conn.getresponse()
        data = resp.read()
        return resp.status, data.decode("utf-8", errors="replace")
    finally:
        conn.close()

# Streamed pull to avoid timeouts on large downloads
def _ollama_pull_stream(model: str) -> bool:
    url = urlparse(OLLAMA_BASE_URL)
    conn_cls = http.client.HTTPSConnection if url.scheme == "https" else http.client.HTTPConnection
    conn = conn_cls(url.hostname, url.port or (443 if url.scheme == "https" else 80), timeout=OLLAMA_TIMEOUT_SECONDS)
    try:
        payload = json.dumps({"name": model, "stream": True}).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        conn.request("POST", "/api/pull", body=payload, headers=headers)
        resp = conn.getresponse()
        if resp.status not in (200, 206):
            data = resp.read().decode("utf-8", errors="replace")
            print(f"[prepare_data] Ollama pull failed ({resp.status}): {data[:200]}")
            return False
        # Read streaming JSONL chunks until 'status'=='success' or 'completed'
        buf = b""
        while True:
            chunk = resp.read(8192)
            if not chunk:
                break
            buf += chunk
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line.decode("utf-8", errors="replace"))
                except Exception:
                    continue
                # Optional progress logging
                if "status" in obj:
                    st = obj.get("status", "")
                    pct = obj.get("completed", 0)
                    total = obj.get("total", 0)
                    if total:
                        print(f"[prepare_data] Pull: {st} {pct}/{total}")
                    else:
                        print(f"[prepare_data] Pull: {st}")
                if obj.get("status") in ("success", "completed"):
                    return True
        # If stream ended without explicit success, check availability
        return _ollama_model_available(model)
    except Exception as ex:
        print(f"[prepare_data] Ollama streamed pull error: {ex}")
        return False
    finally:
        conn.close()

def _ollama_model_available(model: str) -> bool:
    status, data = _ollama_request("GET", "/api/tags")
    if status != 200:
        print(f"[prepare_data] Ollama /api/tags returned {status}; response: {data[:200]}")
        return False
    try:
        obj = json.loads(data)
        models = obj.get("models", [])
        names = {m.get("name") for m in models if isinstance(m, dict)}
        return model in names
    except Exception as ex:
        print(f"[prepare_data] Failed to parse /api/tags: {ex}")
        return False

def _ollama_generate(prompt: str, model: str) -> str:
    """Call Ollama /api/generate with stream disabled and parse the response.

    Returns the generated text. Raises RuntimeError if HTTP status is not 200.
    Tries to handle both single-JSON and JSONL (stream-like) responses.
    """
    body = {"model": model, "prompt": prompt, "stream": False}
    status, data = _ollama_request("POST", "/api/generate", body)
    if status != 200:
        raise RuntimeError(f"Ollama generate failed ({status}): {data[:200]}")
    # First try single JSON
    try:
        obj = json.loads(data)
        if isinstance(obj, dict) and "response" in obj:
            return str(obj.get("response", ""))
    except Exception:
        pass
    # Fallback: parse as JSONL (concatenate 'response' fragments)
    out = []
    for line in data.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            part = json.loads(line)
            resp = part.get("response")
            if resp:
                out.append(str(resp))
        except Exception:
            continue
    if out:
        return "".join(out)
    # As a last resort, return raw data
    return data

# Try pull with stream first, then non-stream as fallback
def _ollama_try_pull_model(model: str) -> bool:
    if _ollama_pull_stream(model):
        return True
    status, data = _ollama_request("POST", "/api/pull", {"name": model, "stream": False})
    if status == 200:
        return True
    print(f"[prepare_data] Ollama pull failed ({status}): {data[:200]}")
    return False

def _ollama_clean_text(raw_text: str) -> str:
    if not OLLAMA_ENABLED:
        return raw_text

    # Hard cap input size to reduce timeouts
    MAX_CHARS = 20000
    text_for_llm = raw_text[:MAX_CHARS]

    system_guidance = (
        "You are a text cleanup assistant. Clean the following extracted PDF text:\n"
        "- Repair broken URLs/DOIs/emails by removing internal spaces.\n"
        "- Remove hyphenation at line breaks, zero-width/soft characters.\n"
        "- Normalize whitespace, unwrap lines while preserving paragraphs.\n"
        "- Do not hallucinate; keep original wording/content. Only fix formatting.\n"
    )
    prompt = f"{system_guidance}\n=== BEGIN TEXT ===\n{text_for_llm}\n=== END TEXT ===\nReturn only the cleaned text."

    # Try once, then fall back; do not pre-check availability or pull
    try:
        cleaned = _ollama_generate(prompt, OLLAMA_MODEL).strip()
        if cleaned:
            return cleaned
    except Exception as ex:
        print(f"[prepare_data] Ollama cleaning failed (skipping LLM): {ex}")

    return raw_text

def load_source_data(data_files: Optional[List[str]] = None) -> List[Tuple[str, str]]:
    """Load and parse source data files.

    - If data_files is None, discover files under default input dir.
    - Only PDF files are parsed here; others are ignored.
    - Returns a list of (path, text) tuples for successfully parsed PDFs.
    """
    if data_files is None:
        input_dir = _default_input_dir()
        discovered = discover_source_files(str(input_dir))
        data_files = [p for p in discovered if Path(p).suffix.lower() == ".pdf"]

    results: List[Tuple[str, str]] = []
    for file_path in data_files:
        ext = Path(file_path).suffix.lower()
        if ext != ".pdf":
            continue
        try:
            text = _extract_text_from_pdf(file_path)
        except Exception as ex:
            print(f"[prepare_data] Failed to parse PDF {file_path}: {ex}")
            text = ""
        pre_clean = _clean_extracted_text(text, keep_punctuation=True)
        llm_clean = _ollama_clean_text(pre_clean)
        results.append((file_path, llm_clean))

    return results



def _estimate_tokens(text: str) -> int:
    # Rough heuristic: ~4 chars per token for English
    return max(1, (len(text) + 3) // 4)


def _split_into_sentences(text: str) -> List[str]:
    # Hint section headers to become boundaries
    section_words = [
        "ABSTRACT", "Abstract", "INTRODUCTION", "Introduction", "BACKGROUND", "Background",
        "METHODS", "Methods", "MATERIALS", "Materials", "RESULTS", "Results",
        "DISCUSSION", "Discussion", "CONCLUSION", "Conclusions", "Conclusion",
        "ACKNOWLEDGEMENTS", "Acknowledgements", "REFERENCES", "References"
    ]
    for w in section_words:
        text = re.sub(rf"\b{re.escape(w)}\b\s*:?\s*", f"{w}. ", text)
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()
    # Split on sentence enders followed by space and a capital/number
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\(])", text)
    # Post-trim
    return [p.strip() for p in parts if p and p.strip()]


essential_section_titles = {
    "abstract", "introduction", "background", "methods", "materials", "results",
    "discussion", "conclusion", "conclusions", "acknowledgements", "references"
}


def _semantic_chunks_from_sentences(
    sentences: List[str],
    target_tokens: int = 350,
    max_tokens: int = 500,
    overlap_tokens: int = 50,
) -> List[str]:
    chunks: List[str] = []
    if not sentences:
        return chunks

    current: List[str] = []
    current_tok = 0

    def flush_current():
        nonlocal current, current_tok
        if not current:
            return
        chunk_text = " ".join(current).strip()
        chunks.append(chunk_text)
        # Build overlap window by taking trailing sentences up to overlap_tokens
        overlap: List[str] = []
        tok = 0
        for s in reversed(current):
            tok += _estimate_tokens(s) + 1
            overlap.append(s)
            if tok >= overlap_tokens:
                break
        current = list(reversed(overlap))
        current_tok = sum(_estimate_tokens(s) + 1 for s in current)

    for s in sentences:
        s_tok = _estimate_tokens(s)
        if s_tok >= max_tokens:
            # Split this long sentence by words
            words = s.split()
            approx_words_per_chunk = max_tokens * 4 // 5  # ~80% of max in words heuristically
            if approx_words_per_chunk <= 0:
                approx_words_per_chunk = len(words)
            step = max(1, approx_words_per_chunk - max(5, overlap_tokens))
            i = 0
            while i < len(words):
                piece_words = words[i:i + approx_words_per_chunk]
                piece = " ".join(piece_words)
                if current_tok + _estimate_tokens(piece) > max_tokens:
                    flush_current()
                current.append(piece)
                current_tok += _estimate_tokens(piece) + 1
                if current_tok >= target_tokens:
                    flush_current()
                i += step
            continue

        if current_tok + s_tok <= max_tokens:
            current.append(s)
            current_tok += s_tok + 1
            if current_tok >= target_tokens:
                flush_current()
        else:
            flush_current()
            # After overlap, try to add the sentence (may flush again if still too big)
            if _estimate_tokens(s) > max_tokens:
                # already handled by branch above, but keep guard
                words = s.split()
                for i in range(0, len(words), max(1, max_tokens - overlap_tokens)):
                    piece = " ".join(words[i:i + max(1, max_tokens - overlap_tokens)])
                    current.append(piece)
                    current_tok += _estimate_tokens(piece) + 1
                    if current_tok >= target_tokens:
                        flush_current()
            else:
                current.append(s)
                current_tok += _estimate_tokens(s) + 1
                if current_tok >= target_tokens:
                    flush_current()

    # flush remainder
    if current:
        chunks.append(" ".join(current).strip())

    return chunks


def prepare_data() -> bool:
    """Orchestrate preparation pipeline.

    - Loads and chunks data, writes data/output/chunks.jsonl
    - Inserts chunks into ChromaDB (single insertion path)
    Returns False on failure.
    """
    try:
        ok = chunk_data()
        return bool(ok)
    except Exception as ex:
        print(f"[prepare_data] prepare_data failed: {ex}")
        return False


def chunk_data() -> bool:
    """
    Create semantic chunks from source documents and persist them to ChromaDB.

    This uses sentence-aware semantic chunking with overlap instead of fixed-size
    word windows, so related sentences stay together. Results are upserted into
    a persistent Chroma collection.
    """
    try:
        client, collection = _get_chroma_client_and_collection()
    except Exception as ex:
        print(f"[prepare_data] Chroma init failed: {ex}")
        return False

    # Load and clean data first
    input_dir = _default_input_dir()
    try:
        files = discover_source_files(str(input_dir))
    except ValueError as e:
        print(f"[prepare_data] {e}")
        return False
    pdfs = [p for p in files if Path(p).suffix.lower() == ".pdf"]
    items = load_source_data(pdfs)

    # Semantic chunking parameters (token heuristics)
    TARGET_TOKENS = 350
    MAX_TOKENS = 500
    OVERLAP_TOKENS = 50

    ids: List[str] = []
    documents: List[str] = []
    metadatas: List[dict] = []

    # Determine starting sequential ID by current collection size (best-effort)
    next_id_int = 0
    try:
        # collection.count() is available in recent versions; fallback to 0
        count_fn = getattr(collection, "count", None)
        if callable(count_fn):
            next_id_int = int(count_fn() or 0)
    except Exception:
        next_id_int = 0

    for doc_index, (path_str, text) in enumerate(items):
        if not text:
            continue
        sentences = _split_into_sentences(text)
        chunks = _semantic_chunks_from_sentences(
            sentences,
            target_tokens=TARGET_TOKENS,
            max_tokens=MAX_TOKENS,
            overlap_tokens=OVERLAP_TOKENS,
        )
        for chunk_idx, chunk_text in enumerate(chunks):
            if not chunk_text:
                continue
            # Sequential integer ID scheme as strings: "0", "1", ...
            doc_id = str(next_id_int)
            next_id_int += 1
            ids.append(doc_id)
            documents.append(chunk_text)
            metadatas.append({
                "source": path_str,
                "chunk_index": chunk_idx,
                "doc_index": doc_index,
                "tokens": _estimate_tokens(chunk_text),
                "filename": str(Path(path_str).name),
            })

    # Write chunks to JSONL for downstream steps (e.g., generate_metadatas)
    try:
        module_dir = Path(__file__).resolve().parent
        project_root = module_dir.parent.parent
        out_dir = (project_root / "data" / "output").resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "chunks.jsonl"
        with out_path.open("w", encoding="utf-8") as f:
            for _id, m, doc in zip(ids, metadatas, documents):
                row = {
                    "id": _id,
                    "source": m.get("source", ""),
                    "doc_index": m.get("doc_index", 0),
                    "chunk_index": m.get("chunk_index", 0),
                    "text": doc,
                    "tokens": m.get("tokens", _estimate_tokens(doc)),
                }
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception as ex:
        print(f"[prepare_data] Failed to write chunks.jsonl: {ex}")

    if not documents:
        print("[prepare_data] No chunks created.")
        # Even if no documents, initialize Chroma and write a sentinel to force DB creation
        try:
            client, collection = _get_chroma_client_and_collection()
            sentinel_id = "__init__"
            sentinel_doc = "chroma-initialization-sentinel"
            sentinel_meta = {"type": "init", "note": "created from chunk_data when no documents"}
            try:
                collection.add(ids=[sentinel_id], documents=[sentinel_doc], metadatas=[sentinel_meta])
                print(f"[prepare_data] Wrote sentinel to Chroma to force DB creation at {CHROMA_PERSIST_DIR}.")
            except Exception as ex2:
                if "embedding" in str(ex2).lower():
                    collection.add(
                        ids=[sentinel_id],
                        documents=[sentinel_doc],
                        metadatas=[sentinel_meta],
                        embeddings=[_cheap_embedding(sentinel_doc)],
                    )
                    print("[prepare_data] Wrote sentinel with fallback embedding to initialize DB.")
                else:
                    print(f"[prepare_data] Failed to write sentinel to Chroma: {ex2}")
            try:
                persist_fn = getattr(client, "persist", None)
                if callable(persist_fn):
                    persist_fn()
                    print(f"[prepare_data] Chroma client.persist() called for path: {CHROMA_PERSIST_DIR}")
            except Exception:
                pass
        except Exception:
            # As a last resort, ensure the path exists
            try:
                Path(CHROMA_PERSIST_DIR).mkdir(parents=True, exist_ok=True)
            except Exception:
                pass
        return False

    # Upsert into Chroma (persisted by default)
    try:
        # Batch in reasonable sizes to avoid large payloads
        BATCH = 256
        for i in range(0, len(documents), BATCH):
            try:
                collection.upsert(
                    ids=ids[i:i+BATCH],
                    documents=documents[i:i+BATCH],
                    metadatas=metadatas[i:i+BATCH],
                )
            except Exception as batch_ex:
                # Provide fallback embeddings if Chroma requires them
                if "embedding" in str(batch_ex).lower():
                    print("[prepare_data] Chroma requires embeddings for upsert; using fallback vectors.")
                    embeddings = [_cheap_embedding(t) for t in documents[i:i+BATCH]]
                    collection.upsert(
                        ids=ids[i:i+BATCH],
                        documents=documents[i:i+BATCH],
                        metadatas=metadatas[i:i+BATCH],
                        embeddings=embeddings,
                    )
                else:
                    raise
        print(f"[prepare_data] Persisted {len(documents)} semantic chunks to Chroma collection '{CHROMA_COLLECTION_NAME}' at {CHROMA_PERSIST_DIR}")
        # Ensure persistence is flushed to disk if the client supports it
        try:
            persist_fn = getattr(client, "persist", None)
            if callable(persist_fn):
                persist_fn()
                print(f"[prepare_data] Chroma client.persist() called for path: {CHROMA_PERSIST_DIR}")
        except Exception:
            pass
        return True
    except Exception as ex:
        print(f"[prepare_data] Failed to upsert chunks to Chroma: {ex}")
        return False

def _ensure_chunks_file() -> Path:
    """Ensure chunks.jsonl exists by running chunk_data() if needed.

    Returns the path to the chunks.jsonl file (regardless of whether it existed
    already or was just created).
    """
    module_dir = Path(__file__).resolve().parent
    project_root = module_dir.parent.parent
    out_dir = (project_root / "data" / "output").resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "chunks.jsonl"
    if not out_path.exists():
        # Generate chunks file
        try:
            chunk_data()
        except Exception as ex:
            print(f"[prepare_data] chunk_data failed while ensuring chunks file: {ex}")
        # Even if chunk_data failed, return the path; caller will handle absence
    return out_path


def _load_chunks_from_jsonl(chunks_path: Path) -> Tuple[List[str], List[str], List[dict]]:
    """Load chunk rows from JSONL and produce ids, documents, metadatas.

    Each JSONL line is expected to have: id, source, doc_index, chunk_index, text, tokens.
    Fallback to synthesized ids if "id" is missing.
    """
    ids: List[str] = []
    documents: List[str] = []
    metadatas: List[dict] = []
    if not chunks_path.exists():
        return ids, documents, metadatas
    with chunks_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            text = obj.get("text", "")
            src = obj.get("source", "")
            di = int(obj.get("doc_index", 0))
            ci = int(obj.get("chunk_index", 0))
            tok = int(obj.get("tokens", _estimate_tokens(text)))
            cid = str(obj.get("id")) if obj.get("id") is not None else f"doc{di}_chunk{ci}"
            ids.append(cid)
            documents.append(text)
            # Minimal, Chroma-friendly metadata
            metadatas.append({
                "source": src,
                "doc_index": di,
                "chunk_index": ci,
                "tokens": tok,
                # Shallow filename for convenience
                "filename": str(Path(src).name) if src else "",
            })
    return ids, documents, metadatas


def _cheap_embedding(text: str, dim: int = 64) -> List[float]:
    """Deterministic, cheap embedding to satisfy Chroma when no embedder is set.

    Not semantically meaningful; only used as a fallback to allow .add().
    """
    # Simple rolling hash into fixed-size vector
    vec = [0.0] * dim
    if not text:
        return vec
    for i, ch in enumerate(text):
        idx = (ord(ch) + i) % dim
        vec[idx] += (ord(ch) % 53) / 53.0
    # Normalize
    norm = sum(v * v for v in vec) ** 0.5
    if norm > 0:
        vec = [v / norm for v in vec]
    return vec


def generate_metadatas() -> bool:
    """Generate JSONL metadata only (no Chroma insertion).

    - Ensures chunks.jsonl exists (calls chunk_data() if necessary).
    - Loads ids, documents, metadatas from JSONL so other steps can consume them.
    - Does NOT write to ChromaDB to enforce a single insertion path via chunk_data().
    """
    try:
        print("Genrating embeddings")
        chunks_path = _ensure_chunks_file()
        ids, documents, metadatas = _load_chunks_from_jsonl(chunks_path)
        if not ids:
            print("[prepare_data] No chunks found in JSONL. Run chunk_data() to generate.")
        else:
            print(f"[prepare_data] Loaded {len(ids)} chunks from {chunks_path} (metadata only, no DB writes).")
        return True
    except Exception as ex:
        print(f"[prepare_data] generate_metadatas failed: {ex}")
        return False


def apply_embedding() -> bool:
    """
    Placeholder: if you plan to use external embeddings, integrate here.
    Chroma can also generate embeddings via an embedding function; this default uses raw documents.
    """
    return True

def apply_retrieval(query: str) -> bool:
    """
    Basic retrieval from persisted Chroma collection.
    """
    try:
        print("Applying retrievals")
        _, collection = _get_chroma_client_and_collection()
    except Exception as ex:
        print(f"[prepare_data] Chroma init failed: {ex}")
        return False
    try:
        res = collection.query(query_texts=[query], n_results=5)
        print(f"[prepare_data] Retrieval results: {res}")
        return True
    except Exception as ex:
        print(f"[prepare_data] Retrieval failed: {ex}")
        return False


def interactive_qa(top_k: int = 5, max_context_chars: int = 8000) -> None:
    """
    Interactive Q&A loop:
    - Prompts the user for a question (stdin) until the user types q/quit/exit or empty line.
    - Retrieves top_k chunks from Chroma.
    - Sends a strictly context-grounded prompt to Ollama to answer using ONLY the retrieved context.
    - Prints the answer and lightweight source citations.

    This function assumes a local Ollama server (OLLAMA_BASE_URL) and a model tag in OLLAMA_MODEL.
    It gracefully degrades if Ollama is unavailable by printing the retrieved context.
    """
    try:
        _, collection = _get_chroma_client_and_collection()
    except Exception as ex:
        print(f"[qa] Failed to init Chroma: {ex}")
        return

    print("[qa] Interactive Q&A. Ask a question, or type 'q' to quit.")
    while True:
        try:
            question = input("question> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not question or question.lower() in {"q", "quit", "exit"}:
            break

        # Query Chroma first; try text-based, then fallback to cheap embedding.
        try:
            res = collection.query(query_texts=[question], n_results=top_k, include=["documents", "metadatas", "distances"])  # type: ignore
        except Exception as ex:
            if "embedding" in str(ex).lower():
                try:
                    q_emb = [_cheap_embedding(question)]
                    res = collection.query(query_embeddings=q_emb, n_results=top_k, include=["documents", "metadatas", "distances"])  # type: ignore
                except Exception as ex2:
                    print(f"[qa] Retrieval failed: {ex2}")
                    continue
            else:
                print(f"[qa] Retrieval failed: {ex}")
                continue

        ids = (res.get("ids") or [[]])[0]
        docs = (res.get("documents") or [[]])[0]
        metas = (res.get("metadatas") or [[]])[0]
        dists = (res.get("distances") or [[]])[0]

        if not ids:
            print("[qa] No results found in Chroma for your question.")
            continue

        # Build a compact context with filenames and chunk indices.
        context_parts = []
        used_citations = []  # (filename, chunk_index)
        total = 0
        for i in range(len(ids)):
            meta = metas[i] if i < len(metas) else {}
            filename = (meta or {}).get("filename") or (meta or {}).get("source") or ""
            chunk_index = (meta or {}).get("chunk_index")
            doc_text = (docs[i] or "")
            snippet = doc_text.replace("\n", " ")
            # Truncate overly long snippets to keep prompt size reasonable
            if len(snippet) > 1200:
                snippet = snippet[:1200] + "..."
            item = f"[#{i+1}] source={filename} chunk={chunk_index}\n{snippet}\n"
            if total + len(item) <= max_context_chars:
                context_parts.append(item)
                total += len(item)
                used_citations.append((filename, chunk_index))
            else:
                break
        context = "\n".join(context_parts)

        # Construct a strict, grounded prompt for Ollama.
        system_instructions = (
            "You are a precise assistant. Use ONLY the content in the CONTEXT to answer the QUESTION. "
            "Do not add facts that are not present in the context. If the context does not contain the answer, "
            "respond exactly with: I don't know. Keep the answer concise and accurate."
        )
        prompt = (
            f"{system_instructions}\n\n"
            f"CONTEXT:\n{context}\n\n"
            f"QUESTION: {question}\n\n"
            f"Answer:"
        )

        # Call Ollama; handle unavailability gracefully.
        try:
            answer = _ollama_generate(prompt, OLLAMA_MODEL).strip()
        except Exception as ex:
            print(f"[qa] Ollama call failed: {ex}")
            print("[qa] Showing top retrieved context instead (no LLM):")
            print(context)
            continue

        # Print the answer and simple citations.
        print("\n[answer]")
        print(answer)
        if used_citations:
            cites = ", ".join(
                f"{fn or 'unknown'}#chunk-{ci}" for fn, ci in used_citations
            )
            print(f"[sources] {cites}")

    print("[qa] Bye.")

def send_to_llm() -> bool:
    return True

def cleanup_with_llm() -> bool:
    """Placeholder for future LLM-based cleanup. Currently a no-op for tests."""
    return True


def apply_sentence_transformers() -> bool:
    """Placeholder for Sentence-Transformers embedding step. Currently a no-op for tests."""
    return True

if __name__ == "__main__":
    input_dir = _default_input_dir()
    try:
        required_files = discover_source_files(str(input_dir))
    except ValueError as e:
        print(f"[prepare_data] {e}")
        print(f"[prepare_data] Create the directory at: {input_dir}")
        required_files = []
    contents = load_source_data(required_files)
    print(contents)
    # After printing the raw contents, also print the semantic chunks for each document
    try:
        for path, text in contents:
            if not text:
                continue
            print(f"[prepare_data] Semantic chunks for: {path}")
            sentences = _split_into_sentences(text)
            chunks = _semantic_chunks_from_sentences(
                sentences,
                target_tokens=350,
                max_tokens=500,
                overlap_tokens=50,
            )
            for idx, ch in enumerate(chunks):
                print(f"[chunk {idx}] tokens={_estimate_tokens(ch)}\n{ch}\n---")
    except Exception as ex:
        print(f"[prepare_data] Failed to generate/print semantic chunks: {ex}")
