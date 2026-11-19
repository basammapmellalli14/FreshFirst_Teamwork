
// =====================================
// FRESH FIRST - REPORTS & ANALYTICS
// =====================================

document.addEventListener("DOMContentLoaded", function () {

    let products = [];
    let verifications = [];
    let actions = [];

    const API = "";

    // Load user information
    function loadUser() {
        let user = {};

        try {
            user = JSON.parse(localStorage.getItem("user") || "{}");
        } catch (error) {}

        const name = user.full_name ||
            user.username ||
            localStorage.getItem("username") ||
            "Administrator";

        const profile = document.getElementById("profileName");

        if (profile) {
            profile.textContent = "Welcome, " + name;
        }
    }

    // Escape HTML
    function escapeHTML(value) {
        return String(value ?? "").replace(/[&<>"']/g, char => ({
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#039;"
        })[char]);
    }

    // Load reports from backend
    async function loadReports() {
        try {
            const [productResponse, verificationResponse, actionResponse] =
                await Promise.all([
                    fetch(API + "/api/products", {
                        credentials: "include"
                    }),
                    fetch(API + "/api/verifications", {
                        credentials: "include"
                    }),
                    fetch(API + "/api/actions", {
                        credentials: "include"
                    })
                ]);

            const productData = await productResponse.json();
            const verificationData = await verificationResponse.json();
            const actionData = await actionResponse.json();

            if (!productResponse.ok ||
                productData.status !== "success") {
                throw new Error(productData.message || "Unable to load products.");
            }

            if (!verificationResponse.ok ||
                verificationData.status !== "success") {
                throw new Error(verificationData.message || "Unable to load verifications.");
            }

            if (!actionResponse.ok ||
                actionData.status !== "success") {
                throw new Error(actionData.message || "Unable to load actions.");
            }

            products = productData.products || [];
            verifications = verificationData.verifications || [];
            actions = actionData.actions || [];

            renderReports();

        } catch (error) {
            console.error("Reports loading error:", error);

            document.getElementById("reportInfo").textContent =
                "Unable to load report data from the backend. Please check that the backend server is running and you are logged in.";
        }
    }

    // Date calculation
    function daysLeft(date) {
        if (!date) return null;

        const expiry = new Date(String(date).substring(0, 10) + "T00:00:00");

        if (Number.isNaN(expiry.getTime())) return null;

        const today = new Date();
        today.setHours(0, 0, 0, 0);

        return Math.ceil((expiry - today) / 86400000);
    }

    // Product status
    function getStatus(product) {
        const priority = String(product.priority || "").toUpperCase();

        if (priority === "CRITICAL") return "UNSAFE";
        if (priority === "HIGH" || priority === "INSPECTION") return "WARNING";
        if (priority === "MEDIUM") return "WARNING";
        if (priority === "LOW") return "SAFE";

        const days = daysLeft(product.expiry_date);

        if (days !== null && days < 0) return "UNSAFE";
        if (days !== null && days <= 3) return "WARNING";

        return "SAFE";
    }

    // Verification status
    function getVerificationStatus(item) {
        return String(
            item.status ||
            item.verification_status ||
            item.result ||
            ""
        ).toUpperCase();
    }

    // Action status
    function getActionStatus(item) {
        return String(
            item.status ||
            item.action_status ||
            ""
        ).toUpperCase().replace(/[\s-]+/g, "_");
    }

    // Render all reports
    function renderReports() {

        let safe = 0;
        let warning = 0;
        let unsafe = 0;
        let totalQuantity = 0;
        let nearExpiry = 0;
        let expired = 0;

        products.forEach(product => {

            const status = getStatus(product);

            if (status === "SAFE") safe++;
            else if (status === "WARNING") warning++;
            else unsafe++;

            totalQuantity += Number(product.quantity) || 0;

            const days = daysLeft(product.expiry_date);

            if (days !== null && days < 0) {
                expired++;
            } else if (days !== null && days <= 3) {
                nearExpiry++;
            }
        });

        // Main summary cards
        document.getElementById("totalProducts").textContent =
            products.length;

        document.getElementById("totalQuantity").textContent =
            totalQuantity;

        document.getElementById("nearExpiry").textContent =
            nearExpiry;

        document.getElementById("expired").textContent =
            expired;

        // Stock health summary
        document.getElementById("safeCount").textContent = safe;
        document.getElementById("warningCount").textContent = warning;
        document.getElementById("unsafeCount").textContent = unsafe;

        document.getElementById("healthTotal").textContent =
            products.length;

        const total = products.length || 1;
        const green = safe / total * 100;
        const yellow = warning / total * 100;

        document.getElementById("donut").style.background =
            `conic-gradient(
                #36ad75 0% ${green}%,
                #e6aa35 ${green}% ${green + yellow}%,
                #df5555 ${green + yellow}% 100%
            )`;

        // Product stock table
        const stockTable = document.getElementById("stockReport");

        if (products.length === 0) {
            stockTable.innerHTML =
                '<tr><td colspan="6">No products available.</td></tr>';
        } else {
            stockTable.innerHTML = products.map(product => {

                const status = getStatus(product);
                const statusClass = status.toLowerCase();

                return `
                    <tr>
                        <td><strong>${escapeHTML(product.product_name)}</strong></td>
                        <td>${escapeHTML(product.category_name)}</td>
                        <td>${escapeHTML(product.quantity)} ${escapeHTML(product.unit)}</td>
                        <td>${escapeHTML(product.expiry_date)}</td>
                        <td>
                            ${product.storage_temperature !== null &&
                            product.storage_temperature !== undefined
                                ? escapeHTML(product.storage_temperature) + " °C"
                                : "Not specified"}
                        </td>
                        <td>
                            <span class="status ${statusClass}">
                                ${status}
                            </span>
                        </td>
                    </tr>
                `;
            }).join("");
        }

        // Verification summary
        const verificationStatuses = verifications.map(getVerificationStatus);

        document.getElementById("totalVerifications").textContent =
            verifications.length;

        document.getElementById("safeVerifications").textContent =
            verificationStatuses.filter(status => status === "SAFE").length;

        document.getElementById("warningVerifications").textContent =
            verificationStatuses.filter(status => status === "WARNING").length;

        document.getElementById("unsafeVerifications").textContent =
            verificationStatuses.filter(status => status === "UNSAFE").length;

        // Action summary
        const actionStatuses = actions.map(getActionStatus);

        document.getElementById("totalActions").textContent =
            actions.length;

        document.getElementById("pendingActions").textContent =
            actionStatuses.filter(status => status === "PENDING").length;

        document.getElementById("progressActions").textContent =
            actionStatuses.filter(status =>
                status === "IN_PROGRESS" || status === "INPROGRESS"
            ).length;

        document.getElementById("completedActions").textContent =
            actionStatuses.filter(status =>
                status === "DONE" || status === "COMPLETED"
            ).length;

        document.getElementById("reportInfo").textContent =
            "Reports are loaded from the FreshFirst backend using product, verification and action records.";
    }

    // Export stock report
    window.exportStock = function () {

        if (!products.length) {
            alert("No products available to export.");
            return;
        }

        const headers = [
            "Product",
            "Category",
            "Quantity",
            "Unit",
            "Purchase Date",
            "Expiry Date",
            "Storage Temperature",
            "Status"
        ];

        const rows = products.map(product => [
            product.product_name,
            product.category_name,
            product.quantity,
            product.unit,
            product.purchase_date,
            product.expiry_date,
            product.storage_temperature,
            getStatus(product)
        ]);

        const csv = [headers, ...rows].map(row =>
            row.map(value =>
                '"' + String(value ?? "").replace(/"/g, '""') + '"'
            ).join(",")
        ).join("\n");

        const blob = new Blob(
            ["\uFEFF" + csv],
            { type: "text/csv;charset=utf-8;" }
        );

        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");

        link.href = url;
        link.download = "FreshFirst_Stock_Report.csv";

        document.body.appendChild(link);
        link.click();
        link.remove();

        URL.revokeObjectURL(url);
    };

    // Logout
    window.logout = async function () {

        try {
            await fetch(API + "/api/logout", {
                method: "POST",
                credentials: "include"
            });
        } catch (error) {
            console.error("Logout error:", error);
        }

        localStorage.removeItem("user");
        localStorage.removeItem("username");
        localStorage.removeItem("role");

        window.location.href = "login.html";
    };

    loadUser();
    loadReports();

});
