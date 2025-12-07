import chromadb
from chromadb.config import Settings

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

    sentences = [
        "Go to Florida to pick and eat oranges.",
        "In England I can learn about Shakespeare.",
        "My favorite food is pasta.",
        "I like to hike in the mountains"
    ]

    collection = add_sentences_to_chromadb(sentences)
    question = input("Ask a question: ")
    results = collection.query(
        query_texts=[question],
        n_results=2,
    )
    print(results)