
// =====================================
// FRESH FIRST - SUGGESTED ACTIONS
// =====================================

document.addEventListener("DOMContentLoaded", function () {

    const actionForm = document.getElementById("actionForm");

    if (!actionForm) return;

    actionForm.addEventListener("submit", async function (event) {

        event.preventDefault();

        const productName =
            document.getElementById("productName").value.trim();

        const suggestedAction =
            document.getElementById("suggestedAction").value;

        const remarks =
            document.getElementById("remarks").value.trim();

        if (!productName || !suggestedAction) {
            alert("Please enter the product name and select an action.");
            return;
        }

        const actionData = {
            product_name: productName,
            suggested_action: suggestedAction,
            remarks: remarks
        };

        try {

            const response = await fetch("/api/actions", {
                method: "POST",
                credentials: "include",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(actionData)
            });

            const data = await response.json();

            if (!response.ok || data.status !== "success") {
                throw new Error(
                    data.message || "Unable to save suggested action."
                );
            }

            alert("Suggested action saved successfully!");

            actionForm.reset();

        } catch (error) {

            console.error("Action saving error:", error);

            alert("Unable to save action: " + error.message);

        }

    });

});
