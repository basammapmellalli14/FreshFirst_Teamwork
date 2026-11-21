
// =====================================
// FRESH FIRST - LOGIN PAGE
// =====================================

document.addEventListener("DOMContentLoaded", function () {

    const loginForm = document.getElementById("loginForm");

    if (!loginForm) return;

    loginForm.addEventListener("submit", async function (event) {

        event.preventDefault();

        const username =
            document.getElementById("username").value.trim();

        const password =
            document.getElementById("password").value;

        const message =
            document.getElementById("loginMessage");

        if (!username || !password) {
            message.textContent = "Please enter username and password.";
            message.style.color = "red";
            return;
        }

        try {

            message.textContent = "Logging in...";
            message.style.color = "#0d6efd";

            const response = await fetch("/api/login", {
                method: "POST",
                credentials: "include",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    username: username,
                    password: password
                })
            });

            const data = await response.json();

            if (!response.ok || data.status !== "success") {
                throw new Error(
                    data.message || "Invalid username or password."
                );
            }

            // Store login information if returned by backend
            const user = data.user || {};

            localStorage.setItem("user", JSON.stringify(user));

            if (user.username || username) {
                localStorage.setItem("username", user.username || username);
            }

            if (user.role) {
                localStorage.setItem("role", user.role);
            }

            message.textContent = "Login successful!";
            message.style.color = "green";

            window.location.href = "dashboard.html";

        } catch (error) {

            console.error("Login error:", error);

            message.textContent = error.message;
            message.style.color = "red";

        }

    });

});
