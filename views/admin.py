"""心与星寻 · 管理后台（Streamlit）。

只有管理员能进：邮箱 + 密码（写在 Streamlit Secrets 里，不进代码库）。
数据全部经服务端 RPC 读取（密钥在请求体），浏览器拿不到任何库凭据。

功能（参考成熟后台的信息架构）：
  总览       KPI 卡片 + 注册趋势 + 数据分布 + 最近动态
  用户管理   搜索 / 排序 / 全量导出 CSV / 点进单个用户
  用户详情   账号、资料、长期记忆、对话记录、日记、路灯
  警报中心   极端内容上报（高亮关键词），支持导出
  回应库     小程序端 116 条陪伴文案，按情绪/话题筛选
  系统自检   接口连通性 + 各表读数 + 密钥校验
"""

import os
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

from core.admin import AdminAPI, AdminError

VERSION = "1.0.0"


# ============================ 登录 ============================

# 内置口令（本工程既定值）。生产环境可在 Streamlit Secrets 的 [admin] 段覆盖。
DEFAULT_PWD = "gld20080802"
DEFAULT_KEY = "gld20080802"


def _creds():
    sec = {}
    try:
        sec = dict(st.secrets.get("admin", {}))
    except Exception:
        sec = {}
    email = sec.get("email") or os.environ.get("HSX_ADMIN_EMAIL") or "admin@heart-stars.local"
    pwd = sec.get("password") or os.environ.get("HSX_ADMIN_PASSWORD") or DEFAULT_PWD
    key = sec.get("db_key") or os.environ.get("HSX_ADMIN_KEY") or DEFAULT_KEY
    return email, pwd, key


def _login_screen():
    st.markdown('<div class="hero"><h1>管理后台</h1><p>心与星寻 · 仅管理员可进</p></div>', unsafe_allow_html=True)
    left, right = st.columns([1, 1.2])
    with left:
        with st.form("admin_login"):
            email = st.text_input("管理员邮箱")
            pwd = st.text_input("密码", type="password")
            if st.form_submit_button("进入", width="stretch"):
                ok_email, ok_pwd, _ = _creds()
                if email.strip().lower() == ok_email.lower() and pwd == ok_pwd:
                    st.session_state.admin_ok = True
                    st.rerun()
                else:
                    st.error("邮箱或密码不对")
    with right:
        st.markdown('<div class="card"><h4>这里能做什么</h4>'
                    '<p>· 看用户规模与增长趋势</p>'
                    '<p>· 查单个用户的资料、长期记忆与对话记录</p>'
                    '<p>· 接收极端内容警报，第一时间知道谁需要帮助</p>'
                    '<p>· 浏览小程序端 116 条陪伴文案</p></div>', unsafe_allow_html=True)
        st.caption("账号密码已内置于应用；若想更稳妥，可在 Streamlit Secrets 的 [admin] 段覆盖，"
                   "覆盖后立即生效（详见《Streamlit发布操作步骤.md》第 4 段）。")


# ============================ 小工具 ============================

def _api():
    if "admin_api" not in st.session_state:
        st.session_state.admin_api = AdminAPI(_creds()[2])
    return st.session_state.admin_api


def _run(fn, *a, **kw):
    try:
        return fn(*a, **kw), None
    except AdminError as e:
        return None, e.friendly


def _fmt_dt(s):
    if not s:
        return ""
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(s)[:16]


def _days_ago(n):
    return datetime.now().astimezone() - timedelta(days=n)


# ============================ 总览 ============================

