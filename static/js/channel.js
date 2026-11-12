import {
    apiRequest,
    createVideoCard,
    getToken,
    initHeader,
    showMessage,
} from "./common.js";


const userId = new URLSearchParams(window.location.search).get("id");

const videosContainer = document.querySelector("#channel-videos");
const message = document.querySelector("#channel-message");
const channelTitle = document.querySelector("#channel-title");
const channelDescription = document.querySelector("#channel-description");
const channelSubscribers = document.querySelector("#channel-subscribers");
const avatar = document.querySelector("#channel-avatar");
const subscribeButton = document.querySelector("#subscribe-button");

let currentUser = null;
let isOwnChannel = false;


function renderVideos(videos) {
    videosContainer.replaceChildren();

    for (const video of videos) {
        videosContainer.append(createVideoCard(video));
    }
}


function renderSubscription(data) {
    subscribeButton.textContent = data.subscribed
        ? "Отписаться"
        : "Подписаться";

    channelSubscribers.textContent =
        `${data.subscribers_count} подписчиков`;
}


async function loadSubscription() {
    if (!getToken() || isOwnChannel) {
        subscribeButton.hidden = true;
        return;
    }

    const data = await apiRequest(
        `/users/${encodeURIComponent(userId)}/subscription`,
    );

    subscribeButton.hidden = false;
    renderSubscription(data);
}


async function toggleSubscription() {
    subscribeButton.disabled = true;

    try {
        const data = await apiRequest(
            `/users/${encodeURIComponent(userId)}/subscribe`,
            {
                method: "POST",
            },
        );

        renderSubscription(data);
    } catch (error) {
        showMessage(message, error.message);
    } finally {
        subscribeButton.disabled = false;
    }
}


async function loadChannel() {
    if (!userId || !/^\d+$/.test(userId)) {
        showMessage(message, "Некорректный ID канала.");
        return;
    }

    try {
        const profile = await apiRequest(
            `/users/${encodeURIComponent(userId)}`,
        );

        channelTitle.textContent = profile.email;
        channelDescription.textContent = "Канал пользователя";
        avatar.textContent = profile.email.charAt(0).toUpperCase();

        if (getToken()) {
            try {
                currentUser = await apiRequest("/users/me");
            } catch {
                currentUser = null;
            }
        }

        isOwnChannel = currentUser?.id === profile.id;

        const videos = isOwnChannel
            ? await apiRequest("/users/me/videos")
            : await apiRequest(
                `/users/${encodeURIComponent(userId)}/videos`,
            );

        renderVideos(videos);

        if (videos.length === 0) {
            showMessage(
                message,
                isOwnChannel
                    ? "У вас пока нет видео."
                    : "На этом канале пока нет публичных видео.",
                "info",
            );
        }

        await loadSubscription();
    } catch (error) {
        showMessage(message, error.message);
    }
}


subscribeButton.addEventListener("click", toggleSubscription);

await initHeader();
await loadChannel();