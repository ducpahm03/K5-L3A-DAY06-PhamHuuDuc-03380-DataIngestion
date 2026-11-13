"""Choose a real embedding provider (API or local) with disk caching and rate limit handling."""
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Protocol
from dotenv import load_dotenv

load_dotenv()


class Embedder(Protocol):
    model_name: str
    dimensions: int

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        ...

    def embed_query(self, question: str) -> list[float]:
        ...


class MyEmbedder:
    """Production Gemini API embedding implementation with persistent disk cache."""

    def __init__(self, model_name: str = "gemini-embedding-001", cache_file: str = "embeddings_cache.json") -> None:
        self.model_name = model_name
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment or .env file.")

        from google import genai
        self.client = genai.Client(api_key=self.api_key)

        # Persistent disk cache
        self.cache_path = Path(cache_file)
        self.cache: dict[str, list[float]] = {}
        if self.cache_path.exists():
            try:
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    self.cache = json.load(f)
                print(f"[Embedder Cache] Loaded {len(self.cache)} cached vectors from {self.cache_path.name}")
            except Exception as e:
                print(f"[Embedder Cache] Could not load cache: {e}")

        # Dimensions: 3072 for gemini-embedding-001
        self.dimensions = 3072

    def _save_cache(self) -> None:
        try:
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(self.cache, f)
        except Exception as e:
            print(f"[Embedder Cache] Save warning: {e}")

    def _hash(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def embed_documents(self, texts: list[str], batch_size: int = 50) -> list[list[float]]:
        """Batch embed list of texts with disk cache and 429 rate limit backoff."""
        results: list[list[float] | None] = [None] * len(texts)
        missing_indices: list[int] = []
        missing_texts: list[str] = []

        for idx, text in enumerate(texts):
            h = self._hash(text)
            if h in self.cache:
                results[idx] = self.cache[h]
            else:
                missing_indices.append(idx)
                missing_texts.append(text if text.strip() else " ")

        if not missing_texts:
            print(f"[Embedder] 100% hits from cache ({len(texts)} chunks). No API calls needed.")
            return [vec for vec in results if vec is not None]

        print(f"[Embedder] {len(texts) - len(missing_texts)} in cache, {len(missing_texts)} need embedding via Gemini API...")

        for i in range(0, len(missing_texts), batch_size):
            batch_texts = missing_texts[i : i + batch_size]
            batch_idxs = missing_indices[i : i + batch_size]

            success = False
            attempts = 0
            while not success and attempts < 5:
                attempts += 1
                try:
                    res = self.client.models.embed_content(
                        model=self.model_name,
                        contents=batch_texts
                    )
                    for text, vec, target_idx in zip(batch_texts, res.embeddings, batch_idxs):
                        vector_vals = vec.values
                        self.cache[self._hash(text)] = vector_vals
                        results[target_idx] = vector_vals

                    self._save_cache()
                    success = True
                    print(f"[Embedder] Embedded {i + len(batch_texts)}/{len(missing_texts)} chunks...")
                    time.sleep(1.0)
                except Exception as e:
                    err_msg = str(e)
                    if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                        wait_sec = 32
                        print(f"[Embedder RateLimit] Quota reached. Cooling down for {wait_sec}s before retry (attempt {attempts}/5)...")
                        time.sleep(wait_sec)
                    else:
                        print(f"[Embedder Error] {e}. Waiting 5s...")
                        time.sleep(5.0)

            if not success:
                raise RuntimeError(f"Failed to embed batch starting at index {i} after 5 attempts.")

        return [vec for vec in results if vec is not None]

    def embed_query(self, question: str) -> list[float]:
        """Embed a single query string, checking cache first."""
        h = self._hash(question)
        if h in self.cache:
            return self.cache[h]

        clean_q = question if question.strip() else " "
        attempts = 0
        while attempts < 4:
            attempts += 1
            try:
                res = self.client.models.embed_content(
                    model=self.model_name,
                    contents=[clean_q]
                )
                vec = res.embeddings[0].values
                self.cache[h] = vec
                self._save_cache()
                return vec
            except Exception as e:
                if "429" in str(e):
                    time.sleep(25)
                else:
                    time.sleep(3)
        raise RuntimeError(f"Query embedding failed for: {question[:50]}")
