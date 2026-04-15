from __future__ import annotations

import json
import sys
import uuid
from datetime import datetime, timedelta

from config.settings import get_settings

# Realistic synthetic events for the demo
SYNTHETIC_EVENTS = [
    {
        "source": "cloud_logging",
        "service": "checkout",
        "raw_payload": (
            "ERROR 2025-02-17T14:23:01Z checkout-pod-7f8d9 "
            "NullPointerException in ShippingCalculator.calculate() — "
            "address.getCep() returned null for order #48291. "
            "Stack: com.acme.checkout.shipping.ShippingCalculator.calculate(ShippingCalculator.java:87)"
        ),
        "metadata": {"pod": "checkout-pod-7f8d9", "namespace": "production", "version": "v2.15.0"},
    },
    {
        "source": "application",
        "service": "payments",
        "raw_payload": (
            "CRITICAL 2025-02-17T14:25:00Z payments-pod-3a1b2 "
            "Gateway timeout after 10000ms for transaction txn_9182736. "
            "Payment gateway returned HTTP 504. Customer charged but confirmation pending. "
            "Retry attempt 3/3 failed."
        ),
        "metadata": {"pod": "payments-pod-3a1b2", "gateway": "gateway-alpha", "amount_brl": "459.90"},
    },
    {
        "source": "cloud_logging",
        "service": "inventory",
        "raw_payload": (
            "WARNING 2025-02-17T14:20:00Z inventory-pod-5c4d3 "
            "High memory usage detected: RSS=1.8GB (limit=2GB, 90%). "
            "GC frequency increasing: 12 collections in last minute. "
            "Heap: used=1.2GB, committed=1.5GB, max=1.5GB"
        ),
        "metadata": {"pod": "inventory-pod-5c4d3", "memory_pct": 90, "gc_count": 12},
    },
    {
        "source": "cloud_logging",
        "service": "checkout",
        "raw_payload": (
            "METRIC_ALERT 2025-02-17T14:30:00Z "
            "CPU usage for checkout service at 92% (threshold: 80%). "
            "p99 latency: 1200ms (SLO: 500ms). Active pods: 3/3 at capacity. "
            "HPA max replicas reached."
        ),
        "metadata": {"cpu_pct": 92, "p99_ms": 1200, "replicas": 3, "hpa_max": 3},
    },
    {
        "source": "deploy",
        "service": "checkout",
        "raw_payload": (
            "DEPLOY 2025-02-17T14:15:00Z checkout v2.15.0 → v2.15.1 "
            "Deployer: ci-bot. Changes: fix null check in ShippingCalculator, "
            "add Redis cache for inventory lookup. Rollout: 0/3 pods updated."
        ),
        "metadata": {"from_version": "v2.15.0", "to_version": "v2.15.1", "deployer": "ci-bot"},
    },
    {
        "source": "application",
        "service": "api-gateway",
        "raw_payload": (
            "ERROR 2025-02-17T14:28:00Z api-gw-pod-9e8f7 "
            "Rate limit exceeded for tenant tenant_acme: 150 req/s (limit: 100 req/s). "
            "Returning HTTP 429 for 50 requests. Source IP: 203.0.113.42"
        ),
        "metadata": {"tenant": "tenant_acme", "rate": 150, "limit": 100},
    },
    {
        "source": "cloud_logging",
        "service": "payments",
        "raw_payload": (
            "ERROR 2025-02-17T14:32:00Z payments-pod-1x2y3 "
            "5xx error rate at 8.5% (last 5 min). "
            "Top errors: HTTP 504 (gateway timeout) 65%, HTTP 500 (internal) 35%. "
            "Affected endpoints: /api/v1/charge, /api/v1/refund"
        ),
        "metadata": {"error_rate": 8.5, "top_status": 504, "window_min": 5},
    },
    {
        "source": "application",
        "service": "inventory",
        "raw_payload": (
            "CRITICAL 2025-02-17T14:35:00Z inventory-pod-5c4d3 "
            "OOMKilled: container inventory exceeded memory limit (2Gi). "
            "Pod restarting (restart count: 3 in last 30 min). "
            "Last known RSS: 2.1GB."
        ),
        "metadata": {"restart_count": 3, "memory_limit": "2Gi", "rss_gb": 2.1},
    },
    {
        "source": "cloud_logging",
        "service": "frontend",
        "raw_payload": (
            "INFO 2025-02-17T14:18:00Z frontend-pod-a1b2c "
            "Health check passed. Response time: 45ms. "
            "Active users: 1,247. Cache hit rate: 94%."
        ),
        "metadata": {"response_ms": 45, "active_users": 1247, "cache_hit": 0.94},
    },
    {
        "source": "application",
        "service": "checkout",
        "raw_payload": (
            "ERROR 2025-02-17T14:33:00Z checkout-pod-7f8d9 "
            "Connection pool exhausted for inventory-service. "
            "Active connections: 50/50. Waiting requests: 23. "
            "Timeout after 5000ms. Failing open with cached inventory data."
        ),
        "metadata": {"pool_active": 50, "pool_max": 50, "waiting": 23},
    },
]


def generate_events(
    random_mode: bool = False,
    incident_mode: bool = False,
) -> list[dict]:
    """Generate synthetic events with UUIDs and timestamps.

    Args:
        random_mode: If True, use the random event generator instead of
            the fixed SYNTHETIC_EVENTS list.
        incident_mode: If True (and random_mode is True), force an
            incident scenario in the generated events.
    """
    now = datetime.utcnow()
    events = []

    if random_mode:
        from scripts.generate_events import generate_random_events
        templates = generate_random_events(count=10, incident_mode=incident_mode)
    else:
        templates = SYNTHETIC_EVENTS

    for i, template in enumerate(templates):
        events.append({
            "event_id": str(uuid.uuid4()),
            "timestamp": (now - timedelta(minutes=20 - i * 2)).isoformat(),
            "source": template["source"],
            "service": template["service"],
            "raw_payload": template["raw_payload"],
            "metadata": json.dumps(template.get("metadata", {})),
            "processed": False,
        })

    return events


def seed_bigquery() -> None:
    """Insert synthetic events into BigQuery raw_events table."""
    settings = get_settings()

    if not settings.gcp_project_id:
        print("⚠️  GCP_PROJECT_ID não configurado. Pulando seed do BigQuery.")
        print("   Configure no .env para usar BigQuery na demo.")
        return

    from google.cloud import bigquery

    client = bigquery.Client(project=settings.gcp_project_id)
    table_id = settings.bq_raw_table_id

    events = generate_events()
    errors = client.insert_rows_json(table_id, events)

    if errors:
        print(f"❌ Erros ao inserir eventos: {errors}")
        sys.exit(1)
    else:
        print(f"✅ {len(events)} eventos inseridos em {table_id}")


if __name__ == "__main__":
    seed_bigquery()
