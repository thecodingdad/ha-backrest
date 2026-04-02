"""API client for Backrest."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp

from .const import (
    API_BACKUP,
    API_DO_REPO_TASK,
    API_GET_CONFIG,
    API_GET_OPERATIONS,
    API_GET_SUMMARY,
    API_LIST_SNAPSHOTS,
)

_LOGGER = logging.getLogger(__name__)


class BackrestConnectionError(Exception):
    """Error connecting to Backrest."""


class BackrestAuthError(Exception):
    """Authentication error with Backrest."""


class BackrestApiClient:
    """API client for Backrest using Connect RPC (HTTP/JSON)."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        base_url: str,
        username: str | None = None,
        password: str | None = None,
    ) -> None:
        """Initialize the API client."""
        self._session = session
        self._base_url = base_url.rstrip("/")
        self._auth: aiohttp.BasicAuth | None = None
        if username and password:
            self._auth = aiohttp.BasicAuth(username, password)

    async def _request(self, endpoint: str, payload: dict[str, Any] | None = None) -> Any:
        """Make a POST request to the Backrest API."""
        url = f"{self._base_url}{endpoint}"
        data = payload or {}

        try:
            resp = await self._session.post(
                url,
                json=data,
                auth=self._auth,
                headers={"Content-Type": "application/json"},
            )
        except (aiohttp.ClientError, TimeoutError) as err:
            raise BackrestConnectionError(
                f"Cannot connect to Backrest at {self._base_url}: {err}"
            ) from err

        if resp.status in (401, 403):
            raise BackrestAuthError(
                f"Authentication failed (status {resp.status})"
            )

        if resp.status != 200:
            text = await resp.text()
            raise BackrestConnectionError(
                f"Unexpected response from Backrest (status {resp.status}): {text}"
            )

        return await resp.json()

    async def async_get_config(self) -> dict[str, Any]:
        """Fetch Backrest configuration (plans and repos)."""
        return await self._request(API_GET_CONFIG)

    async def async_get_summary(self) -> dict[str, Any]:
        """Fetch the summary dashboard."""
        return await self._request(API_GET_SUMMARY)

    async def async_get_operations(
        self,
        plan_id: str | None = None,
        repo_id: str | None = None,
    ) -> dict[str, Any]:
        """Fetch operations, optionally filtered by plan or repo."""
        selector: dict[str, str] = {}
        if plan_id:
            selector["planId"] = plan_id
        if repo_id:
            selector["repoId"] = repo_id

        return await self._request(API_GET_OPERATIONS, {"selector": selector})

    async def async_list_snapshots(
        self,
        plan_id: str | None = None,
        repo_id: str | None = None,
    ) -> dict[str, Any]:
        """List snapshots, optionally filtered."""
        payload: dict[str, str] = {}
        if plan_id:
            payload["planId"] = plan_id
        if repo_id:
            payload["repoId"] = repo_id
        return await self._request(API_LIST_SNAPSHOTS, payload)

    async def async_trigger_backup(self, plan_id: str) -> dict[str, Any]:
        """Trigger a backup for the given plan."""
        return await self._request(API_BACKUP, {"value": plan_id})

    async def async_do_repo_task(
        self, repo_id: str, task: int
    ) -> dict[str, Any]:
        """Execute a repository task (prune=5, check=6)."""
        return await self._request(
            API_DO_REPO_TASK, {"repoId": repo_id, "task": task}
        )

    async def async_test_connection(self) -> bool:
        """Test the connection to Backrest."""
        await self._request(API_GET_CONFIG)
        return True
