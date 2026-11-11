import {
    apiRequest,
    getToken,
    initHeader,
    showMessage,
} from "./common.js";

const userId = new URLSearchParams(window.location.search).get("id");

const videosContainer = document.querySelector("#channel-videos");
const message = document.querySelector("#channel-message");
const channelTitle = document.querySelector("#channel-title");
const channelDescription = document.querySelector("#channel-description");
const avatar = document.querySelector("#channel-avatar");
const subscribeButton = document.querySelector("#subscribe-button");
const subscribersElement = document.querySelector("#channel-subscribers");

let currentUserId = null;
let isSubscribed = false;

function updateSubscribeButton(subscribed) {
    isSubscribed = subscribed;

    subscribeButton.textContent = subscribed
        ? "Отписаться"
        : "Подписаться";

    subscribeButton.classList.toggle("button-secondary", subscribed);
    subscribeButton.classList.toggle("button-primary", !subscribed);
}

function updateSubscribersCount(count) {
    subscribersElement.textContent = `Подписчики: ${count}`;
}

async function loadSubscriptionStatus() {
    if (!getToken() || !currentUserId || currentUserId === Number(userId)) {
        subscribeButton.hidden = true;
        return;
    }

    try {
        const result = await apiRequest(`/users/${userId}/subscription`);

        updateSubscribeButton(result.subscribed);
        updateSubscribersCount(result.subscribers_count);
        subscribeButton.hidden = false;
    } catch {
        subscribeButton.hidden = true;
    }
}

async function loadChannel() {
    if (!userId || !/^\d+$/.test(userId)) {
        showMessage(message, "Некорректный ID канала.");
        return;
    }

    try {
        const videos = await apiRequest(`/users/${userId}/videos`);

        if (getToken()) {
            try {
                const currentUser = await apiRequest("/users/me");
                currentUserId = currentUser.id;
            } catch {
                currentUserId = null;
            }
        }

        channelTitle.textContent = `Канал #${userId}`;
        channelDescription.textContent = videos.length > 0
            ? `Видео пользователя #${userId}`
            : "Публичных видео пока нет.";

        avatar.textContent = "U";

        if (videos.length > 0) {
            const email = videos[0].owner.email;

            channelTitle.textContent = email;
            avatar.textContent = email.charAt(0).toUpperCase();
        }

        await loadSubscriptionStatus();

        if (videos.length === 0) {
            showMessage(
                message,
                "На этом канале пока нет публичных видео.",
                "info",
            );
            return;
        }

        for (const video of videos) {
            const article = document.createElement("article");
            article.className = "video-card";

            const previewLink = document.createElement("a");
            previewLink.className = "video-preview";
            previewLink.href = `/video.html?id=${encodeURIComponent(video.id)}`;
            previewLink.textContent = "▶";

            const content = document.createElement("div");
            content.className = "video-card-content";

            const title = document.createElement("a");
            title.className = "video-card-title";
            title.href = previewLink.href;
            title.textContent = video.title;

            const meta = document.createElement("p");
            meta.className = "video-card-meta";
            meta.textContent = `${video.views_count} просмотров`;

            content.append(title, meta);
            article.append(previewLink, content);
            videosContainer.append(article);
        }
    } catch (error) {
        showMessage(message, error.message);
    }
}

subscribeButton.addEventListener("click", async () => {
    if (!userId || !getToken()) {
        return;
    }

    subscribeButton.disabled = true;

    try {
        const result = await apiRequest(`/users/${userId}/subscribe`, {
            method: "POST",
        });

        updateSubscribeButton(result.subscribed);
        updateSubscribersCount(result.subscribers_count);
    } catch (error) {
        showMessage(message, error.message);
    } finally {
        subscribeButton.disabled = false;
    }
});

await initHeader();
await loadChannel();