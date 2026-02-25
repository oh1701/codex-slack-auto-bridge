# Codex Slack Auto Bridge

Slack メッセージをローカル `codex` CLI に渡し、返信を Slack スレッドに返す Socket Mode ブリッジです。

Languages: [English](./README.md) | [한국어](./README.ko.md) | 日本語 | [中文](./README.zh-CN.md)

## 0) AI へのインストール依頼文

以下をそのまま AI ツールに貼り付けて使えます。

```text
Install this repository from https://github.com/oh1701/codex-slack-auto-bridge/tree/main and follow README exactly.
```

## 1) 前提条件

- `codex` CLI がインストール済み
- Python 3.11 以上
- Slack アプリのトークン:
  - App-Level token (`xapp-...`)
  - Bot token (`xoxb-...`)

## 2) Slack アプリ設定（Socket Mode）

1. アプリ作成
   - `https://api.slack.com/apps`
   - `Create New App` -> `From scratch`
   - アプリ名とワークスペースを選択

2. Socket Mode 有効化 + App-Level token 作成
   - `Socket Mode` を開く
   - 有効化
   - Scope `connections:write` でトークン作成
   - `xapp-...` を `slack.app_token` に設定

3. `OAuth & Permissions` で Bot Token Scope 追加
   - 必須:
     - `app_mentions:read`
     - `chat:write`
   - 推奨:
     - `channels:history`
     - `groups:history`
     - `im:history`
     - `mpim:history`

4. ワークスペースにインストール
   - `Install to Workspace`
   - `xoxb-...` を `slack.bot_token` に設定

5. Event Subscriptions 設定
   - `Event Subscriptions` を有効化
   - Socket Mode では Request URL は不要
   - Bot events を追加:
     - 最小: `app_mention`
     - 推奨: `message.channels`, `message.groups`, `message.im`, `message.mpim`
   - 必要なら再インストール

任意の環境変数:

```bash
export SLACK_APP_TOKEN="xapp-..."
export SLACK_BOT_TOKEN="xoxb-..."
```

## 3) インストール

リポジトリのルートで実行:

```bash
chmod +x scripts/*.sh
./scripts/install.sh
```

実行内容:
- `slack-bridge-runtime/.venv` を作成
- Python 依存関係をインストール

## 4) 設定の読み込み順

ブリッジは次の順で設定を読み込みます:

1. `./config.toml`（ローカル、最優先）
2. `~/.codex/config.toml`（Codex グローバル設定）
3. 環境変数（任意のフォールバック）

## 5) `config.toml` 設定

`~/.codex/config.toml` に値を記載してください。

`./config.toml` が存在する場合は `~/.codex/config.toml` より優先されます。

`~/.codex/config.toml` の例:

```toml
[slack]
app_token = "xapp-..."
bot_token = "xoxb-..."
channel_id = "C0123456789" # 任意

[slack_bridge]
codex_cd = "/absolute/path/to/your/project" # 任意（既定: ブリッジのパス）
codex_timeout_sec = 300
history_turns = 6
mention_only = false
allowed_channels = []
```

### チャンネル設定

- `slack.channel_id`: デフォルトの単一チャンネルフィルタ
- `slack_bridge.allowed_channels`: 明示的な許可チャンネル一覧
- `allowed_channels` が空で `channel_id` が設定されている場合は `channel_id` を使用
- 両方空なら全チャンネル許可
- DM は常に許可

チャンネル ID 形式:
- 公開チャンネル: `C...`
- 非公開チャンネル: `G...`
- DM: `D...`

チャンネル ID の確認方法:
- Slack でチャンネルを開き、リンクをコピー
- 例: `https://app.slack.com/client/T.../C0123456789`
- `C0123456789` を使用

### ブリッジ動作設定

- `codex_timeout_sec`:
  - 1回の `codex exec` 応答を待つ最大秒数
  - タイムアウト時はエラーメッセージを返す
- `history_turns`:
  - スレッドごとのプロンプトに含める過去会話ターン数
  - 値が大きいほど文脈は増えるがトークン消費も増える
- `mention_only`:
  - `true`: チャンネルでは bot メンション付きメッセージのみ処理
  - `false`: チャンネルの通常メッセージも処理
  - DM はこの設定に関係なく処理

## 5) `codex` / `codex resume` で自動起動

シェルフックを設定:

```bash
./scripts/install-shell-hook.sh
source ~/.zshrc   # bash: source ~/.bashrc
```

`codex` または `codex resume` 実行時にブリッジがバックグラウンドで自動起動されます。

## 6) 最終実行コマンド

シェルフック設定後（`./scripts/install-shell-hook.sh` + `source ~/.zshrc` または `~/.bashrc`）:

```bash
codex
codex resume
codex resume <session_id>
```
