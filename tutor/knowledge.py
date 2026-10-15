from dataclasses import dataclass
import hashlib
import json
import re


@dataclass(frozen=True)
class Chunk:
    id: str
    section: str
    title: str
    text: str
    url: str


def read_chunks(path, sources_path, max_chars=2400):
    text = path.read_text(encoding="utf-8")
    sources = json.loads(sources_path.read_text(encoding="utf-8"))
    matches = list(re.finditer(r"\[SECTION (\d+): ([^\]]+)\]", text))
    chunks = []
    for i, match in enumerate(matches):
        section, title = match.groups()
        body = text[match.end():matches[i + 1].start() if i + 1 < len(matches) else len(text)].strip()
        paragraphs = re.split(r"\n\s*\n", body)
        current = ""
        pieces = []
        for paragraph in paragraphs:
            if len(paragraph) > max_chars:
                raise ValueError(f"Knowledge paragraph too long in section {section}.")
            if current and len(current) + len(paragraph) + 2 > max_chars:
                pieces.append(current)
                current = ""
            current += ("\n\n" if current else "") + paragraph
        if current:
            pieces.append(current)
        for n, piece in enumerate(pieces):
            chunks.append(Chunk(f"s{section}-c{n}", section, title, title + "\n" + piece, sources[section]["url"]))
    if not chunks:
        raise ValueError("No knowledge sections were found.")
    return text, chunks


class KnowledgeIndex:
    def __init__(self, directory, knowledge_path, sources_path, embedding_model, embedder, *, embedding_profile="768|v1", top_k=4):
        import chromadb
        from chromadb.config import Settings
        text, self.chunks = read_chunks(knowledge_path, sources_path)
        digest = hashlib.sha256((text + embedding_model + "|" + embedding_profile).encode()).hexdigest()[:24]
        self.embedder = embedder
        self.top_k = top_k
        self.client = chromadb.PersistentClient(path=str(directory), settings=Settings(anonymized_telemetry=False))
        self.collection = self.client.get_or_create_collection(
            name=f"ccna-{digest}", embedding_function=None, metadata={"hnsw:space": "cosine"})
        existing = set(self.collection.get(include=[])["ids"])
        missing = [c for c in self.chunks if c.id not in existing]
        if missing:
            vectors = self.embedder([c.text for c in missing], document=True)
            self.collection.upsert(ids=[c.id for c in missing], documents=[c.text for c in missing],
                                   embeddings=vectors, metadatas=[{"section": c.section, "title": c.title, "url": c.url} for c in missing])

    def retrieve(self, query, section=None):
        params = {"query_embeddings": self.embedder([query], document=False),
                  "n_results": min(self.top_k, self.collection.count()), "include": ["documents", "metadatas"]}
        if section:
            params["where"] = {"section": str(section)}
        result = self.collection.query(**params)
        return [Chunk(id, metadata["section"], metadata["title"], doc, metadata["url"])
                for id, doc, metadata in zip(result["ids"][0], result["documents"][0], result["metadatas"][0])]
