import chromadb
import uuid

client = chromadb.Client()
collection = client.get_or_create_collection(name="my_collection")


def add_vector(id, document, metadata):
    id = str(uuid.uuid4())
    collection.add(
        ids=[id],
        documents=[document],
        metadatas=[metadata]
    )
    return id

def query_vector(query, n_results=5):
    results = collection.query(
        query_texts=[query],
        n_results=n_results
    )
    return results

def batch_add_vectors(documents):
    ids = [str(uuid.uuid4()) for _ in documents]
    collection.add(
        ids=ids,
        documents=documents,
        metadatas=[{"index": str(i)} for i in range(len(documents))]
    )
    return ids


if __name__ == "__main__":
    # Example usage
    policies = []

    with open("store_policy_samples.txt", "r", encoding="utf-8") as f:
        policies = f.read().splitlines()

    batch_add_vectors(policies)

    response = query_vector("What perks do Loyalty members get?")
    
    for i, query_results in enumerate(response['documents']):
        print(f"Query: {response['documents'][i]}")
        for j, doc in enumerate(query_results):
            print(f"Result {j+1}: {doc} (Metadata: {response['metadatas'][i][j]})")

    