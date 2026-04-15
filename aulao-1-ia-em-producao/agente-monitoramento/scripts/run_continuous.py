"""Continuous demo runner.

Usage:
    python -m scripts.run_continuous --interval 60 --count 10
    python -m scripts.run_continuous --incident --interval 300
    python -m scripts.run_continuous --dry --interval 30
"""

from __future__ import annotations

import asyncio
import json
import signal
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import click
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.syntax import Syntax
from rich.table import Table

from config.settings import get_settings
from observability.logger import setup_logging
from pipeline.engine import PipelineEngine
from providers.terminal_sink import TerminalSink
from schemas.events import RawEvent
from scripts.generate_events import generate_random_events
from scripts.seed_rag import seed_rag

console = Console()

# ── Accumulated stats across cycles ──────────────────────────────────────

@dataclass
class AccumulatedStats:
    total_events: int = 0
    total_anomalies: int = 0
    total_alerts: int = 0
    total_cost: float = 0.0
    total_llm_calls: int = 0
    cycles_completed: int = 0
    # Previous cycle for delta comparison
    prev_anomalies: int = 0
    prev_avg_risk: float = 0.0


# ── Display helpers ──────────────────────────────────────────────────────

_SEVERITY_COLORS = {
    "critical": "bold white on dark_red",
    "high": "bold bright_red",
    "medium": "bold yellow",
    "low": "bold green",
}


def print_banner() -> None:
    banner = """
╔══════════════════════════════════════════════════════════════╗
║          AGENTE DE MONITORAMENTO IA — MODO CONTÍNUO         ║
║          Aulão: IA em Produção de Verdade                   ║
╠══════════════════════════════════════════════════════════════╣
║  Pipeline: Classify → Extract → Detect → RAG → RCA → Alert ║
║  EWMA acumula entre ciclos • Ctrl+C para parar              ║
╚══════════════════════════════════════════════════════════════╝
    """
    console.print(banner, style="bold cyan")


def print_cycle_header(cycle: int, incident_mode: bool) -> None:
    mode_str = " [INCIDENTE]" if incident_mode else ""
    now = datetime.now().strftime("%H:%M:%S")
    console.print()
    console.rule(
        f"[bold cyan] Ciclo {cycle} — {now}{mode_str} ",
        style="cyan",
    )
    console.print()


def build_results_table(enriched) -> Table:
    table = Table(title="Resultados do Pipeline", show_lines=True)
    table.add_column("Serviço", style="cyan")
    table.add_column("Tipo")
    table.add_column("Severidade")
    table.add_column("Anomalia")
    table.add_column("Z-Score", justify="right")
    table.add_column("Risk", justify="right")

    for e in enriched:
        color = _SEVERITY_COLORS.get(e.severity, "white")
        anomaly_str = "[bold red]SIM[/bold red]" if e.is_anomaly else "[green]Não[/green]"
        risk_color = _SEVERITY_COLORS.get(e.risk_level, "white")

        table.add_row(
            e.service,
            e.event_type,
            f"[{color}]{e.severity.upper()}[/{color}]",
            anomaly_str,
            f"{e.z_score:.2f}",
            f"[{risk_color}]{e.risk_score}[/{risk_color}]",
        )
    return table


def build_ewma_table(engine: PipelineEngine) -> Table:
    """Build the EWMA state panel showing all tracked buckets."""
    snapshot = engine.anomaly_detector.get_states_snapshot()

    table = Table(title="Estado do Detector de Anomalias (EWMA)", show_lines=True)
    table.add_column("Bucket", style="cyan", min_width=25)
    table.add_column("Obs", justify="right", width=6)
    table.add_column("Média", justify="right", width=7)
    table.add_column("StdDev", justify="right", width=7)
    table.add_column("Status", width=13)

    for bucket, info in snapshot.items():
        status = "[green]Ativo[/green]" if info["status"] == "active" else "[yellow]Treinando[/yellow]"
        table.add_row(
            bucket,
            str(info["count"]),
            f"{info['mean']:.2f}",
            f"{info['std']:.2f}",
            status,
        )

    if not snapshot:
        table.add_row("[dim]Nenhum bucket ainda[/dim]", "", "", "", "")

    return table