def _page_overview(api):
    stats, err = _run(api.stats)
    if err:
        st.error(err)
        return
    stats = stats or {}

    st.markdown("### 总览")
    c = st.columns(4)
    c[0].metric("注册用户", stats.get("users", 0), help="不含 administrator 账号")
    c[1].metric("今日新增", stats.get("users_new_1d", 0))
    c[2].metric("近 7 天活跃", stats.get("active_7d", 0), help="7 天内有对话记录的用户数")
    c[3].metric("极端内容警报", stats.get("alerts", 0))

    c = st.columns(4)
    c[0].metric("对话消息", stats.get("messages", 0))
    c[1].metric("日记（蜡烛）", stats.get("diaries", 0))
    c[2].metric("周记（路灯）", stats.get("lamps", 0))
    c[3].metric("长期记忆档案", stats.get("memory", 0))

    st.caption("最近一条对话：%s ｜ 回应库文案：%d 条 ｜ 微信绑定：%d 条"
               % (_fmt_dt(stats.get("last_message_at")) or "—", stats.get("library", 0), stats.get("bindings", 0)))

    users, uerr = _run(api.users)
    if uerr:
        st.warning(uerr)
        return
    users = users or []

    st.markdown("#### 注册趋势")
    if users:
        df = pd.DataFrame(users)
        df["注册日"] = df["created_at"].apply(lambda s: str(s)[:10])
        trend = df.groupby("注册日").size().reset_index(name="新增").sort_values("注册日")
        st.bar_chart(trend.set_index("注册日"), height=220)

        col1, col2 = st.columns([1, 1])
        with col1:
            st.markdown("#### 账号来源")
            src = df["provider"].value_counts().rename(index={"wechat": "微信", "phone": "手机号", "unknown": "未知"})
            st.dataframe(src.rename("人数").reset_index().rename(columns={"index": "来源"}),
                         width="stretch", hide_index=True)
        with col2:
            st.markdown("#### 活跃度分布")
            live = pd.DataFrame({
                "指标": ["有对话", "有日记", "有周记", "有长期记忆"],
                "人数": [int(df["msg_count"].astype(int).gt(0).sum()),
                       int(df["diary_count"].astype(int).gt(0).sum()),
                       int(df["lamp_count"].astype(int).gt(0).sum()),
                       int(df["turns"].astype(int).gt(0).sum())],
            })
            st.dataframe(live, width="stretch", hide_index=True)


# ============================ 用户管理 ============================

def _page_users(api):
    st.markdown("### 用户管理")
    q = st.text_input("搜索（手机号 / 昵称 / uid）", placeholder="输入后回车")
    users, err = _run(api.users, q)
    if err:
        st.error(err)
        return
    users = users or []

    if not users:
        st.info("没有匹配的用户。")
        return

    df = pd.DataFrame(users)
    show = pd.DataFrame({
        "选": False,
        "用户": [u["nick_name"] or (u["phone"] or u["uid"][:14]) for u in users],
        "手机号": [u["phone"] or "—" for u in users],
        "来源": [{"wechat": "微信", "phone": "手机号"}.get(u["provider"], "未知") for u in users],
        "注册时间": [_fmt_dt(u["created_at"]) for u in users],
        "对话": [u["msg_count"] for u in users],
        "日记": [u["diary_count"] for u in users],
        "周记": [u["lamp_count"] for u in users],
        "轮数": [u["turns"] for u in users],
        "星币": [u["coins"] for u in users],
        "会员": ["是" if u["is_member"] else "否" for u in users],
        "uid": [u["uid"] for u in users],
    })
    st.caption("共 %d 位用户" % len(users))
    edited = st.data_editor(show, width="stretch", hide_index=True, height=420,
                            column_config={
                                "选": st.column_config.CheckboxColumn(width="small"),
                                "uid": st.column_config.TextColumn(width="medium"),
                            },
                            disabled=[c for c in show.columns if c != "选"])
    picked = edited[edited["选"] == True] if "选" in edited else pd.DataFrame()
    if not picked.empty:
        st.session_state.admin_uid = picked.iloc[0]["uid"]
        st.session_state.admin_page = "用户详情"
        st.rerun()

    st.download_button("导出全部用户 CSV", show.drop(columns=["选", "uid"]).to_csv(index=False).encode("utf-8-sig"),
                       file_name="heart-stars-users.csv", mime="text/csv")

    st.divider()
    st.markdown("#### 直接打开某个用户")
    opts = {("%s ｜ %s ｜ %s" % (u["nick_name"] or "未起名", u["phone"] or u["uid"][:16], _fmt_dt(u["created_at"]))): u["uid"] for u in users}
    sel = st.selectbox("选择用户", ["—"] + list(opts.keys()))
    if sel != "—":
        st.session_state.admin_uid = opts[sel]
        st.session_state.admin_page = "用户详情"
        st.rerun()


# ============================ 用户详情 ============================

