import {
    apiRequest,
    initHeader,
    requireAuth,
    showMessage,
} from "./common.js";

const message = document.querySelector("#subscriptions-message");
const subscriptionsList = document.querySelector("#subscriptions-list");

async function loadSubscriptions() {
    const currentUser = await requireAuth();

    if (!currentUser) {
        return;
    }

    try {
        const channels = await apiRequest("/users/subscriptions");

        if (channels.length === 0) {
            showMessage(
                message,
                "Вы пока ни на кого не подписаны.",
                "info",
            );
            return;
        }

        for (const channel of channels) {
            const article = document.createElement("article");
            article.className = "video-card";

            const content = document.createElement("div");
            content.className = "video-card-content";

            const title = document.createElement("a");
            title.className = "video-card-title";
            title.href =
                `/channel.html?id=${encodeURIComponent(channel.id)}`;
            title.textContent = channel.email;

            const meta = document.createElement("p");
            meta.className = "video-card-meta";
            meta.textContent = "Канал";

            content.append(title, meta);
            article.append(content);

            subscriptionsList.append(article);
        }
    } catch (error) {
        showMessage(message, error.message);
    }
}

await initHeader();
await loadSubscriptions();