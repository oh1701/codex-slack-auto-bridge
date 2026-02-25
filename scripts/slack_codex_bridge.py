#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import threading
import time
import tomllib
from collections import deque
from dataclasses import dataclass
from typing import Any

try:
    from slack_sdk.socket_mode import SocketModeClient
    from slack_sdk.socket_mode.request import SocketModeRequest
    from slack_sdk.socket_mode.response import SocketModeResponse
    from slack_sdk.web import WebClient
except ImportError as exc:  # pragma: no cover - runtime dependency check
    sys.stderr.write(
        "slack_sdk가 필요합니다. "
        "예: ./slack-bridge-runtime/bootstrap.sh\n"
    )
    raise SystemExit(2) from exc


SCRIPT_PATH = pathlib.Path(__file__).resolve()
CODEX_ROOT = SCRIPT_PATH.parent.parent
DEFAULT_CONFIG_PATH = CODEX_ROOT / "config.toml"
GLOBAL_CODEX_CONFIG_PATH = pathlib.Path.home() / ".codex" / "config.toml"
DEFAULT_STATE_PATH = CODEX_ROOT / "tmp" / "slack-bridge-state.json"
DEFAULT_CHANNEL_ID = ""
MAX_CODEX_CONCURRENCY = 2


@dataclass
class BridgeConfig:
    app_token: str
    bot_token: str
    channel_id: str
    codex_cd: str
    codex_timeout_sec: int
    history_turns: int
    mention_only: bool
    state_path: pathlib.Path
    codex_command: str
    model: str
    allowed_channels: tuple[str, ...]


