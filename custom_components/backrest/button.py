"""Button platform for Backrest."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_URL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import BackrestCoordinator
from .entity import BackrestEntity, plan_device_info, repo_device_info

_LOGGER = logging.getLogger(__name__)

# Backrest DoRepoTask task types (from service.proto Task enum)
REPO_TASK_PRUNE = 2
REPO_TASK_CHECK = 3
REPO_TASK_UNLOCK = 5


@dataclass(frozen=True, kw_only=True)
class BackrestButtonDescription(ButtonEntityDescription):
    """Describes a Backrest button entity."""


PLAN_BUTTON_DESCRIPTIONS: tuple[BackrestButtonDescription, ...] = (
    BackrestButtonDescription(
        key="trigger_backup",
        translation_key="trigger_backup",
        icon="mdi:play",
    ),
)

REPO_BUTTON_DESCRIPTIONS: tuple[BackrestButtonDescription, ...] = (
    BackrestButtonDescription(
        key="prune",
        translation_key="prune_repo",
        icon="mdi:delete-sweep",
    ),
    BackrestButtonDescription(
        key="check",
        translation_key="check_repo",
        icon="mdi:check-decagram",
    ),
    BackrestButtonDescription(
        key="unlock",
        translation_key="unlock_repo",
        icon="mdi:lock-open-variant",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Backrest button entities."""
    coordinator: BackrestCoordinator = hass.data[DOMAIN][entry.entry_id]
    base_url = entry.data[CONF_URL]
    entities: list[ButtonEntity] = []

    for plan_id, plan_data in coordinator.data.plans.items():
        device = plan_device_info(
            entry.entry_id, plan_id, plan_data.plan_name,
            plan_data.repo_id, base_url,
        )
        for description in PLAN_BUTTON_DESCRIPTIONS:
            entities.append(
                BackrestPlanButton(coordinator, description, plan_id, device)
            )

    for repo_id, repo_data in coordinator.data.repos.items():
        device = repo_device_info(entry.entry_id, repo_id, repo_data.repo_uri, base_url)
        for description in REPO_BUTTON_DESCRIPTIONS:
            entities.append(
                BackrestRepoButton(coordinator, description, repo_id, device)
            )

    async_add_entities(entities)


class BackrestPlanButton(BackrestEntity, ButtonEntity):
    """Button to trigger a backup plan."""

    entity_description: BackrestButtonDescription

    def __init__(
        self,
        coordinator: BackrestCoordinator,
        description: BackrestButtonDescription,
        plan_id: str,
        device_info: Any,
    ) -> None:
        """Initialize the button."""
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

    async def async_press(self) -> None:
        """Trigger the backup."""
        await self.coordinator.client.async_trigger_backup(self._plan_id)
        await self.coordinator.async_request_refresh()


class BackrestRepoButton(BackrestEntity, ButtonEntity):
    """Button for repository maintenance tasks."""

    entity_description: BackrestButtonDescription

    TASK_MAP = {
        "prune": REPO_TASK_PRUNE,
        "check": REPO_TASK_CHECK,
        "unlock": REPO_TASK_UNLOCK,
    }

    def __init__(
        self,
        coordinator: BackrestCoordinator,
        description: BackrestButtonDescription,
        repo_id: str,
        device_info: Any,
    ) -> None:
        """Initialize the button."""
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

    async def async_press(self) -> None:
        """Execute the repository task."""
        task = self.TASK_MAP.get(self.entity_description.key)
        if task is not None:
            await self.coordinator.client.async_do_repo_task(self._repo_id, task)
            await self.coordinator.async_request_refresh()
