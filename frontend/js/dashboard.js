
/* =====================================
   FRESH FIRST - DASHBOARD JAVASCRIPT
   ===================================== */

/* SAMPLE FRONTEND DATA */

const products = [
    {
        product_name: "Fresh Milk",
        category_name: "Dairy",
        quantity: 20,
        unit: "litres",
        expiry_date: "2026-11-20"
    },
    {
        product_name: "Apple",
        category_name: "Fruits",
        quantity: 30,
        unit: "kg",
        expiry_date: "2026-11-22"
    },
    {
        product_name: "Banana",
        category_name: "Fruits",
        quantity: 25,
        unit: "kg",
        expiry_date: "2026-11-17"
    },
    {
        product_name: "Carrot",
        category_name: "Vegetables",
        quantity: 15,
        unit: "kg",
        expiry_date: "2026-11-25"
    },
    {
        product_name: "Bread",
        category_name: "Bakery",
        quantity: 20,
        unit: "packets",
        expiry_date: "2026-11-18"
    }
];

/* CALCULATE PRODUCT STATUS */

function getDaysLeft(expiryDate) {
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const expiry = new Date(expiryDate + "T00:00:00");
    expiry.setHours(0, 0, 0, 0);

    return Math.ceil((expiry - today) / (1000 * 60 * 60 * 24));
}

products.forEach(product => {
    product.days_left = getDaysLeft(product.expiry_date);

    if (product.days_left < 0) {
        product.status = "UNSAFE";
    } else if (product.days_left <= 3) {
        product.status = "WARNING";
    } else {
        product.status = "SAFE";
    }
});

/* NEEDS ATTENTION DATA */

let attentionItems = [];

/* SAFE HTML */

