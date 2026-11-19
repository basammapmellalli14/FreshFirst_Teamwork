
// =====================================
// FRESH FIRST - SETTINGS PAGE
// =====================================

document.addEventListener("DOMContentLoaded", function () {

    const settingsForm = document.getElementById("settingsForm");

    // Load existing settings
    loadSettings();

    async function loadSettings() {

        try {

            const response = await fetch("/api/settings", {
                method: "GET",
                credentials: "include"
            });

            const data = await response.json();

            if (!response.ok || data.status !== "success") {
                throw new Error(data.message || "Unable to load settings");
            }

            console.log("Settings loaded:", data.settings || data);

        } catch (error) {

            console.error("Settings loading error:", error);

        }
    }

    // Save settings
    if (settingsForm) {

        settingsForm.addEventListener("submit", async function (event) {

            event.preventDefault();

            const formData = new FormData(settingsForm);
            const settingsData = Object.fromEntries(formData.entries());

            try {

                const response = await fetch("/api/settings", {
                    method: "PUT",
                    credentials: "include",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify(settingsData)
                });

                const data = await response.json();

                if (!response.ok || data.status !== "success") {
                    throw new Error(data.message || "Unable to save settings");
                }

                alert("Settings saved successfully!");

                await loadSettings();

            } catch (error) {

                console.error("Settings saving error:", error);

                alert("Unable to save settings: " + error.message);

            }

        });

    }

});
