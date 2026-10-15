# MiniQMT Share

本项目是 [xqshare](https://github.com/jasonhu/xqshare) 的本地 fork（仓库 [miniqmt-share](https://github.com/georgezhu08/miniqmt-share)），仅用于私有部署，**不发布到 PyPI**。

为避免误安装官方 `xqshare` 后产生 Python namespace、CLI 和配置冲突，本 fork 使用完全独立的命名空间。仓库根目录的 `README.md` 保持 upstream 原样；本 fork 的专属说明全部维护在本文档中。

## 命名映射

| 类型 | 本 fork | upstream `xqshare` |
|---|---|---|
| Git 仓库 | `miniqmt-share` | `xqshare` |
| Python distribution | `miniqmt-share` | `xqshare` |
| Python import package | `miniqmt_share` | `xqshare` |
| 服务端启动 | `python -m miniqmt_share.server` | `python -m xqshare.server` |
| 服务端 CLI | `miniqmt-share-server` | `xqshare-server` |
| 行情 CLI | `miniqmt-xtdata` | `xtdata` |
| 交易 CLI | `miniqmt-xttrader` | `xttrader` |
| 环境变量前缀 | `MINIQMT_SHARE_*` | `XQSHARE_*` |
| QMT 本身变量 | `QMT_*`（不变） | `QMT_*`（不变） |
| 默认端口 | `51812` | `18812` |
| 认证配置文件 | `miniqmt-share.clients.yaml` | `clients.yaml` |
| 日志目录 | `logs/miniqmt_share/` | `logs/` |

## 安装

本 fork 不存在于公共 package index，请在仓库目录本地安装：

```bash
cd /path/to/miniqmt-share
python -m pip install -e .          # 运行
python -m pip install -e ".[dev]"   # 开发（含 pytest/pandas/black/flake8）
```

如其他私有项目依赖本 fork，使用：

```text
miniqmt-share @ git+ssh://git@github.com/georgezhu08/miniqmt-share.git
```

## Python 使用

```python
import miniqmt_share
from miniqmt_share import connect, disconnect
from miniqmt_share.client import XtQuantRemote

connect("192.168.1.100")
```

服务端（Windows）：

```bash
python -m miniqmt_share.server --port 51812
```

服务端默认监听 `51812`（upstream 为 `18812`，避免同机冲突/误连）。显式 `--port` 或 `MINIQMT_SHARE_PORT` 优先级更高。

## 认证（fail-closed）

服务端启动时必须存在有效认证配置，否则**拒绝启动**（不提供任何公开默认 secret）：

1. 复制示例配置：`cp miniqmt-share.clients.yaml.example miniqmt-share.clients.yaml`
2. 为每个客户端设置强密钥
3. 服务端目录启动：`miniqmt-share-server`

配置文件查找优先级：显式参数 > `MINIQMT_SHARE_CLIENTS_FILE` > `./miniqmt-share.clients.yaml`。

客户端默认 client id 为 `miniqmt-share-client`；secret 无默认值，必须通过 `--secret` 或 `MINIQMT_SHARE_CLIENT_SECRET` 提供。

### 密钥管理

- **生成**：使用密码学随机源，例如 `python -c "import secrets; print(secrets.token_urlsafe(24))"`；禁止使用弱口令或示例中的占位值
- **存放**：`miniqmt-share.clients.yaml` 含密钥，必须保持 untracked（勿提交 git），文件权限仅限服务运行账户可读
- **轮换**：直接编辑服务端运行目录的 `miniqmt-share.clients.yaml` 即可，服务端每 5 分钟检测文件变更并自动热重载，**无需重启**；轮换后同步更新客户端 `.env` / `MINIQMT_SHARE_CLIENT_SECRET`
- **撤销**：删除对应 client 条目（热重载后该客户端的新连接被拒绝，已建立的旧连接在断开重连时失效）；彻底封禁需重启服务端

## 日志

默认日志目录 `logs/miniqmt_share/`（upstream 为 `logs/`），含 `server.log`、`api_calls.log`、`client_YYYYMMDD.log`。可用 `MINIQMT_SHARE_LOG_DIR`、`MINIQMT_SHARE_LOG_RETENTION` 覆盖。

## CLI

```bash
miniqmt-share-server --help
miniqmt-xtdata get_stock_list_in_sector --sector-name "沪深A股" -f json --compact
miniqmt-xttrader query_stock_positions
```

本 fork **不提供** `xqshare-server`、`xtdata`、`xttrader` 短命令。如需短命令，请在 shell 中自行 alias，不要通过 entry point 提供（会与官方 xqshare 竞争）。

## 环境变量迁移

| 旧（upstream） | 新（本 fork） |
|---|---|
| `XQSHARE_REMOTE_HOST` | `MINIQMT_SHARE_REMOTE_HOST` |
| `XQSHARE_REMOTE_PORT` | `MINIQMT_SHARE_REMOTE_PORT` |
| `XQSHARE_CLIENT_ID` | `MINIQMT_SHARE_CLIENT_ID` |
| `XQSHARE_CLIENT_SECRET` | `MINIQMT_SHARE_CLIENT_SECRET` |
| `XQSHARE_CLIENT_<client_id>` | `MINIQMT_SHARE_CLIENT_<client_id>` |
| `XQSHARE_FORMAT` | `MINIQMT_SHARE_FORMAT` |
| `XQSHARE_PORT` | `MINIQMT_SHARE_PORT` |
| `XQSHARE_LOG_DIR` | `MINIQMT_SHARE_LOG_DIR` |
| `XQSHARE_LOG_RETENTION` | `MINIQMT_SHARE_LOG_RETENTION` |
| `XQSHARE_RUN_INTEGRATION` | `MINIQMT_SHARE_RUN_INTEGRATION` |
| （upstream 无） | `MINIQMT_SHARE_CLIENTS_FILE` |

无 fallback：本 fork 不读取旧 `XQSHARE_*` 变量，请同步更新 `.env` 文件。`QMT_*`（如 `QMT_ACCOUNT_ID`、`QMT_USERDATA_PATH`）属于 QMT 本身命名空间，保持不变。

## 与官方 xqshare 共存

两个 distribution 可安装在同一环境而互不干扰：

- import 隔离：`miniqmt_share` 与 `xqshare` 是不同 package；
- CLI 隔离：本 fork 只提供 `miniqmt-*` 命令，官方 `xtdata`/`xttrader`/`xqshare-server` 由官方包提供，无竞争；
- 配置隔离：互不读取对方环境变量。

注意：RPC 协议序列化标记 `__xqshare_serialized__` 为 wire protocol 标识，client/server 两侧一致即可，为保持协议兼容有意保留，不影响与官方包的命名空间隔离。

## Upstream 同步原则

- `README.md` 为 upstream-owned：同步时直接接受 upstream 版本，不做 fork 品牌改写；
- 本文档由 fork 独立维护，同步后不被覆盖；
- 每次同步 upstream 后，按下方映射表重新审计新增文件：

```text
xqshare (distribution)    -> miniqmt-share
xqshare (Python package)  -> miniqmt_share
xqshare-server            -> miniqmt-share-server
xtdata CLI                -> miniqmt-xtdata
xttrader CLI              -> miniqmt-xttrader
XQSHARE_*                 -> MINIQMT_SHARE_*
```

审计命令：

```bash
rg -n --hidden --glob '!.git/**' 'from xqshare|import xqshare|XQSHARE_|xqshare-server|include = \["xqshare' .
```

（`README.md`、LICENSE、upstream remote 中的 `xqshare` 为 approved upstream references，不需替换。）

## Windows 服务器部署与升级

服务端需运行在装有 xtquant 的 Windows 上。推荐部署为 git 仓库，便于升级与版本审计：

### 首次部署

```bat
cd C:\Users\<user>
git clone https://github.com/georgezhu08/miniqmt-share.git
cd miniqmt-share
python -m pip install -e .
:: 创建认证配置（见"密钥管理"）
copy miniqmt-share.clients.yaml.example miniqmt-share.clients.yaml
```

若服务器无法直连 GitHub（连接被重置），用 git bundle 离线同步：

```bash
# 本地
git bundle create miniqmt-share.bundle main
scp miniqmt-share.bundle <user>@<server>:C:/Users/<user>/
```

```bat
:: 服务器
cd C:\Users\<user>\miniqmt-share
git init
git fetch C:\Users\<user>\miniqmt-share.bundle main
git checkout -f -B main FETCH_HEAD
```

### 日常升级

```bat
cd C:\Users\<user>\miniqmt-share
git pull                     :: 或 bundle 方式：git fetch <bundle> main && git checkout -f main
python -m pip install -e . --no-deps   :: 刷新 egg-info 版本元数据
```

然后重启服务（见下）。升级前建议 `git log --oneline -5` 确认版本，升级后 `python -c "import importlib.metadata as m; print(m.version('miniqmt-share'))"` 验证。

### 启动/重启服务

通过 `wmic process call create` 启动可脱离 SSH 会话存活：

```bat
wmic process call create "cmd /c cd /d C:\Users\<user>\miniqmt-share && python -m miniqmt_share.server --host 0.0.0.0 --port 51812 > server-stdout.log 2>&1"
```

重启流程：`netstat -ano | findstr 51812` 找到 PID → `taskkill /pid <PID> /f` → 重新启动。

验收：`netstat -ano | findstr 51812` 出现 LISTENING；`logs\miniqmt_share\server.log` 出现"有效账号数量"；客户端机器跑 `pytest tests/test_integration.py -m integration`（需设置 `MINIQMT_SHARE_REMOTE_HOST` 等环境变量）。

### 部署注意事项

- 认证配置 `miniqmt-share.clients.yaml` 为 untracked，`git checkout -f` 不会覆盖它；同样不受影响的还有 `.env`、`logs/`
- 默认端口 `51812` 与 upstream xqshare 的 `18812` 可同机并存，互不影响
- 旧客户端脚本若硬编码 `18812`/旧密钥，升级服务端后需同步更新

## Migration Notes

- v1.1.3+miniqmt.1：完成从 upstream `xqshare` 的完整命名空间迁移；旧 `XQSHARE_*` 环境变量不再被读取，升级前请更新部署的 `.env` 与启动脚本。
- v1.1.3+miniqmt.2（运行身份隔离）：
  - 默认端口 `18812` → `51812`（服务端/客户端/CLI/示例统一）；
  - 认证 fail-closed：移除公开默认 secret（`xqshare-default-secret`）与默认客户端 `client-standard`，配置缺失时服务端拒绝启动；
  - 认证配置文件 `clients.yaml` → `miniqmt-share.clients.yaml`，可用 `MINIQMT_SHARE_CLIENTS_FILE` 覆盖；
  - 日志目录 `logs/` → `logs/miniqmt_share/`，主日志更名为 `server.log`，logger 改为 `miniqmt_share.api` / `miniqmt_share.client`；
  - `pyproject.toml` 的 distribution readme 指向本文档（`README.md` 保持 upstream 原样）。
- upstream `README.md` 中的 `pip install xqshare`、`xtdata` 等内容描述的是 upstream 项目，保留原样。
