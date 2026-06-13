from __future__ import annotations

import contextlib
import io
import os


class EmbeddingModel:
    def __init__(self, model_name: str, hf_token: str | None = None) -> None:
        from sentence_transformers import SentenceTransformer

        if hf_token:
            os.environ["HF_TOKEN"] = hf_token
            os.environ["HUGGINGFACEHUB_API_TOKEN"] = hf_token

        kwargs = {}
        if hf_token:
            kwargs["token"] = hf_token

        buffer_out = io.StringIO()
        buffer_err = io.StringIO()
        try:
            with contextlib.redirect_stdout(buffer_out), contextlib.redirect_stderr(buffer_err):
                self.model = SentenceTransformer(model_name, **kwargs)
        except TypeError:
            kwargs.pop("token", None)
            if hf_token:
                kwargs["use_auth_token"] = hf_token
            with contextlib.redirect_stdout(buffer_out), contextlib.redirect_stderr(buffer_err):
                self.model = SentenceTransformer(model_name, **kwargs)

    def encode(self, texts: list[str]) -> list[list[float]]:
        return self.model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
            convert_to_numpy=True,
        ).tolist()
