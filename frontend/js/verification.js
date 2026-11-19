
// =====================================
// FRESH FIRST - VERIFICATION PAGE
// =====================================

document.addEventListener("DOMContentLoaded", function () {

    const verificationForm = document.getElementById("verificationForm");
    const verificationResult = document.getElementById("verificationResult");

    if (!verificationForm) return;

    verificationForm.addEventListener("submit", async function (event) {

        event.preventDefault();

        const productName =
            document.getElementById("productName").value.trim();

        const quantity =
            document.getElementById("quantity").value;

        const temperature =
            document.getElementById("temperature").value;

        if (!productName || quantity === "" || temperature === "") {
            alert("Please enter all required verification details.");
            return;
        }

        const verificationData = {
            product_name: productName,
            quantity: Number(quantity),
            temperature: Number(temperature)
        };

        try {

            const response = await fetch("/api/verifications", {
                method: "POST",
                credentials: "include",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(verificationData)
            });

            const data = await response.json();

            if (!response.ok || data.status !== "success") {
                throw new Error(
                    data.message || "Unable to save verification."
                );
            }

            if (verificationResult) {
                verificationResult.style.display = "block";
                verificationResult.textContent =
                    "Verification saved successfully!";
            }

            alert("Verification saved successfully!");

            verificationForm.reset();

        } catch (error) {

            console.error("Verification error:", error);

            alert("Unable to save verification: " + error.message);

        }

    });

});
