import json
import math
import httpx
import pytest
from tutor.engine import GenerationError
from tutor.knowledge import Chunk
from tutor.ollama_backend import OllamaTutor, ipv4_facts
from tutor.chat import stream_reply
from tutor.store import UsageStore

MODELS = {"models": [{"name": "qwen3:1.7b"}, {"name": "nomic-embed-text:v1.5"}]}


def tutor_for(handler):
    client = httpx.Client(base_url="http://127.0.0.1:11434/",
                          transport=httpx.MockTransport(handler), trust_env=False)
    return OllamaTutor("http://127.0.0.1:11434", "qwen3:1.7b", "nomic-embed-text:v1.5", client=client)


def event(text="", done=False, **kwargs):
    return json.dumps({"message": {"content": text, "thinking": "hidden reasoning"},
                       "done": done, **kwargs}) + "\n"


def test_local_embeddings_prefixes_batches_and_normalization():
    sent = []
    def respond(request):
        if request.url.path == "/api/tags":
            return httpx.Response(200, json=MODELS)
        assert request.url.path == "/api/embed"
        body = json.loads(request.content)
        sent.append(body)
        assert "authorization" not in request.headers
        return httpx.Response(200, json={"embeddings": [[1.0] * 768 for _ in body["input"]]})
    tutor = tutor_for(respond)
    vectors = tutor.embed(["reference"] * 5, document=True)
    assert len(vectors) == 5
    assert math.isclose(sum(v * v for v in vectors[0]), 1.0)
    tutor.embed(["OSPF"], document=False)
    assert [len(body["input"]) for body in sent] == [4, 1, 1]
    assert all(text.startswith("search_document: ") for body in sent[:2] for text in body["input"])
    assert sent[-1]["input"] == ["search_query: OSPF"]
    assert all(body["keep_alive"] == 0 and body["truncate"] is False for body in sent)


def test_streaming_local_contract_bounded_history_and_verified_subnet():
    sent = []
    def respond(request):
        if request.url.path == "/api/tags":
            return httpx.Response(200, json=MODELS)
        assert request.url.path == "/api/chat"
        sent.append(json.loads(request.content))
        return httpx.Response(200, text=event("A clear ") + event("answer.", True),
                              headers={"content-type": "application/x-ndjson"})
    tutor = tutor_for(respond)
    chunk = Chunk("s1-c0", "1", "Subnetting", "An IPv4 LAN subnet.", "https://www.rfc-editor.org")
    history = [{"role": "user", "content": "Old question " * 300},
               {"role": "assistant", "content": "Old answer " * 300}] * 8
    assert "".join(tutor.stream_answer("Explain 192.168.10.77/26", [chunk], history=history)) == "A clear answer."
    body = sent[0]
    assert body["model"] == "qwen3:1.7b"
    assert body["stream"] and body["think"] is False
    assert body["keep_alive"] == 0 and body["options"]["num_gpu"] == 0
    assert body["options"]["num_ctx"] == 4096
    assert body["messages"][0]["role"] == "system"
    assert sum(len(m["content"]) for m in body["messages"][1:-1]) <= 2000
    current = json.loads(body["messages"][-1]["content"])
    assert current["verified_calculations"][0]["network"] == "192.168.10.64/26"
    assert current["verified_calculations"][0]["broadcast"] == "192.168.10.127"
    assert current["verified_calculations"][0]["usable_count"] == 62
    assert "[s1-c0]" in current["reference_excerpts"]


@pytest.mark.parametrize("payload", [{"models": []},
                                    {"models": [{"name": "qwen3:1.7b", "remote_host": "https://ollama.com"},
                                                {"name": "nomic-embed-text:v1.5"}]}])
def test_unavailable_or_cloud_models_fail_before_inference(payload):
    def respond(request):
        assert request.url.path == "/api/tags", "Must not generate or embed using an unavailable/cloud model"
        return httpx.Response(200, json=payload)
    tutor = tutor_for(respond)
    with pytest.raises(GenerationError):
        tutor.embed(["reference"], document=True)


@pytest.mark.parametrize("values", [[], [1.0] * 3, [float("nan")] * 768, [0.0] * 768])
def test_invalid_embeddings_rejected(values):
    def respond(request):
        if request.url.path == "/api/tags":
            return httpx.Response(200, json=MODELS)
        # JSON cannot encode NaN in strict transports: use a raw response for that test.
        content = json.dumps({"embeddings": [values]})
        return httpx.Response(200, text=content)
    with pytest.raises(GenerationError, match="reference search"):
        tutor_for(respond).embed(["reference"], document=True)


def test_missing_done_marker_saves_partial_output_and_consumes_trial(tmp_path):
    def respond(request):
        if request.url.path == "/api/tags":
            return httpx.Response(200, json=MODELS)
        return httpx.Response(200, text=event("Partial local answer."))
    tutor = tutor_for(respond)
    store = UsageStore(tmp_path / "quota.db", cooldown_seconds=0)
    with pytest.raises(GenerationError, match="interrupted"):
        list(stream_reply(store, "u", "chat", "Question", lambda: False,
                          lambda: (tutor.stream_answer("Question", []), [])))
    assert store.trial_used("u")
    assert store.messages("chat", "u")[1]["interrupted"]
    assert store.messages("chat", "u")[1]["content"] == "Partial local answer."


def test_connection_failure_does_not_consume_trial_and_is_sanitized(tmp_path):
    def respond(request):
        raise httpx.ConnectError("sensitive low-level details", request=request)
    tutor = tutor_for(respond)
    store = UsageStore(tmp_path / "db", cooldown_seconds=0)
    with pytest.raises(GenerationError) as exc:
        list(stream_reply(store, "u", "chat", "Question", lambda: False,
                          lambda: (tutor.stream_answer("Question", []), [])))
    assert "sensitive" not in str(exc.value)
    assert not store.trial_used("u")
    assert not store.messages("chat", "u")


@pytest.mark.parametrize("cidr,count,broadcast", [
    ("10.0.0.1/30", 2, "10.0.0.3"), ("10.0.0.0/31", 2, None), ("10.0.0.7/32", 1, None),
])
def test_subnet_facts_respect_lan_point_to_point_and_host_routes(cidr, count, broadcast):
    result = ipv4_facts("Explain " + cidr)[0]
    assert result["usable_count"] == count
    assert result["broadcast"] == broadcast


def test_invalid_or_absent_cidr_does_not_invent_calculations():
    assert ipv4_facts("OSPF ExStart or 999.999.9.9/26") == []