def _clean_str(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    return ""


def _to_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    return default


def _to_int(value: Any, default: int) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        cleaned = value.strip()
        if re.fullmatch(r"-?\d+", cleaned):
            return int(cleaned)
    return default


def _read_toml_dict(path: pathlib.Path) -> dict[str, Any]:
    try:
        with path.open("rb") as f:
            data = tomllib.load(f)
    except FileNotFoundError:
        return {}
    except (tomllib.TOMLDecodeError, OSError) as exc:
        raise ValueError(f"{path} 로딩 실패: {exc}") from exc

    if isinstance(data, dict):
        return data
    return {}


def _merge_dicts(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = dict(base)
    for key, value in override.items():
        base_value = merged.get(key)
        if isinstance(base_value, dict) and isinstance(value, dict):
            merged[key] = _merge_dicts(base_value, value)
        else:
            merged[key] = value
    return merged


def load_config(config_path: pathlib.Path) -> BridgeConfig:
    global_data: dict[str, Any] = {}
    if config_path != GLOBAL_CODEX_CONFIG_PATH:
        global_data = _read_toml_dict(GLOBAL_CODEX_CONFIG_PATH)
    local_data = _read_toml_dict(config_path)
    data = _merge_dicts(global_data, local_data)

    slack = data.get("slack") if isinstance(data.get("slack"), dict) else {}
    bridge = data.get("slack_bridge") if isinstance(data.get("slack_bridge"), dict) else {}

    app_token = (
        _clean_str(slack.get("app_token"))
        or _clean_str(slack.get("socket_app_token"))
        or _clean_str(slack.get("socket_mode_app_token"))
        or _clean_str(os.environ.get("SLACK_APP_TOKEN"))
        or _clean_str(os.environ.get("SLACK_SOCKET_APP_TOKEN"))
        or _clean_str(os.environ.get("SLACK_SOCKET_MODE_APP_TOKEN"))
    )
    bot_token = (
        _clean_str(slack.get("bot_token"))
        or _clean_str(slack.get("api_token"))
        or _clean_str(os.environ.get("SLACK_BOT_TOKEN"))
        or _clean_str(os.environ.get("SLACK_API_TOKEN"))
    )
    channel_id = (
        _clean_str(slack.get("channel_id"))
        or _clean_str(slack.get("channel"))
        or _clean_str(os.environ.get("SLACK_CHANNEL_ID"))
        or _clean_str(os.environ.get("SLACK_CHANNEL"))
        or DEFAULT_CHANNEL_ID
    )

    codex_cd = (
        _clean_str(bridge.get("codex_cd"))
        or _clean_str(os.environ.get("CODEX_BRIDGE_CWD"))
        or str(CODEX_ROOT)
    )
    codex_timeout_sec = max(
        30,
        _to_int(
            bridge.get("codex_timeout_sec")
            if bridge.get("codex_timeout_sec") is not None
            else os.environ.get("CODEX_BRIDGE_TIMEOUT_SEC"),
            300,
        ),
    )
    history_turns = max(
        1,
        _to_int(
            bridge.get("history_turns")
            if bridge.get("history_turns") is not None
            else os.environ.get("CODEX_BRIDGE_HISTORY_TURNS"),
            6,
        ),
    )
    mention_only = _to_bool(
        bridge.get("mention_only")
        if bridge.get("mention_only") is not None
        else os.environ.get("CODEX_BRIDGE_MENTION_ONLY"),
        True,
    )
    model = _clean_str(bridge.get("model")) or _clean_str(os.environ.get("CODEX_BRIDGE_MODEL"))
    codex_command = (
        _clean_str(bridge.get("codex_command"))
        or _clean_str(os.environ.get("CODEX_BRIDGE_COMMAND"))
        or "codex"
    )

    allowed_channels_raw = bridge.get("allowed_channels")
    allowed_channels: list[str] = []
    if isinstance(allowed_channels_raw, list):
        for item in allowed_channels_raw:
            cleaned = _clean_str(item)
            if cleaned:
                allowed_channels.append(cleaned)
    if not allowed_channels and channel_id:
        allowed_channels.append(channel_id)

    state_path = DEFAULT_STATE_PATH
    state_path_raw = _clean_str(bridge.get("state_path")) or _clean_str(
        os.environ.get("CODEX_BRIDGE_STATE_PATH")
    )
    if state_path_raw:
        state_path = pathlib.Path(state_path_raw).expanduser().resolve()

    if not app_token:
        raise ValueError("slack.app_token 또는 SLACK_APP_TOKEN 이 필요합니다. (Socket Mode xapp-...)")
    if not bot_token:
        raise ValueError("slack.bot_token 또는 SLACK_BOT_TOKEN 이 필요합니다. (xoxb-...)")

    return BridgeConfig(
        app_token=app_token,
        bot_token=bot_token,
        channel_id=channel_id,
        codex_cd=codex_cd,
        codex_timeout_sec=codex_timeout_sec,
        history_turns=history_turns,
        mention_only=mention_only,
        state_path=state_path,
        codex_command=codex_command,
        model=model,
        allowed_channels=tuple(allowed_channels),
    )


class HistoryStore:
    def __init__(self, path: pathlib.Path, history_turns: int) -> None:
        self.path = path
        self.max_messages = max(2, history_turns * 2)
        self._lock = threading.Lock()
        self._data: dict[str, list[dict[str, str]]] = {}
        self._load()

    def _load(self) -> None:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            self._data = {}
            return
        if not isinstance(raw, dict):
            self._data = {}
            return
        parsed: dict[str, list[dict[str, str]]] = {}
        for key, value in raw.items():
            if not isinstance(key, str) or not isinstance(value, list):
                continue
            rows: list[dict[str, str]] = []
            for item in value:
                if not isinstance(item, dict):
                    continue
                role = _clean_str(item.get("role"))
                text = _clean_str(item.get("text"))
                if role in {"user", "assistant"} and text:
                    rows.append({"role": role, "text": text})
            if rows:
                parsed[key] = rows[-self.max_messages :]
        self._data = parsed

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8")

    def append(self, key: str, role: str, text: str) -> None:
        cleaned = _clean_str(text)
        if not cleaned:
            return
        if role not in {"user", "assistant"}:
            return
        with self._lock:
            bucket = self._data.setdefault(key, [])
            bucket.append({"role": role, "text": cleaned})
            if len(bucket) > self.max_messages:
                self._data[key] = bucket[-self.max_messages :]
            self._save()

    def snapshot(self, key: str) -> list[dict[str, str]]:
        with self._lock:
            return list(self._data.get(key, []))


class SlackCodexBridge:
    def __init__(self, config: BridgeConfig) -> None:
        self.config = config
        self.history = HistoryStore(config.state_path, config.history_turns)
        self.web_client = WebClient(token=config.bot_token)
        auth = self.web_client.auth_test()
        self.bot_user_id = _clean_str(auth.get("user_id"))
        self.socket_client = SocketModeClient(
            app_token=config.app_token,
            web_client=self.web_client,
        )
        self.socket_client.socket_mode_request_listeners.append(self._on_socket_request)
        self._seen_event_ids: deque[str] = deque(maxlen=1024)
        self._seen_lock = threading.Lock()
        # Limit concurrent `codex exec` workers to prevent process storms.
        self._codex_sem = threading.BoundedSemaphore(MAX_CODEX_CONCURRENCY)

    def _is_duplicate_event(self, event_id: str) -> bool:
        if not event_id:
            return False
        with self._seen_lock:
            if event_id in self._seen_event_ids:
                return True
            self._seen_event_ids.append(event_id)
        return False

    def _on_socket_request(self, client: SocketModeClient, req: SocketModeRequest) -> None:
        if req.type != "events_api":
            return
        client.send_socket_mode_response(SocketModeResponse(envelope_id=req.envelope_id))
        payload = req.payload if isinstance(req.payload, dict) else {}
        event_id = _clean_str(payload.get("event_id"))
        if self._is_duplicate_event(event_id):
            return
        event = payload.get("event")
        if not isinstance(event, dict):
            return
        event_type = _clean_str(event.get("type"))
        if event_type not in {"message", "app_mention"}:
            return
        threading.Thread(target=self._process_message_event, args=(event,), daemon=True).start()

    def _should_handle_channel(self, channel: str, channel_type: str) -> bool:
        if not channel:
            return False
        # Always allow direct messages regardless of allowed_channels filter.
        if self._is_dm_channel(channel_type):
            return True
        if self.config.allowed_channels:
            return channel in self.config.allowed_channels
        return True

    def _is_dm_channel(self, channel_type: str) -> bool:
        return channel_type in {"im", "mpim"}

    def _normalize_user_text(self, raw_text: str, channel_type: str) -> str:
        text = raw_text.strip()
        if not text:
            return ""
        mention = f"<@{self.bot_user_id}>"
        if self.config.mention_only and not self._is_dm_channel(channel_type):
            if mention not in text:
            return ""
        text = text.replace(mention, " ").strip()
        return re.sub(r"\s+", " ", text)

    def _infer_language(self, text: str) -> str:
        if re.search(r"[\uac00-\ud7a3]", text):
            return "ko"
        if re.search(r"[\u3040-\u30ff]", text):
            return "ja"
        if re.search(r"[\u4e00-\u9fff]", text):
            return "zh"
        if re.search(r"[A-Za-z]", text):
            return "en"
        return "en"

    def _build_prompt(self, history_rows: list[dict[str, str]], user_text: str) -> str:
        lang = self._infer_language(user_text)

        prompt_meta = {
            "ko": {
                "intro": "너는 Slack에서 대화를 이어가는 Codex 어시스턴트다.",
                "lang": "아래 이전 맥락을 유지해서 한국어로 답해라.",
                "history_title": "[대화 맥락]",
                "role": {"user": "사용자", "assistant": "어시스턴트"},
                "req_title": "요구사항:",
                "req1": "1) 답변은 한국어로 작성",
                "req2": "2) 핵심만 간결하게 답변",
            },
            "en": {
                "intro": "You are a Codex assistant continuing a Slack conversation.",
                "lang": "Keep the previous context and reply in English.",
                "history_title": "[Conversation Context]",
                "role": {"user": "User", "assistant": "Assistant"},
                "req_title": "Requirements:",
                "req1": "1) Write the response in English.",
                "req2": "2) Keep it concise and focused.",
            },
            "ja": {
                "intro": "あなたはSlackの会話を引き継ぐCodexアシスタントです。",
                "lang": "これまでの文脈を維持し、日本語で回答してください。",
                "history_title": "[会話履歴]",
                "role": {"user": "ユーザー", "assistant": "アシスタント"},
                "req_title": "要件:",
                "req1": "1) 日本語で回答してください。",
                "req2": "2) 重要な点を簡潔に回答してください。",
            },
            "zh": {
                "intro": "你是一个在 Slack 中接续对话的 Codex 助手。",
                "lang": "请保留之前的上下文，并用中文回复。",
                "history_title": "[对话上下文]",
                "role": {"user": "用户", "assistant": "助手"},
                "req_title": "要求:",
                "req1": "1) 用中文回答。",
                "req2": "2) 简洁地回答核心内容。",
            },
        }
        meta = prompt_meta.get(lang, prompt_meta["en"])

        lines = [
            meta["intro"],
            meta["lang"],
            "",
            meta["history_title"],
        ]
        for row in history_rows[-self.history.max_messages :]:
            role = meta["role"].get(row["role"], row["role"])
            lines.append(f"{role}: {row['text']}")
        lines.extend(
            [
                f"{meta['role'].get('user', 'User')}: {user_text}",
                "",
                meta["req_title"],
                meta["req1"],
                meta["req2"],
            ]
        )
        return "\n".join(lines)

    def _run_codex(self, prompt: str) -> tuple[bool, str]:
        with tempfile.NamedTemporaryFile(prefix="slack-codex-last-", suffix=".txt", delete=False) as tmp:
            output_path = pathlib.Path(tmp.name)

        cmd = [
            self.config.codex_command,
            "exec",
            "--skip-git-repo-check",
            "-C",
            self.config.codex_cd,
            "--output-last-message",
            str(output_path),
        ]
        if self.config.model:
            cmd.extend(["-m", self.config.model])
        cmd.append(prompt)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.codex_timeout_sec,
            )
        except subprocess.TimeoutExpired:
            output_path.unlink(missing_ok=True)
            return False, "응답 생성이 시간 초과되었습니다. 잠시 후 다시 시도해 주세요."
        except OSError as exc:
            output_path.unlink(missing_ok=True)
            return False, f"Codex 실행 실패: {exc}"

        reply = ""
        try:
            reply = output_path.read_text(encoding="utf-8").strip()
        except OSError:
            reply = ""
        finally:
            output_path.unlink(missing_ok=True)

        if result.returncode != 0:
            stderr = (result.stderr or result.stdout or "").strip()
            if stderr:
                tail = stderr.splitlines()[-1]
                return False, f"Codex 실행 오류: {tail}"
            return False, f"Codex 실행 오류(returncode={result.returncode})"

        if not reply:
            return False, "응답이 비어 있습니다. 다시 시도해 주세요."
        return True, reply

    def _post_reply(self, channel: str, thread_ts: str, text: str) -> None:
        self.web_client.chat_postMessage(channel=channel, thread_ts=thread_ts, text=text[:3500])

    def _process_message_event(self, event: dict[str, Any]) -> None:
        if _clean_str(event.get("subtype")):
            return
        if _clean_str(event.get("bot_id")):
            return
        user = _clean_str(event.get("user"))
        if not user or user == self.bot_user_id:
            return

        channel_type = _clean_str(event.get("channel_type"))
        channel = _clean_str(event.get("channel"))
        if not self._should_handle_channel(channel, channel_type):
            return
        thread_ts = _clean_str(event.get("thread_ts")) or _clean_str(event.get("ts"))
        if not thread_ts:
            return

        raw_text = _clean_str(event.get("text"))
        user_text = self._normalize_user_text(raw_text, channel_type)
        if not user_text:
            return

        thread_key = f"{channel}:{thread_ts}"
        history_rows = self.history.snapshot(thread_key)
        prompt = self._build_prompt(history_rows, user_text)
        self.history.append(thread_key, "user", user_text)

        with self._codex_sem:
            ok, reply = self._run_codex(prompt)
        if not ok:
            reply = f"처리 중 오류가 발생했습니다.\n{reply}"

        try:
            self._post_reply(channel=channel, thread_ts=thread_ts, text=reply)
        except Exception as exc:  # pragma: no cover - Slack API runtime
            sys.stderr.write(f"[slack-bridge] chat_postMessage 실패: {exc}\n")
            return

        if ok:
            self.history.append(thread_key, "assistant", reply)

    def run(self) -> None:
        self.socket_client.connect()
        channels = ", ".join(self.config.allowed_channels) if self.config.allowed_channels else "all"
        print(
            "[slack-bridge] started: "
            "bot_user="
            f"{self.bot_user_id}, channels={channels}, mention_only={self.config.mention_only}, "
            f"max_concurrency={MAX_CODEX_CONCURRENCY}",
            flush=True,
        )
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[slack-bridge] interrupted, stopping...")
            self.socket_client.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Slack Socket Mode -> Codex bridge")
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="Primary config path (defaults to ./config.toml, fallback: ~/.codex/config.toml)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config_path = pathlib.Path(args.config).expanduser().resolve()
    try:
        config = load_config(config_path)
    except ValueError as exc:
        print(f"[slack-bridge][FAIL] {exc}")
        return 2

    print(
        "[slack-bridge] config: "
        f"path={config_path}, mention_only={config.mention_only}, "
        f"allowed_channels={list(config.allowed_channels)}",
        flush=True,
    )
    bridge = SlackCodexBridge(config)
    bridge.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
