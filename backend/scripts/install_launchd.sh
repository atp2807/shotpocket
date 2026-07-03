#!/usr/bin/env bash
# ShotPocket 야간 배치 LaunchAgent 설치 (맥 전용).
#
#   deploy/me.sitos.shotpocket.nightly.plist → ~/Library/LaunchAgents/ 로 복사 후
#   launchctl 로 부트스트랩(재설치 시 기존 것을 언로드하고 다시 로드).
#
# 사용:  bash scripts/install_launchd.sh
# 제거:  bash scripts/install_launchd.sh uninstall
set -euo pipefail

LABEL="me.sitos.shotpocket.nightly"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_PLIST="${SCRIPT_DIR}/../deploy/${LABEL}.plist"
DEST_DIR="${HOME}/Library/LaunchAgents"
DEST_PLIST="${DEST_DIR}/${LABEL}.plist"
DOMAIN="gui/$(id -u)"

mkdir -p "${HOME}/Library/Logs"

# 언로드(있으면). bootout 이 없는 구버전 대비 legacy unload 도 시도.
unload() {
    launchctl bootout "${DOMAIN}/${LABEL}" 2>/dev/null || \
        launchctl unload "${DEST_PLIST}" 2>/dev/null || true
}

if [[ "${1:-}" == "uninstall" ]]; then
    unload
    rm -f "${DEST_PLIST}"
    echo "제거 완료: ${LABEL}"
    exit 0
fi

# plist 유효성 검사 후 설치
plutil -lint "${SRC_PLIST}"
mkdir -p "${DEST_DIR}"
cp "${SRC_PLIST}" "${DEST_PLIST}"

unload  # 재설치 대비 기존 것 정리
if ! launchctl bootstrap "${DOMAIN}" "${DEST_PLIST}" 2>/dev/null; then
    # 구버전 macOS 폴백
    launchctl load "${DEST_PLIST}"
fi

echo "설치 완료: ${LABEL} (매일 03:30, 로그 ~/Library/Logs/shotpocket-nightly.log)"
launchctl print "${DOMAIN}/${LABEL}" 2>/dev/null | grep -E "state|program" || true
