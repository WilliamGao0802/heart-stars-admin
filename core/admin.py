"""管理后台数据访问（core 层，不依赖 streamlit）。

所有读操作走 PostgREST RPC（SECURITY DEFINER 函数），密钥在请求体里传。
写操作（禁用/备注等）暂时不做——后台定位是「看」，不误伤线上数据。
"""

import os

from .cloud import CloudClient, CloudError


def default_admin_key():
    """优先取环境变量 / Streamlit Secrets，没有则用项目既定密钥。"""
    return os.environ.get("HSX_ADMIN_KEY", "gld20080802")


def make_admin_client(key=None):
    """管理员客户端：不带用户会话，只带管理密钥。"""
    return _client(key)


def _client(key):
    c = CloudClient()
    c._admin_key = key or default_admin_key()
    return c


class AdminAPI:
    def __init__(self, key=None):
        self.key = key or default_admin_key()
        self.client = _client(self.key)

    def _rpc(self, fn, params=None):
        p = {"p_key": self.key}
        if params:
            p.update(params)
        try:
            return self.client.rpc(fn, p)
        except CloudError as e:
            raise AdminError(e.message, e.code)

    # ---------------- 接口 ----------------

    def stats(self):
        return self._rpc("admin_stats") or {}

    def users(self, q="", limit=200, offset=0):
        return self._rpc("admin_users", {"p_limit": limit, "p_offset": offset, "p_q": q}) or []

    def user_detail(self, uid):
        return self._rpc("admin_user_detail", {"p_uid": uid}) or {}

    def alerts(self, limit=200):
        return self._rpc("admin_alerts_list", {"p_limit": limit}) or []

    def library(self, q="", limit=800):
        return self._rpc("admin_library", {"p_q": q, "p_limit": limit}) or []

    def ping(self):
        try:
            return self.client.rpc("admin_stats", {"p_key": self.key}) is not None
        except CloudError:
            return False


class AdminError(Exception):
    def __init__(self, message, code=""):
        super().__init__(message)
        self.message = message
        self.code = code

    @property
    def friendly(self):
        if self.code == "DATABASE_P0001" or "forbidden" in self.message:
            return "管理密钥不正确"
        if self.code == "no_rpc" or "does not exist" in self.message:
            return "后台数据库函数还没建好（请先执行建函数脚本）"
        return self.message
