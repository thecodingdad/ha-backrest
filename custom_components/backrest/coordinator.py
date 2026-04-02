"""Data update coordinator for Backrest."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import logging
from typing import Any

from croniter import croniter

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import BackrestApiClient, BackrestAuthError, BackrestConnectionError
from .const import (
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    STATUS_INPROGRESS,
    STATUS_MAP,
)

_LOGGER = logging.getLogger(__name__)


def _safe_int(value: Any) -> int:
    """Convert a string or int value to int, returning 0 on failure."""
    if value is None:
        return 0
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0


@dataclass
class BackrestPlanData:
    """Data for a single backup plan."""

    plan_id: str
    plan_name: str
    repo_id: str
    disabled: bool = False
    last_status: str | None = None
    last_backup_time: datetime | None = None
    next_backup_time: datetime | None = None
    is_running: bool = False
    backup_duration: float | None = None
    files_added: int = 0
    files_changed: int = 0
    snapshot_count: int = 0
    bytes_processed: int = 0
    data_added: int = 0
    last_operation_id: str | None = None
    display_message: str | None = None


@dataclass
class BackrestRepoData:
    """Data for a single repository."""

    repo_id: str
    repo_uri: str
    total_snapshots: int = 0


@dataclass
class BackrestData:
    """Aggregated data from Backrest."""

    plans: dict[str, BackrestPlanData] = field(default_factory=dict)
    repos: dict[str, BackrestRepoData] = field(default_factory=dict)


class BackrestCoordinator(DataUpdateCoordinator[BackrestData]):
    """Coordinator for polling Backrest."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: BackrestApiClient,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the coordinator."""
        scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.client = client
        self._entry = entry
        self._previous_operation_ids: dict[str, str | None] = {}

    async def _async_update_data(self) -> BackrestData:
        """Fetch data from Backrest."""
        try:
            config, summary, operations = await asyncio.gather(
                self.client.async_get_config(),
                self.client.async_get_summary(),
                self.client.async_get_operations(),
            )
        except BackrestAuthError as err:
            raise ConfigEntryAuthFailed from err
        except BackrestConnectionError as err:
            raise UpdateFailed(f"Cannot connect to Backrest: {err}") from err

        data = BackrestData()

        # Parse repos from config
        config_obj = config.get("config", config)
        for repo in config_obj.get("repos", []):
            repo_id = repo.get("id", "")
            data.repos[repo_id] = BackrestRepoData(
                repo_id=repo_id,
                repo_uri=repo.get("uri", ""),
            )

        # Parse plans from config
        for plan in config_obj.get("plans", []):
            plan_id = plan.get("id", "")
            schedule = plan.get("schedule", {})
            cron_expr = schedule.get("cron") if isinstance(schedule, dict) else None

            next_backup: datetime | None = None
            if cron_expr:
                try:
                    cron = croniter(cron_expr, datetime.now(tz=timezone.utc))
                    next_backup = cron.get_next(datetime).replace(tzinfo=timezone.utc)
                except (ValueError, KeyError):
                    _LOGGER.debug("Cannot parse cron expression: %s", cron_expr)

            data.plans[plan_id] = BackrestPlanData(
                plan_id=plan_id,
                plan_name=plan.get("id", plan_id),
                repo_id=plan.get("repo", ""),
                disabled=plan.get("disabled", False),
                next_backup_time=next_backup,
            )

        # Parse operations for status and running state
        op_list = operations.get("operations", [])
        self._parse_operations(op_list, data)

        # Fire events for newly completed backups
        self._fire_backup_events(data)

        # Fetch snapshot counts
        await self._fetch_snapshot_counts(data)

        return data

    def _parse_operations(
        self, op_list: list[dict[str, Any]], data: BackrestData
    ) -> None:
        """Parse operations to extract status and running state."""
        # Sort by start time descending to find latest per plan
        op_list.sort(
            key=lambda o: int(o.get("unixTimeStartMs", "0")),
            reverse=True,
        )

        seen_plans: set[str] = set()

        for op in op_list:
            plan_id = op.get("planId", "")
            status = op.get("status")
            op_backup = op.get("operationBackup")

            if plan_id not in data.plans:
                continue

            plan_data = data.plans[plan_id]

            # Check for running operations
            if status == STATUS_INPROGRESS:
                plan_data.is_running = True

            # Extract last completed backup info (first completed op per plan)
            if plan_id not in seen_plans and op_backup and status in STATUS_MAP:
                seen_plans.add(plan_id)
                plan_data.last_status = STATUS_MAP[status]

                start_ms = int(op.get("unixTimeStartMs", "0"))
                end_ms = int(op.get("unixTimeEndMs", "0"))

                if end_ms:
                    plan_data.last_backup_time = datetime.fromtimestamp(
                        end_ms / 1000, tz=timezone.utc
                    )

                if start_ms and end_ms:
                    plan_data.backup_duration = (end_ms - start_ms) / 1000

                last_status = op_backup.get("lastStatus", {})
                summary = last_status.get("summary", {})
                plan_data.files_added = _safe_int(summary.get("filesNew"))
                plan_data.files_changed = _safe_int(summary.get("filesChanged"))
                plan_data.bytes_processed = _safe_int(summary.get("totalBytesProcessed"))
                plan_data.data_added = _safe_int(summary.get("dataAdded"))
                plan_data.last_operation_id = op.get("id")
                plan_data.display_message = op.get("displayMessage")

    def _fire_backup_events(self, data: BackrestData) -> None:
        """Fire events for newly completed backups by comparing operation IDs."""
        for plan_id, plan_data in data.plans.items():
            prev_op_id = self._previous_operation_ids.get(plan_id)
            curr_op_id = plan_data.last_operation_id

            # Fire event if we have a previous state and the operation ID changed
            if prev_op_id is not None and curr_op_id != prev_op_id:
                self.hass.bus.async_fire(
                    f"{DOMAIN}_backup_finished",
                    {
                        "plan_id": plan_id,
                        "plan_name": plan_data.plan_name,
                        "repo_id": plan_data.repo_id,
                        "status": plan_data.last_status,
                        "duration": plan_data.backup_duration,
                        "files_added": plan_data.files_added,
                        "files_changed": plan_data.files_changed,
                        "data_added": plan_data.data_added,
                        "bytes_processed": plan_data.bytes_processed,
                        "message": plan_data.display_message,
                    },
                )
                _LOGGER.debug(
                    "Fired backrest_backup_finished for plan %s (op %s -> %s)",
                    plan_id, prev_op_id, curr_op_id,
                )

            self._previous_operation_ids[plan_id] = curr_op_id

    async def _fetch_snapshot_counts(self, data: BackrestData) -> None:
        """Fetch snapshot counts for all plans and repos."""
        try:
            tasks = {
                plan_id: self.client.async_list_snapshots(plan_id=plan_id)
                for plan_id in data.plans
            }
            results = await asyncio.gather(*tasks.values(), return_exceptions=True)

            repo_counts: dict[str, int] = {}

            for plan_id, result in zip(tasks.keys(), results):
                if isinstance(result, Exception):
                    _LOGGER.debug("Failed to get snapshots for plan %s: %s", plan_id, result)
                    continue

                snapshots = result.get("snapshots", [])
                count = len(snapshots)
                data.plans[plan_id].snapshot_count = count

                repo_id = data.plans[plan_id].repo_id
                repo_counts[repo_id] = repo_counts.get(repo_id, 0) + count

            for repo_id, count in repo_counts.items():
                if repo_id in data.repos:
                    data.repos[repo_id].total_snapshots = count

        except Exception:
            _LOGGER.debug("Failed to fetch snapshot counts", exc_info=True)
