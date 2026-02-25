# Codex Slack Auto Bridge

A lightweight Socket Mode bridge that relays Slack messages to local `codex` CLI and posts replies back to Slack threads.

Languages: English (default) | [한국어](./README.ko.md) | [日本語](./README.ja.md) | [中文](./README.zh-CN.md)

## 0) Prompt For AI Install Help

Copy and paste this into your AI tool:

```text
Install this repository from https://github.com/oh1701/codex-slack-auto-bridge and follow README exactly.
```

## 1) Prerequisites

- `codex` CLI installed
- Python 3.11+
- Slack app tokens:
  - App-Level token (`xapp-...`)
  - Bot token (`xoxb-...`)

## 2) Slack App Setup (Socket Mode)

1. Create app
   - Go to `https://api.slack.com/apps`
   - `Create New App` -> `From scratch`
   - Choose app name and workspace

2. Enable Socket Mode + create App-Level token
   - Open `Socket Mode`
   - Enable it
   - Create App-Level token with scope `connections:write`
   - Put `xapp-...` into `slack.app_token`

3. Add Bot Token Scopes in `OAuth & Permissions`
   - Required:
     - `app_mentions:read`
     - `chat:write`
   - Recommended (for channel/DM history handling):
     - `channels:history`
     - `groups:history`
     - `im:history`
     - `mpim:history`

4. Install app to workspace
   - Click `Install to Workspace`
   - Put `xoxb-...` into `slack.bot_token`

5. Configure Event Subscriptions
   - Enable `Event Subscriptions`
   - For Socket Mode, Request URL is not required
   - Add bot events:
     - Minimum: `app_mention`
     - Recommended: `message.channels`, `message.groups`, `message.im`, `message.mpim`
   - Reinstall app if Slack asks

Optional environment variables:

```bash
export SLACK_APP_TOKEN="xapp-..."
export SLACK_BOT_TOKEN="xoxb-..."
```

## 3) Install (권장 순서)

Run from repository root in this order:

```bash
chmod +x scripts/*.sh slack-bridge-runtime/*.sh

# 1) Create venv and install requirements.txt
./slack-bridge-runtime/bootstrap.sh

# 2) (Optional) copy example config as baseline
cp -n config.toml.example ~/.codex/config.toml

# 3) (Recommended) install shell hook for auto-start
./scripts/install.sh --with-shell-hook
```

`./slack-bridge-runtime/bootstrap.sh` is the point that runs:

```bash
python3 -m pip install -r slack-bridge-runtime/requirements.txt
```

`./scripts/install.sh` also calls the same bootstrap internally, so if you only need dependencies, you can run either:

```bash
./scripts/install.sh
```

or:

```bash
./slack-bridge-runtime/bootstrap.sh
```

What this does:
- Creates `slack-bridge-runtime/.venv`
- Installs Python dependencies from `slack-bridge-runtime/requirements.txt`

## 4) Config Loading Order

The bridge loads configuration in this order:

1. `./config.toml` (local project config, highest priority)
2. `~/.codex/config.toml` (global Codex fallback)
3. Environment variables (optional fallback)

## 5) Configure `config.toml`

Write values to `~/.codex/config.toml` (global config).

If you do create `./config.toml`, it takes precedence over `~/.codex/config.toml`.

Example content for `~/.codex/config.toml`:

```toml
[slack]
app_token = "xapp-..."
bot_token = "xoxb-..."
channel_id = "C0123456789" # optional

[slack_bridge]
codex_cd = "/absolute/path/to/your/project" # optional (default: bridge repo path)
codex_timeout_sec = 300
history_turns = 6
mention_only = false
allowed_channels = []
```

### Channel Settings

- `slack.channel_id`: default single-channel filter.
- `slack_bridge.allowed_channels`: explicit allowlist.
- If `allowed_channels` is empty and `channel_id` is set, `channel_id` is used.
- If both are empty, all channels are allowed.
- DMs are always allowed.

Channel ID formats:
- Public channel: `C...`
- Private channel: `G...`
- DM: `D...`

How to find channel ID:
- Open the channel in Slack and copy its link.
- Example link: `https://app.slack.com/client/T.../C0123456789`
- Use `C0123456789` as the ID.

### Bridge Behavior Settings

- `codex_timeout_sec`:
  - Maximum time (seconds) to wait for one `codex exec` response.
  - If timeout is reached, the bridge returns a timeout error message.
- `history_turns`:
  - Number of previous conversation turns to include in prompt context per thread.
  - Higher value keeps more context, but uses more tokens.
- `mention_only`:
  - `true`: in channels, process only messages that mention the bot.
  - `false`: in channels, process normal messages too.
  - In DMs, messages are processed regardless of this setting.

## 5) Auto-Start With `codex` / `codex resume`

Install shell hook:

```bash
./scripts/install-shell-hook.sh
source ~/.zshrc   # bash: source ~/.bashrc
```

Running `codex` or `codex resume` auto-starts the bridge in background and keeps it running.

## 6) Final Run Commands

After shell hook setup (`./scripts/install-shell-hook.sh` + `source ~/.zshrc` or `~/.bashrc`):

```bash
codex
codex resume
codex resume <session_id>
```
