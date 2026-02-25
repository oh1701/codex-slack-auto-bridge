# Codex Slack Auto Bridge

一个基于 Socket Mode 的轻量桥接器：把 Slack 消息转发到本地 `codex` CLI，并将回复发回 Slack 线程。

Languages: [English](./README.md) | [한국어](./README.ko.md) | [日本語](./README.ja.md) | 中文

## 0) 给 AI 的安装请求语句

可直接复制到 AI 工具中：

```text
Install this repository from https://github.com/oh1701/codex-slack-auto-bridge and follow README exactly.
```

## 1) 前置条件

- 已安装 `codex` CLI
- Python 3.11+
- Slack 应用令牌：
  - App-Level token（`xapp-...`）
  - Bot token（`xoxb-...`）

将其安装到 Codex 文件夹下：`~/.codex/codex-slack-auto-bridge`.

示例：

```text
~/.codex/
└── codex-slack-auto-bridge/
    ├── README.md
    ├── scripts/
    ├── slack-bridge-runtime/
    └── log/
```

## 2) Slack 应用配置（Socket Mode）

1. 创建应用
   - 打开 `https://api.slack.com/apps`
   - `Create New App` -> `From scratch`
   - 选择应用名和工作区

2. 启用 Socket Mode + 创建 App-Level token
   - 打开 `Socket Mode`
   - 启用
   - 使用 `connections:write` scope 创建 token
   - 将 `xapp-...` 写入 `slack.app_token`

3. 在 `OAuth & Permissions` 添加 Bot Token Scope
   - 必需：
     - `app_mentions:read`
     - `chat:write`
   - 推荐：
     - `channels:history`
     - `groups:history`
     - `im:history`
     - `mpim:history`

4. 安装到工作区
   - 点击 `Install to Workspace`
   - 将 `xoxb-...` 写入 `slack.bot_token`

5. 配置 Event Subscriptions
   - 启用 `Event Subscriptions`
   - 使用 Socket Mode 时不需要 Request URL
   - 添加 bot events：
     - 最低：`app_mention`
     - 推荐：`message.channels`, `message.groups`, `message.im`, `message.mpim`
   - 若 Slack 提示则重新安装应用

可选环境变量：

```bash
export SLACK_APP_TOKEN="xapp-..."
export SLACK_BOT_TOKEN="xoxb-..."
```

## 3) 安装

在仓库根目录执行：

```bash
chmod +x scripts/*.sh
./scripts/install.sh
```

该步骤会：
- 创建 `slack-bridge-runtime/.venv`
- 安装 Python 依赖

## 4) 配置加载顺序

桥接器按以下顺序读取配置：

1. `./config.toml`（本地配置，优先级最高）
2. `~/.codex/config.toml`（Codex 全局配置，兜底）
3. 环境变量（可选兜底）

## 5) 配置 `config.toml`

请在 `~/.codex/config.toml` 中填写配置。

如果存在 `./config.toml`，则其优先于 `~/.codex/config.toml`。

`~/.codex/config.toml` 示例：

```toml
[slack]
app_token = "xapp-..."
bot_token = "xoxb-..."
channel_id = "C0123456789" # 可选

[slack_bridge]
codex_cd = "/absolute/path/to/your/project" # 可选（默认: 桥接仓库路径）
codex_timeout_sec = 300
history_turns = 6
mention_only = false
allowed_channels = []
```

### 频道设置

- `slack.channel_id`：默认单频道过滤
- `slack_bridge.allowed_channels`：显式允许频道列表
- 当 `allowed_channels` 为空且设置了 `channel_id` 时，使用 `channel_id`
- 两者都为空时，允许所有频道
- DM 始终允许

频道 ID 格式：
- 公共频道：`C...`
- 私有频道：`G...`
- DM：`D...`

如何获取频道 ID：
- 在 Slack 打开频道并复制链接
- 示例：`https://app.slack.com/client/T.../C0123456789`
- 使用 `C0123456789`

### 桥接器行为设置

- `codex_timeout_sec`：
  - 单次 `codex exec` 的最大等待时间（秒）
  - 超时后桥接器会返回超时错误消息
- `history_turns`：
  - 每个线程在提示词中包含的历史对话轮数
  - 数值越大，上下文越完整，但 token 消耗越高
- `mention_only`：
  - `true`：在频道中只处理提及机器人的消息
  - `false`：在频道中也处理普通消息
  - DM 不受此项影响，始终会处理

## 5) 使用 `codex` / `codex resume` 自动启动

安装 shell hook：

```bash
./scripts/install-shell-hook.sh
source ~/.zshrc   # bash: source ~/.bashrc
```

运行 `codex` 或 `codex resume` 时会自动在后台启动并保持桥接进程。

## 6) 最终运行命令

完成 shell hook（`./scripts/install-shell-hook.sh` + `source ~/.zshrc` 或 `~/.bashrc`）后：

```bash
codex
codex resume
codex resume <session_id>
```
