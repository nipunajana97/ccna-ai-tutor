import hashlib
import ipaddress
from pathlib import Path
import re
from tutor.engine import subnet_scenario
from tutor.knowledge import KnowledgeIndex, read_chunks

ROOT = Path(__file__).resolve().parents[1]


def test_generated_subnet_answers_match_independent_ipaddress_calculation():
    for seed in range(250):
        scenario = subnet_scenario(seed)
        cidr = re.search(r"(192\.168\.\d+\.\d+/\d+)", scenario.scenario).group(1)
        network = ipaddress.ip_interface(cidr).network
        assert len(set(scenario.choices)) == 4
        assert scenario.choices[scenario.correct_index] == str(network.network_address)
        assert str(network.broadcast_address) in scenario.explanation
        assert f"({network.num_addresses - 2} hosts)" in scenario.explanation


def test_knowledge_chunking_preserves_sections_and_complete_text():
    _, chunks = read_chunks(ROOT / "ccna_knowledge.txt", ROOT / "docs/sources.json")
    assert {c.section for c in chunks} == set("123456")
    assert len({c.id for c in chunks}) == len(chunks)
    assert all(len(c.text) < 2600 and c.url.startswith("https://") for c in chunks)


def test_real_chroma_storage_and_section_filter_without_remote_model(tmp_path):
    calls = []
    def embed(texts, document):
        calls.append((len(texts), document))
        vectors = []
        for text in texts:
            vector = [0.0] * 768
            for word in text.lower().split():
                vector[int(hashlib.sha256(word.encode()).hexdigest(), 16) % 768] += 1
            vectors.append(vector)
        return vectors
    args = (tmp_path / "chroma", ROOT / "ccna_knowledge.txt", ROOT / "docs/sources.json", "fake-embedding", embed)
    index = KnowledgeIndex(*args)
    count = index.collection.count()
    first_document_calls = sum(n for n, doc in calls if doc)
    second = KnowledgeIndex(*args)
    assert second.collection.count() == count
    assert sum(n for n, doc in calls if doc) == first_document_calls
    chunks = second.retrieve("OSPF hello timers MTU", section="3")
    assert chunks and all(c.section == "3" for c in chunks)
