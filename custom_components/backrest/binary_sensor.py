"""Binary sensor platform for Backrest."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_URL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import BackrestCoordinator
from .entity import BackrestEntity, plan_device_info

PLAN_BINARY_SENSOR_DESCRIPTIONS: tuple[BinarySensorEntityDescription, ...] = (
    BinarySensorEntityDescription(
        key="backup_running",
        translation_key="backup_running",
        device_class=BinarySensorDeviceClass.RUNNING,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Backrest binary sensor entities."""
    coordinator: BackrestCoordinator = hass.data[DOMAIN][entry.entry_id]
    base_url = entry.data[CONF_URL]
    entities: list[BinarySensorEntity] = []

    for plan_id, plan_data in coordinator.data.plans.items():
        device = plan_device_info(
            entry.entry_id, plan_id, plan_data.plan_name,
            plan_data.repo_id, base_url,
        )
        for description in PLAN_BINARY_SENSOR_DESCRIPTIONS:
            entities.append(
                BackrestBackupRunningSensor(coordinator, description, plan_id, device)
            )

    async_add_entities(entities)


class BackrestBackupRunningSensor(BackrestEntity, BinarySensorEntity):
    """Binary sensor for backup running state."""

    def __init__(
        self,
        coordinator: BackrestCoordinator,
        description: BinarySensorEntityDescription,
        plan_id: str,
        device_info: Any,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, device_info)
        self.entity_description = description
        self._plan_id = plan_id
        self._attr_unique_id = (
            f"{coordinator._entry.entry_id}_{plan_id}_{description.key}"
        )

    @property
    def available(self) -> bool:
        """Return True if the plan exists in coordinator data."""
        return super().available and self._plan_id in self.coordinator.data.plans

    @property
    def is_on(self) -> bool | None:
        """Return True if backup is currently running."""
        plan = self.coordinator.data.plans.get(self._plan_id)
        if plan is None:
            return None
        return plan.is_running
