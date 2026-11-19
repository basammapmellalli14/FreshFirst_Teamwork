
// =====================================
// FRESH FIRST - USER MANAGEMENT
// =====================================

document.addEventListener("DOMContentLoaded", function () {

    const API = "";
    let users = [];

    const userTable = document.getElementById("userTable");
    const userModal = document.getElementById("userModal");
    const searchInput = document.getElementById("search");
    const roleFilter = document.getElementById("roleFilter");

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

    // Normalize role names for filtering and counting
    function normalizeRole(role) {
        return String(role || "").trim().toLowerCase();
    }

    // Get user information from API fields
    function getUserId(user) {
        return user.user_id ?? user.id ?? "-";
    }

    function getFullName(user) {
        return user.full_name ?? user.fullName ?? "";
    }

    function getUsername(user) {
        return user.username ?? "";
    }

    function getRole(user) {
        return user.role ?? "";
    }

    function getCreatedDate(user) {
        return user.created_at ?? user.createdAt ?? "-";
    }

    // Load users from backend
    async function loadUsers() {

        userTable.innerHTML =
            '<tr><td colspan="6" class="empty">Loading users...</td></tr>';

        try {

            const response = await fetch(API + "/api/users", {
                method: "GET",
                credentials: "include"
            });

            const data = await response.json();

            if (!response.ok || data.status !== "success") {
                throw new Error(data.message || "Unable to load users.");
            }

            users = Array.isArray(data.users) ? data.users : [];

            renderUsers();

        } catch (error) {

            console.error("User loading error:", error);

            userTable.innerHTML =
                `<tr><td colspan="6" class="empty">
                    ${escapeHTML(error.message)}
                </td></tr>`;
        }
    }

    // Display users in table
    function renderUsers() {

        const search = searchInput.value.trim().toLowerCase();
        const selectedRole = normalizeRole(roleFilter.value);

        // Summary cards
        document.getElementById("totalUsers").textContent = users.length;

        document.getElementById("adminCount").textContent =
            users.filter(user =>
                normalizeRole(getRole(user)) === "admin"
            ).length;

        document.getElementById("staffCount").textContent =
            users.filter(user =>
                normalizeRole(getRole(user)) === "staff"
            ).length;

        // Search and filter
        const filteredUsers = users.filter(user => {

            const name = getFullName(user).toLowerCase();
            const username = getUsername(user).toLowerCase();
            const role = normalizeRole(getRole(user));

            const matchesSearch =
                name.includes(search) || username.includes(search);

            const matchesRole =
                !selectedRole || role === selectedRole;

            return matchesSearch && matchesRole;
        });

        if (filteredUsers.length === 0) {

            userTable.innerHTML =
                '<tr><td colspan="6" class="empty">No users found.</td></tr>';

            return;
        }

        userTable.innerHTML = filteredUsers.map(user => {

            return `
                <tr>
                    <td>${escapeHTML(getUserId(user))}</td>
                    <td>${escapeHTML(getFullName(user))}</td>
                    <td>${escapeHTML(getUsername(user))}</td>
                    <td>
                        <span class="role">
                            ${escapeHTML(getRole(user))}
                        </span>
                    </td>
                    <td>${escapeHTML(getCreatedDate(user))}</td>
                    <td class="actions">—</td>
                </tr>
            `;

        }).join("");
    }

    // Open Add User modal
    window.openAdd = function () {

        document.getElementById("modalTitle").textContent = "Add User";

        document.getElementById("editId").value = "";
        document.getElementById("fullName").value = "";
        document.getElementById("usernameInput").value = "";
        document.getElementById("passwordInput").value = "";
        document.getElementById("userRole").value = "Staff";

        userModal.style.display = "flex";
    };

    // Close modal
    window.closeModal = function () {
        userModal.style.display = "none";
    };

    // Add new user
    window.saveUser = async function () {

        const fullName =
            document.getElementById("fullName").value.trim();

        const username =
            document.getElementById("usernameInput").value.trim();

        const role =
            document.getElementById("userRole").value;

        if (!fullName || !username || !role) {
            alert("Please fill in all required user details.");
            return;
        }

        const userData = {
            full_name: fullName,
            username: username,
            role: role
        };

        try {

            const response = await fetch(API + "/api/users", {
                method: "POST",
                credentials: "include",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(userData)
            });

            const data = await response.json();

            if (!response.ok || data.status !== "success") {
                throw new Error(data.message || "Unable to add user.");
            }

            alert("User added successfully!");

            userModal.style.display = "none";

            await loadUsers();

        } catch (error) {

            console.error("User adding error:", error);

            alert("Unable to add user: " + error.message);
        }
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

    // Search and role filter
    searchInput.addEventListener("input", renderUsers);
    roleFilter.addEventListener("change", renderUsers);

    // Close modal when clicking outside
    userModal.addEventListener("click", function (event) {
        if (event.target === userModal) {
            userModal.style.display = "none";
        }
    });

    // Initial load
    loadUsers();

});
