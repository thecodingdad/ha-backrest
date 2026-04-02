"""Base entity for Backrest integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

if TYPE_CHECKING:
    from .coordinator import BackrestCoordinator


class BackrestEntity(CoordinatorEntity["BackrestCoordinator"]):
    """Base entity for Backrest."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: BackrestCoordinator,
        device_info: DeviceInfo,
    ) -> None:
        """Initialize base entity."""
        super().__init__(coordinator)
        self._attr_device_info = device_info


def plan_device_info(
    entry_id: str,
    plan_id: str,
    plan_name: str,
    repo_id: str,
    base_url: str,
) -> DeviceInfo:
    """Return device info for a backup plan."""
    return DeviceInfo(
        identifiers={(DOMAIN, f"{entry_id}_plan_{plan_id}")},
        name=plan_name,
        manufacturer="Backrest",
        model="Backup Plan",
        entry_type=DeviceEntryType.SERVICE,
        via_device=(DOMAIN, f"{entry_id}_repo_{repo_id}"),
        configuration_url=base_url,
    )


def repo_device_info(
    entry_id: str,
    repo_id: str,
    repo_uri: str,
    base_url: str,
) -> DeviceInfo:
    """Return device info for a repository."""
    return DeviceInfo(
        identifiers={(DOMAIN, f"{entry_id}_repo_{repo_id}")},
        name=f"Repository: {repo_id}",
        manufacturer="Backrest",
        model="Repository",
        entry_type=DeviceEntryType.SERVICE,
        configuration_url=base_url,
    )
