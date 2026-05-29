"""Pytest configuration for the backend test suite.

Disable Langfuse tracing so tests never emit telemetry to a real project.
Must run before backend.main is imported — main calls get_client() at import
time, and the client reads this env var to decide whether tracing is on.
"""

import os

os.environ["LANGFUSE_TRACING_ENABLED"] = "false"
