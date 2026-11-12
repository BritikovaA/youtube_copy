import {
    apiRequest,
    createVideoCard,
    hideMessage,
    initHeader,
    showMessage,
} from "./common.js";


const searchForm = document.querySelector("#search-form");
const searchInput = document.querySelector("#search-input");
const videosContainer = document.querySelector("#videos-list");
const message = document.querySelector("#videos-message");


async function loadVideos(search = "") {
    hideMessage(message);
    videosContainer.replaceChildren();

    try {
        const params = new URLSearchParams();

        if (search.trim()) {
            params.set("search", search.trim());
        }

        const query = params.toString();
        const path = query
            ? `/videos?${query}`
            : "/videos";

        const videos = await apiRequest(path);

        if (videos.length === 0) {
            showMessage(
                message,
                search.trim()
                    ? "По вашему запросу ничего не найдено."
                    : "Пока нет доступных видео.",
                "info",
            );
            return;
        }

        for (const video of videos) {
            videosContainer.append(createVideoCard(video));
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