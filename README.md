# 今日待办 · Today Todo

一个极简的在线待办清单：邮箱账号登录、数据云端存储、移动端友好，支持一键隐藏已完成项目。

![版本](https://img.shields.io/badge/version-v1.6-blue)
![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.x-000000?logo=flask&logoColor=white)

## 功能特性

- **新增任务**：回车或点击「添加」；空白内容前后端双重拦截
- **勾选 / 取消完成**：已完成任务划线并自动沉底，剩余计数实时更新
- **删除任务**：单条删除，点击即移除
- **剩余计数**：顶部实时显示「剩余 N 项待完成」与总条数
- **一键隐藏已完成**：待办与已完成之间整行灰底按钮，显示偏好本地记忆
- **邮箱账号体系**：注册 / 登录 / 退出，PBKDF2 加盐哈希存密码，Token 鉴权
- **找回密码**：忘记密码时用「邮箱 + 管理员密钥」自助重置，密钥存于服务端 `data/admin_key.txt`，重置后作废旧 Token
- **云端同步**：数据存服务端 SQLite，换设备登录同一邮箱即可看到相同待办
- **移动端适配**：390px 起响应式布局，触摸友好的点击区域，适配刘海屏安全区
- **PWA 可安装**：安卓 Chrome「添加到主屏幕」后全屏运行，离线也能打开，体验接近原生 App
- **乐观更新**：新增 / 勾选 / 删除均为即时反馈，后台静默同步，失败自动回滚

## 技术栈

| 层 | 选型 |
|---|---|
| 后端 | Python 3.11 + Flask（单端口 HTTP 服务） |
| 数据库 | SQLite（WAL 模式 + synchronous=NORMAL） |
| 前端 | 原生 HTML / CSS / JavaScript（无构建、无框架依赖） |
| 鉴权 | 邮箱 + 密码（PBKDF2-SHA256，10 万次迭代）+ 随机 Token |

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动服务（默认 3000 端口，可用 PORT 环境变量覆盖）
python server.py

# 3. 打开浏览器
open http://127.0.0.1:3000
```

首次启动会自动创建 `data/todos.db` 并建表，无需手动初始化数据库。

## 安装到手机（免应用商店）

1. 手机 Chrome 打开站点（**必须是 HTTPS 或 localhost**，PWA 的硬性要求）
2. 点右上角菜单 → **「添加到主屏幕」/「安装应用」**
3. 桌面出现图标，打开后全屏运行、无浏览器地址栏，与原生 App 观感一致

> Service Worker 会缓存应用外壳，断网时仍能打开界面（数据需联网同步）。
> 修改前端后若发现手机仍是旧版本，把 `static/sw.js` 里的 `CACHE_NAME` 版本号改一下即可强制更新。

## 目录结构

```
todo-app/
├── server.py               # Flask 后端：认证 + 待办 CRUD + 静态页托管 + PWA 路由
├── static/
│   ├── index.html          # 前端单页应用（登录层 + 待办主界面）
│   ├── manifest.webmanifest# PWA 清单（应用名、图标、独立窗口模式）
│   ├── sw.js               # Service Worker（应用外壳缓存 + 离线回退）
│   └── icon-*.png          # 应用图标（192/512/maskable/apple-touch）
├── requirements.txt        # Python 依赖
├── development-log.md      # 开发日志（含 Bug 排查与迭代记录）
├── preview/                # 界面截图
└── data/                   # 运行时生成，已被 .gitignore 排除
    └── todos.db
```

## API 一览

所有需登录的接口通过自定义请求头 **`X-Auth-Token`** 携带登录 Token。

| 方法 | 路径 | 说明 | 鉴权 |
|---|---|---|---|
| POST | `/api/register` | 注册并返回 Token | 否 |
| POST | `/api/login` | 登录并返回 Token | 否 |
| POST | `/api/reset-password` | 凭邮箱 + 管理员密钥重置密码，作废旧 Token | 否 |
| POST | `/api/logout` | 退出，注销当前 Token | 是 |
| GET | `/api/todos` | 获取当前用户全部待办 | 是 |
| POST | `/api/todos` | 新增待办（`{"text": "..."}`） | 是 |
| PUT | `/api/todos/<id>` | 切换完成状态（`{"done": true}`） | 是 |
| DELETE | `/api/todos/<id>` | 删除待办 | 是 |

**错误约定**：参数非法返回 `400`，未登录或 Token 失效返回 `401`，非本人资源返回 `404`，响应体统一为 `{"error": "提示文案"}`。

## 设计要点

### 为什么用 `X-Auth-Token` 而不是 `Authorization`

托管平台的反向代理会用平台自身的 JWT 覆盖 `Authorization` 请求头，导致自建服务的登录 Token 丢失、登录后立即 401。改用自定义头 `X-Auth-Token` 可稳定穿透代理。详见 [`development-log.md`](./development-log.md) 第四章。

### 为什么做乐观更新

线上单次 API 往返约 100ms，若每次操作都等响应再更新界面会有明显延迟感。前端改为「先更新界面、后台同步、失败回滚」，实测交互反馈从约 100~300ms 降至 1ms 级。

### 数据隔离

所有待办查询与写入都带 `user_id` 条件，跨账号访问返回 404，避免越权读写。

## 部署

项目可作为单个 HTTP 服务部署到任意支持 Python 的平台（监听 `PORT` 环境变量、绑定 `0.0.0.0`）：

```bash
PORT=3000 python server.py
```

生产环境建议用 WSGI 服务器替代 Flask 开发服务器，例如：

```bash
pip install gunicorn
PORT=3000 gunicorn -w 2 -b 0.0.0.0:$PORT server:app
```

> 注意：SQLite 适合单机小流量场景。若需多实例横向扩容，请将存储层替换为 PostgreSQL / MySQL 等集中式数据库。

## 安全说明

- 密码以 PBKDF2-SHA256（10 万次迭代 + 每用户随机盐）哈希存储，不落明文
- 登录 Token 为 32 字节随机值，退出登录即从服务端删除
- `data/` 目录已加入 `.gitignore`，数据库不会进入版本库
- 仓库中不含任何密钥；真实部署请通过环境变量或平台密钥管理注入

## 许可证

如需开源，可自行添加 `LICENSE` 文件（如 MIT）。当前未声明许可证。
