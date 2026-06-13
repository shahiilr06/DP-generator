# Usage

1. Open the web UI at `http://localhost:3000`.
2. Type a question in the chat box.
3. The backend will:
   - Retrieve relevant documents from the vector store.
   - Send a prompt to the Nemotron‑3 model via OpenRouter.
   - Stream the response back to the UI using SSE.
4. The UI displays the answer with a premium glassmorphism style.

You can adjust the **max examples** (turn pairs) using the slider in the *Auto‑generator* tab (up to 20 pairs).
