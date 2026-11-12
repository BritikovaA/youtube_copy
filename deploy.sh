#!/usr/bin/env bash
set -Eeuo pipefail

readonly SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly ENV_EXAMPLE="${SCRIPT_DIR}/.env.example"
readonly ENV_FILE="${SCRIPT_DIR}/.env"

log() {
    printf '\n[deploy] %s\n' "$*"
}

fail() {
    printf '\n[deploy] ERROR: %s\n' "$*" >&2
    exit 1
}

require_ubuntu() {
    if [[ ! -r /etc/os-release ]]; then
        fail "Не удалось определить операционную систему. Скрипт предназначен для Ubuntu."
    fi

    # shellcheck disable=SC1091
    source /etc/os-release

    if [[ "${ID:-}" != "ubuntu" ]]; then
        fail "Поддерживается Ubuntu. Обнаружена система: ${PRETTY_NAME:-unknown}."
    fi
}

configure_privileges() {
    if [[ "${EUID}" -eq 0 ]]; then
        SUDO=()
        return
    fi

    if ! command -v sudo >/dev/null 2>&1; then
        fail "Для установки Docker нужны права root. Установите sudo или запустите скрипт от root."
    fi

    SUDO=(sudo)
}

install_docker() {
    log "Проверка Docker Engine и Docker Compose"

    if ! command -v docker >/dev/null 2>&1; then
        log "Docker не найден. Установка Docker Engine из официального репозитория."

        "${SUDO[@]}" apt-get update
        "${SUDO[@]}" apt-get install -y ca-certificates curl

        "${SUDO[@]}" install -m 0755 -d /etc/apt/keyrings
        "${SUDO[@]}" curl -fsSL \
            https://download.docker.com/linux/ubuntu/gpg \
            -o /etc/apt/keyrings/docker.asc
        "${SUDO[@]}" chmod a+r /etc/apt/keyrings/docker.asc

        local ubuntu_codename
        # shellcheck disable=SC1091
        source /etc/os-release
        ubuntu_codename="${UBUNTU_CODENAME:-${VERSION_CODENAME:-}}"

        [[ -n "${ubuntu_codename}" ]] || fail "Не удалось определить кодовое имя Ubuntu."

        printf '%s\n' \
            "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${ubuntu_codename} stable" \
            | "${SUDO[@]}" tee /etc/apt/sources.list.d/docker.list >/dev/null

        "${SUDO[@]}" apt-get update
        "${SUDO[@]}" apt-get install -y \
            docker-ce \
            docker-ce-cli \
            containerd.io \
            docker-buildx-plugin \
            docker-compose-plugin
    fi

    if ! docker compose version >/dev/null 2>&1; then
        log "Docker Compose Plugin не найден. Установка."
        "${SUDO[@]}" apt-get update
        "${SUDO[@]}" apt-get install -y docker-compose-plugin
    fi

    if ! command -v docker >/dev/null 2>&1; then
        fail "Docker Engine не удалось установить."
    fi

    if ! docker compose version >/dev/null 2>&1; then
        fail "Docker Compose Plugin не удалось установить."
    fi

    if ! "${SUDO[@]}" systemctl is-active --quiet docker; then
        log "Запуск Docker daemon"
        "${SUDO[@]}" systemctl enable --now docker
    fi

    log "Docker Engine и Docker Compose готовы к работе."
}

prepare_environment() {
    if [[ -f "${ENV_FILE}" ]]; then
        log "Файл .env уже существует. Существующие настройки сохранены."
        return
    fi

    [[ -f "${ENV_EXAMPLE}" ]] || fail "Не найден ${ENV_EXAMPLE}. Добавьте .env.example в корень проекта."

    cp "${ENV_EXAMPLE}" "${ENV_FILE}"
    log "Файл .env создан на основе .env.example."
    printf '[deploy] Проверьте значения секретов и параметров в %s перед использованием проекта.\n' "${ENV_FILE}"
}

deploy_project() {
    log "Запуск проекта"
    cd "${SCRIPT_DIR}"

    # Для непривилегированного пользователя используем sudo, чтобы не требовать
    # повторного входа в систему после добавления в группу docker.
    "${SUDO[@]}" docker compose up --build -d

    log "Команда запуска завершена."
    "${SUDO[@]}" docker compose ps
}

main() {
    require_ubuntu
    configure_privileges
    install_docker
    prepare_environment
    deploy_project
}

main "$@"
