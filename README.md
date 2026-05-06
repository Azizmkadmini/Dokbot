# Dokbot — AI Customer Support Chatbot

> **Multi-tenant RAG chatbot that answers customer questions using your documentation.**
> Ingest PDFs or web pages, embed the widget on any site in 2 lines of code.

[![CI](https://github.com/Azizmkadmini/Dokbot/actions/workflows/ci.yml/badge.svg)](https://github.com/Azizmkadmini/Dokbot/actions/workflows/ci.yml)

---

## What it does

| Feature | Details |
|---|---|
| **Document ingestion** | Upload PDFs, TXT files, or scrape any URL |
| **Semantic search** | ChromaDB + OpenAI embeddings (cosine similarity) |
| **Contextual answers** | GPT-4o-mini with retrieved context + conversation history |
| **Multi-tenant** | Each client has an isolated knowledge base |
| **Embeddable widget** | Drop-in JS chat widget, zero dependencies |
| **Admin dashboard** | Ingest docs, view sources, monitor usage |
| **Evaluation suite** | Benchmark with keyword hit rate + LLM-as-judge |
| **Cost tracking** | Per-query cost in USD logged and exposed in analytics |

---

## Architecture

```
┌─────────────────────────────────────────────┐
│              Client Website                  │
│  <script src="widget.js"></script>           │
│  RAGSupport.init({ tenantId: "acme" })       │
└────────────────────┬────────────────────────┘
                     │ POST /chat
                     ▼
┌─────────────────────────────────────────────┐
│            FastAPI Backend                   │
│                                             │
│  /chat  ──► retrieve() ──► OpenAI GPT-4o   │
│  /ingest ──► chunk() ──► embed() ──► store  │
│  /analytics ──► usage logs                  │
└─────────────────────────────────────────────┘
                     │
            ┌────────┴────────┐
            │   ChromaDB      │  ← persisted on disk / Docker volume
            │  (per-tenant    │
            │  collections)   │
            └─────────────────┘
```

---

## Quick Start

### 1. Clone & configure

```bash
git clone https://github.com/Azizmkadmini/Dokbot.git
cd Dokbot
cp .env.example .env
# Edit .env and set your OPENAI_API_KEY
```

### 2. Run with Docker (recommended)

```bash
docker compose up --build
```

API available at `http://localhost:8000`
Swagger docs at `http://localhost:8000/docs`

### 3. Run locally (dev)

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

---

## Ingest your first document

```bash
# Upload a PDF
curl -X POST http://localhost:8000/ingest/file \
  -H "X-API-Key: change-me-in-production" \
  -F "tenant_id=demo" \
  -F "source_name=Product FAQ" \
  -F "file=@your-faq.pdf"

# Or scrape a URL
curl -X POST http://localhost:8000/ingest/url \
  -H "X-API-Key: change-me-in-production" \
  -H "Content-Type: application/json" \
  -d '{"tenant_id": "demo", "url": "https://yoursite.com/faq", "source_name": "FAQ page"}'
```

---

## Embed the widget

```html
<!-- Add to any page, right before </body> -->
<script src="https://yourdomain.com/widget.js"></script>
<script>
  RAGSupport.init({
    apiUrl: "https://api.yourdomain.com",
    tenantId: "your-client-id",
    primaryColor: "#6366f1",
    title: "Support Assistant",
    welcomeMessage: "Hi! How can I help you today?",
  });
</script>
```

---

## API Reference

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/chat` | None | Ask a question |
| `POST` | `/ingest/file` | Admin key | Upload PDF/TXT |
| `POST` | `/ingest/url` | Admin key | Scrape a URL |
| `DELETE` | `/ingest/source` | Admin key | Remove a source |
| `GET` | `/ingest/sources/{tenant_id}` | Admin key | List sources |
| `GET` | `/analytics/{tenant_id}` | Admin key | Usage stats |
| `GET` | `/health` | None | Health check |

---

## Evaluation

The system includes a benchmark suite with 8 real support questions.

```bash
cd eval
pip install httpx openai

# Basic evaluation (keyword hit rate, latency, cost)
python evaluate.py --api-url http://localhost:8000 --tenant-id demo

# Full evaluation with LLM-as-judge
python evaluate.py --tenant-id demo --judge --openai-api-key sk-...
```

**Sample output:**
```
======================================================
RAG Evaluation — tenant: demo
Benchmark: 8 questions
======================================================
  ✅ [q001] returns       khr=100%  sources=yes  latency=420ms
  ✅ [q002] shipping      khr=67%   sources=yes  latency=380ms
  ...
──────────────────────────────────────────────────────
SUMMARY
  Questions answered   : 8/8
  Avg keyword hit rate : 87%
  Source retrieval rate: 100%
  Avg latency          : 410ms
  P95 latency          : 590ms
  Total cost           : $0.00042
  Cost per query       : $0.000053
  LLM judge relevance  : 4.6/5
  LLM judge grounded   : 4.8/5
──────────────────────────────────────────────────────
```

---

## Configuration

All settings via environment variables (see `.env.example`):

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | — | Required |
| `OPENAI_MODEL` | `gpt-4o-mini` | Chat model |
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` | Embedding model |
| `ADMIN_API_KEY` | `change-me` | Protects ingest/analytics endpoints |
| `CHUNK_SIZE` | `500` | Tokens per chunk |
| `CHUNK_OVERLAP` | `50` | Overlap between chunks |
| `TOP_K` | `5` | Chunks retrieved per query |
| `SCORE_THRESHOLD` | `0.3` | Min cosine similarity to include a chunk |

---

## Tests

```bash
cd backend
pytest tests/ -v
```

Tests cover:
- Health endpoint
- Ingest auth (missing key, wrong key, success)
- Chat with empty/populated collection
- Chat with conversation history
- RAG core logic (chunking, context building) — no OpenAI calls

---

## Project structure

```
Dokbot/
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI routers (chat, ingest, analytics)
│   │   ├── core/         # RAG logic, config, chunking, embeddings
│   │   ├── db/           # ChromaDB client
│   │   └── services/     # PDF/URL extraction
│   ├── tests/            # pytest unit & integration tests
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── widget/           # Embeddable JS chat widget + demo page
│   └── dashboard/        # Admin dashboard (vanilla HTML/JS)
├── eval/
│   ├── benchmark.json    # 8-question evaluation dataset
│   └── evaluate.py       # Evaluation script with LLM-as-judge
├── .github/workflows/    # GitHub Actions CI
├── docker-compose.yml
└── .env.example
```

---

## Cost estimate (production)

| Scale | Monthly cost |
|---|---|
| 1,000 questions/month | ~$0.05 |
| 10,000 questions/month | ~$0.50 |
| 100,000 questions/month | ~$5.00 |

*Based on gpt-4o-mini pricing, avg 300 tokens input + 100 tokens output.*

---

## Deployment

**Railway (easiest):**
```bash
railway up
```

**Render:** Connect repo → set env vars → deploy.

**VPS (Docker):**
```bash
docker compose up -d
```

---

## Tech stack

- **Backend**: FastAPI, ChromaDB, OpenAI SDK, pypdf, BeautifulSoup4
- **Frontend**: Vanilla JS (zero dependencies), HTML/CSS
- **Eval**: httpx, OpenAI (LLM-as-judge)
- **Infra**: Docker, GitHub Actions

---

## License

This project is released under the [MIT License](LICENSE).

## Security

See [SECURITY.md](SECURITY.md) for how to report vulnerabilities and baseline hardening tips for self-hosted deployments.

---

*Built with AI-assisted development (Cursor). All architecture decisions, prompts, and evaluations designed and validated by the author.*
