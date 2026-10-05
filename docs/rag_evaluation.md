# RAG Evaluation

> Submission note: replace the bracketed fields after running the experiment on
> your chosen evaluation documents. Do not fabricate measurements.

## Goal

This experiment compares basic dense vector similarity search with hybrid
retrieval. Both methods use the same documents, chunking settings, embedding
model, `top_k=4`, LLM, and answer prompt. This isolates the effect of retrieval.

## Methods

### Vector Search

The question is embedded with `all-MiniLM-L6-v2`. ChromaDB returns the chunks
with the smallest cosine distance. This method can match semantically similar
phrasing even when the query and document use different words.

### Hybrid Search

The system obtains candidates from both vector similarity and BM25 keyword
search. Reciprocal Rank Fusion combines the rankings without requiring the two
score scales to match. This should improve exact names, identifiers, and numeric
queries, at the cost of extra processing.

## Experimental Setup

- Evaluation notebook: `[NAME AND UUID]`
- Documents: `[LIST DOCUMENTS]`
- Chunk size/overlap: `600 / 100 words`
- Embedding model: `sentence-transformers/all-MiniLM-L6-v2`
- Top-k: `4`
- LLM: `openai/gpt-oss-120b` through Groq
- Date/environment: `[DATE AND MACHINE OR HF SPACE]`

Run:

```bash
python scripts/evaluate_rag.py NOTEBOOK_UUID docs/evaluation_questions.json
```

The script creates `rag_evaluation_results.csv`. Inspect each retrieved chunk,
ask the same questions in the UI, and fill in answer-quality and citation fields.

## Scoring Rubric

| Score | Definition |
|---:|---|
| 1 | Incorrect, unsupported, or substantially hallucinated |
| 2 | A small correct part but major omissions/errors |
| 3 | Mostly correct but incomplete or weakly cited |
| 4 | Correct and sufficiently complete with valid citations |
| 5 | Complete, precise, grounded, and correctly cited |

## Results

Paste or summarize the generated CSV here. Include the actual retrieved chunk
IDs—not just the number of chunks.

| Question | Method | Retrieved Chunks | Retrieval Time | Answer Quality | Citation Correct? |
|---|---|---|---:|---:|---|
| `[Q1]` | Vector | `[IDs]` | `[x.xxx s]` | `[/5]` | `[Yes/No]` |
| `[Q1]` | Hybrid | `[IDs]` | `[x.xxx s]` | `[/5]` | `[Yes/No]` |

## Discussion and Final Decision

Report average latency, average quality, failure cases, and citation accuracy.
Explain which method worked better for semantic paraphrases versus exact terms.

Final selection: `[Vector/Hybrid]`, because `[evidence-based reason]`.

Tradeoff: `[quality improvement]` versus `[measured latency or complexity cost]`.
