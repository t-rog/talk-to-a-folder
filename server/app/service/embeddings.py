"""
Embedding generation via Voyage AI. Isolated from the vector store so swapping
embedders (OpenAI, Cohere, local) doesn't touch storage code.
"""
import time
from typing import Any, Callable, List, Optional

import voyageai

from ..config import VOYAGE_API_KEY, VOYAGE_MODEL


def _log(msg: str) -> None:
    print(f"[embed] {msg}", flush=True)


def _with_retry(fn: Callable[[], Any], attempts: int = 3, base_delay: float = 0.5) -> Any:
    """
    Retry a callable with exponential backoff. Covers transient failures from
    external APIs: network blips, 429 rate limits, 503s. Doesn't distinguish
    retryable from non-retryable errors — at our scale, blanket retry is fine
    (a permanent error fails fast on its own in under 4 seconds total).
    """
    last_exc: Optional[Exception] = None
    for i in range(attempts):
        try:
            return fn()
        except Exception as e:
            last_exc = e
            if i < attempts - 1:
                delay = base_delay * (2 ** i)
                _log(f"retry {i + 1}/{attempts} after {type(e).__name__}: {e} (sleep {delay}s)")
                time.sleep(delay)
    assert last_exc is not None
    raise last_exc


if VOYAGE_API_KEY:
    _voyage = voyageai.Client(api_key=VOYAGE_API_KEY)
    _log(f"voyage client ready, model={VOYAGE_MODEL}")
else:
    _voyage = None
    _log("WARNING: VOYAGE_API_KEY not set — embedding calls will fail")


def embed(texts: List[str], input_type: str) -> List[List[float]]:
    """
    Embed a list of texts via Voyage. input_type must be 'document' or 'query';
    Voyage uses different embeddings for each to improve retrieval quality.
    Retries with exponential backoff on transient failures.
    """
    if _voyage is None:
        raise RuntimeError("VOYAGE_API_KEY is not set; cannot embed")
    t = time.time()
    result = _with_retry(lambda: _voyage.embed(texts, model=VOYAGE_MODEL, input_type=input_type))
    _log(f"  voyage.embed({input_type}, {len(texts)} items) took {time.time() - t:.2f}s")
    return result.embeddings
