from __future__ import annotations

import asyncio
import json
import sys
import time
from datetime import datetime

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.syntax import Syntax
from rich.table import Table

from config.settings import get_settings
from observability.logger import setup_logging
from pipeline.engine import PipelineEngine
from pipeline.rag import RAGEngine
from providers.dummy_llm import DummyLLM
from providers.faiss_store import FAISSStore
from providers.local_embeddings import LocalEmbeddings
from providers.terminal_sink import TerminalSink
from schemas.events import RawEvent
from scripts.seed_bigquery import SYNTHETIC_EVENTS
from scripts.seed_rag import seed_rag

console = Console()


def print_banner() -> None:
    banner = """
╔══════════════════════════════════════════════════════════════╗
║          🤖  AGENTE DE MONITORAMENTO IA  🤖                ║
║          Aulão: IA em Produção de Verdade                   ║
╠══════════════════════════════════════════════════════════════╣
║  Pipeline: Classify → Extract → Detect → RAG → RCA → Alert ║
╚══════════════════════════════════════════════════════════════╝
    """
    console.print(banner, style="bold cyan")


def print_config(settings) -> None:
    table = Table(title="⚙️  Configuração", show_lines=True)
    table.add_column("Parâmetro", style="cyan")
    table.add_column("Valor", style="green")

    table.add_row("Pipeline Mode", settings.pipeline_mode)
    table.add_row("Prompt Version", settings.prompt_version)
    table.add_row("Alert Threshold", str(settings.alert_risk_threshold))
    table.add_row("Batch Size", str(settings.pipeline_batch_size))
    table.add_row("LLM Provider", "DummyLLM (dry)" if settings.is_dry_run else "Anthropic Claude")
    table.add_row("RAG Data", settings.rag_data_dir)
    table.add_row("BigQuery", "Desabilitado" if settings.is_dry_run or not settings.gcp_project_id else settings.bq_raw_table_id)

    console.print(table)
    console.print()


def build_events_table(events: list[RawEvent]) -> Table:
    table = Table(title="📥 Eventos a Processar", show_lines=True)
    table.add_column("#", style="dim", width=3)
    table.add_column("Serviço", style="cyan")
    table.add_column("Fonte", style="green")
    table.add_column("Payload (preview)", max_width=60)

    for i, e in enumerate(events, 1):
        table.add_row(str(i), e.service, e.source, e.raw_payload[:80] + "...")

    return table


def build_results_table(enriched, tracer) -> Table:
    table = Table(title="📊 Resultados do Pipeline", show_lines=True)
    table.add_column("Serviço", style="cyan")
    table.add_column("Tipo")
    table.add_column("Severidade")
    table.add_column("Anomalia")
    table.add_column("Z-Score", justify="right")
    table.add_column("Risk", justify="right")
    table.add_column("Método")

    severity_colors = {
        "critical": "bold white on dark_red",
        "high": "bold bright_red",
        "medium": "bold yellow",
        "low": "bold green",
    }

    for e in enriched:
        color = severity_colors.get(e.severity, "white")
        anomaly_str = "🔴 SIM" if e.is_anomaly else "✅ Não"
        risk_color = severity_colors.get(e.risk_level, "white")

        table.add_row(
            e.service,
            e.event_type,
            f"[{color}]{e.severity.upper()}[/{color}]",
            anomaly_str,
            f"{e.z_score:.2f}",
            f"[{risk_color}]{e.risk_score}[/{risk_color}]",
            e.classification_method,
        )

    return table


def build_observability_table(tracer) -> Table:
    table = Table(title="🔭 Observabilidade", show_lines=True)
    table.add_column("Métrica", style="cyan")
    table.add_column("Valor", style="green", justify="right")

    summary = tracer.metrics.summary()
    table.add_row("Run ID", tracer.run_id[:12] + "...")
    table.add_row("Prompt Version", tracer.prompt_version)
    table.add_row("Eventos Processados", str(tracer.events_processed))
    table.add_row("Classificados", str(tracer.events_classified))
    table.add_row("Anomalias Detectadas", str(tracer.anomalies_detected))
    table.add_row("Alertas Emitidos", str(tracer.alerts_emitted))
    table.add_row("Total LLM Calls", str(summary["total_calls"]))
    table.add_row("Input Tokens", f"{summary['total_input_tokens']:,}")
    table.add_row("Output Tokens", f"{summary['total_output_tokens']:,}")
    table.add_row("Custo Estimado", f"${summary['total_cost_usd']:.4f}")
    table.add_row("Latência Média", f"{summary['avg_latency_ms']:.1f}ms")
    table.add_row("Fallback Rate", f"{summary['fallback_rate']:.1%}")

    return table


