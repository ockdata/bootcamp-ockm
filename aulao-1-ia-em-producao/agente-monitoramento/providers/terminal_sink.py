from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from schemas.alerts import Alert

_SEVERITY_COLORS = {
    "critical": "bold white on dark_red",
    "high": "bold bright_red",
    "medium": "bold yellow",
    "low": "bold green",
}

# Border/accent colors — softer tones so text inside remains readable
_BORDER_COLORS = {
    "critical": "red",
    "high": "bright_red",
    "medium": "yellow",
    "low": "green",
}


class TerminalSink:
    """Outputs alerts to the terminal using Rich panels. Implements AlertSink protocol."""

    def __init__(self, console: Console | None = None):
        self.console = console or Console()

    async def send(self, alert: Alert) -> bool:
        text_color = _SEVERITY_COLORS.get(alert.risk_level, "bold white")
        border_color = _BORDER_COLORS.get(alert.risk_level, "white")

        # Build recommendations list
        recs = "\n".join(f"  • {r}" for r in alert.recommendations) if alert.recommendations else "  Nenhuma recomendação"

        body = (
            f"[bold]Serviço:[/bold] {alert.service}\n"
            f"[bold]Severidade:[/bold] [{text_color}]{alert.severity.upper()}[/{text_color}]\n"
            f"[bold]Risk Score:[/bold] [{text_color}]{alert.risk_score}/100 ({alert.risk_level})[/{text_color}]\n"
            f"\n[bold]Resumo:[/bold]\n  {alert.summary}\n"
            f"\n[bold]Causa Raiz:[/bold]\n  {alert.root_cause}\n"
            f"\n[bold]Recomendações:[/bold]\n{recs}"
        )

        panel = Panel(
            body,
            title=f"🚨 ALERTA: {alert.title}",
            border_style=border_color,
            padding=(1, 2),
        )
        self.console.print(panel)
        return True

    def print_summary_table(self, alerts: list[Alert]) -> None:
        """Print a summary table of all alerts emitted."""
        if not alerts:
            self.console.print("[dim]Nenhum alerta emitido neste ciclo.[/dim]")
            return

        table = Table(title="📊 Resumo de Alertas", show_lines=True)
        table.add_column("Serviço", style="cyan")
        table.add_column("Severidade")
        table.add_column("Risk", justify="right")
        table.add_column("Título")

        for a in alerts:
            color = _SEVERITY_COLORS.get(a.risk_level, "white")
            table.add_row(
                a.service,
                f"[{color}]{a.severity.upper()}[/{color}]",
                f"[{color}]{a.risk_score}[/{color}]",
                a.title,
            )

        self.console.print(table)
