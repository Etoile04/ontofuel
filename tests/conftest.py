"""Shared test configuration and fixtures.

This module provides cross-cutting test infrastructure, including
environment-aware skip conditions for optional dependencies like
embedding models that require network access.
"""

import os

import pytest


def _check_embeddings_available() -> bool:
    """Check whether an embedding model can actually be loaded.

    ``chonkie`` may be installed ( wheels ) but the underlying
    SentenceTransformer / model2vec weights still need to be downloaded
    from HuggingFace Hub.  In sandboxed CI runners this download can
    fail (network restrictions, registry downtime).  Rather than let
    every semantic test explode, we probe once at collection time.

    The check is gated behind ONTOFUEL_CI=true so local developers
    with cached models are never affected.
    """
    if os.environ.get("ONTOFUEL_CI") != "true":
        # Assume available outside CI (local dev typically has cached models)
        return True

    try:
        from chonkie import AutoEmbeddings  # noqa: F401

        emb = AutoEmbeddings.get_embeddings("minishlab/potion-base-8M")
        return emb is not None
    except Exception:
        return False


EMBEDDINGS_AVAILABLE = _check_embeddings_available()
"""True when the embedding model can be instantiated (needs network)."""