def print_accumulated_stats(stats: AccumulatedStats) -> None:
    console.print(
        f"\n[bold]Estatísticas Acumuladas ({stats.cycles_completed} ciclos)[/bold]\n"
        f"  Eventos: {stats.total_events}  |  "
        f"Anomalias: {stats.total_anomalies}  |  "
        f"Alertas: {stats.total_alerts}  |  "
        f"LLM Calls: {stats.total_llm_calls}  |  "
        f"Custo: ${stats.total_cost:.4f}"
    )


def print_delta(stats: AccumulatedStats, cycle_anomalies: int, cycle_avg_risk: float) -> None:
    """Show delta vs previous cycle."""
    if stats.cycles_completed <= 1:
        return

    anom_delta = cycle_anomalies - stats.prev_anomalies
    risk_delta = cycle_avg_risk - stats.prev_avg_risk
    anom_arrow = "[red]↑[/red]" if anom_delta > 0 else "[green]↓[/green]" if anom_delta < 0 else "→"
    risk_arrow = "[red]↑[/red]" if risk_delta > 5 else "[green]↓[/green]" if risk_delta < -5 else "→"

    console.print(
        f"  Delta vs ciclo anterior: "
        f"Anomalias {anom_arrow} ({anom_delta:+d})  |  "
        f"Risk médio {risk_arrow} ({risk_delta:+.1f})"
    )


def countdown_visual(seconds: int) -> None:
    """Show a Rich Live countdown between cycles."""
    end_time = time.time() + seconds
    next_cycle_time = (datetime.now() + timedelta(seconds=seconds)).strftime("%H:%M:%S")

    try:
        with Live(console=console, refresh_per_second=1) as live:
            while True:
                remaining = end_time - time.time()
                if remaining <= 0:
                    break
                mins, secs = divmod(int(remaining), 60)
                panel = Panel(
                    f"\n              [bold]{mins:02d}:{secs:02d}[/bold]\n\n"
                    f"   Próximo ciclo: {next_cycle_time}\n"
                    f"   Ctrl+C para parar",
                    title="Aguardando próximo ciclo...",
                    border_style="dim",
                    padding=(0, 2),
                )
                live.update(panel)
                time.sleep(0.5)
    except KeyboardInterrupt:
        raise


# ── Main loop ────────────────────────────────────────────────────────────