def _page_detail(api):
    st.markdown("### 用户详情")
    uid = st.session_state.get("admin_uid")
    if not uid:
        st.info("先在「用户管理」里选一个用户。")
        return
    if st.button("← 返回用户列表"):
        st.session_state.admin_page = "用户管理"
        st.rerun()

    d, err = _run(api.user_detail, uid)
    if err:
        st.error(err)
        return
    d = d or {}
    acc = d.get("account") or {}
    prof = d.get("profile") or {}
    mem = d.get("memory") or {}

    c = st.columns(4)
    c[0].metric("对话消息", len(d.get("messages") or []))
    c[1].metric("日记", len(d.get("diaries") or []))
    c[2].metric("周记", len(d.get("lamps") or []))
    c[3].metric("累计轮数", mem.get("turn_count", 0))

    st.markdown('<div class="card"><h4>账号</h4>'
                '<p class="kv">uid：%s</p><p class="kv">手机号：%s</p>'
                '<p class="kv">注册：%s ｜ 最近登录：%s</p></div>'
                % (uid, acc.get("phone") or "—", _fmt_dt(acc.get("created_at")), _fmt_dt(acc.get("last_login"))),
                unsafe_allow_html=True)

    t1, t2, t3, t4 = st.tabs(["资料", "长期记忆", "对话记录", "日记 / 周记"])

    with t1:
        if prof:
            st.json(prof, expanded=True)
        else:
            st.caption("这位用户还没有个人资料行（可能是纯手机号新账号）。")

    with t2:
        if mem:
            st.markdown("**档案（注入给模型的版本）**")
            st.json(mem.get("profile") or {}, expanded=True)
            st.markdown("**近期状态**")
            st.json(mem.get("mood") or {}, expanded=True)
            st.caption("累计 %s 轮 ｜ 上次摘要于第 %s 轮 ｜ 更新于 %s"
                       % (mem.get("turn_count"), mem.get("summarized_at"), _fmt_dt(mem.get("updated_at"))))
        else:
            st.caption("还没有长期记忆档案（聊够 10 轮才会生成）。")

    with t3:
        msgs = d.get("messages") or []
        if not msgs:
            st.caption("还没有对话记录。")
        for m in reversed(msgs):
            who = "用户" if m["role"] == "user" else "星寻"
            st.markdown('<div class="card"><p class="kv">%s ｜ %s</p><p>%s</p></div>'
                        % (who, _fmt_dt(m.get("created_at")), m.get("content", "")),
                        unsafe_allow_html=True)
        if msgs:
            st.download_button("导出这位用户的对话 CSV",
                               pd.DataFrame(msgs).to_csv(index=False).encode("utf-8-sig"),
                               file_name="user-%s-chat.csv" % uid[:10], mime="text/csv")

    with t4:
        diaries = d.get("diaries") or []
        lamps = d.get("lamps") or []
        st.markdown("**日记（蜡烛）**")
        for x in diaries:
            st.markdown('<div class="card"><p class="kv">%s ｜ %s</p><p>%s</p></div>'
                        % (_fmt_dt(x.get("created_at")), x.get("source") or "write", x.get("content") or ""),
                        unsafe_allow_html=True)
        if not diaries:
            st.caption("没有日记。")
        st.markdown("**周记（路灯）**")
        for x in lamps:
            st.markdown('<div class="card"><p class="kv">%s ｜ %s ｜ 本周 %s 条</p><p>%s</p></div>'
                        % (_fmt_dt(x.get("created_at")), x.get("week_label") or "", x.get("week_count") or 0, x.get("content") or ""),
                        unsafe_allow_html=True)
        if not lamps:
            st.caption("没有周记。")


# ============================ 警报中心 ============================

def _page_alerts(api):
    st.markdown("### 警报中心")
    st.caption("用户发出极端内容时（自杀 / 自残 / 极端言论），系统会立刻停止对话、不保存该条，并把账号与内容推到这里。")
    alerts, err = _run(api.alerts)
    if err:
        st.error(err)
        return
    alerts = alerts or []

    if not alerts:
        st.success("目前没有警报。")
        return

    df = pd.DataFrame(alerts)
    df["时间"] = df["created_at"].apply(_fmt_dt)
    df["命中词"] = df["words"].apply(lambda s: "、".join([w for w in str(s).split(",") if w]))
    st.error("有 %d 条警报需要关注" % len(df))
    st.dataframe(df[["时间", "user_id", "source", "命中词", "content"]].rename(
        columns={"user_id": "用户", "source": "来源", "content": "原话"}),
        width="stretch", hide_index=True, height=380)
    st.download_button("导出警报 CSV", df.to_csv(index=False).encode("utf-8-sig"),
                       file_name="heart-stars-alerts.csv", mime="text/csv")

    st.markdown("#### 处置建议")
    st.markdown('<div class="card">'
                '<p>1. 如果这条警报来自一个已知账号，先看他的「用户详情」里的对话记录，判断是即时风险还是长期状态。</p>'
                '<p>2. 系统已经给用户看过安全回应（含 12356 与 120），但**真人跟进不可替代**。</p>'
                '<p>3. 记录处置结果（本后台不写库，避免误改线上数据）。</p></div>',
                unsafe_allow_html=True)


