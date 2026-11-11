import {
    apiRequest,
    getToken,
    initHeader,
    showMessage,
} from "./common.js";

const videoId = new URLSearchParams(window.location.search).get("id");

const content = document.querySelector("#video-content");
const message = document.querySelector("#video-message");
const player = document.querySelector("#video-player");
const likeButton = document.querySelector("#like-button");
const likeMessage = document.querySelector("#like-message");
const subscribeButton = document.querySelector("#subscribe-button");

let ownerId = null;

function updateSubscribeButton(subscribed) {
    subscribeButton.textContent = subscribed
        ? "Отписаться"
        : "Подписаться";

    subscribeButton.classList.toggle("button-secondary", subscribed);
    subscribeButton.classList.toggle("button-primary", !subscribed);
}

async function loadSubscriptionStatus() {
    if (!getToken() || !ownerId) {
        subscribeButton.hidden = true;
        return;
    }

    try {
        const currentUser = await apiRequest("/users/me");

        if (currentUser.id === ownerId) {
            subscribeButton.hidden = true;
            return;
        }

        const result = await apiRequest(`/users/${ownerId}/subscription`);

        updateSubscribeButton(result.subscribed);
        subscribeButton.hidden = false;
    } catch {
        subscribeButton.hidden = true;
    }
}

async function loadVideo() {
    if (!videoId || !/^\d+$/.test(videoId)) {
        showMessage(message, "Некорректный ID видео.");
        return;
    }

    try {
        const video = await apiRequest(`/videos/${videoId}`);

        document.title = `${video.title} — YouTube Copy`;
        player.src = video.video_url;

        document.querySelector("#video-title").textContent = video.title;
        document.querySelector("#video-views").textContent =
            `${video.views_count} просмотров`;

        document.querySelector("#video-date").textContent =
            new Date(video.created_at).toLocaleDateString("ru-RU");

        document.querySelector("#video-description").textContent =
            video.description || "Описание отсутствует.";

        ownerId = video.owner.id;

        document.querySelector("#channel-email").textContent =
            video.owner.email;

        document.querySelector("#channel-link").href =
            `/channel.html?id=${encodeURIComponent(ownerId)}`;

        content.hidden = false;

        await loadSubscriptionStatus();
    } catch (error) {
        showMessage(message, error.message);
    }
}

likeButton.addEventListener("click", async () => {
    try {
        const result = await apiRequest(`/videos/${videoId}/like`, {
            method: "POST",
        });

        likeMessage.textContent = result.liked
            ? `Лайк поставлен · ${result.likes_count} лайков`
            : `Лайк убран · ${result.likes_count} лайков`;
    } catch (error) {
        likeMessage.textContent = error.message;
    }
});

subscribeButton.addEventListener("click", async () => {
    if (!ownerId || !getToken()) {
        return;
    }

    subscribeButton.disabled = true;

    try {
        const result = await apiRequest(`/users/${ownerId}/subscribe`, {
            method: "POST",
        });

        updateSubscribeButton(result.subscribed);
    } catch (error) {
        likeMessage.textContent = error.message;
    } finally {
        subscribeButton.disabled = false;
    }
});

await initHeader();
await loadVideo();