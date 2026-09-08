"""HTTP rate-limit policy for the control service.

Authenticated routes are limited per principal. Unauthenticated webhook and
pairing-redeem routes are limited per client IP. Liveness and desk shells are
exempt so probes and page loads are never blocked by a busy principal.
"""
from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass, field


EXEMPT_PATHS = frozenset({"/", "/desk", "/welcome", "/api/v1/health"})
# /static/* is unauthenticated CSS; middleware skips rate limits when no bearer identity.

UNAUTH_LIMITED_PATHS = frozenset({
    "/api/v1/github/webhooks",
    "/api/v1/remote-access/redeem",
})


@dataclass
class RateLimitPolicy:
    """Sliding-window limits. Values of 0 or less disable that bucket."""

    authenticated_limit: int = 120
    unauthenticated_limit: int = 60
    window_sec: float = 60.0


@dataclass
class RateLimiter:
    policy: RateLimitPolicy = field(default_factory=RateLimitPolicy)
    _hits: dict[str, deque[float]] = field(default_factory=lambda: defaultdict(deque))

    def _prune(self, key: str, now: float) -> deque[float]:
        window = self._hits[key]
        cutoff = now - self.policy.window_sec
        while window and window[0] <= cutoff:
            window.popleft()
        return window

    def check(self, key: str, *, limit: int, now: float | None = None) -> tuple[bool, int]:
        """Return (allowed, retry_after_sec). Records the hit when allowed."""
        if limit <= 0:
            return True, 0
        now = time.monotonic() if now is None else now
        window = self._prune(key, now)
        if len(window) >= limit:
            retry_after = max(1, int(self.policy.window_sec - (now - window[0])) + 1)
            return False, retry_after
        window.append(now)
        return True, 0

    def check_authenticated(self, principal_id: str, *, now: float | None = None) -> tuple[bool, int]:
        return self.check(
            f"principal:{principal_id}", limit=self.policy.authenticated_limit, now=now)

    def check_unauthenticated(self, client_ip: str, *, now: float | None = None) -> tuple[bool, int]:
        return self.check(
            f"ip:{client_ip}", limit=self.policy.unauthenticated_limit, now=now)


def coerce_policy(value) -> RateLimitPolicy:
    if value is None:
        return RateLimitPolicy()
    if isinstance(value, RateLimitPolicy):
        return value
    return RateLimitPolicy(
        authenticated_limit=int(getattr(value, "authenticated_limit", 120)),
        unauthenticated_limit=int(getattr(value, "unauthenticated_limit", 60)),
        window_sec=float(getattr(value, "window_sec", 60.0)),
    )
