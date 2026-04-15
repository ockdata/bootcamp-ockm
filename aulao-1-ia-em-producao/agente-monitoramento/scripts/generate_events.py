"""
Usage:
    python -m scripts.generate_events --count 10 --preview
"""

from __future__ import annotations

import random
import string
from datetime import datetime, timedelta
from typing import Literal

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SERVICES = ["checkout", "payments", "inventory", "api-gateway", "frontend", "users", "orders"]
_NAMESPACES = ["production", "production", "production", "staging"]
_GATEWAYS = ["gateway-alpha", "gateway-beta", "gateway-gamma", "gateway-delta"]
_DEPLOYERS = ["ci-bot", "deploy-bot", "github-actions", "argocd"]
_IPS = ["203.0.113.42", "198.51.100.17", "10.0.3.45", "172.16.0.12", "192.168.1.100"]


def _pod(service: str) -> str:
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=5))
    return f"{service}-pod-{suffix}"


def _version() -> str:
    return f"v{random.randint(2, 4)}.{random.randint(0, 30)}.{random.randint(0, 9)}"


def _txn_id() -> str:
    return f"txn_{random.randint(1_000_000, 9_999_999)}"


def _order_id() -> str:
    return f"#{random.randint(10000, 99999)}"


def _ts(minutes_ago: int = 0) -> str:
    t = datetime.utcnow() - timedelta(minutes=minutes_ago)
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def _cpu() -> int:
    return random.randint(15, 45)


def _cpu_high() -> int:
    return random.randint(82, 98)


def _mem_pct() -> int:
    return random.randint(30, 60)


def _mem_high() -> int:
    return random.randint(85, 96)


def _latency_normal() -> int:
    return max(10, int(random.gauss(120, 40)))


def _latency_high() -> int:
    return max(200, int(random.gauss(800, 300)))


def _error_rate_low() -> float:
    return round(random.uniform(0.1, 1.5), 1)


def _error_rate_high() -> float:
    return round(random.uniform(5.0, 15.0), 1)


# ---------------------------------------------------------------------------
# Template pools by severity
# ---------------------------------------------------------------------------

def _normal_templates() -> list[dict]:
    """~40% of generated events — healthy system."""
    svc = random.choice(_SERVICES)
    pod = _pod(svc)
    templates = [
        {
            "source": "cloud_logging",
            "service": svc,
            "raw_payload": (
                f"INFO {_ts()} {pod} Health check passed. "
                f"Response time: {_latency_normal()}ms. "
                f"Active users: {random.randint(200, 3000)}. Cache hit rate: {random.randint(88, 99)}%."
            ),
            "metadata": {"pod": pod, "namespace": "production"},
            "_severity_hint": "low",
        },
        {
            "source": "cloud_logging",
            "service": svc,
            "raw_payload": (
                f"INFO {_ts()} {pod} Metrics nominal. "
                f"CPU: {_cpu()}%, Memory: {_mem_pct()}%, "
                f"p99 latency: {_latency_normal()}ms, error rate: {_error_rate_low()}%."
            ),
            "metadata": {"pod": pod, "cpu_pct": _cpu(), "memory_pct": _mem_pct()},
            "_severity_hint": "low",
        },
        {
            "source": "deploy",
            "service": svc,
            "raw_payload": (
                f"DEPLOY {_ts()} {svc} {_version()} → {_version()} "
                f"Deployer: {random.choice(_DEPLOYERS)}. Rollout: 3/3 pods updated. Status: SUCCESS."
            ),
            "metadata": {"deployer": random.choice(_DEPLOYERS), "status": "success"},
            "_severity_hint": "low",
        },
        {
            "source": "application",
            "service": svc,
            "raw_payload": (
                f"INFO {_ts()} {pod} Request completed successfully. "
                f"Endpoint: /api/v1/{random.choice(['products', 'orders', 'users', 'cart'])}. "
                f"Latency: {_latency_normal()}ms. Status: 200."
            ),
            "metadata": {"pod": pod, "status_code": 200},
            "_severity_hint": "low",
        },
        {
            "source": "cloud_logging",
            "service": svc,
            "raw_payload": (
                f"INFO {_ts()} {pod} Scheduled job completed. "
                f"Job: cache_warmup. Duration: {random.randint(5, 30)}s. Items processed: {random.randint(100, 5000)}."
            ),
            "metadata": {"pod": pod, "job": "cache_warmup"},
            "_severity_hint": "low",
        },
        {
            "source": "cloud_logging",
            "service": svc,
            "raw_payload": (
                f"INFO {_ts()} {pod} Auto-scaling check. "
                f"Current replicas: {random.randint(2, 5)}/{random.randint(5, 10)}. "
                f"CPU avg: {_cpu()}%. No scaling action needed."
            ),
            "metadata": {"pod": pod, "scaling_action": "none"},
            "_severity_hint": "low",
        },
    ]
    return [random.choice(templates)]


