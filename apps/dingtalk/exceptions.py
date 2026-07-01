"""
DingTalk-specific exceptions.
"""
import logging

logger = logging.getLogger("apps")


class DingTalkError(Exception):
    """Base exception for DingTalk API errors."""

    def __init__(self, message="钉钉 API 错误", errcode=None, errmsg=None):
        self.errcode = errcode
        self.errmsg = errmsg
        full_msg = f"{message}: errcode={errcode}, errmsg={errmsg}"
        super().__init__(full_msg)


class TokenRefreshError(DingTalkError):
    """Failed to refresh access token."""

    def __init__(self, errcode=None, errmsg=None):
        super().__init__("钉钉 Token 获取失败", errcode=errcode, errmsg=errmsg)


class APIRequestError(DingTalkError):
    """Generic API request failure."""

    def __init__(self, endpoint="", errcode=None, errmsg=None):
        super().__init__(f"钉钉 API 请求失败 [{endpoint}]", errcode=errcode, errmsg=errmsg)


def check_response(response_json, endpoint=""):
    """Validate DingTalk API response.

    All DingTalk APIs return `{"errcode": 0, ...}` on success.
    Raises APIRequestError when errcode != 0.
    """
    errcode = response_json.get("errcode", -1)
    if errcode != 0:
        errmsg = response_json.get("errmsg", "未知错误")
        logger.error(f"DingTalk API error [{endpoint}]: errcode={errcode} errmsg={errmsg}")
        raise APIRequestError(endpoint=endpoint, errcode=errcode, errmsg=errmsg)
    return response_json
