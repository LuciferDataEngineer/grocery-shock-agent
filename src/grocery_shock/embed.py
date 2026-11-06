"""Signed feature hashing.

This is a local, deterministic embedder. It does not download a neural model.
Similar wording lands near similar vectors because shared tokens vote into the
same coordinates. DuckDB VSS then builds an HNSW index over those vectors.
"""

from __future__ import annotations

import hashlib
import math
import re

DIM = 128
_TOKEN = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    tokens = _TOKEN.findall(text.lower())
    grams = list(tokens)
    grams.extend(f"{left}_{right}" for left, right in zip(tokens, tokens[1:], strict=False))
    return grams


def embed(text: str, dim: int = DIM) -> list[float]:
    vector = [0.0] * dim
    for token in tokenize(text):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "little") % dim
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]
