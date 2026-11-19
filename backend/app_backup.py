
from flask import Flask, request, jsonify, session, send_from_directory
from werkzeug.security import check_password_hash
from db import get_db_connection
from datetime import datetime
import os

app = Flask(__name__)

# --------------------------------------------------
# APPLICATION CONFIGURATION
# --------------------------------------------------

app.secret_key = "freshfirst_development_secret_key"

FRONTEND_FOLDER = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "frontend")
)


# --------------------------------------------------
# 1. HOME PAGE
# --------------------------------------------------

@app.route("/")
def home():
    return send_from_directory(FRONTEND_FOLDER, "index.html")


# --------------------------------------------------
# 2. FRONTEND HTML PAGES
# --------------------------------------------------

@app.route("/<page>.html")
def frontend_pages(page):
    return send_from_directory(FRONTEND_FOLDER, page + ".html")


# --------------------------------------------------
# 3. CSS, JAVASCRIPT AND IMAGE FILES
# --------------------------------------------------

@app.route("/<path:filename>")
def frontend_static(filename):
    return send_from_directory(FRONTEND_FOLDER, filename)


# --------------------------------------------------
# 4. BACKEND HEALTH CHECK
# --------------------------------------------------

@app.route("/api/health")
def health():
    return jsonify({
        "status": "success",
        "message": "Fresh First Flask backend is running!"
    })


# --------------------------------------------------
# 5. USER LOGIN API
# --------------------------------------------------

@app.route("/api/login", methods=["POST"])
def login():

    data = request.get_json(silent=True) or {}

    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        return jsonify({
            "status": "error",
            "message": "Username and password are required."
        }), 400

    connection = get_db_connection()

    if not connection:
        return jsonify({
            "status": "error",
            "message": "Database connection failed."
        }), 500

    cursor = None

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT user_id, full_name, username, password_hash, role
            FROM users
            WHERE username = %s
            """,
            (username,)
        )

        user = cursor.fetchone()

        if not user or not check_password_hash(
            user["password_hash"], password
        ):
            return jsonify({
                "status": "error",
                "message": "Invalid username or password."
            }), 401

        session["user_id"] = user["user_id"]
        session["username"] = user["username"]
        session["full_name"] = user["full_name"]
        session["role"] = user["role"]

        return jsonify({
            "status": "success",
            "message": "Login successful!",
            "user": {
                "user_id": user["user_id"],
                "full_name": user["full_name"],
                "username": user["username"],
                "role": user["role"]
            }
        })

    except Exception as e:
        print("Login Error:", e)

        return jsonify({
            "status": "error",
            "message": "An error occurred during login."
        }), 500

    finally:
        if cursor:
            cursor.close()

        connection.close()


# --------------------------------------------------
# 6. LOGOUT API
# --------------------------------------------------

@app.route("/api/logout", methods=["POST"])
def logout():

    session.clear()

    return jsonify({
        "status": "success",
        "message": "Logged out successfully."
    })


# --------------------------------------------------
# 7. ADD PRODUCT API
# --------------------------------------------------

@app.route("/api/products", methods=["POST"])
def add_product():

    if "user_id" not in session:
        return jsonify({
            "status": "error",
            "message": "Please login first."
        }), 401

    data = request.get_json(silent=True) or {}

    product_name = str(data.get("productName", "")).strip()
    category_name = str(data.get("category", "")).strip()
    expiry_date = data.get("expiryDate")
    quantity = data.get("quantity")
    temperature = data.get("temperature")

    if not product_name or not category_name or not expiry_date or quantity is None:
        return jsonify({
            "status": "error",
            "message": "Please fill all required fields."
        }), 400

    try:
        quantity = int(quantity)

        if quantity <= 0:
            raise ValueError

        datetime.strptime(expiry_date, "%Y-%m-%d")

        if temperature is not None and temperature != "":
            temperature = float(temperature)
        else:
            temperature = None

    except (ValueError, TypeError):
        return jsonify({
            "status": "error",
            "message": "Enter valid quantity, expiry date and temperature."
        }), 400

    connection = get_db_connection()

    if not connection:
        return jsonify({
            "status": "error",
            "message": "Database connection failed."
        }), 500

    cursor = None

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT category_id
            FROM categories
            WHERE category_name = %s
            """,
            (category_name,)
        )

        category = cursor.fetchone()

        if not category:
            return jsonify({
                "status": "error",
                "message": "Selected category does not exist."
            }), 400

        cursor.execute(
            """
            INSERT INTO products
            (
                product_name,
                category_id,
                quantity,
                expiry_date,
                storage_temperature,
                created_by
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                product_name,
                category["category_id"],
                quantity,
                expiry_date,
                temperature,
                session["user_id"]
            )
        )

        connection.commit()

        return jsonify({
            "status": "success",
            "message": "Product added successfully!",
            "product_id": cursor.lastrowid
        }), 201

    except Exception as e:
        connection.rollback()
        print("Add Product Error:", e)

        return jsonify({
            "status": "error",
            "message": "Unable to add product."
        }), 500

    finally:
        if cursor:
            cursor.close()

        connection.close()


# --------------------------------------------------
# 8. VIEW PRODUCTS API
# --------------------------------------------------

@app.route("/api/products", methods=["GET"])
def get_products():

    if "user_id" not in session:
        return jsonify({
            "status": "error",
            "message": "Please login first."
        }), 401

    connection = get_db_connection()

    if not connection:
        return jsonify({
            "status": "error",
            "message": "Database connection failed."
        }), 500

    cursor = None

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                p.product_id,
                p.product_name,
                c.category_name,
                p.quantity,
                p.expiry_date,
                p.storage_temperature
            FROM products p
            JOIN categories c
                ON p.category_id = c.category_id
            ORDER BY p.product_id DESC
            """
        )

        products = cursor.fetchall()

        for product in products:

            product["expiry_date"] = product["expiry_date"].isoformat()

            if product["storage_temperature"] is not None:
                product["storage_temperature"] = float(
                    product["storage_temperature"]
                )

        return jsonify({
            "status": "success",
            "products": products
        })

    except Exception as e:
        print("View Products Error:", e)

        return jsonify({
            "status": "error",
            "message": "Unable to retrieve products."
        }), 500

    finally:
        if cursor:
            cursor.close()

        connection.close()


# --------------------------------------------------
# 9. RUN FLASK APPLICATION
# --------------------------------------------------

if __name__ == "__main__":

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )
