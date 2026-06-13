from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import os


@dataclass(slots=True)
class PrivacyConfig:
    epsilon: float = 1.5
    similarity_threshold: float = 0.9
    max_reference_examples: int = 4
    enable_retrieval_noise: bool = True


@dataclass(slots=True)
class AppConfig:
    data_dir: Path = Path("dataset")
    output_dir: Path = Path("outputs")
    chroma_dir: Path = Path("chroma_db")
    vector_backend: str = "local"
    default_dataset: Path = Path("dataset/customer_support_data.csv")
    collection_name: str = "support_dialogues"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # OpenRouter settings
    openrouter_api_key: str = field(
        default_factory=lambda: os.getenv("OPENROUTER_API_KEY", "")
    )
    openrouter_model: str = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"

    max_new_tokens: int = 1024
    hf_token: str | None = field(
        default_factory=lambda: os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACEHUB_API_TOKEN")
    )
    privacy: PrivacyConfig = field(default_factory=PrivacyConfig)


DEFAULT_CONFIG = AppConfig()
