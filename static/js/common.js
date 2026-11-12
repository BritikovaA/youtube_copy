
export const API_BASE = "";

export function getToken() {
    return localStorage.getItem("access_token");
}

export function setToken(token) {
    localStorage.setItem("access_token", token);
}

export function removeToken() {
    localStorage.removeItem("access_token");
}

export async function apiRequest(path, options = {}) {
    const headers = new Headers(options.headers || {});
    const token = getToken();

    if (token) {
        headers.set("Authorization", `Bearer ${token}`);
    }

    const isFormData = options.body instanceof FormData;

    if (options.body && !isFormData && !headers.has("Content-Type")) {
        headers.set("Content-Type", "application/json");
    }

    const response = await fetch(`${API_BASE}${path}`, {
        ...options,
        headers,
    });

    if (response.status === 204) {
        return null;
    }

    const contentType = response.headers.get("content-type") || "";

    const data = contentType.includes("application/json")
        ? await response.json()
        : await response.text();

    if (!response.ok) {
        if (response.status === 401) {
            removeToken();
        }

        const detail = typeof data === "object" && data !== null
            ? data.detail
            : data;

        throw new Error(detail || `Ошибка HTTP ${response.status}`);
    }

    return data;
}

export function showMessage(element, message, type = "error") {
    element.textContent = message;
    element.className = `message message-${type}`;
    element.hidden = false;
}

export function hideMessage(element) {
    element.hidden = true;
    element.textContent = "";
}

export function formatDate(value) {
    return new Intl.DateTimeFormat("ru-RU", {
        year: "numeric",
        month: "long",
        day: "numeric",
    }).format(new Date(value));
}

export async function submitVideoReport(videoId) {
    return apiRequest(
        `/videos/${encodeURIComponent(videoId)}/report`,
        {
            method: "POST",
        },
    );
}

export function createVideoCard(video) {
    const article = document.createElement("article");
    article.className = "video-card";

    const previewLink = document.createElement("a");
    previewLink.className = "video-preview";
    previewLink.href = `/video.html?id=${encodeURIComponent(video.id)}`;
    previewLink.textContent = "▶";
    previewLink.setAttribute("aria-label", `Открыть видео: ${video.title}`);

    const content = document.createElement("div");
    content.className = "video-card-content";

    const title = document.createElement("a");
    title.className = "video-card-title";
    title.href = previewLink.href;
    title.textContent = video.title;

    const author = document.createElement("a");
    author.className = "video-card-author";
    author.href = `/channel.html?id=${encodeURIComponent(video.owner.id)}`;
    author.textContent = video.owner.email;

    const meta = document.createElement("p");
    meta.className = "video-card-meta";
    meta.textContent =
        `${video.views_count} просмотров · ${formatDate(video.created_at)}`;

    content.append(title, author, meta);

    if (video.is_private) {
        const privacy = document.createElement("span");
        privacy.className = "video-privacy";
        privacy.textContent = "Приватное";
        content.append(privacy);
    }

    if (video.is_hidden) {
        const moderationBadge = document.createElement("span");
        moderationBadge.className = "video-moderation-badge";
        moderationBadge.textContent = "Нарушает правила";
        content.append(moderationBadge);
    } else if (video.is_reported) {
        const reportedBadge = document.createElement("span");
        reportedBadge.className = "video-reported-badge";
        reportedBadge.textContent = "На проверке";
        content.append(reportedBadge);
    }

    const actions = document.createElement("div");
    actions.className = "video-card-actions";

    const reportButton = document.createElement("button");
    reportButton.className = "button button-report";
    reportButton.type = "button";
    reportButton.textContent = "Пожаловаться";
    reportButton.hidden = video.is_hidden || video.is_reported;

    const reportMessage = document.createElement("span");
    reportMessage.className = "report-message";
    reportMessage.hidden = true;

    reportButton.addEventListener("click", async () => {
        reportButton.disabled = true;

        try {
            await submitVideoReport(video.id);

            reportButton.hidden = true;
            reportMessage.textContent = "Жалоба отправлена";
            reportMessage.className = "report-message report-message-success";
            reportMessage.hidden = false;
        } catch (error) {
            reportButton.disabled = false;
            reportMessage.textContent = error.message;
            reportMessage.className = "report-message report-message-error";
            reportMessage.hidden = false;
        }
    });

    actions.append(reportButton, reportMessage);
    content.append(actions);

    article.append(previewLink, content);

    return article;
}

export async function initHeader() {
    const actions = document.querySelector("#auth-actions");
    const uploadLink = document.querySelector("#upload-link");

    if (!actions) {
        return;
    }

    const token = getToken();

    if (!token) {
        actions.hidden = false;
        return;
    }

    try {
        const user = await apiRequest("/users/me");

        actions.replaceChildren();
        actions.hidden = false;

        const channelLink = document.createElement("a");
        channelLink.className = "button button-secondary";
        channelLink.href = `/channel.html?id=${encodeURIComponent(user.id)}`;
        channelLink.textContent = "Мой канал";

        const subscriptionsLink = document.createElement("a");
        subscriptionsLink.className = "button button-secondary";
        subscriptionsLink.href = "/subscriptions.html";
        subscriptionsLink.textContent = "Подписки";

        const logoutButton = document.createElement("button");
        logoutButton.className = "button button-secondary";
        logoutButton.type = "button";
        logoutButton.textContent = "Выйти";

        logoutButton.addEventListener("click", () => {
            removeToken();
            window.location.href = "/";
        });

        actions.append(
            channelLink,
            subscriptionsLink,
        );

        if (user.role === "moderator") {
            const moderationLink = document.createElement("a");
            moderationLink.className = "button button-secondary";
            moderationLink.href = "/moderation.html";
            moderationLink.textContent = "Модерация видео";

            actions.append(moderationLink);
        }

        actions.append(logoutButton);

        if (uploadLink) {
            uploadLink.hidden = false;
        }
    } catch {
        removeToken();
        actions.hidden = false;

        if (uploadLink) {
            uploadLink.hidden = true;
        }
    }
}

export async function requireAuth() {
    if (!getToken()) {
        window.location.href = "/auth.html?mode=login";
        return null;
    }

    try {
        return await apiRequest("/users/me");
    } catch {
        removeToken();
        window.location.href = "/auth.html?mode=login";
        return null;
    }
}
