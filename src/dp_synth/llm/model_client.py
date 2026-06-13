from __future__ import annotations

from dataclasses import dataclass
import logging

from dp_synth.config import AppConfig


LOGGER = logging.getLogger(__name__)


def _get_torch():
    import torch

    return torch


@dataclass(slots=True)
class ModelBackendInfo:
    backend: str
    model_name: str


class GemmaModelClient:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        torch = _get_torch()
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.backend_info: ModelBackendInfo | None = None
        self.model = None
        self.tokenizer = None
        self._load_model()

    def _load_model(self) -> None:
        torch = _get_torch()
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer

            tokenizer = AutoTokenizer.from_pretrained(
                self.config.llm_model_name,
                token=self.config.hf_token,
            )
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token
            model = AutoModelForCausalLM.from_pretrained(
                self.config.llm_model_name,
                token=self.config.hf_token,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                device_map="auto" if torch.cuda.is_available() else None,
            )
            if not torch.cuda.is_available():
                model = model.to(self.device)
            self.model = model
            self.tokenizer = tokenizer
            self.backend_info = ModelBackendInfo(backend="transformers", model_name=self.config.llm_model_name)
        except Exception as exc:
            raise RuntimeError(
                "Failed to load the model. "
                "Provide a valid Hugging Face token with Gemma access and accept the Gemma license on Hugging Face. "
                "You can paste the token into the Streamlit sidebar or set HF_TOKEN/HUGGINGFACEHUB_API_TOKEN before launch."
            ) from exc

    def generate(self, prompt: str) -> str:
        if self.backend_info is None or self.model is None or self.tokenizer is None:
            raise RuntimeError("Model is not initialized.")

        torch = _get_torch()

        inputs = self.tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=self.config.max_input_length,
        )
        inputs = {key: value.to(self.device) for key, value in inputs.items()}
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=self.config.max_new_tokens,
                do_sample=True,
                temperature=0.8,
                top_p=0.95,
                pad_token_id=self.tokenizer.eos_token_id,
            )
        return self.tokenizer.decode(outputs[0], skip_special_tokens=True)

