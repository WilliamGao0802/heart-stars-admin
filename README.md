# 心与星寻 · 管理者网站（最终版）

与「网站最终版」配套的运营后台，**独立部署、独立链接**。只有管理员能进。
**六个页面**：总览 / 用户管理 / 用户详情 / 警报中心 / 回应库 / 系统自检。

> 它读的是**同一个云数据库**，与网站、小程序、App 看到的是同一批用户与数据。

---

## 一、登录信息

| 项目 | 值 |
|---|---|
| 登录邮箱 | `admin@heart-stars.local` |
| 登录密码 | `gld20080802` |
| 数据库密钥 `db_key` | `gld20080802`（必须与数据库函数里一致） |

---

## 二、为什么这个后台不能放 GitHub Pages

它是 **Streamlit 应用**（需要跑 Python 服务端），而 GitHub Pages 只能托管静态网页。
所以它走 **Streamlit Community Cloud**——好处是**不看仓库名**，随便起。

---

## 三、部署（4 步）

### 第 1 步 · 建仓库
https://github.com/new → 仓库名 `heart-stars-admin` → 可见性选 **Private（私有）**
→ 不要勾 Add a README → Create

> 建议 Private：口令写在源码里，仓库公开等于把后台口令公开。
> Streamlit Cloud **支持私有仓库**，功能没有区别。

### 第 2 步 · 上传
1. 资源管理器进入本文件夹**里面**
2. 「查看 → 显示 → 隐藏的项目」，让 `.streamlit` 现形
3. **Ctrl+A 全选里面的全部内容**（不是选中这个文件夹本身！）
4. 进空仓库 → **Add file** → **Upload files** → 拖进去 → **Commit changes**

> ⚠️ 两个坑：① 拖的是文件夹**里面的东西**，拖文件夹本身会多套一层，
> 云端找不到 `app.py`；② `.streamlit/` 是**隐藏文件夹**，必须一起传。

### 第 3 步 · 部署
1. https://share.streamlit.io → 用 GitHub 登录
2. **Create app** → **Deploy a public app from GitHub**
3. 三项填：
   - **Repository**：`你的用户名/heart-stars-admin`
   - **Branch**：`main`
   - **Main file path**：**`app.py`** ← 不要加文件夹前缀
4. 点 **Deploy!**，等 1–3 分钟

> 看不到私有仓库？点 GitHub 授权入口，把这个仓库勾上再刷新。

### 第 4 步 · （可选）换自己的口令
**App Settings → Secrets** 粘：

```toml
[admin]
email = "你的邮箱@example.com"
password = "换一个强密码"
db_key = "gld20080802"
```

> `db_key` **必须保持 `gld20080802`**（要和云端数据库函数一致）；`email`/`password` 随便改。

---

## 四、怎么读到数据的

所有读取都走云端 **RPC 函数**（`admin_stats` / `admin_users` / `admin_user_detail` /
`admin_alerts_list` / `admin_library`），密钥放请求体、函数内部校验。

原因：实测云网关**不透传自定义请求头**，「请求头带密钥 + 行级安全策略」读不到数据（返回 0 行）。

后台**只读**，不提供写操作，不会误改线上数据。

---

## 五、常见问题

**Q：登录说「邮箱或密码不对」** → 用上面第二节的账号。
**Q：进去了但说「管理密钥不正确」** → Secrets 里 `db_key` 改回 `gld20080802`。
**Q：部署后白屏** → Main file path 是不是 `app.py`。
