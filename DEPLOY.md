# 部署到老薛主机（cPanel + Setup Python App）

面向**完全不熟悉 Linux 命令**的操作手册。全程在 cPanel 网页里点，只有第 4 步需要复制粘贴三条命令。

> 对应版本：v1.5（Flask + SQLite + PWA）
> 预计耗时：30–45 分钟（不含域名解析生效时间）

---

## 第 0 步：准备域名解析

在你**购买域名的网站**（不一定是老薛）后台，找到 DNS 解析设置，添加：

| 类型 | 主机记录 | 记录值 |
|---|---|---|
| A | `@` | 老薛主机面板首页显示的 IP |
| A | `www` | 同上 |

如果想用子域名（推荐，例如 `todo.你的域名.com`）：

| 类型 | 主机记录 | 记录值 |
|---|---|---|
| A | `todo` | 同上 |

解析生效通常 10 分钟～2 小时，期间可以先做下面的步骤。

---

## 第 1 步：在 cPanel 创建 Python 应用

进入 cPanel → 「软件」→ **Setup Python App** → 右上角 **CREATE APPLICATION**，按下面填：

| 字段 | 填写内容 | 说明 |
|---|---|---|
| Python version | 选 **3.8 或更高**（有 3.11 选 3.11） | 代码兼容 3.8+ |
| Application root | `todoapp` | 会自动变成 `/home/你的账户/todoapp` |
| Application URL | 选择你的域名，或子域名 `todo.你的域名.com` | 网站访问地址 |
| Application startup file | `passenger_wsgi.py` | **必须完全一致** |
| Application entry point | `application` | **必须完全一致** |
| Passenger log file | 留空，或填 `passenger.log` | 出问题时看日志用 |

点 **CREATE**。创建后页面会显示一段类似这样的信息，先复制保存：

```
Virtualenv: /home/你的账户/virtualenv/todoapp/3.11
```

> 如果 Application URL 的下拉框里没有你想要的域名/子域名：先退出这里，到 cPanel →「域名」→ **子域名 / 别名** 把它加进去，再回来创建应用。

⚠️ **重要：先不要填任何代码，先做下一步上传文件。**

---

## 第 2 步：上传项目文件

1. 在 cPanel 找到「文件」→ **文件管理器**
2. 进入 `public_html` 的**上一级目录**（就是你的 home 目录，能看到 `public_html`、`mail`、`www` 等文件夹）
3. 点上方 **上传** → 选择事先准备好的 `todo-app-deploy.zip` → 等待上传完成
4. 上传后在文件列表里找到 `todo-app-deploy.zip`，右键 → **解压（Extract）** → 会生成 `todo-app-deploy` 文件夹
5. 把这个文件夹**重命名为 `todoapp`**（必须和第 1 步 Application root 一致）
6. 确认目录里能看到这些文件/文件夹：
   ```
   passenger_wsgi.py
   server.py
   static/
   requirements.txt
   manifest.webmanifest (在 static 里)
   ```

> 部署包里**不含数据库**，首次访问会自动创建 `data/todos.db`，这是干净的初始状态。

---

## 第 3 步：安装 Flask 依赖

在 cPanel 首页「高级」区块找 **终端（Terminal）**，点开。如果找不到终端，就在你电脑上用 SSH 工具（如 PuTTY）连上主机（老薛会员中心可以看 SSH 信息）。

复制粘贴下面三行，每行粘完按回车：

```bash
cd ~/todoapp
source ~/virtualenv/todoapp/3.11/bin/activate
pip install -r requirements.txt
```

> 第二行里的 `3.11` 换成第 1 步页面上显示的 Python 版本（例如 `3.8`、`3.10`）。

看到 `Successfully installed flask-...` 就成功了。

---

## 第 4 步：重启应用并测试

回到 cPanel → **Setup Python App**，找到刚建的应用，点 **RESTART**。

然后在浏览器打开你的域名：

- ✅ 看到「📝 今日待办」和登录框 → 部署成功
- ❌ 看到 500 / Internal Server Error → 打开应用详情页里配置的 `passenger.log`，把最后 20 行发给我

**注册一个账号测试**：新增一条、勾选、删除、刷新页面看是否还在。

---

## 第 5 步：开启 HTTPS（PWA 必需）

1. cPanel → 「安全」→ **SSL/TLS Status**
2. 找到你的域名，点 **Run AutoSSL**（如果没有证书的话）
3. 等待几分钟，状态变成绿色 ✅
4. 回到 cPanel → 「网站」→ **Domains**，把域名的 **Force HTTPS Redirect** 打开

现在用 `https://你的域名` 访问，浏览器地址栏应显示小锁 🔒。

---

## 第 6 步：验证 PWA 可安装

用**手机 Chrome** 打开 `https://你的域名`，依次检查：

1. 页面能打开、能登录 → 后端正常
2. 浏览器访问 `https://你的域名/manifest.webmanifest` → 能看到一段 JSON，不是 404
3. 浏览器访问 `https://你的域名/sw.js` → 能看到 JavaScript 代码，不是 404
4. Chrome 菜单 → **「添加到主屏幕」/「安装应用」** → 桌面出现蓝色对勾图标
5. 打开桌面图标 → 全屏运行、没有地址栏 ✅

> 若第 2、3 项是 404，说明文件没上传到正确目录，回到第 2 步核对。

---

## 第 7 步：备份（重要）

cPanel 自带备份：**「文件」→ 备份 / Backup Wizard** → 下载完整备份，建议每月一次。

需要单独备份的数据只有一个文件：

```
/home/你的账户/todoapp/data/todos.db
```

用文件管理器右键 **下载** 即可。恢复时先停止应用，上传覆盖，再 RESTART。

---

## 常见问题

| 现象 | 原因 / 解决 |
|---|---|
| 500 Internal Server Error | 看 `passenger.log`；最常见是没装 flask 或 startup file 填错 |
| 页面样式全乱、图标 404 | `static/` 目录没上传完整，或重命名后的目录名不是 `todoapp` |
| 能打开但一直转圈、接口 401 | 正常，需要先注册/登录（这是设计行为） |
| 手机装了 PWA 后界面是旧的 | `static/sw.js` 里的 `CACHE_NAME` 改个版本号（如 `todo-shell-v2`），重新访问一次 |
| 改了代码没生效 | cPanel → Setup Python App → **RESTART** |
| 域名打不开 | DNS 未生效，等一会儿；或在 cPanel「Domains」里确认域名已绑定到该应用 |

---

## 部署完成后的检查清单

- [ ] `https://你的域名` 可访问，有 HTTPS 小锁
- [ ] 注册 / 登录 / 新增 / 勾选 / 删除 / 隐藏已完成 全部正常
- [ ] 手机 Chrome「添加到主屏幕」成功，图标正确
- [ ] 断网打开 PWA 不白屏
- [ ] 已下载一次数据库备份

完成这些，你的 App 就正式跑在自己域名上了，与家人共用即可（注册时用各自邮箱，数据互相隔离）。