async def setup_components(dry: bool, no_bq: bool):
    """One-time setup of LLM, RAG, sinks, etc."""
    settings = get_settings()
    setup_logging(level=settings.log_level, fmt="console")

    console.print("[bold]Inicializando componentes...[/bold]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        # LLM
        task_llm = progress.add_task("Inicializando LLM...", total=1)
        if dry or not settings.anthropic_api_key:
            from providers.dummy_llm import DummyLLM
            llm = DummyLLM()
            llm_name = "DummyLLM (heurístico)"
        else:
            from providers.anthropic_llm import AnthropicLLM
            llm = AnthropicLLM(
                api_key=settings.anthropic_api_key,
                model=settings.llm_primary_model,
            )
            llm_name = f"Anthropic ({settings.llm_primary_model})"
        progress.update(task_llm, advance=1, description=f"LLM: {llm_name}")

        # RAG
        task_rag = progress.add_task("Indexando documentos RAG...", total=1)
        rag_engine, doc_count = await seed_rag(settings.rag_data_dir)
        progress.update(task_rag, advance=1, description=f"RAG: {doc_count} docs indexados")

        # Sinks
        task_sink = progress.add_task("Configurando alert sinks...", total=1)
        terminal_sink = TerminalSink(console=console)
        sinks = [terminal_sink]
        progress.update(task_sink, advance=1, description="Sink: Terminal (Rich)")

    console.print()

    # BigQuery store (optional)
    bq_store = None
    if not dry and not no_bq and settings.gcp_project_id:
        from providers.bigquery_store import BigQueryStore
        bq_store = BigQueryStore(
            project_id=settings.gcp_project_id,
            dataset=settings.bq_dataset,
        )
        console.print(f"[green]BigQuery habilitado:[/green] {settings.bq_enriched_table_id}")
    else:
        console.print("[dim]BigQuery desabilitado[/dim]")

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

    return settings, llm, rag_engine, sinks, terminal_sink, bq_store


async def run_continuous(
    interval: int,
    count: int,
    incident: bool,
    dry: bool,
    no_bq: bool,
) -> None:
    settings, llm, rag_engine, sinks, terminal_sink, bq_store = await setup_components(dry, no_bq)

    # Build engine once — EWMA detector is shared across cycles
    engine = PipelineEngine(
        llm=llm,
        rag_engine=rag_engine,
        alert_sinks=sinks,
        prompt_version=settings.prompt_version,
        alert_threshold=settings.alert_risk_threshold,
        anomaly_state_file=settings.anomaly_state_file,
    )

    stats = AccumulatedStats()
    cycle = 0
    force_incident_next = incident  # First cycle uses CLI flag

    while True:
        cycle += 1
        is_incident = force_incident_next
        force_incident_next = incident  # Reset for subsequent cycles

        print_cycle_header(cycle, is_incident)

        # ── Generate events ──
        events_raw = generate_random_events(
            count=count,
            incident_mode=is_incident,
        )
        events = [
            RawEvent(
                source=e["source"],
                service=e["service"],
                raw_payload=e["raw_payload"],
                metadata=e.get("metadata", {}),
            )
            for e in events_raw
        ]
        console.print(f"  Gerados {len(events)} eventos {'[bold red](INCIDENTE)[/bold red]' if is_incident else '(aleatórios)'}")

        # ── Run pipeline ──
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
            enriched, alerts, tracer = await engine.process_batch(
                events,
                on_event_done=lambda: progress.advance(task),
            )

        elapsed = time.perf_counter() - start_time
        console.print()

        # ── Results ──
        console.print(build_results_table(enriched))
        console.print()

        # ── Alerts ──
        if alerts:
            console.print(f"[bold red]{len(alerts)} Alertas Emitidos[/bold red]\n")
            terminal_sink.print_summary_table(alerts)
        else:
            console.print("[green]Nenhum alerta emitido neste ciclo.[/green]")
        console.print()

        # ── EWMA State ──
        console.print(build_ewma_table(engine))
        console.print()

        # ── Update accumulated stats ──
        cycle_anomalies = tracer.anomalies_detected
        cycle_avg_risk = (
            sum(e.risk_score for e in enriched) / len(enriched) if enriched else 0.0
        )
        summary = tracer.metrics.summary()

        stats.total_events += tracer.events_processed
        stats.total_anomalies += cycle_anomalies
        stats.total_alerts += len(alerts)
        stats.total_cost += summary["total_cost_usd"]
        stats.total_llm_calls += summary["total_calls"]
        stats.cycles_completed = cycle

        print_accumulated_stats(stats)
        print_delta(stats, cycle_anomalies, cycle_avg_risk)

        # Save for next delta
        stats.prev_anomalies = cycle_anomalies
        stats.prev_avg_risk = cycle_avg_risk

        # ── Save to BigQuery ──
        if bq_store:
            try:
                await bq_store.save_enriched(enriched)
                await bq_store.save_llm_calls(tracer.metrics.records)
                console.print(f"\n  [dim]Dados salvos em BigQuery[/dim]")
            except Exception as exc:
                console.print(f"\n  [yellow]BigQuery erro: {exc}[/yellow]")

        # ── Cycle summary ──
        console.print(
            Panel(
                f"[bold]Ciclo {cycle} concluído em {elapsed:.1f}s[/bold]\n\n"
                f"  Eventos: {len(enriched)}  |  "
                f"Anomalias: {cycle_anomalies}  |  "
                f"Alertas: {len(alerts)}  |  "
                f"Custo: ${summary['total_cost_usd']:.4f}",
                title=f"Ciclo {cycle} Completo",
                border_style="bold green" if not alerts else "bold red",
                padding=(1, 2),
            )
        )

        # ── Countdown to next cycle ──
        countdown_visual(interval)


# ── CLI ──────────────────────────────────────────────────────────────────

@click.command("run-continuous")
@click.option("--interval", "-i", default=300, help="Segundos entre ciclos (default: 300).")
@click.option("--count", "-n", default=10, help="Eventos por batch (default: 10).")
@click.option("--incident", is_flag=True, help="Forçar cenário de incidente a cada ciclo.")
@click.option("--dry", is_flag=True, help="Usar DummyLLM (sem custo).")
@click.option("--no-bq", is_flag=True, help="Pular BigQuery.")
def main(interval: int, count: int, incident: bool, dry: bool, no_bq: bool) -> None:
    """Modo contínuo: gera eventos → roda pipeline → repete."""
    try:
        asyncio.run(run_continuous(interval, count, incident, dry, no_bq))
    except KeyboardInterrupt:
        console.print("\n[yellow]Demo contínua encerrada pelo usuário.[/yellow]")
        sys.exit(0)


if __name__ == "__main__":
    main()