def _degradation_templates() -> list[dict]:
    """~30% — things starting to go wrong."""
    svc = random.choice(_SERVICES)
    pod = _pod(svc)
    templates = [
        {
            "source": "cloud_logging",
            "service": svc,
            "raw_payload": (
                f"WARNING {_ts()} {pod} Latency increasing. "
                f"p50: {_latency_normal()}ms → p99: {_latency_high()}ms. "
                f"SLO target: 500ms. Breach probability: {random.randint(40, 80)}%."
            ),
            "metadata": {"pod": pod, "p99_ms": _latency_high()},
            "_severity_hint": "medium",
        },
        {
            "source": "cloud_logging",
            "service": svc,
            "raw_payload": (
                f"WARNING {_ts()} {pod} Memory usage rising. "
                f"RSS: {random.uniform(1.2, 1.8):.1f}GB (limit: 2GB, {_mem_high()}%). "
                f"GC frequency: {random.randint(8, 20)} collections/min."
            ),
            "metadata": {"pod": pod, "memory_pct": _mem_high(), "gc_count": random.randint(8, 20)},
            "_severity_hint": "medium",
        },
        {
            "source": "cloud_logging",
            "service": svc,
            "raw_payload": (
                f"WARNING {_ts()} {pod} Connection pool filling up. "
                f"Active: {random.randint(35, 45)}/50 connections. "
                f"Wait queue: {random.randint(3, 10)} requests."
            ),
            "metadata": {"pod": pod, "pool_active": random.randint(35, 45), "pool_max": 50},
            "_severity_hint": "medium",
        },
        {
            "source": "cloud_logging",
            "service": svc,
            "raw_payload": (
                f"METRIC_ALERT {_ts()} CPU usage for {svc} at {_cpu_high()}% "
                f"(threshold: 80%). Sustained for {random.randint(2, 10)} minutes."
            ),
            "metadata": {"cpu_pct": _cpu_high(), "threshold": 80},
            "_severity_hint": "medium",
        },
        {
            "source": "application",
            "service": svc,
            "raw_payload": (
                f"WARNING {_ts()} {pod} Slow query detected. "
                f"Query: SELECT * FROM orders WHERE ... Duration: {random.randint(2000, 8000)}ms. "
                f"Rows scanned: {random.randint(50000, 500000)}."
            ),
            "metadata": {"pod": pod, "query_duration_ms": random.randint(2000, 8000)},
            "_severity_hint": "medium",
        },
        {
            "source": "application",
            "service": svc,
            "raw_payload": (
                f"WARNING {_ts()} {pod} Retry storm detected. "
                f"Endpoint: /api/v1/inventory. Retry rate: {random.randint(15, 40)}% of requests. "
                f"Avg retries per request: {random.uniform(1.5, 3.0):.1f}."
            ),
            "metadata": {"pod": pod, "retry_rate_pct": random.randint(15, 40)},
            "_severity_hint": "medium",
        },
    ]
    return [random.choice(templates)]


