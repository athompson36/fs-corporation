"""Shared ambient-environment isolation for tests.

A developer `.env` exports real provider credentials and host wiring into the shell.
Tests that assert fail-closed behavior must not observe those values, or they pass
for the wrong reason on a clean machine and fail on a configured one.
"""
import os
import unittest

# Variables a developer .env or fs-dev shell may export into the test process.
AMBIENT_VARS = (
    "ANTHROPIC_API_KEY",
    "FEED_API_KEY",
    "GITHUB_APP_ID",
    "GITHUB_INSTALLATION_ID",
    "GITHUB_PRIVATE_KEY_FILE",
    "GITHUB_WEBHOOK_SECRET",
    "MODEL_PROVIDER_API_KEY",
    "MODEL_PROVIDER_BASE_URL",
    "VAPID_CONTACT_EMAIL",
    "VAPID_PRIVATE_KEY",
    "VAPID_PRIVATE_KEY_FILE",
    "VAPID_PUBLIC_KEY",
    "VAPID_PUBLIC_KEY_FILE",
    "FS_CORP_GITHUB_WEBHOOK_PUBLIC_URL",
    "FS_CORP_TAILSCALE_AUTHKEY",
    "FS_CORP_TAILSCALE_FUNNEL_WEBHOOKS",
    "FS_CORP_TAILSCALE_IP",
    "FS_CORP_WORKER_SCRATCH_HOST",
)


def clear_ambient_env(test: unittest.TestCase, names=AMBIENT_VARS) -> None:
    """Remove *names* from os.environ for the duration of *test*, then restore."""
    saved = {name: os.environ.pop(name) for name in names if name in os.environ}
    test.addCleanup(os.environ.update, saved)


class AmbientEnvIsolatedTestCase(unittest.TestCase):
    """Base class for tests whose assertions depend on credentials being absent."""

    def setUp(self):
        super().setUp()
        clear_ambient_env(self)
