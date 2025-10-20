"""Gradio Chat Interface for AEGIS RAG.

Sprint 10 Features 10.2-10.5: Gradio UI Implementation

This module provides a complete Gradio-based chat interface including:
- Chat interface with conversation history (Feature 10.2)
- Document upload and indexing (Feature 10.3)
- Conversation history persistence (Feature 10.4)
- Health dashboard integration (Feature 10.5)

Installation:
    pip install gradio>=4.0.0

Usage:
    python src/ui/gradio_app.py

    Or:
    python -m src.ui.gradio_app
"""

import asyncio
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
import structlog

try:
    import gradio as gr
except ImportError:
    raise ImportError(
        "Gradio is not installed. Please install it with: pip install gradio>=4.0.0"
    )

from src.core.config import settings

logger = structlog.get_logger(__name__)

# API Configuration
API_BASE_URL = f"http://localhost:{settings.api_port}"
CHAT_ENDPOINT = f"{API_BASE_URL}/api/v1/chat/"
HEALTH_ENDPOINT = f"{API_BASE_URL}/health"  # Use main health endpoint instead


class GradioApp:
    """Gradio Chat Application for AEGIS RAG.

    This class manages the Gradio UI and integrates with the FastAPI backend.
    """

    def __init__(self):
        """Initialize Gradio app."""
        self.session_id = str(uuid.uuid4())
        self.client = httpx.AsyncClient(timeout=30.0)

        logger.info(
            "gradio_app_initialized",
            session_id=self.session_id,
            api_base_url=API_BASE_URL
        )

    async def chat(
        self,
        message: str,
        history: list[list[str]]
    ) -> tuple[list[list[str]], str]:
        """Process chat message.

        Args:
            message: User message
            history: Chat history (list of [user_msg, bot_msg] pairs)

        Returns:
            Tuple of (updated history, cleared input)
        """
        if not message.strip():
            return history, ""

        logger.info("chat_message_received", message=message[:100], session_id=self.session_id)

        try:
            # Call chat API
            response = await self.client.post(
                CHAT_ENDPOINT,
                json={
                    "query": message,
                    "session_id": self.session_id,
                    "include_sources": True
                }
            )

            if response.status_code == 200:
                data = response.json()
                answer = data["answer"]
                sources = data.get("sources", [])

                # Format answer with sources
                formatted_answer = self._format_answer_with_sources(answer, sources)

                # Add to history
                history.append([message, formatted_answer])

                logger.info(
                    "chat_response_success",
                    answer_length=len(answer),
                    sources_count=len(sources),
                    session_id=self.session_id
                )

                return history, ""
            else:
                error_msg = f"Fehler {response.status_code}: {response.text}"
                history.append([message, f"⚠️ {error_msg}"])
                logger.error("chat_api_error", status=response.status_code, error=response.text)
                return history, ""

        except Exception as e:
            error_msg = f"Verbindungsfehler: {str(e)}"
            history.append([message, f"❌ {error_msg}"])
            logger.error("chat_exception", error=str(e), session_id=self.session_id)
            return history, ""

    def _format_answer_with_sources(self, answer: str, sources: list[dict]) -> str:
        """Format answer with source citations.

        Args:
            answer: Generated answer
            sources: List of source documents

        Returns:
            Formatted answer string with citations
        """
        formatted = answer

        if sources:
            formatted += "\n\n---\n**📚 Quellen:**\n"
            for i, source in enumerate(sources[:3], 1):  # Top 3 sources
                title = source.get("title", "Unknown")
                score = source.get("score", 0.0)
                if score:
                    formatted += f"{i}. {title} (Relevanz: {score:.2f})\n"
                else:
                    formatted += f"{i}. {title}\n"

        return formatted

    async def upload_document(self, file) -> str:
        """Upload and index a document.

        Args:
            file: Uploaded file object from Gradio

        Returns:
            Status message
        """
        if file is None:
            return "⚠️ Bitte wählen Sie eine Datei."

        logger.info("document_upload_started", filename=file.name)

        try:
            # Call ingestion API
            files = {"file": (file.name, open(file.name, "rb"), "application/octet-stream")}

            response = await self.client.post(
                f"{API_BASE_URL}/api/v1/documents/upload",
                files=files
            )

            if response.status_code == 200:
                data = response.json()
                chunks = data.get("chunks_created", 0)
                logger.info("document_upload_success", filename=file.name, chunks=chunks)
                return f"✅ Dokument '{Path(file.name).name}' erfolgreich indexiert!\n📊 {chunks} Chunks erstellt."
            else:
                logger.error("document_upload_failed", status=response.status_code)
                return f"❌ Fehler beim Hochladen: {response.text}"

        except Exception as e:
            logger.error("document_upload_exception", error=str(e))
            return f"❌ Fehler beim Hochladen: {str(e)}"

    async def clear_chat(self) -> list:
        """Clear conversation history.

        Returns:
            Empty history list
        """
        logger.info("clearing_conversation", session_id=self.session_id)

        try:
            # Call delete history API
            response = await self.client.delete(
                f"{API_BASE_URL}/api/v1/chat/history/{self.session_id}"
            )

            if response.status_code == 200:
                logger.info("conversation_cleared", session_id=self.session_id)
            else:
                logger.warning("conversation_clear_failed", status=response.status_code)

        except Exception as e:
            logger.error("conversation_clear_exception", error=str(e))

        # Generate new session ID
        self.session_id = str(uuid.uuid4())
        logger.info("new_session_created", session_id=self.session_id)

        return []  # Empty chatbot

    async def get_health_stats(self) -> dict[str, Any]:
        """Get system health statistics.

        Returns:
            Health metrics dictionary
        """
        try:
            response = await self.client.get(HEALTH_ENDPOINT)

            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Health API returned {response.status_code}"}

        except Exception as e:
            logger.error("health_check_failed", error=str(e))
            return {"error": str(e)}

    def build_interface(self) -> gr.Blocks:
        """Build Gradio interface.

        Returns:
            Gradio Blocks app
        """
        # Custom CSS
        custom_css = """
        #chatbot {
            height: 600px;
        }
        .source-citation {
            font-size: 0.9em;
            color: #666;
        }
        """

        with gr.Blocks(
            title="AEGIS RAG",
            theme=gr.themes.Soft(),
            css=custom_css
        ) as demo:
            gr.Markdown("# 🛡️ AEGIS RAG")
            gr.Markdown("**Agentic Enterprise Graph Intelligence System**")
            gr.Markdown("Stellen Sie Fragen zu Ihren Dokumenten oder laden Sie neue Dokumente hoch.")

            with gr.Tabs() as tabs:
                # Tab 1: Chat Interface (Feature 10.2)
                with gr.Tab("💬 Chat"):
                    chatbot = gr.Chatbot(
                        value=[],
                        elem_id="chatbot",
                        label="Conversation",
                        height=600,
                        show_copy_button=True
                    )

                    with gr.Row():
                        msg = gr.Textbox(
                            placeholder="Ihre Frage...",
                            show_label=False,
                            elem_id="user-input",
                            scale=9,
                            lines=2
                        )
                        submit = gr.Button("Senden", elem_id="submit-btn", scale=1, variant="primary")

                    with gr.Row():
                        clear = gr.Button("🗑️ Chat löschen", elem_id="clear-btn")

                    # Example queries
                    gr.Examples(
                        examples=[
                            "Was ist AEGIS RAG?",
                            "Erkläre die Memory-Architektur",
                            "Welche Komponenten hat das System?",
                            "Was wurde in Sprint 9 implementiert?",
                            "Wie funktioniert der CoordinatorAgent?",
                        ],
                        inputs=msg,
                        label="Beispiel-Fragen"
                    )

                    # Event handlers
                    submit.click(
                        self.chat,
                        inputs=[msg, chatbot],
                        outputs=[chatbot, msg]
                    )
                    msg.submit(
                        self.chat,
                        inputs=[msg, chatbot],
                        outputs=[chatbot, msg]
                    )
                    clear.click(
                        self.clear_chat,
                        outputs=chatbot
                    )

                # Tab 2: Document Upload (Feature 10.3)
                with gr.Tab("📄 Dokumente hochladen"):
                    gr.Markdown("### Dokumente zum RAG-System hinzufügen")
                    gr.Markdown("Unterstützte Formate: PDF, TXT, MD, DOCX, CSV")

                    file_upload = gr.File(
                        label="Datei auswählen",
                        file_types=[".pdf", ".txt", ".md", ".docx", ".csv"],
                        elem_id="file-upload"
                    )

                    upload_btn = gr.Button(
                        "Hochladen & Indexieren",
                        elem_id="upload-btn",
                        variant="primary"
                    )
                    upload_status = gr.Textbox(
                        label="Status",
                        elem_id="upload-status",
                        interactive=False,
                        lines=3
                    )

                    upload_btn.click(
                        self.upload_document,
                        inputs=file_upload,
                        outputs=upload_status
                    )

                # Tab 3: System Health (Feature 10.5)
                with gr.Tab("📊 System Health"):
                    gr.Markdown("### System Status & Metrics")

                    refresh_btn = gr.Button("🔄 Refresh", elem_id="refresh-health")

                    health_json = gr.JSON(
                        label="Health Metrics",
                        elem_id="health-json"
                    )

                    refresh_btn.click(
                        self.get_health_stats,
                        outputs=health_json
                    )

                    # Auto-load on tab open
                    demo.load(self.get_health_stats, outputs=health_json)

                # Tab 4: About
                with gr.Tab("ℹ️ Über AEGIS RAG"):
                    gr.Markdown("""
                    ## Über AEGIS RAG

                    **AEGIS RAG** (Agentic Enterprise Graph Intelligence System) ist ein
                    produktionsreifes RAG-System mit Multi-Agent Orchestration.

                    ### Features:
                    - 🤖 Multi-Agent System (LangGraph)
                    - 🔍 Hybrid Search (Vector + Graph + Keyword)
                    - 💾 3-Layer Memory Architecture (Redis, Qdrant, Graphiti)
                    - 📊 Real-time Monitoring & Observability
                    - 🔌 MCP Client Integration

                    ### Technologie-Stack:
                    - **Backend:** FastAPI, LangGraph, LlamaIndex
                    - **Vector DB:** Qdrant
                    - **Graph DB:** Neo4j
                    - **Cache:** Redis
                    - **LLM:** Ollama (qwen2.5:7b)
                    - **Embeddings:** nomic-embed-text

                    ### Session Info:
                    """)

                    session_info = gr.Markdown(f"**Session ID:** `{self.session_id}`")

            # Footer
            gr.Markdown("---")
            gr.Markdown(
                "Built with ❤️ using [Gradio](https://gradio.app) | "
                "[API Docs](http://localhost:8000/docs) | "
                "[Health](http://localhost:8000/health)"
            )

        return demo

    def launch(
        self,
        server_name: str = "0.0.0.0",
        server_port: int = 7860,
        share: bool = False
    ):
        """Launch Gradio app.

        Args:
            server_name: Server host (default: 0.0.0.0)
            server_port: Server port (default: 7860)
            share: Create public URL (default: False)
        """
        demo = self.build_interface()

        logger.info(
            "launching_gradio_app",
            server_name=server_name,
            server_port=server_port,
            share=share
        )

        demo.launch(
            server_name=server_name,
            server_port=server_port,
            share=share
        )


def main():
    """Main entry point."""
    import logging

    # Configure logging
    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    )

    logger.info("=== AEGIS RAG Gradio UI ===")
    logger.info("Starting Gradio interface...")
    logger.info(f"API Backend: {API_BASE_URL}")
    logger.info(f"Make sure FastAPI is running on port {settings.api_port}")

    # Create and launch app
    app = GradioApp()
    app.launch()


if __name__ == "__main__":
    main()
