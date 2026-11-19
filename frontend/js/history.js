
// =====================================
// FRESH FIRST - HISTORY PAGE
// =====================================

document.addEventListener("DOMContentLoaded", function () {

    const searchInput = document.getElementById("historySearch");
    const historyTable = document.getElementById("historyTable");

    // Load history when page opens
    loadHistory();

    async function loadHistory() {

        try {

            const response = await fetch("/api/history", {
                method: "GET",
                credentials: "include"
            });

            const data = await response.json();

            if (!response.ok || data.status !== "success") {
                throw new Error(data.message || "Unable to load history");
            }

            const records =
                data.history || data.records || data.items || [];

            displayHistory(records);

        } catch (error) {

            console.error("History loading error:", error);

            const tbody = historyTable?.querySelector("tbody");

            if (tbody) {
                tbody.innerHTML =
                    '<tr><td colspan="10">Unable to load history. Please try again.</td></tr>';
            }
        }
    }

    // Display history records
    function displayHistory(records) {

        if (!historyTable) return;

        const tbody = historyTable.querySelector("tbody");

        if (!tbody) return;

        tbody.innerHTML = "";

        if (!records.length) {
            tbody.innerHTML =
                '<tr><td colspan="10">No history records available.</td></tr>';
            return;
        }

        records.forEach(function (record) {

            const row = document.createElement("tr");

            Object.values(record).forEach(function (value) {

                const cell = document.createElement("td");

                cell.textContent =
                    value === null || value === undefined ? "" : value;

                row.appendChild(cell);

            });

            tbody.appendChild(row);

        });

        applyHistorySearch();
    }

    // Search history records
    function applyHistorySearch() {

        if (!searchInput || !historyTable) return;

        const searchText = searchInput.value.toLowerCase();

        const rows = historyTable.querySelectorAll("tbody tr");

        rows.forEach(function (row) {

            const rowText = row.textContent.toLowerCase();

            row.style.display =
                rowText.includes(searchText) ? "" : "none";

        });
    }

    if (searchInput) {
        searchInput.addEventListener("input", applyHistorySearch);
    }

});
