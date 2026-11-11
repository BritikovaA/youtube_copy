import {
    apiRequest,
    setToken,
    showMessage,
    hideMessage,
} from "./common.js";

const form = document.querySelector("#auth-form");
const title = document.querySelector("#auth-title");
const submitButton = document.querySelector("#auth-submit");
const message = document.querySelector("#auth-message");
const loginTab = document.querySelector("#login-tab");
const registerTab = document.querySelector("#register-tab");
const passwordInput = document.querySelector("#password");

let mode = "login";

function setMode(nextMode) {
    mode = nextMode;

    const isLogin = mode === "login";

    title.textContent = isLogin ? "Вход в аккаунт" : "Регистрация";
    submitButton.textContent = isLogin ? "Войти" : "Зарегистрироваться";
    passwordInput.autocomplete = isLogin ? "current-password" : "new-password";

    loginTab.classList.toggle("active", isLogin);
    registerTab.classList.toggle("active", !isLogin);

    hideMessage(message);
}

loginTab.addEventListener("click", () => setMode("login"));
registerTab.addEventListener("click", () => setMode("register"));

form.addEventListener("submit", async (event) => {
    event.preventDefault();
    hideMessage(message);

    const email = document.querySelector("#email").value.trim();
    const password = passwordInput.value;

    submitButton.disabled = true;

    try {
        if (mode === "register") {
            await apiRequest("/auth/register", {
                method: "POST",
                body: JSON.stringify({ email, password }),
            });
        }

        const tokenResponse = await apiRequest("/auth/login", {
            method: "POST",
            body: JSON.stringify({ email, password }),
        });

        setToken(tokenResponse.access_token);
        window.location.href = "/";
    } catch (error) {
        showMessage(message, error.message);
    } finally {
        submitButton.disabled = false;
    }
});

const initialMode = new URLSearchParams(window.location.search).get("mode");

setMode(initialMode === "register" ? "register" : "login");