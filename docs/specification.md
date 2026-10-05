# Application Specification

## Functional Requirements

1. A user can create, rename, delete, and switch UUID-identified notebooks.
2. PDF, PPTX, TXT, and public single-page URLs can be ingested.
3. Extracted content is chunked, embedded, and isolated per notebook.
4. A user can select vector or hybrid retrieval and receive a grounded answer.
5. Answers expose source name, location, chunk ID, excerpt, score, and timing.
6. Successful conversations persist and reload after application restart.
7. Reports and quizzes with answer keys are saved as downloadable Markdown.
8. Errors are understandable and do not expose application tracebacks in the UI.

## Non-Functional Requirements

- Secrets must only come from environment variables.
- Storage must be replaceable behind an abstraction boundary.
- Components must have separate ingestion, retrieval, generation, and storage roles.
- The Docker application must listen on port 7860.
- A push to `main` must test and then deploy the exact revision to a HF Space.

## Acceptance Criteria

- Two notebooks can ingest different facts without cross-retrieval.
- All four source types produce indexed chunks with citation metadata.
- Restarting locally restores notebooks, messages, and artifacts.
- A no-answer question produces an insufficient-evidence response.
- Both retrieval methods return inspectable chunks and measured retrieval time.
- Report and quiz downloads use the `.md` extension.
- GitHub Actions and the live Space both complete successfully.

## Dependencies and Deployment

The UI is Gradio; storage is local JSON/files; vector persistence is ChromaDB;
embeddings use Sentence Transformers; keyword retrieval uses BM25; generation
uses Groq-hosted GPT-OSS. The application is distributed as a Docker-based Hugging Face Space.
