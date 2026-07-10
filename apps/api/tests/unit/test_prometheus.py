"""Prometheus exporter unit test."""

from eaw.api.prometheus import render_prometheus


def test_render_prometheus_contains_info() -> None:
    text = render_prometheus()
    assert "eaw_info" in text
    assert "eaw_http_requests_total" in text
