import chromadb
from chromadb.config import Settings
import json
import os
import http.client
from urllib.parse import urlparse
from pathlib import Path


def add_sentences_to_chromadb(sentences, collection_name="sentences_collection"):
    client = chromadb.Client(
        Settings(
            anonymized_telemetry=False,
        )
    )
    collection = client.get_or_create_collection(name=collection_name)
    ids = [f"sentence-{i}" for i in range(len(sentences))]
    collection.add(
        documents=sentences,
        ids=ids,
    )
    return collection


# --- Minimal Ollama client ---
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")


def _ollama_generate(prompt: str, model: str = OLLAMA_MODEL) -> str:
    url = urlparse(OLLAMA_BASE_URL)
    conn_cls = (
        http.client.HTTPSConnection
        if url.scheme == "https"
        else http.client.HTTPConnection
    )
    # Windows needs explicit host resolution - use 127.0.0.1 if hostname is None or localhost
    hostname = url.hostname or "localhost"
    if hostname == "localhost":
        hostname = "127.0.0.1"
    port = url.port or (443 if url.scheme == "https" else 11434)
    conn = conn_cls(hostname, port, timeout=60)
    try:
        body = {"model": model, "prompt": prompt, "stream": False}
        payload = json.dumps(body).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        conn.request("POST", "/api/generate", body=payload, headers=headers)
        resp = conn.getresponse()
        data = resp.read().decode("utf-8", errors="replace")
        if resp.status != 200:
            raise RuntimeError(f"Ollama generate failed ({resp.status}): {data[:200]}")
        # Try parse single JSON first
        try:
            obj = json.loads(data)
            if isinstance(obj, dict) and "response" in obj:
                return str(obj.get("response", "")).strip()
        except Exception:
            pass
        # Fallback: parse JSONL stream concatenation
        out = []
        for line in data.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                part = json.loads(line)
                resp_text = part.get("response")
                if resp_text:
                    out.append(resp_text)
            except Exception:
                continue
        return "".join(out).strip()
    finally:
        conn.close()


if __name__ == "__main__":
    # Use project-root relative path so running from any cwd works
    project_root = Path(__file__).resolve().parent.parent.parent
    finma_path = project_root / "data" / "finma.txt"
    if not finma_path.exists():
        raise FileNotFoundError(
            f"{finma_path} not found. Expected file at project root: {finma_path}"
        )
    with finma_path.open("r", encoding="utf-8") as f:
        contents = f.read()
    contents = contents.split("\n")

    sentences = []
    for raw in contents:
        line = raw.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            title = obj.get("title", "") or ""
            link = obj.get("link", "") or ""
            pubDate = obj.get("pubDate", "") or ""
            description = obj.get("description", "") or ""
        except json.JSONDecodeError:
            parts = [p.strip() for p in line.split(" | ")]
            title = parts[0] if len(parts) > 0 else ""
            pubDate = parts[1] if len(parts) > 1 else ""
            link = parts[2] if len(parts) > 2 else ""
            description = ""
        sentence = " ".join(filter(None, (title, link, pubDate, description)))
        sentences.append(sentence)

    collection = add_sentences_to_chromadb(sentences)
    question = input("Ask a question: ")
    results = collection.query(
        query_texts=[question],
        n_results=2,
    )
    print("Raw retrieval results:", results)

    # Pick the highest-score item (first result for the single query)
    top_doc = None
    if results and isinstance(results.get("documents"), list) and results["documents"]:
        # documents is List[List[str]] per query
        docs_for_query = results["documents"][0]
        if docs_for_query:
            top_doc = docs_for_query[0]

    if not top_doc:
        print("No matching document found in Chroma.")
    else:
        prompt = (
            "You are a helpful assistant. Stay strictly on-topic.\n\n"
            f"User question: {question}\n\n"
            "Most relevant source snippet:\n---\n"
            f"{top_doc}\n"
            "---\n\n"
            "Write a detailed elaboration that is derived from the "
            "information above, and can contain relevant, related materials. "
            "If the snippet is not relevant, say politely that the source is not relevant."
        )
        try:
            answer = _ollama_generate(prompt)
            print("\nLLM elaboration (Ollama):\n", answer)
        except Exception as ex:
            print("Failed to generate with Ollama:", ex)
