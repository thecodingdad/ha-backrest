"""Sensor platform for Backrest."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_URL, UnitOfInformation, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import BackrestCoordinator, BackrestPlanData, BackrestRepoData
from .entity import BackrestEntity, plan_device_info, repo_device_info

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class BackrestSensorDescription(SensorEntityDescription):
    """Describes a Backrest sensor entity."""

    value_fn: Callable[[BackrestPlanData], Any]


@dataclass(frozen=True, kw_only=True)
class BackrestRepoSensorDescription(SensorEntityDescription):
    """Describes a Backrest repo sensor entity."""

    value_fn: Callable[[BackrestRepoData], Any]


def _hours_since_last_backup(plan: BackrestPlanData) -> float | None:
    """Calculate hours since last backup."""
    if plan.last_backup_time is None:
        return None
    delta = datetime.now(tz=timezone.utc) - plan.last_backup_time
    return round(delta.total_seconds() / 3600, 1)


PLAN_SENSOR_DESCRIPTIONS: tuple[BackrestSensorDescription, ...] = (
    BackrestSensorDescription(
        key="last_backup_status",
        translation_key="last_backup_status",
        icon="mdi:backup-restore",
        device_class=SensorDeviceClass.ENUM,
        options=["success", "warning", "error", "cancelled"],
        value_fn=lambda d: d.last_status,
    ),
    BackrestSensorDescription(
        key="last_backup_time",
        translation_key="last_backup_time",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda d: d.last_backup_time,
    ),
    BackrestSensorDescription(
        key="next_backup_time",
        translation_key="next_backup_time",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda d: d.next_backup_time,
    ),
    BackrestSensorDescription(
        key="backup_duration",
        translation_key="backup_duration",
        icon="mdi:timer-outline",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.backup_duration,
    ),
    BackrestSensorDescription(
        key="files_added",
        translation_key="files_added",
        icon="mdi:file-plus-outline",
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.files_added,
    ),
    BackrestSensorDescription(
        key="files_changed",
        translation_key="files_changed",
        icon="mdi:file-edit-outline",
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.files_changed,
    ),
    BackrestSensorDescription(
        key="snapshot_count",
        translation_key="snapshot_count",
        icon="mdi:package-variant-closed",
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.snapshot_count,
    ),
    BackrestSensorDescription(
        key="bytes_processed",
        translation_key="bytes_processed",
        icon="mdi:database-outline",
        native_unit_of_measurement=UnitOfInformation.BYTES,
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.bytes_processed,
    ),
    BackrestSensorDescription(
        key="data_added",
        translation_key="data_added",
        icon="mdi:database-plus-outline",
        native_unit_of_measurement=UnitOfInformation.BYTES,
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.data_added,
    ),
    BackrestSensorDescription(
        key="last_operation_id",
        translation_key="last_operation_id",
        icon="mdi:identifier",
        value_fn=lambda d: d.last_operation_id,
    ),
    BackrestSensorDescription(
        key="display_message",
        translation_key="display_message",
        icon="mdi:message-alert-outline",
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.display_message,
    ),
    BackrestSensorDescription(
        key="hours_since_last_backup",
        translation_key="hours_since_last_backup",
        icon="mdi:clock-alert-outline",
        native_unit_of_measurement=UnitOfTime.HOURS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=_hours_since_last_backup,
    ),
)

REPO_SENSOR_DESCRIPTIONS: tuple[BackrestRepoSensorDescription, ...] = (
    BackrestRepoSensorDescription(
        key="total_snapshots",
        translation_key="total_snapshots",
        icon="mdi:package-variant-closed",
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.total_snapshots,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Backrest sensor entities."""
    coordinator: BackrestCoordinator = hass.data[DOMAIN][entry.entry_id]
    base_url = entry.data[CONF_URL]
    entities: list[SensorEntity] = []

    for plan_id, plan_data in coordinator.data.plans.items():
        device = plan_device_info(
            entry.entry_id, plan_id, plan_data.plan_name,
            plan_data.repo_id, base_url,
        )
        for description in PLAN_SENSOR_DESCRIPTIONS:
            entities.append(
                BackrestPlanSensor(coordinator, description, plan_id, device)
            )

    for repo_id, repo_data in coordinator.data.repos.items():
        device = repo_device_info(entry.entry_id, repo_id, repo_data.repo_uri, base_url)
        for description in REPO_SENSOR_DESCRIPTIONS:
            entities.append(
                BackrestRepoSensor(coordinator, description, repo_id, device)
            )

    async_add_entities(entities)


class BackrestPlanSensor(BackrestEntity, SensorEntity):
    """Sensor for a Backrest backup plan."""

    entity_description: BackrestSensorDescription

    def __init__(
        self,
        coordinator: BackrestCoordinator,
        description: BackrestSensorDescription,
        plan_id: str,
        device_info: Any,
    ) -> None:
        """Initialize the sensor."""
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
    def native_value(self) -> Any:
        """Return the sensor value."""
        plan = self.coordinator.data.plans.get(self._plan_id)
        if plan is None:
            return None
        return self.entity_description.value_fn(plan)


class BackrestRepoSensor(BackrestEntity, SensorEntity):
    """Sensor for a Backrest repository."""

    entity_description: BackrestRepoSensorDescription

    def __init__(
        self,
        coordinator: BackrestCoordinator,
        description: BackrestRepoSensorDescription,
        repo_id: str,
        device_info: Any,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device_info)
        self.entity_description = description
        self._repo_id = repo_id
        self._attr_unique_id = (
            f"{coordinator._entry.entry_id}_{repo_id}_{description.key}"
        )

    @property
    def available(self) -> bool:
        """Return True if the repo exists in coordinator data."""
        return super().available and self._repo_id in self.coordinator.data.repos

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        repo = self.coordinator.data.repos.get(self._repo_id)
        if repo is None:
            return None
        return self.entity_description.value_fn(repo)
