
// =====================================
// FRESH FIRST - PRIORITY MANAGEMENT
// =====================================

document.addEventListener("DOMContentLoaded", function () {

    const priorityFilter = document.getElementById("priorityFilter");
    const priorityTable = document.getElementById("priorityTable");

    // Load priority products from backend
    loadPriorityProducts();

    async function loadPriorityProducts() {

        try {

            const response = await fetch("/api/priority", {
                method: "GET",
                credentials: "include"
            });

            const data = await response.json();

            if (!response.ok || data.status !== "success") {
                throw new Error(data.message || "Unable to load priority products");
            }

            displayPriorityProducts(
                data.products || data.priority || data.items || []
            );

        } catch (error) {

            console.error("Priority loading error:", error);

        }
    }

    function displayPriorityProducts(products) {

        if (!priorityTable) return;

        const tbody = priorityTable.querySelector("tbody");

        if (!tbody) return;

        tbody.innerHTML = "";

        if (products.length === 0) {
            tbody.innerHTML =
                '<tr><td colspan="6">No priority products available.</td></tr>';
            return;
        }

        products.forEach(function (product) {

            const row = document.createElement("tr");

            const values = [
                product.product_name || "",
                product.category_name || "",
                product.quantity ?? "",
                product.expiry_date || "",
                product.priority || ""
            ];

            values.forEach(function (value, index) {

                const cell = document.createElement("td");

                if (index === 4) {
                    const label = document.createElement("span");
                    label.className = "priority-label";
                    label.textContent = value;
                    cell.appendChild(label);
                } else {
                    cell.textContent = value;
                }

                row.appendChild(cell);
            });

            tbody.appendChild(row);

        });

        applyPriorityFilter();
    }

    // Filter priority products
    function applyPriorityFilter() {

        if (!priorityFilter || !priorityTable) return;

        const selectedPriority =
            priorityFilter.value.toLowerCase();

        const rows = priorityTable.querySelectorAll("tbody tr");

        rows.forEach(function (row) {

            const priorityCell =
                row.querySelector(".priority-label");

            if (!priorityCell) return;

            const rowPriority =
                priorityCell.textContent.trim().toLowerCase();

            row.style.display =
                selectedPriority === "all" ||
                rowPriority === selectedPriority
                    ? ""
                    : "none";

        });
    }

    if (priorityFilter) {
        priorityFilter.addEventListener("change", applyPriorityFilter);
    }

});
