"""Embeddings. O provider padrao e local e deterministico (hashing de unigramas/bigramas): sem rede, sem credencial, sem custo.

Um provider real (API externa) so deve ser habilitado depois de validar o fallback sem LLM; ele entra pela mesma interface
e grava outro `model_name`, de modo que vetores de modelos diferentes nunca sejam comparados entre si.
"""
from __future__ import annotations

import hashlib
import math
import re
import unicodedata
from typing import Protocol

DIM = 256  # deve coincidir com vector(256) em db/migrations/009_knowledge_base.sql


class Embedder(Protocol):
    model_name: str
    dim: int

    def embed(self, text: str) -> list[float]: ...


def tokenize(text: str) -> list[str]:
    plain = unicodedata.normalize("NFKD", text.lower()).encode("ascii", "ignore").decode()
    return re.findall(r"[a-z0-9]+", plain)


class HashingEmbedder:
    model_name = "hash-256-v1"
    dim = DIM

    def embed(self, text: str) -> list[float]:
        tokens = tokenize(text)
        vec = [0.0] * self.dim
        for feature in tokens + [f"{a}_{b}" for a, b in zip(tokens, tokens[1:])]:
            digest = hashlib.sha256(feature.encode()).digest()
            vec[int.from_bytes(digest[:4], "big") % self.dim] += 1.0 if digest[4] & 1 else -1.0
        norm = math.sqrt(sum(x * x for x in vec))
        return [x / norm for x in vec] if norm else vec


def to_pgvector(vec: list[float]) -> str:
    return "[" + ",".join(f"{x:.6f}" for x in vec) + "]"