function escapeHTML(value) {
    return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

/* LOGOUT */

function logout() {
    localStorage.removeItem("user");
    localStorage.removeItem("username");
    localStorage.removeItem("role");

    window.location.href = "login.html";
}

/* USER INFORMATION */

function loadUser() {
    let user = {};

    try {
        user = JSON.parse(localStorage.getItem("user") || "{}");
    } catch (error) {
        user = {};
    }

    const name =
        user.full_name ||
        user.username ||
        localStorage.getItem("username") ||
        "Administrator";

    const role =
        user.role ||
        localStorage.getItem("role") ||
        "ADMIN";

    const profileName = document.getElementById("profileName");
    const profileRole = document.getElementById("profileRole");
    const avatar = document.getElementById("avatar");

    if (profileName) {
        profileName.textContent = name;
    }

    if (profileRole) {
        profileRole.textContent = role;
    }

    if (avatar) {
        avatar.textContent = name.charAt(0).toUpperCase();
    }
}

/* SLIDER */

let currentSlide = 0;
let slideTimer = null;

function showSlide(index) {
    const slides = document.querySelectorAll(".slide");
    const dots = document.querySelectorAll(".slider-dot");

    if (slides.length === 0) return;

    currentSlide = (index + slides.length) % slides.length;

    slides.forEach((slide, i) => {
        slide.classList.toggle("active", i === currentSlide);
    });

    dots.forEach((dot, i) => {
        dot.classList.toggle("active", i === currentSlide);
    });
}

function startSlider() {
    clearInterval(slideTimer);

    slideTimer = setInterval(() => {
        showSlide(currentSlide + 1);
    }, 4000);
}

/* STOCK HEALTH */

function updateHealth() {
    const total = products.length;

    const safe = products.filter(
        p => p.status === "SAFE"
    ).length;

    const warning = products.filter(
        p => p.status === "WARNING"
    ).length;

    const unsafe = products.filter(
        p => p.status === "UNSAFE"
    ).length;

    const health = total > 0
        ? Math.round((safe / total) * 100)
        : 0;

    const setText = (id, value) => {
        const element = document.getElementById(id);

        if (element) {
            element.textContent = value;
        }
    };

    setText("totalProducts", total);
    setText("validProducts", safe);
    setText("nearExpiry", warning);
    setText("expiredProducts", unsafe);

    setText("healthNumber", health + "%");
    setText("healthValid", safe);
    setText("healthNear", warning);
    setText("healthExpired", unsafe);

    const circle = document.getElementById("healthCircle");

    if (circle) {
        const degree = health * 3.6;

        circle.style.background =
            `conic-gradient(
                #22c55e 0deg ${degree}deg,
                #e5e7eb ${degree}deg 360deg
            )`;
    }

    let title = "Attention Required ⚠️";
    let description = "Some products need checking.";
    let status = "🔴 Check stock now";

    if (health >= 80) {
        title = "Excellent Stock Health 🎉";
        description = "Most products are safe.";
        status = "🟢 Stock is healthy";
    } else if (health >= 60) {
        title = "Good Stock Health 👍";
        description = "Some products need attention.";
        status = "🟡 Keep monitoring";
    }

    setText("healthTitle", title);
    setText("healthDescription", description);
    setText("healthStatus", status);
}

/* PRODUCT STATUS */

function displayProducts() {
    const container = document.getElementById("productList");
    const count = document.getElementById("productCount");

    if (!container) return;

    if (count) {
        count.textContent = products.length + " products";
    }

    container.innerHTML = "";

    products.forEach(product => {
        const daysLeft = Number(product.days_left);

        let daysText = daysLeft + " day(s) left";
        let daysClass = "days-good";

        if (daysLeft === 0) {
            daysText = "Expires today";
            daysClass = "days-danger";
        } else if (daysLeft < 0) {
            daysText = Math.abs(daysLeft) + " day(s) overdue";
            daysClass = "days-danger";
        } else if (product.status === "WARNING") {
            daysClass = "days-warning";
        }

        let statusClass = "status-valid";
        let statusIcon = "🟢";

        if (product.status === "WARNING") {
            statusClass = "status-near";
            statusIcon = "🟠";
        } else if (product.status === "UNSAFE") {
            statusClass = "status-expired";
            statusIcon = "🔴";
        }

        const row = document.createElement("div");
        row.className = "product-row";

        row.innerHTML = `
            <div class="product-name">
                <strong>${statusIcon} ${escapeHTML(product.product_name)}</strong>
                <span>🏷️ ${escapeHTML(product.category_name)}</span>
            </div>

            <div>📦 ${escapeHTML(product.quantity)} ${escapeHTML(product.unit)}</div>

            <div>📅 ${escapeHTML(product.expiry_date)}</div>

            <div class="${daysClass}">${escapeHTML(daysText)}</div>

            <div class="${statusClass}">${escapeHTML(product.status)}</div>
        `;

        container.appendChild(row);
    });
}

/* NEEDS ATTENTION */

function displayCritical() {
    const container = document.getElementById("criticalList");

    if (!container) return;

    attentionItems = products
        .filter(product => product.status !== "SAFE")
        .map(product => ({
            product_name: product.product_name,
            action_type: product.status === "UNSAFE"
                ? "Expired product"
                : "Near expiry product",
            description: product.status === "UNSAFE"
                ? "Remove this product from available stock."
                : "Check this product and take action before expiry.",
            priority: product.status === "UNSAFE"
                ? "CRITICAL"
                : "HIGH"
        }));

    if (attentionItems.length === 0) {
        container.innerHTML = "<p>🎉 No pending attention items!</p>";
        return;
    }

    container.innerHTML = "";

    attentionItems.forEach(item => {
        const div = document.createElement("div");
        div.className = "critical-item";

        const priorityClass =
            item.priority === "CRITICAL"
                ? "priority-critical"
                : "priority-high";

        div.innerHTML = `
            <div class="critical-icon">⚠️</div>

            <div>
                <strong>${escapeHTML(item.product_name)}</strong>
                <p>${escapeHTML(item.action_type)}</p>
                <p>${escapeHTML(item.description)}</p>
            </div>

            <span class="${priorityClass}">
                ${escapeHTML(item.priority)}
            </span>
        `;

        container.appendChild(div);
    });
}

/* CURRENT DATE */

function displayCurrentDate() {
    const date = document.getElementById("currentDate");

    if (date) {
        date.textContent = new Date().toLocaleDateString("en-IN", {
            day: "2-digit",
            month: "long",
            year: "numeric"
        });
    }
}

/* START DASHBOARD */

document.addEventListener("DOMContentLoaded", function() {
    loadUser();
    displayCurrentDate();

    updateHealth();
    displayProducts();
    displayCritical();

    showSlide(0);
    startSlider();
});
