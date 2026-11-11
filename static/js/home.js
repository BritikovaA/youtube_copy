import {
    apiRequest,
    createVideoCard,
    initHeader,
    showMessage,
    hideMessage,
} from "./common.js";

const videosList = document.querySelector("#videos-list");
const searchForm = document.querySelector("#search-form");
const searchInput = document.querySelector("#search-input");
const message = document.querySelector("#videos-message");

async function loadVideos(search = "") {
    hideMessage(message);
    videosList.replaceChildren();

    const params = new URLSearchParams();

    if (search.trim()) {
        params.set("search", search.trim());
    }

    const query = params.toString();
    const path = query ? `/videos?${query}` : "/videos";

    try {
        const videos = await apiRequest(path);

        if (videos.length === 0) {
            showMessage(message, "Видео не найдены.", "info");
            return;
        }

        for (const video of videos) {
            videosList.append(createVideoCard(video));
        }
    } catch (error) {
        showMessage(message, error.message);
    }
}

searchForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    await loadVideos(searchInput.value);
});

await initHeader();
await loadVideos();