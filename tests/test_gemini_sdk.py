"""Exercise real SDK serialization/parsing through a local HTTP transport, without API calls."""
import json
import math
import httpx
from google import genai
from google.genai import types
from tutor.engine import GeminiTutor, subnet_scenario
from tutor.knowledge import Chunk


def test_real_gemini_sdk_embeddings_schema_and_sse(monkeypatch):
    scenario = subnet_scenario(42)
    sent = []
    def response(request):
        sent.append((request.url.path, json.loads(request.content)))
        if request.url.path.endswith(":batchEmbedContents"):
            count = len(json.loads(request.content)["requests"])
            return httpx.Response(200, json={"embeddings": [{"values": [1.0] * 768} for _ in range(count)]})
        if request.url.path.endswith(":embedContent"):
            return httpx.Response(200, json={"embedding": {"values": [1.0] * 768}})
        if request.url.path.endswith(":streamGenerateContent"):
            chunks = [json.dumps({"candidates": [{"content": {"role": "model", "parts": [{"text": text}]}}]}) for text in ["A subnet ", "has a boundary."]]
            return httpx.Response(200, content="".join(f"data: {chunk}\n\n" for chunk in chunks), headers={"content-type": "text/event-stream"})
        if request.url.path.endswith(":generateContent"):
            return httpx.Response(200, json={"candidates": [{"content": {"role": "model", "parts": [{"text": scenario.model_dump_json()}]}, "finishReason": "STOP"}]})
        raise AssertionError(request.url)
    original_client = genai.Client
    client = original_client(api_key="test-not-a-real-key", http_options=types.HttpOptions(
        client_args={"transport": httpx.MockTransport(response), "trust_env": False}))
    monkeypatch.setattr(genai, "Client", lambda **kwargs: client)
    tutor = GeminiTutor("unused", "test-generation", "gemini-embedding-001")
    try:
        embeddings = tutor.embed(["doc one", "doc two"], document=True)
        assert len(embeddings) == 2
        assert math.isclose(sum(value * value for value in embeddings[0]), 1.0)
        chunk = Chunk("s1-c0", "1", "Subnetting", "Subnet boundaries.", "https://www.rfc-editor.org/rfc/rfc3021")
        assert tutor.scenario("Subnetting", "Foundation", "", [chunk]) == scenario
        history = [{"role": "user", "content": "What is a subnet?"},
                   {"role": "assistant", "content": "A logical IP network."}]
        assert "".join(tutor.stream_answer("Explain a subnet", [chunk], history=history)) == "A subnet has a boundary."
        generation = next(body for path, body in sent if path.endswith(":generateContent"))
        assert generation["generationConfig"]["responseMimeType"] == "application/json"
        chat = next(body for path, body in sent if path.endswith(":streamGenerateContent"))
        assert [item["role"] for item in chat["contents"]] == ["user", "model", "user"]
        assert chat["contents"][1]["parts"][0]["text"] == "A logical IP network."
        latest = json.loads(chat["contents"][-1]["parts"][0]["text"])
        assert latest["question"] == "Explain a subnet"
        assert "[s1-c0]" in latest["reference_excerpts"]
    finally:
        client.close()
