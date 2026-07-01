"""
DingTalk API client.

Encapsulates all DingTalk Open API calls:
- get_access_token  (delegated to TokenManager)
- get_report_list    — POST /topapi/report/list
- get_user_info      — POST /topapi/v2/user/getuserinfo (SSO callback)

All methods support demo mode with realistic mock data.
"""
import logging
from datetime import datetime, timedelta

import requests
from django.conf import settings
from django.utils import timezone

from .exceptions import APIRequestError, check_response
from .token_manager import token_manager

logger = logging.getLogger("apps")

# DingTalk Open API base URL
API_BASE = "https://oapi.dingtalk.com"


class DingTalkClient:
    """DingTalk Open API client.

    Usage:
        client = DingTalkClient()
        reports = client.get_report_list(start_time, end_time)
    """

    def __init__(self):
        self._token_manager = token_manager  # shared singleton

    # ==================================================================
    # Public API methods
    # ==================================================================

    def get_report_list(self, start_time, end_time, cursor=0, size=20):
        """Fetch work reports from DingTalk.

        POST /topapi/report/list

        Args:
            start_time: int, Unix timestamp (milliseconds)
            end_time: int, Unix timestamp (milliseconds)
            cursor: int, pagination offset
            size: int, max 20 per page

        Returns:
            dict with keys: data_list, next_cursor, has_more
        """
        if self._demo_mode():
            return self._mock_report_list(start_time, end_time, cursor, size)

        return self._request(
            method="POST",
            path="/topapi/report/list",
            data={
                "start_time": start_time,
                "end_time": end_time,
                "cursor": cursor,
                "size": size,
            },
        )

    def get_user_info_by_code(self, auth_code):
        """Get DingTalk user info by temporary auth code (SSO callback).

        POST /topapi/v2/user/getuserinfo

        Args:
            auth_code: str, temporary code from DingTalk OAuth QR scan

        Returns:
            dict with keys: userid, unionid, openid, name, avatar, ...
        """
        if self._demo_mode():
            return self._mock_user_info(auth_code)

        return self._request(
            method="POST",
            path="/topapi/v2/user/getuserinfo",
            data={"code": auth_code},
        )

    # ==================================================================
    # Internal helpers
    # ==================================================================

    def _demo_mode(self):
        return getattr(settings, "DINGTALK_DEMO_MODE", True)

    def _request(self, method, path, data=None):
        """Execute a DingTalk API request with automatic token injection.

        Args:
            method: "GET" or "POST"
            path: API path, e.g. "/topapi/report/list"
            data: request body (JSON for POST, query params for GET)

        Returns:
            Parsed JSON response body

        Raises:
            APIRequestError on non-zero errcode
        """
        token = self._token_manager.get_token()
        url = f"{API_BASE}{path}"

        try:
            if method.upper() == "GET":
                params = data or {}
                params["access_token"] = token
                resp = requests.get(url, params=params, timeout=30)
            else:
                resp = requests.post(
                    url,
                    params={"access_token": token},
                    json=data or {},
                    timeout=30,
                )

            resp.raise_for_status()
            body = resp.json()
            logger.debug(f"DingTalk API {method} {path}: {body}")
            return check_response(body, endpoint=f"{method} {path}")

        except requests.RequestException as e:
            raise APIRequestError(
                endpoint=f"{method} {path}", errcode=-1, errmsg=f"网络错误: {e}"
            )

    # ==================================================================
    # Mock data for demo mode
    # ==================================================================

    def _mock_report_list(self, start_time, end_time, cursor=0, size=20):
        """Return realistic mock work report data for development."""
        logger.info(
            f"Demo mode: mock report list "
            f"start={start_time} end={end_time} cursor={cursor} size={size}"
        )

        if cursor >= 3:  # simulate pagination end
            return {"data_list": [], "next_cursor": 0, "has_more": False}

        # Build mock report entries
        mock_reports = []
        for i in range(min(size, 3)):
            idx = cursor * size + i + 1
            mock_reports.append({
                "report_id": f"demo_report_{idx:04d}",
                "template_name": "日报",
                "create_time": int(
                    (timezone.now() - timedelta(days=idx)).timestamp() * 1000
                ),
                "creator_id": f"demo_user_{idx % 5 + 1}",
                "creator_name": ["张三", "李四", "王五", "赵六", "钱七"][idx % 5],
                "dept_name": ["技术部", "产品部", "技术部", "市场部", "产品部"][idx % 5],
                "contents": [
                    {
                        "key": "今日完成工作",
                        "value": (
                            f"1. 【项目A】完成用户登录模块开发，耗时3小时\n"
                            f"2. 【项目B】修复数据导出 Bug，耗时1.5小时\n"
                            f"3. 参加项目周会，耗时0.5小时"
                        ),
                    },
                    {
                        "key": "今日未完成工作",
                        "value": "【项目A】密码重置功能仍在开发中",
                    },
                    {
                        "key": "需协调工作",
                        "value": "需要运维配合部署测试环境",
                    },
                    {
                        "key": "明日重点工作计划",
                        "value": "完成密码重置功能 + 代码 Review",
                    },
                    {
                        "key": "备注",
                        "value": "今日效率较高",
                    },
                ],
            })

        return {
            "data_list": mock_reports,
            "next_cursor": cursor + 1 if cursor < 2 else 0,
            "has_more": cursor < 2,
        }

    def _mock_user_info(self, auth_code):
        """Return mock user info for demo SSO callback."""
        logger.info(f"Demo mode: mock user info for auth_code={auth_code[:10]}...")

        # In demo mode, map specific auth_codes to demo users
        mock_users = {
            "demo_admin": {"userid": "demo_admin_001", "name": "系统管理员"},
            "demo_exec": {"userid": "demo_exec_001", "name": "公司高层"},
            "demo_mgr": {"userid": "demo_mgr_001", "name": "技术经理"},
            "demo_pm": {"userid": "demo_pm_001", "name": "产品经理"},
            "demo_emp": {"userid": "demo_emp_001", "name": "普通员工"},
        }

        user = mock_users.get(
            auth_code,
            {"userid": f"demo_user_{hash(auth_code) % 1000:03d}", "name": "Demo用户"},
        )

        return {
            "errcode": 0,
            "errmsg": "ok",
            "result": {
                "userid": user["userid"],
                "unionid": f"union_{user['userid']}",
                "openid": f"open_{user['userid']}",
                "name": user["name"],
                "avatar": "",
                "mobile": "13800138000",
            },
        }


# Module-level singleton client
client = DingTalkClient()
