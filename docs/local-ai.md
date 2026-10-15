# Real local AI on the 8 GB Windows laptop

The default backend is Ollama with `qwen3:1.7b` for answers and `nomic-embed-text:v1.5` for search. No Gemini API key is required. This is a practical starting configuration for the supplied Core i5-13420H / Intel UHD / 8 GB RAM screenshot, not a measured CCNA quality or latency guarantee.

## Install and download

1. Close unused applications and browser tabs. The screenshot showed 96% memory use. Aim for roughly 3 GB available before loading models; the setup checker stops before generation if Windows reports less than 2 GB free.
2. Install [Ollama for Windows](https://ollama.com/download/windows), then reopen PowerShell. Keep Ollama running.
3. Download the two local models:

```powershell
ollama pull qwen3:1.7b
ollama pull nomic-embed-text:v1.5
```

The model downloads are approximately 1.4 GB and 274 MB. Runtime memory is higher than the download size. Downloading requires internet; local AI answers do not require a hosted AI API account.

## Check and run

From the existing project folder and virtual environment:

```powershell
.\.venv\Scripts\python.exe check_local_ai.py
.\.venv\Scripts\python.exe start.py --local-ai
```

The first command checks that the server and both models are present. For a real retrieval-and-answer check, run:

```powershell
.\.venv\Scripts\python.exe check_local_ai.py --answer
```

The expected subnet facts for that check are network `192.168.10.64/26`, broadcast `192.168.10.127`, and 62 usable hosts. Compare the generated explanation with those facts and the retrieved sources. The script reports elapsed time without claiming the answer is correct.

Open http://localhost:8501. The banner must say **Local AI test**, not **Local preview**. Ask one question and confirm that it streams a real model response and then locks the composer. New chat and browser refresh must not reset the default local trial. Use **Restart local AI trial** to repeat owner-side tests with a separate preview identity.

`--local-ai` overrides a previously set `DEMO_MODE=true` and selects Ollama. It binds Streamlit to `127.0.0.1`, uses `data/local-ai/`, and makes no Google login, Gemini, or Stripe calls. Subscriptions are disabled in this mode. It is rejected on Render and with remote application/model URLs. Real customer trial records and chats are separate.

For the offline UI example, use `python start.py --demo`. For real Google authentication and Stripe verification, use `python start.py` with both preview flags false and the required credentials configured.

## Memory and response limits

The adapter requests CPU inference, 4,096 context tokens, at most 640 output tokens, and no thinking output. It retrieves two reference chunks, bounds recent conversation text, serializes local model requests within the app process, and requests immediate model unloading after embeddings and answers. This reduces memory pressure at the cost of loading the model again on the next request. Other Ollama clients are outside this app's serialization lock.

If memory is tight or a response fails, close unused programs, check Ollama, and retry. An empty failed request does not consume the free response. Partial text is saved and consumes the response. The model is intentionally small; review answer quality before offering paid access. An 8 GB laptop is a prototype machine, not a proven multi-user hosting configuration.

## Feed the tutor with reference material

Edit `ccna_knowledge.txt` with reviewed CCNA explanations. Preserve the `[SECTION n: title]` structure. Add a corresponding primary-source URL in `docs/sources.json` for any new section. Then stop and restart the app so its cached index resource is refreshed. The changed knowledge gets a new Chroma collection; prior collections are not deleted automatically.

This process indexes documents for retrieval (RAG); it does not fine-tune model weights. The current six sections are starter coverage, not a complete CCNA blueprint. The adapter uses Nomic's `search_document:` / `search_query:` prefixes and validates normalized 768-dimensional vectors. A separate embedding profile prevents reuse of incompatible Gemini vectors.

For explicit IPv4/CIDR addresses in a question, Python supplies network, broadcast, and usable-host facts to the model. The resulting prose still needs review. Other numerical formats and arbitrary model claims are not automatically verified.

## Configuration and later hosting

The defaults work without editing `.env`. Optional overrides are in `.env.example`. The Nomic adapter currently supports `nomic-embed-text` models with 768-dimensional embeddings. Ollama cloud tags are rejected and there is no cloud fallback.

To host for customers later, provide an always-on model server and benchmark its capacity. A Render web service cannot call the Windows PC through `localhost`. The app supports a separate HTTPS Ollama proxy with `OLLAMA_BASE_URL` and `OLLAMA_AUTH_TOKEN`; that proxy must actually validate the token. Preview modes must be off. The prepared Render blueprint does not install Ollama or its model weights.

Primary references:

- https://ollama.com/library/qwen3:1.7b
- https://ollama.com/library/nomic-embed-text
- https://huggingface.co/nomic-ai/nomic-embed-text-v1.5
- https://docs.ollama.com/api/chat
- https://docs.ollama.com/api/embed
- https://docs.ollama.com/windows
