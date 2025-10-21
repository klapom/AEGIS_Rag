"""Gradio Chat Interface for AEGIS RAG.

Sprint 10 Features 10.2-10.7: Gradio UI Implementation

This module provides a complete Gradio-based chat interface including:
- Chat interface with conversation history (Feature 10.2)
- Document upload and indexing (Feature 10.3)
- Conversation history persistence (Feature 10.4)
- Health dashboard integration (Feature 10.5)
- MCP Server Management (Feature 10.6)
- Tool Call Visibility (Feature 10.7)

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
import pandas as pd
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
        # Increased timeout for document upload (embedding generation can take 60+ seconds)
        self.client = httpx.AsyncClient(timeout=180.0)
        self.mcp_client = None  # MCP Client instance (Feature 10.6)

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

    async def upload_document(self, file, progress=gr.Progress()) -> str:
        """Upload and index a document with progress tracking.

        Args:
            file: Uploaded file object from Gradio
            progress: Gradio Progress tracker

        Returns:
            Status message
        """
        if file is None:
            return "⚠️ Bitte wählen Sie eine Datei."

        logger.info("document_upload_started", filename=file.name)

        try:
            # Progress: Start upload
            progress(0, desc="📤 Datei wird hochgeladen...")

            # Call ingestion API
            files = {"file": (file.name, open(file.name, "rb"), "application/octet-stream")}

            # Progress: Processing
            progress(0.2, desc="📄 Dokument wird geladen...")

            # Start async task for progress simulation
            async def simulate_progress():
                """Simulate progress for long-running embedding generation."""
                steps = [
                    (0.3, "✂️ Text wird in Chunks aufgeteilt..."),
                    (0.5, "🧠 Embeddings werden generiert (kann 60+ Sek. dauern)..."),
                    (0.7, "🔍 Chunks werden in Qdrant indexiert..."),
                    (0.9, "✅ Finalisierung...")
                ]
                for prog, desc in steps:
                    await asyncio.sleep(15)  # Update every 15 seconds
                    progress(prog, desc=desc)

            # Start progress simulation
            progress_task = asyncio.create_task(simulate_progress())

            try:
                response = await self.client.post(
                    f"{API_BASE_URL}/api/v1/retrieval/upload",
                    files=files
                )
            finally:
                # Cancel progress simulation
                progress_task.cancel()
                try:
                    await progress_task
                except asyncio.CancelledError:
                    pass

            progress(1.0, desc="✅ Upload abgeschlossen!")

            if response.status_code == 200:
                data = response.json()
                chunks = data.get("chunks_created", 0)
                embeddings = data.get("embeddings_generated", 0)
                duration = data.get("duration_seconds", 0)

                logger.info("document_upload_success", filename=file.name, chunks=chunks)
                return f"""✅ Dokument '{Path(file.name).name}' erfolgreich indexiert!

