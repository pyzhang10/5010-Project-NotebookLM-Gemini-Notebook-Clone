from __future__ import annotations

from pathlib import Path

import gradio as gr
from dotenv import load_dotenv

load_dotenv()

from artifacts import ArtifactService
from ingestion import IngestionService
from llm import GroqClient
from retrieval import VectorIndex
from services import RAGService
from storage import LocalStorage


storage = LocalStorage()
index = VectorIndex(storage)
llm = GroqClient()
ingestion = IngestionService(storage, index)
rag = RAGService(storage, index, llm)
artifacts = ArtifactService(storage, index, llm)


def notebook_choices():
    return [(item.name, item.id) for item in storage.list_notebooks()]


def require_notebook(notebook_id):
    if not notebook_id:
        raise gr.Error("Create or select a notebook first.")
    storage.get_notebook(notebook_id)
    return notebook_id


def refresh(selected=None):
    choices = notebook_choices()
    ids = {value for _, value in choices}
    value = selected if selected in ids else (choices[0][1] if choices else None)
    return (gr.Dropdown(choices=choices, value=value), *load_notebook(value))


def create_notebook(name):
    try:
        notebook = storage.create_notebook(name)
        return (
            gr.Dropdown(choices=notebook_choices(), value=notebook.id),
            "", *load_notebook(notebook.id),
        )
    except Exception as exc:
        raise gr.Error(str(exc))


def rename_notebook(notebook_id, name):
    try:
        require_notebook(notebook_id)
        notebook = storage.rename_notebook(notebook_id, name)
        return gr.Dropdown(choices=notebook_choices(), value=notebook.id), f"Renamed to **{notebook.name}**."
    except Exception as exc:
        raise gr.Error(str(exc))


def delete_notebook(notebook_id, confirmed):
    try:
        require_notebook(notebook_id)
        if not confirmed:
            raise ValueError("Check the confirmation box before deleting.")
        storage.delete_notebook(notebook_id)
        choices = notebook_choices()
        value = choices[0][1] if choices else None
        return (
            gr.Dropdown(choices=choices, value=value), False,
            *load_notebook(value),
        )
    except Exception as exc:
        raise gr.Error(str(exc))


def sources_markdown(notebook_id):
    if not notebook_id:
        return "No sources yet."
    rows = storage.sources(notebook_id)
    if not rows:
        return "No sources yet."
    lines = ["| Source | Type | Chunks |", "|---|---:|---:|"]
    lines.extend(f"| {r['name']} | {r['type']} | {r['chunks']} |" for r in rows)
    return "\n".join(lines)


def load_notebook(notebook_id):
    """Restore the complete view from disk without changing persisted data."""
    if not notebook_id:
        return [], "No sources yet.", "", None, "Create a notebook to begin.", "", "", ""
    try:
        require_notebook(notebook_id)
        files = storage.artifacts(notebook_id)
        latest = files[0].resolve() if files else None
        preview = latest.read_text(encoding="utf-8") if latest else ""
        return (
            storage.history(notebook_id), sources_markdown(notebook_id),
            preview, str(latest) if latest else None, "Notebook loaded.",
            "", "", "",
        )
    except Exception as exc:
        raise gr.Error(str(exc))


def upload_sources(notebook_id, files):
    try:
        require_notebook(notebook_id)
        if not files:
            raise ValueError("Choose at least one PDF, PPTX, or TXT file.")
        messages = []
        for file in files:
            path = file if isinstance(file, str) else file.name
            record = ingestion.ingest_file(notebook_id, path)
            messages.append(f"✓ {record['name']} ({record['chunks']} chunks)")
        return sources_markdown(notebook_id), "\n\n".join(messages)
    except Exception as exc:
        raise gr.Error(str(exc))


def add_url(notebook_id, url):
    try:
        require_notebook(notebook_id)
        record = ingestion.ingest_url(notebook_id, url)
        return sources_markdown(notebook_id), "", f"✓ {record['name']} ({record['chunks']} chunks)"
    except Exception as exc:
        raise gr.Error(str(exc))


def ask(notebook_id, question, method):
    try:
        require_notebook(notebook_id)
        history, citations, timing = rag.answer(notebook_id, question, method)
        return history, "", citations, timing
    except Exception as exc:
        raise gr.Error(str(exc))


def clear_chat(notebook_id):
    try:
        require_notebook(notebook_id)
        storage.clear_history(notebook_id)
        return [], "Chat history cleared."
    except Exception as exc:
        raise gr.Error(str(exc))


def generate_artifact(notebook_id, kind):
    try:
        require_notebook(notebook_id)
        content, path = artifacts.generate(notebook_id, kind)
        return content, path, f"{kind} generated and saved as Markdown."
    except Exception as exc:
        raise gr.Error(str(exc))


