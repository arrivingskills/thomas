import chromadb
from chromadb.config import Settings
import json

def add_sentences_to_chromadb(sentences, collection_name="sentences_collection"):
    client = chromadb.Client(Settings(
        anonymized_telemetry=False,
    ))
    collection = client.get_or_create_collection(name=collection_name)
    ids = [f"sentence-{i}" for i in range(len(sentences))]
    collection.add(
        documents=sentences,
        ids=ids,
    )
    return collection

if __name__ == "__main__":
    with open("data/finma.txt", "r") as f:
        contents = f.read()
    contents = contents.split("\n")

    sentences = []
    for line in contents:
        if len(line) == 0:
            continue
        line = json.loads(line)
        line = f"{line['title']} {line['link']} {line['pubDate']} {line['description']}"
        sentences.append(line)

    collection = add_sentences_to_chromadb(sentences)
    question = input("Ask a question: ")
    results = collection.query(
        query_texts=[question],
        n_results=2,
    )
    print(results)