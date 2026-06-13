# Docker Compose

```yaml
version: "3.9"
services:
  backend:
    build: ./backend
    container_name: dp-rag-backend
    ports:
      - "8000:8000"
    environment:
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
    volumes:
      - chroma_data:/app/chroma_data
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request, sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/api/status').read() else 1)" ]
      interval: 30s
      timeout: 10s
      retries: 3

  frontend:
    build: ./frontend
    container_name: dp-rag-frontend
    ports:
      - "3000:80"
    depends_on:
      backend:
        condition: service_healthy
    volumes:
      - ./frontend/nginx.conf:/etc/nginx/nginx.conf:ro

volumes:
  chroma_data:
```

The backend is a FastAPI service; the frontend is served by Nginx with proxy settings that disable buffering for SSE.