with gr.Blocks(title="Notebook RAG Studio", theme=gr.themes.Soft()) as demo:
    gr.Markdown(
        "# Notebook RAG Studio\n"
        "Create isolated notebooks, ingest sources, ask grounded questions, and generate study artifacts."
    )
    if not llm.available:
        gr.Markdown("⚠️ `GROQ_API_KEY` is not configured. Ingestion works, but chat and artifact generation require the key.")

    with gr.Row():
        notebook_dropdown = gr.Dropdown(label="Active notebook", choices=notebook_choices())
        refresh_button = gr.Button("Refresh")
    notebook_status = gr.Markdown()

    with gr.Tab("Notebooks"):
        with gr.Row():
            new_name = gr.Textbox(label="New notebook name")
            create_button = gr.Button("Create", variant="primary")
        with gr.Row():
            rename_name = gr.Textbox(label="New name")
            rename_button = gr.Button("Rename")
        delete_confirm = gr.Checkbox(label="I understand this permanently deletes the selected notebook")
        delete_button = gr.Button("Delete selected notebook", variant="stop")

    with gr.Tab("Sources"):
        upload = gr.File(label="PDF, PPTX, or TXT", file_count="multiple", file_types=[".pdf", ".pptx", ".txt"])
        upload_button = gr.Button("Ingest files", variant="primary")
        with gr.Row():
            url_input = gr.Textbox(label="Single-page web URL", placeholder="https://example.com/article")
            url_button = gr.Button("Ingest URL")
        ingestion_status = gr.Markdown()
        source_table = gr.Markdown("No sources yet.")

    with gr.Tab("Chat"):
        method = gr.Radio(["Vector Search", "Hybrid Search"], value="Hybrid Search", label="Retrieval approach")
        chatbot = gr.Chatbot(label="Notebook conversation", type="messages", height=430)
        with gr.Row():
            question = gr.Textbox(label="Question", placeholder="Ask only about the notebook sources...", scale=5)
            ask_button = gr.Button("Ask", variant="primary", scale=1)
        clear_button = gr.Button("Clear chat")
        timing = gr.Markdown()
        with gr.Accordion("Retrieved chunks and citations", open=False):
            citation_panel = gr.Markdown()

    with gr.Tab("Artifacts"):
        artifact_kind = gr.Radio(["Report", "Quiz"], value="Report", label="Artifact type")
        artifact_button = gr.Button("Generate Markdown artifact", variant="primary")
        artifact_status = gr.Markdown()
        artifact_preview = gr.Markdown()
        artifact_file = gr.File(label="Download latest artifact", interactive=False)

    # Each selection operation restores all notebook-specific outputs together.
    # .input handles user selection only; programmatic updates already restore
    # the view, avoiding duplicate .change callbacks and stale output races.
    notebook_outputs = [
        chatbot, source_table, artifact_preview, artifact_file, notebook_status,
        citation_panel, timing, artifact_status,
    ]
    demo.load(refresh, inputs=notebook_dropdown, outputs=[notebook_dropdown, *notebook_outputs])
    refresh_button.click(refresh, inputs=notebook_dropdown, outputs=[notebook_dropdown, *notebook_outputs])
    create_button.click(create_notebook, inputs=new_name, outputs=[notebook_dropdown, new_name, *notebook_outputs])
    rename_button.click(rename_notebook, inputs=[notebook_dropdown, rename_name], outputs=[notebook_dropdown, notebook_status])
    delete_button.click(delete_notebook, inputs=[notebook_dropdown, delete_confirm], outputs=[notebook_dropdown, delete_confirm, *notebook_outputs])
    notebook_dropdown.input(load_notebook, inputs=notebook_dropdown, outputs=notebook_outputs)
    upload_button.click(upload_sources, inputs=[notebook_dropdown, upload], outputs=[source_table, ingestion_status])
    url_button.click(add_url, inputs=[notebook_dropdown, url_input], outputs=[source_table, url_input, ingestion_status])
    ask_button.click(ask, inputs=[notebook_dropdown, question, method], outputs=[chatbot, question, citation_panel, timing])
    question.submit(ask, inputs=[notebook_dropdown, question, method], outputs=[chatbot, question, citation_panel, timing])
    clear_button.click(clear_chat, inputs=notebook_dropdown, outputs=[chatbot, timing])
    artifact_button.click(generate_artifact, inputs=[notebook_dropdown, artifact_kind], outputs=[artifact_preview, artifact_file, artifact_status])


if __name__ == "__main__":
    demo.queue().launch(server_name="0.0.0.0", server_port=7860)
