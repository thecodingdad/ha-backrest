"""Constants for the Backrest integration."""

from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "backrest"

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
]

DEFAULT_PORT = 9898
DEFAULT_SCAN_INTERVAL = 60  # seconds
MIN_SCAN_INTERVAL = 10
MAX_SCAN_INTERVAL = 3600

CONF_SCAN_INTERVAL = "scan_interval"

# Backrest API endpoints
API_GET_CONFIG = "/v1.Backrest/GetConfig"
API_GET_SUMMARY = "/v1.Backrest/GetSummaryDashboard"
API_GET_OPERATIONS = "/v1.Backrest/GetOperations"
API_BACKUP = "/v1.Backrest/Backup"
API_DO_REPO_TASK = "/v1.Backrest/DoRepoTask"
API_LIST_SNAPSHOTS = "/v1.Backrest/ListSnapshots"

# Backrest operation status values (string enums from protobuf JSON)
STATUS_INPROGRESS = "STATUS_INPROGRESS"
STATUS_SUCCESS = "STATUS_SUCCESS"
STATUS_WARNING = "STATUS_WARNING"
STATUS_ERROR = "STATUS_ERROR"
STATUS_USER_CANCELLED = "STATUS_USER_CANCELLED"

STATUS_MAP = {
    STATUS_SUCCESS: "success",
    STATUS_WARNING: "warning",
    STATUS_ERROR: "error",
    STATUS_USER_CANCELLED: "cancelled",
}