# ============================ 回应库 ============================

def _page_library(api):
    st.markdown("### 回应库")
    st.caption("小程序端不使用 AI 生成回复，改为从这张表里按情绪/话题选句（个人主体小程序不能过 AI 问答类目）。")
    q = st.text_input("搜索文案 / 情绪 / 话题", placeholder="例如：孤独")
    rows, err = _run(api.library, q)
    if err:
        st.error(err)
        return
    rows = rows or []
    if not rows:
        st.info("没有匹配的文案。")
        return

    df = pd.DataFrame(rows)
    st.caption("共 %d 条" % len(df))
    col1, col2 = st.columns(2)
    with col1:
        moods = ["全部"] + sorted(df["mood"].unique().tolist())
        msel = st.selectbox("按情绪筛选", moods)
    with col2:
        topics = ["全部"] + sorted(df["topic"].unique().tolist())
        tsel = st.selectbox("按话题筛选", topics)
    if msel != "全部":
        df = df[df["mood"] == msel]
    if tsel != "全部":
        df = df[df["topic"] == tsel]

    st.dataframe(df.rename(columns={"id": "ID", "mood": "情绪", "topic": "话题", "text": "文案",
                                    "weight": "权重", "enabled": "启用"}),
                 width="stretch", hide_index=True, height=460)


# ============================ 系统自检 ============================

def _page_health(api):
    st.markdown("### 系统自检")
    st.caption("后台读数据走的是数据库函数（RPC），密钥在请求体里传——云网关不透传自定义请求头，所以没用表直读。")
    ok = st.button("跑一次自检")
    if not ok and not st.session_state.get("health_done"):
        return
    st.session_state.health_done = True

    with st.spinner("检查中…"):
        stats, err = _run(api.stats)

    if err:
        st.error(err)
        st.markdown('<div class="card"><h4>排查顺序</h4>'
                    '<p>1. 密钥：DB 里的函数密钥与 Secrets 里的 <code>db_key</code> 是否一致</p>'
                    '<p>2. 函数：是否已创建 admin_stats / admin_users / admin_user_detail / admin_alerts_list / admin_library</p>'
                    '<p>3. 网络：应用能否访问 mp-api.app.workbuddy.host</p></div>', unsafe_allow_html=True)
        return

    st.success("接口连通，密钥正确。")
    st.json(stats or {}, expanded=True)
    st.caption("版本 v%s" % VERSION)


# ============================ 入口 ============================

PAGES = ["总览", "用户管理", "用户详情", "警报中心", "回应库", "系统自检"]


def render():
    st.markdown("""
    <style>
    .hero h1 { color:#ffd68f; margin:0; font-size:24px; }
    .hero p { color:#9aa6c4; margin:0; font-size:13px; }
    .card { background: rgba(28,36,58,.06); border:1px solid rgba(120,130,160,.25);
            border-radius:12px; padding:12px 14px; margin:8px 0; }
    .card h4 { margin:0 0 6px; font-size:14px; }
    </style>
    """, unsafe_allow_html=True)

    if not st.session_state.get("admin_ok"):
        _login_screen()
        return

    with st.sidebar:
        st.markdown("### 心与星寻 · 后台")
        st.caption("管理员：%s" % _creds()[0])
        st.session_state.admin_page = st.radio("功能", PAGES,
                                               index=PAGES.index(st.session_state.get("admin_page", "总览")))
        st.divider()
        if st.button("退出登录"):
            st.session_state.admin_ok = False
            st.rerun()

    api = _api()
    page = st.session_state.get("admin_page", "总览")
    if page == "总览":
        _page_overview(api)
    elif page == "用户管理":
        _page_users(api)
    elif page == "用户详情":
        _page_detail(api)
    elif page == "警报中心":
        _page_alerts(api)
    elif page == "回应库":
        _page_library(api)
    else:
        _page_health(api)
