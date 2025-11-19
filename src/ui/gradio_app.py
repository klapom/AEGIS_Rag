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
import uuid
from pathlib import Path
from typing import Any

import httpx
import pandas as pd
import structlog

try:
    import gradio as gr
except ImportError as e:
    raise ImportError(
        "Gradio is not installed. Please install it with: pip install gradio>=4.0.0"
    ) from e

import contextlib

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

    def __init__(self) -> None:
        """Initialize Gradio app."""
        self.session_id = str(uuid.uuid4())
        # Increased timeout for document upload (embedding generation can take 60+ seconds)
        self.client = httpx.AsyncClient(timeout=180.0)
        self.mcp_client = None  # MCP Client instance (Feature 10.6)

        logger.info("gradio_app_initialized", session_id=self.session_id, api_base_url=API_BASE_URL)

    async def chat(self, message: str, history: list[dict]) -> tuple[list[dict], str]:
        """Process chat message.

        Args:
            message: User message
            history: Chat history (list of message dicts with role and content)

        Returns:
            Tuple of (updated history, cleared input)
        """
        if not message.strip():
            return history, ""

        logger.info("chat_message_received", message=message[:100], session_id=self.session_id)

        try:
            # Call chat API (Feature 10.7: include tool calls)
            response = await self.client.post(
                CHAT_ENDPOINT,
                json={
                    "query": message,
                    "session_id": self.session_id,
                    "include_sources": True,
                    "include_tool_calls": True,  # Feature 10.7
                },
            )

            if response.status_code == 200:
                data = response.json()
                answer = data["answer"]
                sources = data.get("sources", [])
                tool_calls = data.get("tool_calls", [])  # Feature 10.7

                # Format answer with sources and tool calls (Feature 10.7)
                formatted_answer = self._format_answer_with_sources_and_tools(
                    answer, sources, tool_calls
                )

                # Add to history (messages format for markdown rendering)
                history.append({"role": "user", "content": message})
                history.append({"role": "assistant", "content": formatted_answer})

                logger.info(
                    "chat_response_success",
                    answer_length=len(answer),
                    sources_count=len(sources),
                    tool_calls_count=len(tool_calls),  # Feature 10.7
                    session_id=self.session_id,
                )

                return history, ""
            else:
                error_msg = f"Fehler {response.status_code}: {response.text}"
                history.append({"role": "user", "content": message})
                history.append({"role": "assistant", "content": f"⚠️ {error_msg}"})
                logger.error("chat_api_error", status=response.status_code, error=response.text)
                return history, ""

        except Exception as e:
            error_msg = f"Verbindungsfehler: {str(e)}"
            history.append({"role": "user", "content": message})
            history.append({"role": "assistant", "content": f"❌ {error_msg}"})
            logger.error("chat_exception", error=str(e), session_id=self.session_id)
            return history, ""

    def _format_answer_with_sources_and_tools(
        self, answer: str, sources: list[dict], tool_calls: list[dict]
    ) -> str:
        """Format answer with source citations and MCP tool call information (Feature 10.7).

        Args:
            answer: Generated answer
            sources: list of source documents
            tool_calls: list of MCP tool calls

        Returns:
            Formatted answer string with citations and tool calls
        """
        formatted = answer

        # Add tool calls section (Feature 10.7)
        if tool_calls:
            formatted += "\n\n---\n**🔧 MCP Tool Calls:**\n"
            for i, call in enumerate(tool_calls, 1):
                tool_name = call.get("tool_name", "unknown")
                server = call.get("server", "unknown")
                duration = call.get("duration_ms", 0.0)
                success = call.get("success", True)
                error = call.get("error")

                # Format each tool call
                status_icon = "✅" if success else "❌"
                formatted += f"{i}. {status_icon} **{tool_name}** ({server})\n"
                formatted += f"   ⏱️ {duration:.1f}ms"

                if error:
                    formatted += f"\n   ⚠️ Error: {error}"
                else:
                    # Show result preview (first 100 chars)
                    result = call.get("result")
                    if result:
                        result_preview = str(result)[:100]
                        if len(str(result)) > 100:
                            result_preview += "..."
                        formatted += f"\n   📄 Result: {result_preview}"

                formatted += "\n"

        # Add sources section
        if sources:
            formatted += "\n---\n**📚 Quellen:**\n"
            for i, source in enumerate(sources[:3], 1):  # Top 3 sources
                title = source.get("title", "Unknown")
                score = source.get("score", 0.0)
                if score:
                    formatted += f"{i}. {title} (Relevanz: {score:.2f})\n"
                else:
                    formatted += f"{i}. {title}\n"

        return formatted

    async def upload_document(self, files, progress=gr.Progress()) -> str:
        """Upload and index document(s) with progress tracking.

        Args:
            files: Uploaded file object(s) from Gradio (single file or list of files)
            progress: Gradio Progress tracker

        Returns:
            Status message
        """
        if files is None:
            return "⚠️ Bitte wählen Sie mindestens eine Datei."

        # Handle both single file and multiple files
        if not isinstance(files, list):
            files = [files]

        if len(files) == 0:
            return "⚠️ Bitte wählen Sie mindestens eine Datei."

        logger.info("document_upload_started", file_count=len(files))

        # Track results
        results = []
        total_chunks = 0
        total_embeddings = 0
        total_duration = 0.0
        successful = 0
        failed = 0

        try:
            # Process each file
            for idx, file in enumerate(files, 1):
                idx / len(files)

                # Progress: Start upload for this file
                progress(
                    (idx - 1) / len(files),
                    desc=f"📤 Datei {idx}/{len(files)}: {Path(file.name).name}...",
                )

                # Start async task for progress simulation within this file's progress range
                async def simulate_progress(file_idx: int) -> None:
                    """Simulate progress for long-running embedding generation."""
                    base_progress = (file_idx - 1) / len(files)
                    file_progress_range = 1.0 / len(files)

                    steps = [
                        (0.3, "📄 Dokument wird geladen..."),
                        (0.5, "🧠 Embeddings werden generiert..."),
                        (0.7, "🔍 Chunks werden indexiert..."),
                        (0.9, "✅ Finalisierung..."),
                    ]
                    for prog, desc in steps:
                        await asyncio.sleep(10)  # Update every 10 seconds
                        current_progress = base_progress + (prog * file_progress_range)
                        progress(current_progress, desc=f"Datei {file_idx}/{len(files)}: {desc}")

                # Start progress simulation
                progress_task = asyncio.create_task(simulate_progress(idx))

                try:
                    # Dynamic timeout: base 180s + 60s per file
                    timeout = 180.0 + (len(files) * 60.0)
                    client_with_timeout = httpx.AsyncClient(timeout=timeout)

                    # Call ingestion API with proper file handling
                    with open(file.name, "rb") as f:
                        file_data = {"file": (file.name, f, "application/octet-stream")}
                        response = await client_with_timeout.post(
                            f"{API_BASE_URL}/api/v1/retrieval/upload", files=file_data
                        )
                    await client_with_timeout.aclose()

                except Exception as e:
                    # Cancel progress simulation
                    progress_task.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await progress_task

                    logger.error("document_upload_failed", filename=file.name, error=str(e))
                    results.append(f"❌ {Path(file.name).name}: {str(e)}")
                    failed += 1
                    continue

                finally:
                    # Cancel progress simulation
                    progress_task.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await progress_task

                if response.status_code == 200:
                    data = response.json()
                    chunks = data.get("chunks_created", 0)
                    embeddings = data.get("embeddings_generated", 0)
                    duration = data.get("duration_seconds", 0)

                    total_chunks += chunks
                    total_embeddings += embeddings
                    total_duration += duration
                    successful += 1

                    logger.info("document_upload_success", filename=file.name, chunks=chunks)
                    results.append(f"✅ {Path(file.name).name}: {chunks} Chunks, {duration:.1f}s")
                else:
                    logger.error(
                        "document_upload_failed", filename=file.name, status=response.status_code
                    )
                    results.append(f"❌ {Path(file.name).name}: Fehler {response.status_code}")
                    failed += 1

            progress(1.0, desc="✅ Alle Uploads abgeschlossen!")

            # Build summary message
            summary = f"""{'✅' if failed == 0 else '⚠️'} Upload abgeschlossen: {successful} erfolgreich, {failed} fehlgeschlagen

📊 Gesamt-Statistik:
  • {total_chunks} Chunks erstellt
  • {total_embeddings} Embeddings generiert
  • ⏱️ Gesamtdauer: {total_duration:.1f} Sekunden

📝 Details:
"""
            summary += "\n".join(f"  {result}" for result in results)

            return summary

        except asyncio.CancelledError:
            logger.warning("document_upload_cancelled", file_count=len(files))
            return (
                f"⚠️ Upload wurde abgebrochen. ({successful} von {len(files)} Dateien erfolgreich)"
            )
        except Exception as e:
            logger.error("document_upload_exception", error=str(e))
            return f"❌ Unerwarteter Fehler beim Hochladen: {str(e)}"

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
        self, name: str, transport: str, endpoint: str
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
                description=f"User-connected {transport} server",
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
                "total_tools": stats.total_tools,
            }

            # Get available tools
            tools = await self.mcp_client.list_tools()
            tools_df = pd.DataFrame(
                [
                    {
                        "Tool Name": tool.name,
                        "Server": tool.server,
                        "Description": (
                            tool.description[:100] + "..."
                            if len(tool.description) > 100
                            else tool.description
                        ),
                        "Parameters": str(len(tool.parameters.get("properties", {}))) + " params",
                    }
                    for tool in tools
                ]
            )

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
                return {"status": "disconnected", "server_name": server_name}
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
                "successful_calls": stats.successful_calls,
            }

            tools = await self.mcp_client.list_tools()
            tools_df = pd.DataFrame(
                [
                    {
                        "Tool Name": tool.name,
                        "Server": tool.server,
                        "Description": (
                            tool.description[:100] + "..."
                            if len(tool.description) > 100
                            else tool.description
                        ),
                        "Parameters": str(len(tool.parameters.get("properties", {}))) + " params",
                    }
                    for tool in tools
                ]
            )

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

        with gr.Blocks(title="AEGIS RAG", theme=gr.themes.Soft(), css=custom_css) as demo:
            gr.Markdown("# 🛡️ AEGIS RAG")
            gr.Markdown("**Agentic Enterprise Graph Intelligence System**")
            gr.Markdown(
                "Stellen Sie Fragen zu Ihren Dokumenten oder laden Sie neue Dokumente hoch."
            )

            with gr.Tabs():
                # Tab 1: Chat Interface (Feature 10.2) - REORGANIZED: Input first, History below
                with gr.Tab("💬 Chat"):
                    # Input Section (moved to top)
                    with gr.Row():
                        msg = gr.Textbox(
                            placeholder="Ihre Frage...",
                            show_label=False,
                            elem_id="user-input",
                            scale=9,
                            lines=2,
                        )
                        submit = gr.Button(
                            "Senden", elem_id="submit-btn", scale=1, variant="primary"
                        )

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
                        label="Beispiel-Fragen",
                    )

                    # History Section (below input - more intuitive)
                    chatbot = gr.Chatbot(
                        value=[],
                        elem_id="chatbot",
                        label="Conversation History",
                        height=500,
                        show_copy_button=True,
                        type="messages",  # Enable markdown rendering
                    )

                    with gr.Row():
                        clear = gr.Button("🗑️ Chat löschen", elem_id="clear-btn")

                    # Event handlers
                    submit.click(self.chat, inputs=[msg, chatbot], outputs=[chatbot, msg])
                    msg.submit(self.chat, inputs=[msg, chatbot], outputs=[chatbot, msg])
                    clear.click(self.clear_chat, outputs=chatbot)

                # Tab 2: Document Upload (Feature 10.3)
                with gr.Tab("📄 Dokumente hochladen"):
                    gr.Markdown("### Dokumente zum RAG-System hinzufügen")
                    gr.Markdown("Unterstützte Formate: PDF, TXT, MD, DOCX, CSV")
                    gr.Markdown("💡 **Tipp:** Sie können mehrere Dateien gleichzeitig auswählen!")

                    file_upload = gr.File(
                        label="Datei(en) auswählen",
                        file_types=[".pdf", ".txt", ".md", ".docx", ".csv"],
                        file_count="multiple",  # Enable multi-file upload
                        elem_id="file-upload",
                    )

                    upload_btn = gr.Button(
                        "Hochladen & Indexieren", elem_id="upload-btn", variant="primary"
                    )
                    upload_status = gr.Textbox(
                        label="Status", elem_id="upload-status", interactive=False, lines=3
                    )

                    upload_btn.click(
                        self.upload_document, inputs=file_upload, outputs=upload_status
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
                                value="filesystem",
                            )
                            server_type = gr.Radio(
                                choices=["STDIO", "HTTP"], label="Transport Type", value="STDIO"
                            )
                            server_endpoint = gr.Textbox(
                                label="Endpoint/Command",
                                placeholder="npx @modelcontextprotocol/server-filesystem /tmp",
                                lines=2,
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
                        interactive=False,
                    )

                    refresh_tools_btn = gr.Button("🔄 Tools neu laden")

                    # Example MCP Servers
                    gr.Markdown("### Beispiel-Server")
                    gr.Markdown(
                        """
                    **Filesystem Server:**
                    - Name: `filesystem`
                    - Transport: `STDIO`
                    - Command: `npx @modelcontextprotocol/server-filesystem /tmp`

                    **HTTP Server (Beispiel):**
                    - Name: `custom-http`
                    - Transport: `HTTP`
                    - Endpoint: `http://localhost:3000`
                    """
                    )

                    # Event handlers
                    connect_btn.click(
                        self.connect_mcp_server,
                        inputs=[server_name, server_type, server_endpoint],
                        outputs=[mcp_status, mcp_tools_table],
                    )

                    disconnect_btn.click(
                        self.disconnect_mcp_server, inputs=server_name, outputs=mcp_status
                    )

                    refresh_tools_btn.click(
                        self.refresh_mcp_tools, outputs=[mcp_status, mcp_tools_table]
                    )

                # Tab 4: System Health (Feature 10.5)
                with gr.Tab("📊 System Health"):
                    gr.Markdown("### System Status & Metrics")

                    refresh_btn = gr.Button("🔄 Refresh", elem_id="refresh-health")

                    health_json = gr.JSON(label="Health Metrics", elem_id="health-json")

                    refresh_btn.click(self.get_health_stats, outputs=health_json)

                    # Auto-load on tab open
                    demo.load(self.get_health_stats, outputs=health_json)

                # Tab 5: About
                with gr.Tab("ℹ️ Über AEGIS RAG"):
                    gr.Markdown(
                        """
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
                    """
                    )

                    gr.Markdown(f"**Session ID:** `{self.session_id}`")

                    gr.Markdown(
                        """
                    ### Nützliche Links:
                    - [API Docs](http://localhost:8000/docs)
                    - [Health Endpoint](http://localhost:8000/health)
                    - [Prometheus Metrics](http://localhost:9090)
                    - [Grafana Dashboard](http://localhost:3000)
                    """
                    )

            # Footer
            gr.Markdown("---")
            gr.Markdown(
                "Built with ❤️ using [Gradio](https://gradio.app) | "
                "[API Docs](http://localhost:8000/docs) | "
                "[Health](http://localhost:8000/health)"
            )

        return demo

    def launch(
        self, server_name: str = "0.0.0.0", server_port: int = 7860, share: bool = False
    ):  # nosec B104
        """Launch Gradio app.

        Args:
            server_name: Server host (default: 0.0.0.0 - intentional for web UI)
            server_port: Server port (default: 7860)
            share: Create public URL (default: False)
        """
        demo = self.build_interface()

        logger.info(
            "launching_gradio_app", server_name=server_name, server_port=server_port, share=share
        )

        demo.launch(server_name=server_name, server_port=server_port, share=share)

def main() -> None:
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
