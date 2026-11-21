// =====================================
// FRESH FIRST - BACKEND SESSION LOGIN
// =====================================

document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("loginForm");
    const usernameInput = document.getElementById("username");
    const passwordInput = document.getElementById("password");
    const message = document.getElementById("errorMessage");
    const submitButton = form?.querySelector('button[type="submit"]');

    if (!form || !usernameInput || !passwordInput || !message) return;

    function showMessage(text, isError = true) {
        message.textContent = text;
        message.style.display = text ? "block" : "none";
        message.style.color = isError ? "#b91c1c" : "#166534";
        message.style.background = isError ? "#fee2e2" : "#dcfce7";
    }

    // If a valid Flask session already exists, go directly to dashboard.
    (async () => {
        try {
            const response = await fetch("/api/me", {
                method: "GET",
                credentials: "include",
                headers: { "Accept": "application/json" }
            });
            if (response.ok) {
                const data = await response.json();
                if (data.status === "success" && data.user) {
                    localStorage.setItem("user", JSON.stringify(data.user));
                    localStorage.setItem("username", data.user.username || "");
                    localStorage.setItem("role", data.user.role || "");
                    window.location.replace("dashboard.html");
                }
            }
        } catch (error) {
            console.warn("Session check unavailable:", error);
        }
    })();

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const username = usernameInput.value.trim();
        const password = passwordInput.value;

        if (!username || !password) {
            showMessage("Please enter both username and password.");
            (!username ? usernameInput : passwordInput).focus();
            return;
        }

        showMessage("Signing in…", false);
        if (submitButton) {
            submitButton.disabled = true;
            submitButton.textContent = "Please wait…";
        }

        try {
            const response = await fetch("/api/login", {
                method: "POST",
                credentials: "include",
                headers: {
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                },
                body: JSON.stringify({ username, password })
            });

            const data = await response.json().catch(() => ({}));
            if (!response.ok || data.status !== "success" || !data.user) {
                throw new Error(data.message || `Login failed (${response.status}).`);
            }

            // Confirm that the browser received and can use the Flask session cookie.
            const meResponse = await fetch("/api/me", {
                method: "GET",
                credentials: "include",
                headers: { "Accept": "application/json" }
            });
            const meData = await meResponse.json().catch(() => ({}));
            if (!meResponse.ok || meData.status !== "success" || !meData.user) {
                throw new Error("Login response received, but the session could not be verified. Please try again.");
            }

            const user = meData.user;
            localStorage.setItem("user", JSON.stringify(user));
            localStorage.setItem("username", user.username || username);
            localStorage.setItem("role", user.role || "");
            showMessage("Login successful. Opening dashboard…", false);
            window.location.replace("dashboard.html");
        } catch (error) {
            console.error("Login error:", error);
            showMessage(error.message || "Unable to sign in. Check the backend and database connection.");
        } finally {
            if (submitButton) {
                submitButton.disabled = false;
                submitButton.textContent = "Login";
            }
        }
    });

    usernameInput.addEventListener("input", () => showMessage(""));
    passwordInput.addEventListener("input", () => showMessage(""));
});