📊 Statistik:
  • {chunks} Chunks erstellt
  • {embeddings} Embeddings generiert
  • ⏱️ Dauer: {duration:.1f} Sekunden"""
            else:
                logger.error("document_upload_failed", status=response.status_code)
                return f"❌ Fehler beim Hochladen: {response.text}"

        except asyncio.CancelledError:
            logger.warning("document_upload_cancelled", filename=file.name)
            return "⚠️ Upload wurde abgebrochen."
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

    async def connect_mcp_server(
        self,
        name: str,
        transport: str,
        endpoint: str
    ) -> tuple[dict, pd.DataFrame]:
        """Connect to MCP server and discover tools.

        Feature 10.6: MCP Server Management

        Args:
            name: Server name
            transport: Transport type (HTTP or STDIO)
            endpoint: Server endpoint or command

        Returns:
            Tuple of (status dict, tools DataFrame)
        """
        try:
            # Initialize MCP Client if needed
            if self.mcp_client is None:
                from src.components.mcp import MCPClient
                self.mcp_client = MCPClient()

            # Create server config
            from src.components.mcp import MCPServer, TransportType
            server = MCPServer(
                name=name,
                transport=TransportType.HTTP if transport == "HTTP" else TransportType.STDIO,
                endpoint=endpoint,
                description=f"User-connected {transport} server"
            )

            # Connect to server
            logger.info("connecting_to_mcp_server", name=name, transport=transport)
            success = await self.mcp_client.connect(server)

            if not success:
                return {"error": "Connection failed"}, pd.DataFrame()

            # Get server status
            stats = self.mcp_client.get_stats()
            status = {
                "status": "connected",
                "server_name": name,
                "transport": transport,
                "connected_servers": stats.connected_servers,
                "total_tools": stats.total_tools
            }

            # Get available tools
            tools = await self.mcp_client.list_tools()
            tools_df = pd.DataFrame([
                {
                    "Tool Name": tool.name,
                    "Server": tool.server,
                    "Description": tool.description[:100] + "..." if len(tool.description) > 100 else tool.description,
                    "Parameters": str(len(tool.parameters.get("properties", {}))) + " params"
                }
                for tool in tools
            ])

            logger.info("mcp_server_connected", name=name, tools_count=len(tools))
            return status, tools_df

        except Exception as e:
            logger.error("mcp_connection_failed", error=str(e), exc_info=True)
            return {"error": str(e)}, pd.DataFrame()

    async def disconnect_mcp_server(self, server_name: str) -> dict:
        """Disconnect from MCP server.

        Args:
            server_name: Name of server to disconnect

        Returns:
            Status dictionary
        """
        try:
            if self.mcp_client and server_name:
                await self.mcp_client.disconnect(server_name)
                logger.info("mcp_server_disconnected", name=server_name)
                return {
                    "status": "disconnected",
                    "server_name": server_name
                }
            return {"error": "No MCP client or server name"}
        except Exception as e:
            logger.error("mcp_disconnect_failed", error=str(e))
            return {"error": str(e)}

    async def refresh_mcp_tools(self) -> tuple[dict, pd.DataFrame]:
        """Refresh MCP tools list.

        Returns:
            Tuple of (status dict, tools DataFrame)
        """
        try:
            if not self.mcp_client:
                return {"error": "No MCP client initialized"}, pd.DataFrame()

            stats = self.mcp_client.get_stats()
            status = {
                "connected_servers": stats.connected_servers,
                "total_tools": stats.total_tools,
                "total_calls": stats.total_calls,
                "successful_calls": stats.successful_calls
            }

            tools = await self.mcp_client.list_tools()
            tools_df = pd.DataFrame([
                {
                    "Tool Name": tool.name,
                    "Server": tool.server,
                    "Description": tool.description[:100] + "..." if len(tool.description) > 100 else tool.description,
                    "Parameters": str(len(tool.parameters.get("properties", {}))) + " params"
                }
                for tool in tools
            ])

            return status, tools_df

        except Exception as e:
            logger.error("mcp_refresh_failed", error=str(e))
            return {"error": str(e)}, pd.DataFrame()

    def build_interface(self) -> gr.Blocks:
        """Build Gradio interface.

        Returns:
            Gradio Blocks app
        """
        # Custom CSS
        custom_css = """
        #chatbot {
            height: 500px;
        }
        #user-input {
            font-size: 1.1em;
        }
        .source-citation {
            font-size: 0.9em;
            color: #666;
        }
        .mcp-status {
            background: #f0f0f0;
            padding: 10px;
            border-radius: 5px;
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
                # Tab 1: Chat Interface (Feature 10.2) - REORGANIZED: Input first, History below
                with gr.Tab("💬 Chat"):
                    # Input Section (moved to top)
                    with gr.Row():
                        msg = gr.Textbox(
                            placeholder="Ihre Frage...",
                            show_label=False,
                            elem_id="user-input",
                            scale=9,
                            lines=2
                        )
                        submit = gr.Button("Senden", elem_id="submit-btn", scale=1, variant="primary")

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

                    # History Section (below input - more intuitive)
                    chatbot = gr.Chatbot(
                        value=[],
                        elem_id="chatbot",
                        label="Conversation History",
                        height=500,
                        show_copy_button=True
                    )

                    with gr.Row():
                        clear = gr.Button("🗑️ Chat löschen", elem_id="clear-btn")

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

                # Tab 3: MCP Tools (Feature 10.6)
                with gr.Tab("🔧 MCP Tools"):
                    gr.Markdown("### MCP Server Verwaltung")
                    gr.Markdown("Verbinden Sie externe MCP-Server, um zusätzliche Tools zu nutzen.")

                    # Server Connection Section
                    with gr.Row():
                        with gr.Column(scale=2):
                            server_name = gr.Textbox(
                                label="Server Name",
                                placeholder="filesystem-server",
                                value="filesystem"
                            )
                            server_type = gr.Radio(
                                choices=["STDIO", "HTTP"],
                                label="Transport Type",
                                value="STDIO"
                            )
                            server_endpoint = gr.Textbox(
                                label="Endpoint/Command",
                                placeholder="npx @modelcontextprotocol/server-filesystem /tmp",
                                lines=2
                            )

                        with gr.Column(scale=1):
                            connect_btn = gr.Button("🔌 Verbinden", variant="primary")
                            disconnect_btn = gr.Button("❌ Trennen", variant="secondary")

                    # Server Status Display
                    mcp_status = gr.JSON(label="Server Status", value={})

                    # Available Tools Display
                    gr.Markdown("### Verfügbare Tools")
                    mcp_tools_table = gr.Dataframe(
                        headers=["Tool Name", "Server", "Description", "Parameters"],
                        label="Discovered MCP Tools",
                        interactive=False
                    )

                    refresh_tools_btn = gr.Button("🔄 Tools neu laden")

                    # Example MCP Servers
                    gr.Markdown("### Beispiel-Server")
                    gr.Markdown("""
                    **Filesystem Server:**
                    - Name: `filesystem`
                    - Transport: `STDIO`
                    - Command: `npx @modelcontextprotocol/server-filesystem /tmp`

                    **HTTP Server (Beispiel):**
                    - Name: `custom-http`
                    - Transport: `HTTP`
                    - Endpoint: `http://localhost:3000`
                    """)

                    # Event handlers
                    connect_btn.click(
                        self.connect_mcp_server,
                        inputs=[server_name, server_type, server_endpoint],
                        outputs=[mcp_status, mcp_tools_table]
                    )

                    disconnect_btn.click(
                        self.disconnect_mcp_server,
                        inputs=server_name,
                        outputs=mcp_status
                    )

                    refresh_tools_btn.click(
                        self.refresh_mcp_tools,
                        outputs=[mcp_status, mcp_tools_table]
                    )

                # Tab 4: System Health (Feature 10.5)
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

                # Tab 5: About
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
                    - 🔌 MCP Client Integration (externe Tools)

                    ### Technologie-Stack:
                    - **Backend:** FastAPI, LangGraph, LlamaIndex
                    - **Vector DB:** Qdrant
                    - **Graph DB:** Neo4j
                    - **Cache:** Redis
                    - **LLM:** Ollama (qwen2.5:7b)
                    - **Embeddings:** nomic-embed-text
                    - **MCP:** Model Context Protocol Client

                    ### Sprint 10 Features:
                    - ✅ Chat Interface mit Session Memory
                    - ✅ Dokument Upload mit Progress Tracking
                    - ✅ BM25 Index Persistierung
                    - ✅ MCP Server Management (Feature 10.6)
                    - ✅ Hybrid Search (77 Dokumente indexiert)

                    ### Session Info:
                    """)

                    session_info = gr.Markdown(f"**Session ID:** `{self.session_id}`")

                    gr.Markdown("""
                    ### Nützliche Links:
                    - [API Docs](http://localhost:8000/docs)
                    - [Health Endpoint](http://localhost:8000/health)
                    - [Prometheus Metrics](http://localhost:9090)
                    - [Grafana Dashboard](http://localhost:3000)
                    """)

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
