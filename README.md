# DP-generator: Differentially Private RAG Chatbot

A privacy-preserving Retrieval-Augmented Generation (RAG) system for customer support. This project enables the use of sensitive conversational data for AI-driven support and synthetic data generation without compromising individual privacy.

## 🚀 Key Features
- **Differentially Private Retrieval:** Implements noise-based ranking to prevent the leakage of sensitive documents from the vector store.
- **PII Sanitization:** Automatically detects and masks Personal Identifiable Information (PII) like emails, phone numbers, and IDs using stable aliases.
- **Synthetic Dialogue Generation:** Autonomously generates multi-turn, privacy-safe synthetic conversations for training and testing.
- **Real-time SSE Streaming:** Provides a responsive user experience with live-streaming LLM responses.
- **Containerized Deployment:** Easily deployable using Docker and Docker Compose.

## 🏗️ Architecture
The system consists of three main layers:
1.  **Frontend:** A React-based dashboard for interactive chat and synthetic data generation.
2.  **Backend:** A FastAPI server managing the RAG pipeline, privacy logic, and LLM integrations.
3.  **Privacy Engine:** A specialized module for PII masking and differentially private vector retrieval.

For more details, see the [[Index|Internal Documentation]].

## 🛠️ Getting Started

### Prerequisites
- Docker & Docker Compose
- OpenRouter API Key (for LLM access)

### Setup
1.  Clone the repository.
2.  Create a `.env` file with your `OPENROUTER_API_KEY`.
3.  Start the services:
    ```bash
    docker-compose up --build
    ```
4.  Access the UI at `http://localhost:3000`.

## 📜 Documentation
We use an Obsidian-style internal documentation system. See:
- [[Architecture]] - Detailed system design.
- [[Privacy]] - Deep dive into DP and PII sanitization.
- [[ErrorHistory]] - History of challenges and error resolution.

---
Created by [[shahiilr06]]
