# Privacy Implementation

Privacy is the core pillar of this project. It is achieved through two primary mechanisms:

## 1. PII Sanitization
The [[PIISanitizer]] class in `src/dp_synth/privacy/pii.py` uses regex patterns to identify and mask:
- Emails
- Phone Numbers
- Credit Card Numbers
- [CASE_ID] and [NAME]

We use **Stable Aliases** (SHA-1 hashing) to ensure that the same PII value is replaced by the same alias across different dialogues, maintaining data utility for the LLM.

## 2. Differential Privacy (DP)
During retrieval, we apply the **Exponential Mechanism** (approximated) by adding noise to the similarity scores.

- **Epsilon ($\epsilon$):** Controls the privacy-utility trade-off. Lower epsilon means more noise and higher privacy.
- **Laplace Noise:** Noise is sampled and added to the distances in `src/dp_synth/rag/vector_store.py`.

---
Back to [[Index]]