def _error_templates() -> list[dict]:
    """~20% — clear errors."""
    svc = random.choice(_SERVICES)
    pod = _pod(svc)
    templates = [
        {
            "source": "application",
            "service": svc,
            "raw_payload": (
                f"ERROR {_ts()} {pod} NullPointerException in "
                f"{random.choice(['ShippingCalculator', 'PaymentProcessor', 'OrderValidator', 'InventoryManager'])}"
                f".{random.choice(['calculate', 'process', 'validate', 'update'])}() — "
                f"order {_order_id()} failed."
            ),
            "metadata": {"pod": pod, "namespace": "production", "version": _version()},
            "_severity_hint": "high",
        },
        {
            "source": "application",
            "service": svc,
            "raw_payload": (
                f"ERROR {_ts()} {pod} Gateway timeout after {random.randint(5000, 15000)}ms "
                f"for transaction {_txn_id()}. HTTP 504. "
                f"Retry attempt {random.randint(1, 3)}/3 failed."
            ),
            "metadata": {"pod": pod, "gateway": random.choice(_GATEWAYS), "status_code": 504},
            "_severity_hint": "high",
        },
        {
            "source": "cloud_logging",
            "service": svc,
            "raw_payload": (
                f"ERROR {_ts()} {pod} 5xx error rate at {_error_rate_high()}% "
                f"(last 5 min). Top: HTTP 500 ({random.randint(40, 70)}%), "
                f"HTTP 504 ({random.randint(20, 40)}%). "
                f"Affected: /api/v1/{random.choice(['charge', 'refund', 'orders', 'checkout'])}."
            ),
            "metadata": {"pod": pod, "error_rate": _error_rate_high()},
            "_severity_hint": "high",
        },
        {
            "source": "application",
            "service": svc,
            "raw_payload": (
                f"ERROR {_ts()} {pod} Connection refused to "
                f"{random.choice(['redis-master', 'postgres-primary', 'rabbitmq-0', 'elasticsearch-0'])}:"
                f"{random.choice([6379, 5432, 5672, 9200])}. "
                f"Timeout: 3000ms. Circuit breaker: OPEN."
            ),
            "metadata": {"pod": pod, "circuit_breaker": "open"},
            "_severity_hint": "high",
        },
        {
            "source": "application",
            "service": svc,
            "raw_payload": (
                f"ERROR {_ts()} {pod} DNS resolution failed for "
                f"{random.choice(['payments-svc.production.svc.cluster.local', 'inventory-api.internal', 'cache.redis.internal'])}. "
                f"NXDOMAIN after {random.randint(3, 5)} retries."
            ),
            "metadata": {"pod": pod, "error_type": "dns_failure"},
            "_severity_hint": "high",
        },
        {
            "source": "application",
            "service": "api-gateway",
            "raw_payload": (
                f"ERROR {_ts()} api-gw-pod-{random.randint(1000,9999)} "
                f"Rate limit exceeded for tenant tenant_{random.choice(['acme', 'globex', 'initech', 'umbrella'])}: "
                f"{random.randint(120, 300)} req/s (limit: 100 req/s). "
                f"Returning HTTP 429. Source IP: {random.choice(_IPS)}."
            ),
            "metadata": {"rate": random.randint(120, 300), "limit": 100},
            "_severity_hint": "high",
        },
    ]
    return [random.choice(templates)]


def _critical_templates() -> list[dict]:
    """~10% — severe incidents."""
    svc = random.choice(_SERVICES)
    pod = _pod(svc)
    templates = [
        {
            "source": "application",
            "service": svc,
            "raw_payload": (
                f"CRITICAL {_ts()} {pod} OOMKilled: container exceeded memory limit (2Gi). "
                f"Pod restarting (restart count: {random.randint(2, 8)} in last 30 min). "
                f"Last RSS: {random.uniform(2.0, 2.5):.1f}GB."
            ),
            "metadata": {"pod": pod, "restart_count": random.randint(2, 8), "rss_gb": round(random.uniform(2.0, 2.5), 1)},
            "_severity_hint": "critical",
        },
        {
            "source": "application",
            "service": svc,
            "raw_payload": (
                f"CRITICAL {_ts()} {pod} CrashLoopBackOff detected. "
                f"Container restarted {random.randint(5, 15)} times in last 10 min. "
                f"Last exit code: {random.choice([1, 137, 139, 143])}. Backoff: {random.randint(30, 300)}s."
            ),
            "metadata": {"pod": pod, "restart_count": random.randint(5, 15)},
            "_severity_hint": "critical",
        },
        {
            "source": "application",
            "service": svc,
            "raw_payload": (
                f"CRITICAL {_ts()} {pod} Data integrity violation detected. "
                f"Table: orders. Constraint: fk_order_user_id. "
                f"Affected rows: {random.randint(10, 500)}. Write operations suspended."
            ),
            "metadata": {"pod": pod, "affected_rows": random.randint(10, 500)},
            "_severity_hint": "critical",
        },
        {
            "source": "cloud_logging",
            "service": svc,
            "raw_payload": (
                f"CRITICAL {_ts()} Service {svc} is DOWN. "
                f"All {random.randint(3, 5)} pods unresponsive. "
                f"Last successful health check: {random.randint(2, 10)} minutes ago. "
                f"Endpoints returning HTTP 503."
            ),
            "metadata": {"pod": pod, "status": "down", "pods_unresponsive": random.randint(3, 5)},
            "_severity_hint": "critical",
        },
        {
            "source": "application",
            "service": "payments",
            "raw_payload": (
                f"CRITICAL {_ts()} payments-pod-{random.randint(1000,9999)} "
                f"Payment gateway {random.choice(_GATEWAYS)} returning HTTP 503. "
                f"Failed transactions in last 5 min: {random.randint(50, 500)}. "
                f"Revenue impact estimated: R${random.randint(5000, 50000):,}."
            ),
            "metadata": {"gateway": random.choice(_GATEWAYS), "failed_txns": random.randint(50, 500)},
            "_severity_hint": "critical",
        },
    ]
    return [random.choice(templates)]


