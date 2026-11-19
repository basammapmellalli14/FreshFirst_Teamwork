
// =====================================
// FRESH FIRST - REPORTS PAGE
// =====================================

document.addEventListener("DOMContentLoaded", function () {

    const reportButton = document.getElementById("generateReport");
    const reportMessage = document.getElementById("reportMessage");

    if (!reportButton) return;

    reportButton.addEventListener("click", async function () {

        reportButton.disabled = true;

        if (reportMessage) {
            reportMessage.textContent = "Generating report...";
            reportMessage.style.color = "#0d6efd";
        }

        try {

            const response = await fetch("/api/reports", {
                method: "POST",
                credentials: "include",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({})
            });

            const data = await response.json();

            if (!response.ok || data.status !== "success") {
                throw new Error(
                    data.message || "Unable to generate report."
                );
            }

            if (reportMessage) {
                reportMessage.textContent =
                    data.message || "Report generated successfully!";
                reportMessage.style.color = "#198754";
            } else {
                alert(data.message || "Report generated successfully!");
            }

        } catch (error) {

            console.error("Report generation error:", error);

            if (reportMessage) {
                reportMessage.textContent =
                    "Unable to generate report. Please try again.";
                reportMessage.style.color = "#dc3545";
            } else {
                alert(error.message);
            }

        } finally {
            reportButton.disabled = false;
        }

    });

});
