import {
    apiRequest,
    initHeader,
    requireAuth,
    showMessage,
    hideMessage,
} from "./common.js";

const form = document.querySelector("#upload-form");
const submitButton = document.querySelector("#upload-submit");
const message = document.querySelector("#upload-message");

await initHeader();

const currentUser = await requireAuth();

if (currentUser) {
    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        hideMessage(message);

        const fileInput = document.querySelector("#file");
        const file = fileInput.files?.[0];

        if (!file) {
            showMessage(message, "Выберите видеофайл.");
            return;
        }

        const formData = new FormData();

        formData.append("title", document.querySelector("#title").value.trim());
        formData.append(
            "description",
            document.querySelector("#description").value,
        );
        formData.append(
            "is_private",
            String(document.querySelector("#is-private").checked),
        );
        formData.append("file", file);

        submitButton.disabled = true;
        submitButton.textContent = "Загрузка...";

        try {
            const result = await apiRequest("/videos/upload", {
                method: "POST",
                body: formData,
            });

            window.location.href = `/video.html?id=${result.video.id}`;
        } catch (error) {
            showMessage(message, error.message);
        } finally {
            submitButton.disabled = false;
            submitButton.textContent = "Загрузить";
        }
    });
}