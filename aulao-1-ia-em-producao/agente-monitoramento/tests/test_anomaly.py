"""Tests for EWMA anomaly detection."""

from __future__ import annotations

import pytest

from pipeline.anomaly import AnomalyDetector


def test_no_anomaly_with_few_data_points():
    detector = AnomalyDetector()

    # First few points shouldn't trigger anomaly (not enough history)
    r1 = detector.detect("checkout", "log", "low")
    r2 = detector.detect("checkout", "log", "low")
    r3 = detector.detect("checkout", "log", "low")

    assert not r1.is_anomaly
    assert not r2.is_anomaly
    assert not r3.is_anomaly


def test_anomaly_on_severity_spike():
    detector = AnomalyDetector(z_threshold=2.0)

    # Build baseline with low severity
    for _ in range(10):
        detector.detect("payments", "log", "low")

    # Spike to critical
    result = detector.detect("payments", "log", "critical")

    assert result.is_anomaly
    assert result.z_score > 2.0
    assert result.bucket == "payments:log"


def test_no_anomaly_consistent_severity():
    detector = AnomalyDetector()

    # Consistent medium severity
    for _ in range(20):
        result = detector.detect("inventory", "metric_alert", "medium")

    # Last result should not be anomalous
    assert not result.is_anomaly


def test_separate_buckets():
    detector = AnomalyDetector()

    # Different services get separate tracking
    for _ in range(10):
        detector.detect("checkout", "log", "low")

    for _ in range(10):
        detector.detect("payments", "log", "high")

    # Critical on checkout (was always low) should be anomaly
    r = detector.detect("checkout", "log", "critical")
    assert r.is_anomaly

    # High on payments (was always high) should NOT be anomaly
    r2 = detector.detect("payments", "log", "high")
    assert not r2.is_anomaly


def test_z_score_returned():
    detector = AnomalyDetector()

    for _ in range(5):
        detector.detect("svc", "log", "low")

    result = detector.detect("svc", "log", "critical")
    assert isinstance(result.z_score, float)
