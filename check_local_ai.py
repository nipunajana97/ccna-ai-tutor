"""Check the Windows/local Ollama setup. Does not read, print, or require an AI API key."""
import argparse
from dataclasses import replace
from pathlib import Path
import sys
import time
from dotenv import load_dotenv
from tutor.config import ROOT, Settings
from tutor.engine import GenerationError
from tutor.knowledge import KnowledgeIndex
from tutor.ollama_backend import OllamaTutor


def available_windows_memory_gb():
    if sys.platform != "win32":
        return None
    import ctypes

    class MemoryStatus(ctypes.Structure):
        _fields_ = [("length", ctypes.c_ulong), ("memory_load", ctypes.c_ulong),
                    ("total_phys", ctypes.c_ulonglong), ("avail_phys", ctypes.c_ulonglong),
                    ("total_page", ctypes.c_ulonglong), ("avail_page", ctypes.c_ulonglong),
                    ("total_virtual", ctypes.c_ulonglong), ("avail_virtual", ctypes.c_ulonglong),
                    ("avail_extended", ctypes.c_ulonglong)]
    status = MemoryStatus()
    status.length = ctypes.sizeof(status)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        return None
    return status.avail_phys / 1024 ** 3


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check Ollama, required local models, and optionally a real RAG answer")
    parser.add_argument("--answer", action="store_true", help="Index the reference and generate a real answer (uses RAM/CPU)")
    args = parser.parse_args(argv)
    load_dotenv(ROOT / ".env")
    # This owner-side check is for the local backend, even if old Gemini settings remain in .env.
    import os
    os.environ["AI_PROVIDER"] = "ollama"
    settings = replace(Settings.from_env(), local_test=True, demo=False)
    errors = settings.errors()
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    try:
        tutor = OllamaTutor(settings.ollama_url, settings.model, settings.embedding_model, settings.ollama_token)
        tutor.check_models()
        print("OK: Ollama is running and both downloaded local models are installed.")
        print(f"Chat: {settings.model}; embeddings: {settings.embedding_model}")
        free = available_windows_memory_gb()
        if free is not None:
            print(f"Available physical RAM: {free:.1f} GB")
            if free < 2:
                print("Close unused apps before loading the models; aim for roughly 3 GB free on this 8 GB laptop.")
                return 2
        if args.answer:
            started = time.perf_counter()
            index = KnowledgeIndex(settings.data_dir / "local-ai" / "chroma", ROOT / "ccna_knowledge.txt",
                                   ROOT / "docs/sources.json", settings.embedding_model, tutor.embed,
                                   embedding_profile=settings.embedding_profile, top_k=2)
            question = "Explain the network and broadcast addresses for 192.168.10.77/26."
            chunks = index.retrieve(question)
            print("\n" + question + "\n")
            answer = []
            for token in tutor.stream_answer(question, chunks):
                answer.append(token)
                print(token, end="", flush=True)
            if not "".join(answer).strip():
                raise GenerationError("Ollama returned an empty answer.")
            print(f"\n\nCompleted local retrieval and generation in {time.perf_counter() - started:.1f}s.")
            print("Compare the answer with network .64, broadcast .127, and 62 usable hosts.")
        else:
            print("Next: python check_local_ai.py --answer, or python start.py --local-ai")
        return 0
    except GenerationError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
