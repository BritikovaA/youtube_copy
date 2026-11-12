
import {
    apiRequest,
    formatDate,
    initHeader,
    requireAuth,
    showMessage,
    hideMessage,
} from "/js/common.js";

const moderationList = document.querySelector("#moderation-list");
const moderationMessage = document.querySelector("#moderation-message");
const moderationLoading = document.querySelector("#moderation-loading");
const moderationEmpty = document.querySelector("#moderation-empty");

async function loadModerationQueue() {
    moderationLoading.hidden = false;
    moderationEmpty.hidden = true;
    hideMessage(moderationMessage);

    try {
        const videos = await apiRequest("/videos/moderation");

        moderationList.replaceChildren();

        if (!Array.isArray(videos) || videos.length === 0) {
            moderationEmpty.hidden = false;
            return;
        }

        for (const video of videos) {
            moderationList.append(createModerationCard(video));
        }
    } catch (error) {
        showMessage(moderationMessage, error.message);
    } finally {
        moderationLoading.hidden = true;
    }
}

function createModerationCard(video) {
    const article = document.createElement("article");
    article.className = "moderation-card";

    const heading = document.createElement("div");
    heading.className = "moderation-card-header";

    const title = document.createElement("h2");
    title.className = "moderation-card-title";
    title.textContent = video.title;

    const status = document.createElement("span");
    status.className = "video-reported-badge";
    status.textContent = "На проверке";

    heading.append(title, status);

    const author = document.createElement("p");
    author.className = "moderation-card-author";

    const authorLink = document.createElement("a");
    authorLink.href = `/channel.html?id=${encodeURIComponent(video.owner.id)}`;
    authorLink.textContent = video.owner.email;

    author.append("Автор: ", authorLink);

    const description = document.createElement("p");
    description.className = "moderation-card-description";
    description.textContent = video.description || "Описание отсутствует";

    const meta = document.createElement("p");
    meta.className = "moderation-card-meta";
    meta.textContent =
        `${video.views_count} просмотров · ${formatDate(video.created_at)}`;

    const playerContainer = document.createElement("div");
    playerContainer.className = "moderation-player";

    if (video.video_url) {
        const player = document.createElement("video");
        player.className = "video-player";
        player.controls = true;
        player.preload = "metadata";
        player.src = video.video_url;

        playerContainer.append(player);
    } else {
        const unavailable = document.createElement("p");
        unavailable.className = "message message-error";
        unavailable.textContent =
            "Видео недоступно для просмотра. В ответе API отсутствует video_url.";

        playerContainer.append(unavailable);
    }

    const actions = document.createElement("div");
    actions.className = "moderation-card-actions";

    const restoreButton = document.createElement("button");
    restoreButton.className = "button button-primary";
    restoreButton.type = "button";
    restoreButton.textContent = "Восстановить видео";

    const hideButton = document.createElement("button");
    hideButton.className = "button button-secondary";
    hideButton.type = "button";
    hideButton.textContent = "Оставить скрытым";

    const actionMessage = document.createElement("p");
    actionMessage.className = "moderation-action-message";
    actionMessage.hidden = true;

    restoreButton.addEventListener("click", async () => {
        await moderateVideo(video.id, false, article, [
            restoreButton,
            hideButton,
        ], actionMessage);
    });

    hideButton.addEventListener("click", async () => {
        await moderateVideo(video.id, true, article, [
            restoreButton,
            hideButton,
        ], actionMessage);
    });

    actions.append(restoreButton, hideButton);

    article.append(
        heading,
        author,
        description,
        meta,
        playerContainer,
        actions,
        actionMessage,
    );

    return article;
}

async function moderateVideo(videoId, isHidden, article, buttons, message) {
    for (const button of buttons) {
        button.disabled = true;
    }

    message.hidden = true;

    try {
        await apiRequest(
            `/videos/${encodeURIComponent(videoId)}/moderation`,
            {
                method: "PATCH",
                body: JSON.stringify({
                    is_hidden: isHidden,
                }),
            },
        );

        article.remove();

        if (moderationList.children.length === 0) {
            moderationEmpty.hidden = false;
        }

        showMessage(
            moderationMessage,
            isHidden
                ? "Видео оставлено скрытым."
                : "Видео восстановлено и снова доступно пользователям.",
            "success",
        );
    } catch (error) {
        showMessage(message, error.message);
        for (const button of buttons) {
            button.disabled = false;
        }
    }
}

async function initModerationPage() {
    await initHeader();

    const user = await requireAuth();

    if (!user) {
        return;
    }

    if (user.role !== "moderator") {
        window.location.replace("/");
        return;
    }

    await loadModerationQueue();
}

initModerationPage();
