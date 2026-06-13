# Errors

## "Index not built"
When the vector store has not been initialised, the backend returns an error. The UI now shows an **index‑gate** banner with a *Quick Build* button that triggers the index creation.

## Proxy connection refused (`ECONNREFUSED 127.0.0.1:8000`)
Occurs if the backend container is not running. Ensure `docker compose up` is active and that the backend health‑check passes.
