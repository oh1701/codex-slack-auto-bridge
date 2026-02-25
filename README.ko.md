# Codex Slack Auto Bridge

Slack 메시지를 로컬 `codex` CLI로 전달하고, 결과를 Slack 스레드로 다시 보내는 경량 Socket Mode 브리지입니다.

Languages: [English](./README.md) | 한국어 | [日本語](./README.ja.md) | [中文](./README.zh-CN.md)

## 0) AI에게 설치 요청 시 문구

아래 문구를 AI 도구에 그대로 붙여 넣어 요청할 수 있습니다.

```text
Install this repository from https://github.com/oh1701/codex-slack-auto-bridge/tree/main and follow README exactly.
```

## 1) 준비물

- `codex` CLI 설치
- Python 3.11 이상
- Slack 앱 토큰:
  - App-Level token (`xapp-...`)
  - Bot token (`xoxb-...`)

## 2) Slack 앱 설정 (Socket Mode)

1. 앱 생성
   - `https://api.slack.com/apps` 접속
   - `Create New App` -> `From scratch`
   - 앱 이름/워크스페이스 선택

2. Socket Mode 활성화 + App-Level token 생성
   - `Socket Mode` 메뉴 활성화
   - Scope `connections:write`로 토큰 생성
   - `xapp-...`를 `slack.app_token`에 입력

3. `OAuth & Permissions`에서 Bot Token Scope 추가
   - 필수:
     - `app_mentions:read`
     - `chat:write`
   - 권장:
     - `channels:history`
     - `groups:history`
     - `im:history`
     - `mpim:history`

4. 워크스페이스 설치
   - `Install to Workspace` 클릭
   - `xoxb-...`를 `slack.bot_token`에 입력

5. Event Subscriptions 설정
   - `Event Subscriptions` 활성화
   - Socket Mode에서는 Request URL 불필요
   - Bot events 추가:
     - 최소: `app_mention`
     - 권장: `message.channels`, `message.groups`, `message.im`, `message.mpim`
   - 필요 시 재설치

환경변수 방식(선택):

```bash
export SLACK_APP_TOKEN="xapp-..."
export SLACK_BOT_TOKEN="xoxb-..."
```

## 3) 설치

저장소 루트에서 실행:

```bash
chmod +x scripts/*.sh
./scripts/install.sh
```

실행 내용:
- `slack-bridge-runtime/.venv` 생성
- Python 의존성 설치

## 4) 설정 로딩 순서

브리지는 다음 순서로 설정을 읽습니다.

1. `./config.toml` (로컬 프로젝트 설정, 최우선)
2. `~/.codex/config.toml` (Codex 전역 fallback)
3. 환경변수 (선택 fallback)

## 5) `config.toml` 설정

`~/.codex/config.toml`에 값을 넣어 사용하세요.

`./config.toml`을 별도로 두면 `~/.codex/config.toml`보다 우선 적용됩니다.

`~/.codex/config.toml` 예시:

```toml
[slack]
app_token = "xapp-..."
bot_token = "xoxb-..."
channel_id = "C0123456789" # 선택

[slack_bridge]
codex_cd = "/absolute/path/to/your/project" # 선택 (기본: 브리지 저장소 경로)
codex_timeout_sec = 300
history_turns = 6
mention_only = false
allowed_channels = []
```

### 채널 설정

- `slack.channel_id`: 기본 단일 채널 필터
- `slack_bridge.allowed_channels`: 명시적 허용 채널 목록
- `allowed_channels`가 비어 있고 `channel_id`가 설정되어 있으면 `channel_id`를 사용
- 둘 다 비어 있으면 모든 채널 허용
- DM은 항상 허용

채널 ID 형식:
- 공개 채널: `C...`
- 비공개 채널: `G...`
- DM: `D...`

채널 ID 확인 방법:
- Slack에서 채널을 열고 링크를 복사
- 예: `https://app.slack.com/client/T.../C0123456789`
- `C0123456789` 값을 사용

### 브리지 동작 설정

- `codex_timeout_sec`:
  - 1회 `codex exec` 응답을 기다리는 최대 시간(초)
  - 시간을 초과하면 타임아웃 오류 메시지를 반환
- `history_turns`:
  - 스레드별 프롬프트에 포함할 이전 대화 턴 수
  - 값이 클수록 문맥 유지가 좋아지지만 토큰 사용량이 증가
- `mention_only`:
  - `true`: 채널에서 봇 멘션이 있는 메시지만 처리
  - `false`: 채널 일반 메시지도 처리
  - DM에서는 이 값과 무관하게 메시지를 처리

## 5) `codex` / `codex resume` 자동 기동

쉘 훅 설치:

```bash
./scripts/install-shell-hook.sh
source ~/.zshrc   # bash: source ~/.bashrc
```

`codex` 또는 `codex resume` 실행 시 브리지가 백그라운드에서 자동 기동되고 유지됩니다.

## 6) 최종 실행 명령

쉘 훅 설치(`./scripts/install-shell-hook.sh` + `source ~/.zshrc` 또는 `~/.bashrc`) 후:

```bash
codex
codex resume
codex resume <session_id>
```
