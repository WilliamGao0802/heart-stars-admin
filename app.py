"""心与星寻 · 管理者网站（最终版）。

起服务：   streamlit run app.py

只有管理后台一个页面，入口即登录页。收件箱式六页面在登录后出现。
"""

import streamlit as st

st.set_page_config(
    page_title="心与星寻 · 管理后台",
    page_icon="🔒",
    layout="wide",
    initial_sidebar_state="expanded",
)

from views import admin  # noqa: E402  （必须在 set_page_config 之后导入）

admin.render()
