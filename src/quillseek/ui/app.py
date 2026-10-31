"""Gradio app shell and Documents tab, communicating only with the REST API."""

from __future__ import annotations

import base64
import html
import time
from pathlib import Path
from typing import Any

import gradio as gr

from quillseek.ui.api_client import (
    APIClient,
    BackendAPIError,
    BackendError,
)
from quillseek.ui.theme import THEME

ROOT = Path(__file__).resolve().parents[3]
CSS_PATH = Path(__file__).with_name("styles.css")
HEADERS = ["Document", "Type", "Pages", "Chunks", "Status"]


def _image_data(asset_name: str) -> str:
    data = (ROOT / "assets" / asset_name).read_bytes()
    encoded = base64.b64encode(data).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


def _document_view(client: APIClient) -> tuple[list[list[Any]], str, Any]:
    """Format indexed and pending backend documents for the table and selector."""
    try:
        payload = client.documents()
    except BackendError as error:
        return [], f"Could not load documents: {html.escape(str(error))}", gr.update(choices=[], value=None)

    indexed = payload.get("documents", [])
    pending = payload.get("pending_uploads", [])
    rows: list[list[Any]] = []
    choices: list[tuple[str, str]] = []
    for document in indexed:
        name = document.get("doc_name", "Unknown document")
        pages = document.get("pages", [])
        rows.append(
            [name, Path(name).suffix.lstrip(".").upper(), str(len(pages)), str(document.get("chunk_count", 0)), "Indexed"]
        )
        if document.get("doc_id"):
            choices.append((name, document["doc_id"]))
    for name in pending:
        rows.append([name, Path(name).suffix.lstrip(".").upper(), "—", "—", "Pending indexing"])

    empty = (
        ""
        if rows
        else "### Your library is empty\nUpload a PDF, DOCX, or TXT file to get started."
    )
    return rows, empty, gr.update(choices=choices, value=None)


