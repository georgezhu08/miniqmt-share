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
python -m miniqmt_share.server --port 18812
```

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

无 fallback：本 fork 不读取旧 `XQSHARE_*` 变量，请同步更新 `.env` 文件。`QMT_*`（如 `QMT_ACCOUNT_ID`、`QMT_USERDATA_PATH`）属于 QMT 本身命名空间，保持不变。

## 与官方 xqshare 共存

两个 distribution 可安装在同一环境而互不干扰：

- import 隔离：`miniqmt_share` 与 `xqshare` 是不同 package；
- CLI 隔离：本 fork 只提供 `miniqmt-*` 命令，官方 `xtdata`/`xttrader`/`xqshare-server` 由官方包提供，无竞争；
- 配置隔离：互不读取对方环境变量。

注意：RPC 协议序列化标记 `__xqshare_serialized__` 与默认客户端密钥 `xqshare-default-secret` 为历史兼容值，client/server 两侧一致即可，不影响与官方包的命名空间隔离。

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

## Migration Notes

- v1.1.3+miniqmt.1：完成从 upstream `xqshare` 的完整命名空间迁移；旧 `XQSHARE_*` 环境变量不再被读取，升级前请更新部署的 `.env` 与启动脚本。
- upstream `README.md` 中的 `pip install xqshare`、`xtdata` 等内容描述的是 upstream 项目，保留原样。
