
 // =====================================
 // FRESH FIRST - CATEGORY MANAGEMENT
 // =====================================

document.addEventListener("DOMContentLoaded", function () {

    const categoryForm = document.getElementById("categoryForm");

    // Load categories when page opens
    loadCategories();

    // Fetch categories from backend
    async function loadCategories() {

        try {
            const response = await fetch("/api/categories", {
                method: "GET",
                credentials: "include"
            });

            const data = await response.json();

            if (!response.ok || data.status !== "success") {
                throw new Error(data.message || "Unable to load categories");
            }

            console.log("Categories loaded:", data.categories || []);

        } catch (error) {
            console.error("Category loading error:", error);
        }
    }

    // Add category
    if (categoryForm) {

        categoryForm.addEventListener("submit", async function (event) {

            event.preventDefault();

            const categoryName =
                document.getElementById("categoryName").value.trim();

            const storageTemperature =
                document.getElementById("storageTemperature").value;

            if (!categoryName || storageTemperature === "") {
                alert("Please enter the category name and storage temperature.");
                return;
            }

            const categoryData = {
                category_name: categoryName,
                storage_temperature: Number(storageTemperature)
            };

            try {

                const response = await fetch("/api/categories", {
                    method: "POST",
                    credentials: "include",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify(categoryData)
                });

                const data = await response.json();

                if (!response.ok || data.status !== "success") {
                    throw new Error(data.message || "Unable to add category");
                }

                alert("Category added successfully!");

                categoryForm.reset();

                await loadCategories();

            } catch (error) {

                console.error("Category adding error:", error);

                alert("Unable to add category: " + error.message);
            }

        });
    }

});
