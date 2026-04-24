"""
core/embedder.py
Loads a Hugging Face sentence-transformers model and provides
encode() helpers used by the matcher.

The model is cached at the Streamlit resource level so it only
loads once per server process, not on every user interaction.
"""

import numpy as np
from typing import Union


# ---------------------------------------------------------------------------
# Model config — swap this string to upgrade without touching other modules
# ---------------------------------------------------------------------------
#
# Good progression:
#   Speed / low RAM:  "all-MiniLM-L6-v2"        (~80 MB, fits Streamlit free tier)
#   Balanced:         "all-mpnet-base-v2"         (~420 MB)
#   Best quality:     "mixedbread-ai/mxbai-embed-large-v1"  (~560 MB, needs paid tier)
#
MODEL_NAME = "all-MiniLM-L6-v2"


def load_model():
    """
    Load and return the SentenceTransformer model.
    Call this inside a @st.cache_resource function in app.py
    so Streamlit only loads it once.

    Example in app.py:
        @st.cache_resource
        def get_embedder():
            from core.embedder import load_model
            return load_model()
    """
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        raise ImportError(
            "sentence-transformers is required: pip install sentence-transformers"
        )
    return SentenceTransformer(MODEL_NAME)


def encode(model, texts: Union[str, list[str]], batch_size: int = 32) -> np.ndarray:
    """
    Encode one or more texts into embedding vectors.

    Args:
        model:      Loaded SentenceTransformer instance.
        texts:      Single string or list of strings.
        batch_size: Batch size for encoding (tune for memory vs speed).

    Returns:
        numpy array of shape (n_texts, embedding_dim) or (embedding_dim,)
        for a single string input.
    """
    single = isinstance(texts, str)
    if single:
        texts = [texts]

    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=True,   # L2-normalise so dot product = cosine sim
    )

    return embeddings[0] if single else embeddings


def encode_proposal(model, text: str, chunk_texts: list[str] = None) -> np.ndarray:
    """
    Encode a proposal, using chunk averaging for long documents.

    If chunk_texts is provided (pre-chunked by parser.chunk()), each
    chunk is encoded separately and the result is the mean vector —
    this captures the full semantic spread of a long proposal better
    than encoding the whole text as one string.

    Args:
        model:       Loaded SentenceTransformer instance.
        text:        Full proposal text (used if chunks not provided).
        chunk_texts: Optional list of chunks from parser.chunk().

    Returns:
        Single embedding vector of shape (embedding_dim,).
    """
    if chunk_texts and len(chunk_texts) > 1:
        chunk_embs = encode(model, chunk_texts)
        # Mean pooling across chunks, then re-normalise
        mean_emb = chunk_embs.mean(axis=0)
        norm = np.linalg.norm(mean_emb)
        return mean_emb / norm if norm > 0 else mean_emb
    else:
        return encode(model, text)
