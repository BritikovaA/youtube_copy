import {
    apiRequest,
    formatDate,
    getToken,
    initHeader,
    showMessage,
} from "./common.js";


const videoId = new URLSearchParams(window.location.search).get("id");

const content = document.querySelector("#video-content");
const pageMessage = document.querySelector("#video-page-message");

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

const commentForm = document.querySelector("#comment-form");
const commentInput = document.querySelector("#comment-input");
const commentSubmit = document.querySelector("#comment-submit");
const commentsList = document.querySelector("#comments-list");
const commentsCount = document.querySelector("#comments-count");
const commentsMessage = document.querySelector("#comments-message");
const commentsAuthMessage = document.querySelector(
    "#comments-auth-message",
);

let currentVideo = null;


function renderLikeStatus(data) {
    likeButton.classList.toggle("button-liked", data.liked);
    likeButton.textContent = data.liked
        ? "Нравится ✓"
        : "Нравится";

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


function createCommentElement(comment) {
    const article = document.createElement("article");
    article.className = "comment-item";

    const header = document.createElement("div");
    header.className = "comment-header";

    const author = document.createElement("a");
    author.className = "comment-author";
    author.href = `/channel.html?id=${encodeURIComponent(comment.author.id)}`;
    author.textContent = comment.author.email;

    const createdAt = document.createElement("time");
    createdAt.className = "comment-date";
    createdAt.dateTime = comment.created_at;
    createdAt.textContent = formatDate(comment.created_at);

    const text = document.createElement("p");
    text.className = "comment-text";
    text.textContent = comment.text;

    header.append(author, createdAt);
    article.append(header, text);

    return article;
}


function renderComments(comments) {
    commentsList.replaceChildren();

    for (const comment of comments) {
        commentsList.append(createCommentElement(comment));
    }

    commentsCount.textContent = String(comments.length);

    if (comments.length === 0) {
        const emptyMessage = document.createElement("p");
        emptyMessage.className = "comments-empty";
        emptyMessage.textContent = "Комментариев пока нет.";

        commentsList.append(emptyMessage);
    }
}


async function loadComments() {
    const comments = await apiRequest(
        `/videos/${encodeURIComponent(videoId)}/comments`,
    );

    renderComments(comments);
}


function initCommentForm() {
    if (getToken()) {
        commentForm.hidden = false;
        commentsAuthMessage.hidden = true;
    } else {
        commentForm.hidden = true;
        commentsAuthMessage.hidden = false;
    }
}


async function submitComment(event) {
    event.preventDefault();

    const text = commentInput.value.trim();

    if (!text) {
        showMessage(
            commentsMessage,
            "Введите текст комментария.",
        );
        return;
    }

    commentSubmit.disabled = true;

    try {
        const comment = await apiRequest(
            `/videos/${encodeURIComponent(videoId)}/comments`,
            {
                method: "POST",
                body: JSON.stringify({ text }),
            },
        );

        const emptyMessage = commentsList.querySelector(".comments-empty");

        if (emptyMessage) {
            emptyMessage.remove();
        }

        commentsList.prepend(createCommentElement(comment));

        const currentCount = Number(commentsCount.textContent);
        commentsCount.textContent = String(currentCount + 1);

        commentInput.value = "";
        commentsMessage.hidden = true;
    } catch (error) {
        showMessage(commentsMessage, error.message);
    } finally {
        commentSubmit.disabled = false;
    }
}


async function loadVideo() {
    if (!videoId || !/^\d+$/.test(videoId)) {
        showMessage(pageMessage, "Некорректный ID видео.");
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

        initCommentForm();

        await Promise.all([
            loadLikeStatus(),
            loadSubscription(),
            loadComments(),
        ]);

        content.hidden = false;
    } catch (error) {
        showMessage(pageMessage, error.message);
    }
}


likeButton.addEventListener("click", toggleLike);
subscribeButton.addEventListener("click", toggleSubscription);
commentForm.addEventListener("submit", submitComment);

await initHeader();
await loadVideo();