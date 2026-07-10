"""Analytics unit tests without DB."""

from eaw.application.services.monitoring_service import MonitoringService
from eaw.core.config import get_settings


def test_monitoring_service_constructs() -> None:
    # smoke: class imports and settings load
    settings = get_settings()
    assert settings.app_name
    assert MonitoringService  # type exists
