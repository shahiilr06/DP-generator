# System Architecture

The project is structured as a decoupled application with a Python backend and a React frontend.

## 🧩 Components

### 1. Backend (FastAPI)
The backend is located in `backend/` and `src/dp_synth/`. It handles:
- Vector indexing and retrieval.
- LLM orchestration via [[OpenRouter]].
- Differential Privacy application.

### 2. Frontend (React + Vite)
Located in `frontend/`, it provides:
- A real-time chat interface.
- Configuration for privacy parameters (epsilon).
- Synthetic data visualization.

### 3. Vector Store
The system uses [[ChromaDB]] as the primary vector store, with a local `.pkl` fallback for lightweight environments.

---
Back to [[Index]]