# ---------------------------------------------------------------------------
# Correlated scenarios
# ---------------------------------------------------------------------------

def _scenario_deploy_gone_wrong() -> list[dict]:
    """Deploy → errors → CPU spike → OOMKill → rollback."""
    svc = random.choice(["checkout", "payments", "orders"])
    pod = _pod(svc)
    v_old = _version()
    v_new = _version()
    return [
        {
            "source": "deploy",
            "service": svc,
            "raw_payload": (
                f"DEPLOY {_ts(5)} {svc} {v_old} → {v_new} "
                f"Deployer: {random.choice(_DEPLOYERS)}. Rollout: canary 1/3 pods."
            ),
            "metadata": {"from_version": v_old, "to_version": v_new, "strategy": "canary"},
            "_severity_hint": "low",
        },
        {
            "source": "application",
            "service": svc,
            "raw_payload": (
                f"ERROR {_ts(4)} {pod} NullPointerException after deploy {v_new}. "
                f"New code path in OrderValidator.validate() hitting null reference. "
                f"Error rate spiked from 0.1% to {_error_rate_high()}%."
            ),
            "metadata": {"pod": pod, "version": v_new, "error_rate": _error_rate_high()},
            "_severity_hint": "high",
        },
        {
            "source": "cloud_logging",
            "service": svc,
            "raw_payload": (
                f"METRIC_ALERT {_ts(3)} CPU usage for {svc} at {_cpu_high()}% "
                f"(threshold: 80%). Exception handling overhead causing CPU spike. "
                f"Error rate: {_error_rate_high()}%."
            ),
            "metadata": {"cpu_pct": _cpu_high(), "version": v_new},
            "_severity_hint": "medium",
        },
        {
            "source": "application",
            "service": svc,
            "raw_payload": (
                f"CRITICAL {_ts(2)} {pod} OOMKilled after deploy {v_new}. "
                f"Memory leak in new code path. RSS exceeded 2Gi limit. "
                f"Restart count: {random.randint(3, 6)} in last 15 min."
            ),
            "metadata": {"pod": pod, "version": v_new, "restart_count": random.randint(3, 6)},
            "_severity_hint": "critical",
        },
        {
            "source": "deploy",
            "service": svc,
            "raw_payload": (
                f"DEPLOY {_ts(1)} {svc} {v_new} → {v_old} "
                f"ROLLBACK initiated by auto-rollback policy. "
                f"Reason: error rate > 5% threshold. Pods: 3/3 rolled back."
            ),
            "metadata": {"from_version": v_new, "to_version": v_old, "action": "rollback"},
            "_severity_hint": "high",
        },
    ]


