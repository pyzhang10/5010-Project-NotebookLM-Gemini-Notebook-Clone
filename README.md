---
title: Notebook RAG Studio
emoji: 📚
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
---

# Notebook RAG Studio

Notebook RAG Studio is a full-stack educational NotebookLM-style application.
It creates isolated notebooks, ingests PDF/PPTX/TXT/web sources, answers
source-grounded questions with citations, persists conversations, and generates
downloadable Markdown reports and quizzes with answer keys.



## Required Features

- Create, rename, delete, and switch notebooks
- Persistent, UUID-based per-notebook source/chat/artifact storage
- PDF, PPTX, TXT, and single-page URL ingestion
- Page/slide-aware chunk metadata and ChromaDB embeddings
- Vector similarity and hybrid vector+BM25 retrieval
- Grounded Groq-hosted GPT-OSS answers with visible citations and retrieved chunks
- Persistent chat history
- Markdown report generation and download
- Markdown quiz with answer key, preview, and download
- Friendly input/API errors
- Docker-based Hugging Face deployment
- Tested GitHub Actions deployment pipeline

## Architecture

See [`docs/architecture.md`](docs/architecture.md) for diagrams, module
responsibilities, data flow, storage, RAG, artifact generation, and deployment.

## Local Setup

Python 3.11 is recommended.

```bash
python -m venv .venv
source .venv/bin/activate              # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and set `GROQ_API_KEY`, then run:

```bash
python app.py
```

Open <http://localhost:7860>. The first ingestion downloads the embedding model,
so it can take longer than later requests.

## Environment Variables

| Variable | Required | Default | Purpose |
|---|---:|---|---|
| `GROQ_API_KEY` | Yes | — | Groq chat and artifact generation |
| `GROQ_MODEL` | No | `openai/gpt-oss-120b` | Groq-hosted generation model |
| `EMBEDDING_MODEL` | No | `all-MiniLM-L6-v2` | Local embeddings |
| `APP_DATA_DIR` | No | `./data` | Persistent data root |
| `TOP_K` | No | `4` | Retrieved chunks |
| `CHUNK_SIZE` | No | `600` | Approximate words per chunk |
| `CHUNK_OVERLAP` | No | `100` | Overlapping words |
| `MAX_UPLOAD_MB` | No | `20` | Per-file size limit |

Never commit `.env`. The application only reads the key from the environment.

## Usage

1. Create a notebook.
2. Upload one or more PDF, PPTX, or TXT files, or ingest an HTTP(S) web page.
3. Choose Vector Search or Hybrid Search.
4. Ask a question and expand retrieved chunks to verify citations.
5. Generate a report or quiz and download its `.md` file.
6. Switch notebooks to verify source and conversation isolation.

Scanned PDFs without embedded text are rejected with an OCR explanation.
JavaScript-only or authenticated web pages may not expose readable HTML.

## Retrieval Design

Vector Search embeds the question and retrieves cosine-nearest chunks from
ChromaDB. Hybrid Search independently ranks all chunks with BM25, obtains vector
candidates, and merges both rankings through Reciprocal Rank Fusion. It generally
improves exact-keyword/name/number matching while adding some latency.

Complete the supplied experiment before submission:

```bash
python scripts/evaluate_rag.py NOTEBOOK_UUID docs/evaluation_questions.json
```

Then transfer actual results and conclusions into
[`docs/rag_evaluation.md`](docs/rag_evaluation.md). The template intentionally
contains no invented measurements.

## Testing

```bash
pytest -q
```

Tests cover notebook CRUD/restart persistence, artifact extension safety,
chunk metadata, empty extraction, and blocking local URLs.

## Hugging Face Deployment

1. Create a new **Docker** Space.
2. In Space Settings → Variables and secrets, add `GROQ_API_KEY` as a secret.
3. Optionally add `APP_DATA_DIR=/data` when paid Persistent Storage is attached.
4. Push the repository or configure the workflow below.

The Dockerfile exposes port 7860 and installs all dependencies.

### Storage Behavior

The application persists all data across normal local restarts. Standard free
Hugging Face Space disk is ephemeral and can be cleared when the Space rebuilds
or restarts. This is a deployment limitation, not an application-level deletion.
For durable production storage, attach HF Persistent Storage and set
`APP_DATA_DIR=/data`, or implement another `StorageBackend`.

## GitHub Actions CI/CD

Create these repository secrets:

- `HF_TOKEN`: a Hugging Face write token
- `HF_SPACE_REPO`: `your-hf-username/your-space-name`

Every push to `main` installs dependencies, runs tests, and—only after tests
pass—pushes that exact revision to the Space. Capture a successful run in the
submission video.

## Security and Reliability

- Secrets are environment-only and ignored by Git.
- Notebook IDs are validated UUIDs before file access.
- Filenames are not used as storage paths.
- URL ingestion blocks loopback, link-local, and private-network addresses.
- Upload size and extension are validated.
- The RAG prompt requires insufficient-evidence responses and forbids outside facts.

## Submission Checklist

- [ ] Replace all three Live Links above
- [ ] Run the app locally and on Hugging Face
- [ ] Test create/switch/rename/delete notebooks
- [ ] Test PDF, PPTX, TXT, and URL ingestion
- [ ] Demonstrate citations and saved chat after restart
- [ ] Generate and download both report and quiz Markdown files
- [ ] Run and complete the RAG evaluation with real measurements
- [ ] Add a successful GitHub Actions screenshot/run link
- [ ] Record the required 1–2 minute deployment demonstration
- [ ] Confirm no API key appears anywhere in Git history

## Known Limitations

- No OCR for image-only PDFs
- URL ingestion handles public, server-rendered HTML only
- Artifact context is capped to control model input size
- The current storage backend is designed for a single Space process/user

## Groq 413 / rate-limit fix

Chat, Report and Quiz now share a conservative UTF-8 byte budget for source
text, with 500 tokens reserved for message framing. The defaults reserve 2000
completion tokens within a 7500-token request budget. No tokenizer download is
needed. Model and API key settings are unchanged. GPT-OSS uses low reasoning
effort. Source labels are kept, and reports/quizzes explicitly disclose partial
coverage when source excerpts exceed the budget; this is not a full-document
map/reduce summary. Artifact chunks are interleaved across sources.

Existing `.env` files work without changes. Optional settings:
```dotenv
GROQ_REQUEST_TOKEN_BUDGET=7500
GROQ_MAX_COMPLETION_TOKENS=2000
```
Restart `python app.py` after changing settings. A 429 can still occur when
several requests share the per-minute quota; wait before retrying. Output that
hits the completion limit is rejected instead of saved as a finished artifact.
Do not raise the budget beyond your account limit.