async def run_demo() -> None:
    settings = get_settings()
    setup_logging(level=settings.log_level, fmt="console")

    print_banner()
    print_config(settings)

    # ── Phase 1: Setup ──
    console.print("[bold]📚 Fase 1: Inicializando componentes...[/bold]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        # Setup LLM
        task_llm = progress.add_task("Inicializando LLM...", total=1)
        if settings.is_dry_run or not settings.anthropic_api_key:
            llm = DummyLLM()
            llm_name = "DummyLLM (heurístico)"
        else:
            from providers.anthropic_llm import AnthropicLLM
            llm = AnthropicLLM(api_key=settings.anthropic_api_key, model=settings.llm_primary_model)
            llm_name = f"Anthropic ({settings.llm_primary_model})"
        progress.update(task_llm, advance=1, description=f"LLM: {llm_name}")

        # Setup RAG
        task_rag = progress.add_task("Indexando documentos RAG...", total=1)
        rag_engine, doc_count = await seed_rag(settings.rag_data_dir)
        progress.update(task_rag, advance=1, description=f"RAG: {doc_count} docs indexados")

        # Setup sinks
        task_sink = progress.add_task("Configurando alert sinks...", total=1)
        terminal_sink = TerminalSink(console=console)
        sinks = [terminal_sink]
        progress.update(task_sink, advance=1, description="Sink: Terminal (Rich)")

    console.print()

    from schemas.llm_responses import ClassificationResult

    schema_json = json.dumps(ClassificationResult.model_json_schema(), indent=2, ensure_ascii=False)
    console.print(
        Panel(
            Syntax(schema_json, "json", theme="monokai", line_numbers=False),
            title="Schema: ClassificationResult (enviado ao LLM via Instructor)",
            border_style="cyan",
            padding=(1, 2),
        )
    )
    console.print()

    # ── Phase 2: Load events ──
    console.print("[bold]📥 Fase 2: Carregando eventos...[/bold]")

    if not settings.is_dry_run and settings.gcp_project_id:
        from providers.bigquery_store import BigQueryStore
        store = BigQueryStore(
            project_id=settings.gcp_project_id,
            dataset=settings.bq_dataset,
        )
        events = await store.fetch_unprocessed(limit=settings.pipeline_batch_size)
        console.print(f"  Carregados {len(events)} eventos do BigQuery")
    else:
        events = [
            RawEvent(
                source=e["source"],
                service=e["service"],
                raw_payload=e["raw_payload"],
                metadata=e["metadata"],
            )
            for e in SYNTHETIC_EVENTS
        ]
        console.print(f"  Usando {len(events)} eventos sintéticos (modo dry-run)")

    console.print()
    console.print(build_events_table(events))
    console.print()

    # ── Phase 3: Run pipeline ──
    console.print("[bold]⚡ Fase 3: Executando pipeline...[/bold]\n")

    engine = PipelineEngine(
        llm=llm,
        rag_engine=rag_engine,
        alert_sinks=sinks,
        prompt_version=settings.prompt_version,
        alert_threshold=settings.alert_risk_threshold,
    )

    start_time = time.perf_counter()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Processando eventos...", total=len(events))

        all_enriched, all_alerts, tracer = await engine.process_batch(
            events,
            on_event_done=lambda: progress.advance(task),
        )

    elapsed = time.perf_counter() - start_time
    console.print()

    # ── Phase 4: Results ──
    console.print("[bold]📊 Fase 4: Resultados[/bold]\n")
    console.print(build_results_table(all_enriched, tracer))
    console.print()

    # ── Phase 5: Alerts ──
    if all_alerts:
        console.print(f"[bold]🚨 Fase 5: {len(all_alerts)} Alertas Emitidos[/bold]\n")
        # Alerts were already printed by TerminalSink during pipeline
        terminal_sink.print_summary_table(all_alerts)
    else:
        console.print("[bold]✅ Fase 5: Nenhum alerta emitido (todos abaixo do threshold)[/bold]")
    console.print()

    # ── Phase 6: Observability ──
    console.print("[bold]🔭 Fase 6: Observabilidade[/bold]\n")
    console.print(build_observability_table(tracer))
    console.print()

    # ── Save to BigQuery if configured ──
    if not settings.is_dry_run and settings.gcp_project_id:
        console.print("[bold]💾 Salvando resultados no BigQuery...[/bold]")
        store = BigQueryStore(
            project_id=settings.gcp_project_id,
            dataset=settings.bq_dataset,
        )
        await store.save_enriched(all_enriched)
        await store.save_llm_calls(tracer.metrics.records)
        await store.mark_processed([e.event_id for e in events])
        console.print("  ✅ Dados salvos em BigQuery")
    else:
        console.print("[dim]💾 BigQuery desabilitado (modo dry-run)[/dim]")

    console.print()

    # Final summary
    console.print(
        Panel(
            f"[bold]Pipeline concluído em {elapsed:.2f}s[/bold]\n\n"
            f"  Eventos: {len(all_enriched)}  |  "
            f"Anomalias: {tracer.anomalies_detected}  |  "
            f"Alertas: {len(all_alerts)}  |  "
            f"LLM Calls: {tracer.metrics.total_calls}  |  "
            f"Custo: ${tracer.metrics.total_cost_usd:.4f}",
            title="✅ Demo Completa",
            border_style="bold green",
            padding=(1, 2),
        )
    )


def main() -> None:
    try:
        asyncio.run(run_demo())
    except KeyboardInterrupt:
        console.print("\n[yellow]Demo interrompida pelo usuário.[/yellow]")
        sys.exit(0)


if __name__ == "__main__":
    main()