def _scenario_memory_leak_cascade() -> list[dict]:
    """Memory warning → GC thrashing → pool exhaustion → OOMKill."""
    svc = random.choice(["inventory", "checkout", "orders"])
    pod = _pod(svc)
    return [
        {
            "source": "cloud_logging",
            "service": svc,
            "raw_payload": (
                f"WARNING {_ts(4)} {pod} Memory usage trending up. "
                f"RSS: 1.4GB (limit: 2GB, 70%). Growth rate: +50MB/min. "
                f"Projected OOM in ~12 minutes."
            ),
            "metadata": {"pod": pod, "memory_pct": 70, "growth_mb_min": 50},
            "_severity_hint": "medium",
        },
        {
            "source": "cloud_logging",
            "service": svc,
            "raw_payload": (
                f"WARNING {_ts(3)} {pod} GC thrashing detected. "
                f"Full GC every {random.randint(3, 8)}s. Pause time: {random.randint(200, 800)}ms. "
                f"Application threads blocked {random.randint(30, 60)}% of time."
            ),
            "metadata": {"pod": pod, "gc_pause_ms": random.randint(200, 800)},
            "_severity_hint": "medium",
        },
        {
            "source": "application",
            "service": svc,
            "raw_payload": (
                f"ERROR {_ts(2)} {pod} Connection pool exhausted for database. "
                f"Active: 50/50. Wait queue: {random.randint(20, 50)} requests. "
                f"Timeout after 5000ms. Requests failing."
            ),
            "metadata": {"pod": pod, "pool_active": 50, "pool_max": 50, "waiting": random.randint(20, 50)},
            "_severity_hint": "high",
        },
        {
            "source": "application",
            "service": svc,
            "raw_payload": (
                f"CRITICAL {_ts(1)} {pod} OOMKilled: RSS reached 2.1GB (limit: 2Gi). "
                f"Root cause: unbounded cache in InventoryCache. "
                f"Restart count: {random.randint(2, 5)}. Service degraded."
            ),
            "metadata": {"pod": pod, "rss_gb": 2.1, "restart_count": random.randint(2, 5)},
            "_severity_hint": "critical",
        },
    ]


def _scenario_payment_gateway_outage() -> list[dict]:
    """Timeout → 5xx spike → rate limit → frontend errors."""
    gateway = random.choice(_GATEWAYS)
    return [
        {
            "source": "application",
            "service": "payments",
            "raw_payload": (
                f"ERROR {_ts(4)} {_pod('payments')} Gateway timeout from {gateway}. "
                f"Transaction {_txn_id()} timed out after 10000ms. "
                f"First timeout in 5 min window."
            ),
            "metadata": {"gateway": gateway, "timeout_ms": 10000},
            "_severity_hint": "high",
        },
        {
            "source": "cloud_logging",
            "service": "payments",
            "raw_payload": (
                f"ERROR {_ts(3)} 5xx error rate for payments spiked to {_error_rate_high()}%. "
                f"All errors are HTTP 504 from {gateway}. "
                f"Affected: /api/v1/charge, /api/v1/refund."
            ),
            "metadata": {"error_rate": _error_rate_high(), "gateway": gateway},
            "_severity_hint": "high",
        },
        {
            "source": "application",
            "service": "api-gateway",
            "raw_payload": (
                f"ERROR {_ts(2)} api-gw-pod-{random.randint(1000,9999)} "
                f"Rate limiter triggered for payment endpoints. "
                f"Returning HTTP 429 for {random.randint(30, 100)} req/s to prevent cascade."
            ),
            "metadata": {"action": "rate_limit", "dropped_rps": random.randint(30, 100)},
            "_severity_hint": "high",
        },
        {
            "source": "application",
            "service": "frontend",
            "raw_payload": (
                f"ERROR {_ts(1)} {_pod('frontend')} Checkout flow failing. "
                f"Payment API returning 429/504. User-facing error: 'Pagamento temporariamente indisponível'. "
                f"Affected users: {random.randint(50, 300)} in last 5 min."
            ),
            "metadata": {"affected_users": random.randint(50, 300)},
            "_severity_hint": "high",
        },
    ]


def _scenario_calm_period() -> list[dict]:
    """All healthy — health checks and normal metrics."""
    events = []
    for _ in range(random.randint(3, 5)):
        svc = random.choice(_SERVICES)
        pod = _pod(svc)
        events.append({
            "source": "cloud_logging",
            "service": svc,
            "raw_payload": (
                f"INFO {_ts(random.randint(0, 5))} {pod} "
                f"All systems nominal. CPU: {_cpu()}%, Memory: {_mem_pct()}%, "
                f"Latency p99: {_latency_normal()}ms, Error rate: {_error_rate_low()}%."
            ),
            "metadata": {"pod": pod, "cpu_pct": _cpu(), "memory_pct": _mem_pct()},
            "_severity_hint": "low",
        })
    return events


