"""
DingTalk Access Token manager.

- In-memory caching for dev (no Redis dependency)
- TTL-based auto-refresh
- Thread-safe for simple use cases
"""
import logging
import threading
import time
from datetime import datetime, timedelta, timezone

import requests
from django.conf import settings

from .exceptions import TokenRefreshError, check_response

logger = logging.getLogger("apps")

# Token endpoint
TOKEN_URL = "https://oapi.dingtalk.com/gettoken"
# Safety margin: refresh 200 seconds before actual expiry (7200 - 200)
TOKEN_TTL = 7000


class TokenManager:
    """Manage DingTalk access token with in-memory caching.

    Singleton-style — instantiate once and reuse.
    Thread-safe via a reentrant lock.
    """

    def __init__(self):
        self._token = None
        self._expires_at = None  # absolute timestamp
        self._lock = threading.RLock()

    # ---- public API ----

    def get_token(self):
        """Return a valid access token, refreshing if needed."""
        with self._lock:
            if self._is_valid():
                return self._token
            return self._refresh()

    def invalidate(self):
        """Force token refresh on next get_token() call."""
        with self._lock:
            self._token = None
            self._expires_at = None
            logger.info("DingTalk token manually invalidated")

    def is_demo_mode(self):
        """Check if demo mode is active (no real API calls)."""
        return getattr(settings, "DINGTALK_DEMO_MODE", True)

    # ---- internal ----

    def _is_valid(self):
        """Token is valid if present and not expired."""
        if not self._token or not self._expires_at:
            return False
        return time.time() < self._expires_at

    def _refresh(self):
        """Fetch a new access token from DingTalk."""
        if self.is_demo_mode():
            self._token = "demo_access_token_mock"
            self._expires_at = time.time() + TOKEN_TTL
            logger.info("Demo mode: using mock access token")
            return self._token

        app_key = settings.DINGTALK_APP_KEY
        app_secret = settings.DINGTALK_APP_SECRET

        if not app_key or not app_secret:
            raise TokenRefreshError(
                errcode=-1,
                errmsg="DINGTALK_APP_KEY 或 DINGTALK_APP_SECRET 未配置",
            )

        try:
            resp = requests.get(
                TOKEN_URL,
                params={"appkey": app_key, "appsecret": app_secret},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            check_response(data, endpoint="GET /gettoken")

            self._token = data["access_token"]
            expires_in = data.get("expires_in", 7200)
            # Apply safety margin
            effective_ttl = min(expires_in - 200, TOKEN_TTL)
            self._expires_at = time.time() + effective_ttl

            logger.info(
                f"DingTalk token refreshed (expires in {effective_ttl}s, "
                f"at {datetime.now(timezone.utc) + timedelta(seconds=effective_ttl)})"
            )
            return self._token

        except requests.RequestException as e:
            raise TokenRefreshError(errcode=-1, errmsg=f"网络请求失败: {e}")
        except TokenRefreshError:
            raise
        except Exception as e:
            raise TokenRefreshError(errcode=-1, errmsg=str(e))


# Module-level singleton — import this everywhere
token_manager = TokenManager()