def build_app(client: APIClient | None = None) -> gr.Blocks:
    """Build the Quillseek web app; every action uses the backend API client."""
    api = client or APIClient()
    logo_header = _image_data("logo-dark.svg")
    logo_footer = _image_data("logo.svg")
    CSS_PATH.read_text(encoding="utf-8")

    with gr.Blocks(title="Quillseek") as demo:
        gr.HTML(
            f"""<header class="qs-header">
              <div class="qs-brand"><img src="{logo_header}" alt="Quillseek"></div>
              <p class="qs-tagline">Find the answer in your documents, with sources you can check.</p>
            </header>"""
        )
        health_status = gr.Markdown("Checking backend status…", elem_id="backend-health")

        with gr.Tabs():
            with gr.Tab("Documents", id="documents"):
                gr.Markdown("## Your document library\nUpload and index the files you want to search.")
                with gr.Row(elem_classes=["qs-card"]):
                    uploads = gr.File(
                        label="Choose documents",
                        file_count="multiple",
                        file_types=[".pdf", ".docx", ".txt"],
                        type="filepath",
                    )
                    upload_button = gr.Button("Upload files", variant="primary")
                upload_status = gr.Markdown()
                with gr.Row():
                    index_button = gr.Button("Index pending documents", variant="primary")
                    progress = gr.Slider(
                        minimum=0,
                        maximum=100,
                        value=0,
                        step=1,
                        label="Indexing progress",
                        interactive=False,
                    )
                index_status = gr.Markdown()
                document_table = gr.Dataframe(
                    headers=HEADERS,
                    datatype=["str", "str", "str", "str", "str"],
                    value=[],
                    interactive=False,
                    wrap=True,
                    label="Documents",
                )
                empty_state = gr.Markdown(
                    "### Your library is empty\nUpload a PDF, DOCX, or TXT file to get started.",
                    elem_classes=["empty-state"],
                )
                with gr.Row():
                    delete_choice = gr.Dropdown(
                        label="Indexed document to delete", choices=[], value=None
                    )
                    delete_button = gr.Button("Delete selected document")
                delete_status = gr.Markdown()
                with gr.Row():
                    clear_confirm = gr.Checkbox(
                        label="I understand this deletes all indexed documents and pending uploads"
                    )
                    clear_button = gr.Button("Clear collection", variant="stop")
                clear_status = gr.Markdown()

            with gr.Tab("Search", id="search"):
                gr.Markdown("## Search\nSearch your indexed documents and inspect matching passages.")
                gr.Markdown("Search controls will be available in the next build step.", elem_classes=["empty-state"])

            with gr.Tab("Ask", id="ask"):
                gr.Markdown("## Ask your documents\nGet a concise answer grounded in your indexed sources.")
                gr.Markdown("Question answering controls will be available in the next build step.", elem_classes=["empty-state"])

        gr.HTML(
            f"""<footer class="qs-footer">
              <img src="{logo_footer}" alt="Quillseek">
              <span>Built during the seKer AI internship</span>
              <span>Your index stays on this machine; retrieved passages are sent to Gemini to answer questions.</span>
            </footer>"""
        )

        def backend_status() -> str:
            try:
                status = api.health()
            except BackendError as error:
                return f"🔴 Backend unavailable — {html.escape(str(error))}"
            backend = "🟢 Backend online" if status.get("status") == "ok" else "🟠 Backend needs attention"
            gemini = "configured" if status.get("gemini_configured") else "not configured"
            reachability = status.get("gemini_reachable")
            if reachability is True:
                gemini += " and reachable"
            elif reachability is False and status.get("gemini_configured"):
                gemini += " but not reachable"
            return f"{backend} · Gemini {gemini} · {status.get('chunk_count', 0)} indexed chunks"

        def refresh_documents():
            rows, empty, choices = _document_view(api)
            return rows, empty, choices

        def upload_documents(file_paths):
            if not file_paths:
                return "Choose at least one file.", *refresh_documents()
            try:
                result = api.upload_files(file_paths)
                message = f"Uploaded {result.get('count', len(result.get('uploaded', [])))} file(s). They are ready to index."
            except (BackendError, OSError, ValueError) as error:
                message = f"Upload failed: {html.escape(str(error))}"
            return message, *refresh_documents()

        def index_documents():
            try:
                job = api.start_index()
                job_id = job["job_id"]
            except (BackendError, KeyError) as error:
                rows, empty, choices = refresh_documents()
                yield f"Indexing could not start: {html.escape(str(error))}", 0, rows, empty, choices
                return

            finished = False
            status: dict[str, Any] = {"stage": "queued", "percent": 0, "finished": False}
            while not finished:
                try:
                    status = api.index_status(job_id)
                except BackendError as error:
                    rows, empty, choices = refresh_documents()
                    yield f"Could not read indexing progress: {html.escape(str(error))}", status.get("percent", 0), rows, empty, choices
                    return
                failed = status.get("failed", [])
                message = (
                    f"Indexing **{status.get('stage', 'working')}** · "
                    f"{status.get('indexed', 0)} indexed · {status.get('skipped', 0)} skipped · "
                    f"{status.get('failed_count', len(failed))} failed"
                )
                for failure in failed:
                    message += f"\n\n- {html.escape(failure.get('file_name', 'File'))}: {html.escape(failure.get('reason', 'Indexing failed'))}"
                rows, empty, choices = refresh_documents()
                yield message, status.get("percent", 0), rows, empty, choices
                finished = status.get("finished", False)
                if not finished:
                    time.sleep(0.5)

        def delete_document(doc_id):
            if not doc_id:
                message = "Choose an indexed document first."
            else:
                try:
                    api.delete_document(doc_id)
                    message = "Document deleted."
                except BackendError as error:
                    message = f"Delete failed: {html.escape(str(error))}"
            return message, *refresh_documents()

        def clear_collection(confirmed):
            if not confirmed:
                return "Confirm the clear action before deleting the collection.", gr.update(value=False), *refresh_documents()
            try:
                api.reset_collection()
                message = "Collection and pending uploads cleared."
            except BackendError as error:
                message = f"Clear failed: {html.escape(str(error))}"
            return message, gr.update(value=False), *refresh_documents()

        demo.load(backend_status, outputs=health_status)
        demo.load(refresh_documents, outputs=[document_table, empty_state, delete_choice])
        upload_button.click(
            upload_documents,
            inputs=uploads,
            outputs=[upload_status, document_table, empty_state, delete_choice],
        )
        index_button.click(
            index_documents,
            outputs=[index_status, progress, document_table, empty_state, delete_choice],
        )
        delete_button.click(
            delete_document,
            inputs=delete_choice,
            outputs=[delete_status, document_table, empty_state, delete_choice],
        )
        clear_button.click(
            clear_collection,
            inputs=clear_confirm,
            outputs=[clear_status, clear_confirm, document_table, empty_state, delete_choice],
        )

    return demo


app = build_app()