_SCENARIOS = [
    _scenario_deploy_gone_wrong,
    _scenario_memory_leak_cascade,
    _scenario_payment_gateway_outage,
]

_INCIDENT_SCENARIOS = [
    _scenario_deploy_gone_wrong,
    _scenario_memory_leak_cascade,
    _scenario_payment_gateway_outage,
]

_SEVERITY_GENERATORS = {
    "low": _normal_templates,
    "medium": _degradation_templates,
    "high": _error_templates,
    "critical": _critical_templates,
}

_SEVERITY_WEIGHTS = {
    "low": 0.40,
    "medium": 0.30,
    "high": 0.20,
    "critical": 0.10,
}


def _pick_severity() -> str:
    return random.choices(
        list(_SEVERITY_WEIGHTS.keys()),
        weights=list(_SEVERITY_WEIGHTS.values()),
        k=1,
    )[0]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_random_events(
    count: int = 10,
    scenario_probability: float = 0.6,
    incident_mode: bool = False,
) -> list[dict]:
    """Generate a batch of random realistic events.

    Args:
        count: Target number of events to generate.
        scenario_probability: Probability [0-1] that a correlated scenario
            is included in the batch (the rest are individual random events).
        incident_mode: If True, always include at least one critical
            multi-event scenario and skew severity toward high/critical.

    Returns:
        List of event dicts ready to be converted to RawEvent.
    """
    events: list[dict] = []

    # Decide whether to include a scenario
    include_scenario = incident_mode or (random.random() < scenario_probability)

    if include_scenario:
        if incident_mode:
            # Always pick a dramatic scenario
            scenario_fn = random.choice(_INCIDENT_SCENARIOS)
        else:
            # Could be a calm period or a real scenario
            all_options = _SCENARIOS + [_scenario_calm_period]
            scenario_fn = random.choice(all_options)

        scenario_events = scenario_fn()
        events.extend(scenario_events)

    # Fill remaining with individual random events
    while len(events) < count:
        if incident_mode:
            # Skew toward high/critical in incident mode
            severity = random.choices(
                ["low", "medium", "high", "critical"],
                weights=[0.10, 0.15, 0.40, 0.35],
                k=1,
            )[0]
        else:
            severity = _pick_severity()

        generator = _SEVERITY_GENERATORS[severity]
        events.extend(generator())

    # Trim to exact count
    events = events[:count]

    # Remove internal hint key
    for evt in events:
        evt.pop("_severity_hint", None)

    # Shuffle so scenarios aren't always at the start
    # (but keep scenario events mostly together by only light-shuffling)
    if not incident_mode:
        random.shuffle(events)

    return events


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _cli() -> None:
    """Preview generated events in the terminal."""
    import argparse

    from rich.console import Console
    from rich.table import Table

    parser = argparse.ArgumentParser(description="Generate random monitoring events")
    parser.add_argument("--count", "-n", type=int, default=10, help="Number of events")
    parser.add_argument("--incident", action="store_true", help="Force incident scenario")
    parser.add_argument("--preview", action="store_true", help="Pretty-print to terminal")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")
    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    events = generate_random_events(
        count=args.count,
        incident_mode=args.incident,
    )

    if args.preview:
        console = Console()
        table = Table(title=f"Generated Events ({len(events)})", show_lines=True)
        table.add_column("#", style="dim", width=3)
        table.add_column("Source", style="green", width=14)
        table.add_column("Service", style="cyan", width=14)
        table.add_column("Payload (preview)", max_width=80)

        for i, evt in enumerate(events, 1):
            payload_preview = evt["raw_payload"][:100] + ("..." if len(evt["raw_payload"]) > 100 else "")
            table.add_row(str(i), evt["source"], evt["service"], payload_preview)

        console.print(table)
        console.print(f"\n[dim]Total: {len(events)} events[/dim]")
    else:
        import json
        print(json.dumps(events, indent=2, default=str))


if __name__ == "__main__":
    _cli()
