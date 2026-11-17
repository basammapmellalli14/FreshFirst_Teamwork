
// FRESH FIRST - STOCK MANAGEMENT

document.addEventListener("DOMContentLoaded", function () {

    const stockForm = document.getElementById("stockForm");
    const stockTable = document.querySelector("#stockTable tbody");

    stockForm.addEventListener("submit", function (event) {

        event.preventDefault();

        const productName = document.getElementById("productName").value.trim();
        const category = document.getElementById("category").value;
        const quantity = document.getElementById("quantity").value;
        const unit = document.getElementById("unit").value;
        const expiryDate = document.getElementById("expiryDate").value;
        const temperature = document.getElementById("temperature").value;

        if (!productName || !category || !quantity || !unit || !expiryDate) {
            alert("Please fill all required fields.");
            return;
        }

        const row = document.createElement("tr");

        const values = [
            productName,
            category,
            quantity,
            unit,
            expiryDate,
            temperature ? temperature + " °C" : "Not specified"
        ];

        values.forEach(function (value) {
            const cell = document.createElement("td");
            cell.textContent = value;
            row.appendChild(cell);
        });

        stockTable.appendChild(row);

        alert("Product added successfully!");

        stockForm.reset();

    });

});
