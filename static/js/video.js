import {
    apiRequest,
    formatDate,
    getToken,
    initHeader,
    showMessage,
} from "./common.js";


const videoId = new URLSearchParams(window.location.search).get("id");

const content = document.querySelector("#video-content");
const player = document.querySelector("#video-player");
const title = document.querySelector("#video-title");
const views = document.querySelector("#video-views");
const date = document.querySelector("#video-date");
const likeButton = document.querySelector("#like-button");
const likeMessage = document.querySelector("#like-message");
const likeCount = document.querySelector("#like-count");
const channelEmail = document.querySelector("#channel-email");
const channelLink = document.querySelector("#channel-link");
const subscribeButton = document.querySelector("#subscribe-button");
const description = document.querySelector("#video-description");

let currentVideo = null;


function renderLikeStatus(data) {
    likeButton.classList.toggle("button-liked", data.liked);
    likeButton.textContent = data.liked ? "Нравится ✓" : "Нравится";
    likeCount.textContent = `${data.likes_count} лайков`;
}


async function loadLikeStatus() {
    const data = await apiRequest(
        `/videos/${encodeURIComponent(videoId)}/like`,
    );

    renderLikeStatus(data);
}


async function toggleLike() {
    if (!getToken()) {
        window.location.href = "/auth.html?mode=login";
        return;
    }

    likeButton.disabled = true;

    try {
        const data = await apiRequest(
            `/videos/${encodeURIComponent(videoId)}/like`,
            {
                method: "POST",
            },
        );

        renderLikeStatus(data);
        likeMessage.hidden = true;
    } catch (error) {
        showMessage(likeMessage, error.message);
    } finally {
        likeButton.disabled = false;
    }
}


async function loadSubscription() {
    if (!getToken()) {
        subscribeButton.hidden = true;
        return;
    }

    const user = await apiRequest("/users/me");

    if (user.id === currentVideo.owner.id) {
        subscribeButton.hidden = true;
        return;
    }

    const data = await apiRequest(
        `/users/${encodeURIComponent(currentVideo.owner.id)}/subscription`,
    );

    subscribeButton.hidden = false;
    subscribeButton.textContent = data.subscribed
        ? "Отписаться"
        : "Подписаться";
}


async function toggleSubscription() {
    if (!currentVideo) {
        return;
    }

    subscribeButton.disabled = true;

    try {
        const data = await apiRequest(
            `/users/${encodeURIComponent(currentVideo.owner.id)}/subscribe`,
            {
                method: "POST",
            },
        );

        subscribeButton.textContent = data.subscribed
            ? "Отписаться"
            : "Подписаться";
    } catch (error) {
        showMessage(likeMessage, error.message);
    } finally {
        subscribeButton.disabled = false;
    }
}


async function loadVideo() {
    if (!videoId || !/^\d+$/.test(videoId)) {
        showMessage(likeMessage, "Некорректный ID видео.");
        return;
    }

    try {
        currentVideo = await apiRequest(
            `/videos/${encodeURIComponent(videoId)}`,
        );

        player.src = currentVideo.video_url;
        title.textContent = currentVideo.title;
        views.textContent = `${currentVideo.views_count} просмотров`;
        date.textContent = formatDate(currentVideo.created_at);

        channelEmail.textContent = currentVideo.owner.email;
        channelLink.href =
            `/channel.html?id=${encodeURIComponent(currentVideo.owner.id)}`;

        description.textContent =
            currentVideo.description || "Описание отсутствует.";

        likeCount.textContent = `${currentVideo.likes_count} лайков`;

        await loadLikeStatus();
        await loadSubscription();

        content.hidden = false;
    } catch (error) {
        showMessage(likeMessage, error.message);
    }
}


likeButton.addEventListener("click", toggleLike);
subscribeButton.addEventListener("click", toggleSubscription);

await initHeader();
await loadVideo();