
from flask import Flask, request, jsonify, session, send_from_directory
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps
from db import get_db_connection
from datetime import datetime, date
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
# COMMON HELPERS
# --------------------------------------------------

def login_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({
                "status": "error",
                "message": "Please login first."
            }), 401
        return function(*args, **kwargs)
    return wrapper


def admin_required(function):
    @wraps(function)
    @login_required
    def wrapper(*args, **kwargs):
        if session.get("role") != "ADMIN":
            return jsonify({
                "status": "error",
                "message": "Administrator permission required."
            }), 403
        return function(*args, **kwargs)
    return wrapper


def get_priority(product):
    today = date.today()
    expiry = product["expiry_date"]

    if isinstance(expiry, str):
        expiry = date.fromisoformat(expiry)

    if expiry < today:
        return "CRITICAL"

    if product.get("storage_temperature") is None:
        return "INSPECTION"

    temperature = float(product["storage_temperature"])
    minimum = float(product["min_storage_temp"])
    maximum = float(product["max_storage_temp"])

    if temperature < minimum or temperature > maximum:
        return "HIGH"

    days_left = (expiry - today).days
    near_expiry_days = int(product["near_expiry_days"])

    if days_left <= near_expiry_days:
        return "MEDIUM"

    return "LOW"


def get_product_details(cursor, product_id=None):
    query = """
        SELECT
            p.product_id,
            p.product_name,
            p.category_id,
            c.category_name,
            p.quantity,
            p.unit,
            p.purchase_date,
            p.expiry_date,
            p.storage_temperature,
            c.min_storage_temp,
            c.max_storage_temp,
            c.near_expiry_days,
            p.created_by,
            p.created_at,
            p.is_active
        FROM products p
        JOIN categories c ON p.category_id = c.category_id
        WHERE p.is_active = 1
    """

    if product_id is not None:
        cursor.execute(
            query + " AND p.product_id = %s",
            (product_id,)
        )
        return cursor.fetchone()

    cursor.execute(query + " ORDER BY p.product_id DESC")
    return cursor.fetchall()


def prepare_product(product):
    if not product:
        return product

    for field in ("purchase_date", "expiry_date"):
        if product.get(field):
            product[field] = product[field].isoformat()

    if product.get("created_at"):
        product["created_at"] = product["created_at"].isoformat()

    for field in (
        "storage_temperature",
        "min_storage_temp",
        "max_storage_temp"
    ):
        if product.get(field) is not None:
            product[field] = float(product[field])

    product["priority"] = get_priority(product)
    return product


def add_history(cursor, product_id, activity, details=""):
    cursor.execute(
        """
        INSERT INTO history (product_id, user_id, activity, details)
        VALUES (%s, %s, %s, %s)
        """,
        (product_id, session["user_id"], activity, details)
    )


def parse_product_data(data, updating=False):
    """Validate and prepare product information."""

    product_name = str(data.get("productName", "")).strip()
    category_name = str(data.get("category", "")).strip()
    quantity_value = data.get("quantity")
    unit = str(data.get("unit", "kg")).strip() or "kg"
    purchase_date = data.get("purchaseDate") or None
    expiry_date = data.get("expiryDate")
    temperature = data.get("temperature")

    if not updating or any(
        key in data for key in
        ("productName", "category", "quantity", "expiryDate")
    ):
        if not product_name or not category_name:
            raise ValueError("Product name and category are required.")

        if quantity_value is None or not expiry_date:
            raise ValueError("Quantity and expiry date are required.")

    if updating:
        return {
            "product_name": product_name,
            "category_name": category_name,
            "quantity_value": quantity_value,
            "unit": unit,
            "purchase_date": purchase_date,
            "expiry_date": expiry_date,
            "temperature": temperature
        }

    if len(product_name) > 120 or len(unit) > 20:
        raise ValueError("Product name or unit is too long.")

    quantity = int(quantity_value)

    if quantity <= 0:
        raise ValueError("Quantity must be greater than zero.")

    datetime.strptime(expiry_date, "%Y-%m-%d")

    if purchase_date:
        datetime.strptime(purchase_date, "%Y-%m-%d")

        if purchase_date > expiry_date:
            raise ValueError("Purchase date cannot be after expiry date.")

    if temperature is not None and temperature != "":
        temperature = float(temperature)

        if temperature < -50 or temperature > 100:
            raise ValueError("Enter a valid storage temperature.")
    else:
        temperature = None

    return {
        "product_name": product_name,
        "category_name": category_name,
        "quantity": quantity,
        "unit": unit,
        "purchase_date": purchase_date,
        "expiry_date": expiry_date,
        "temperature": temperature
    }


# --------------------------------------------------
# FRONTEND PAGES AND FILES
# --------------------------------------------------

@app.route("/")
def home():
    return send_from_directory(FRONTEND_FOLDER, "index.html")


@app.route("/<page>.html")
def frontend_pages(page):
    return send_from_directory(FRONTEND_FOLDER, page + ".html")


@app.route("/<path:filename>")
def frontend_static(filename):
    return send_from_directory(FRONTEND_FOLDER, filename)


# --------------------------------------------------
# HEALTH CHECK AND CURRENT USER
# --------------------------------------------------

@app.route("/api/health")
def health():
    connection = get_db_connection()

    if not connection:
        return jsonify({
            "status": "error",
            "message": "Flask is running, but database connection failed."
        }), 500

    connection.close()

    return jsonify({
        "status": "success",
        "message": "Fresh First backend and database are running."
    })


@app.route("/api/me")
@login_required
def current_user():
    return jsonify({
        "status": "success",
        "user": {
            "user_id": session["user_id"],
            "username": session["username"],
            "full_name": session["full_name"],
            "role": session["role"]
        }
    })


# --------------------------------------------------
# LOGIN
# --------------------------------------------------

@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}

    username = str(data.get("username", "")).strip()
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

        session.clear()
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

    except Exception as error:
        print("Login Error:", error)
        return jsonify({
            "status": "error",
            "message": "An error occurred during login."
        }), 500

    finally:
        if cursor:
            cursor.close()
        connection.close()


# --------------------------------------------------
# LOGOUT
# --------------------------------------------------

@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()

    return jsonify({
        "status": "success",
        "message": "Logged out successfully."
    })


# --------------------------------------------------
# STOCK: ADD PRODUCT
# --------------------------------------------------

@app.route("/api/products", methods=["POST"])
@login_required
def add_product():
    data = request.get_json(silent=True) or {}

    try:
        product = parse_product_data(data)
    except (ValueError, TypeError):
        return jsonify({
            "status": "error",
            "message": "Enter valid product details, quantity, dates and temperature."
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
            "SELECT category_id FROM categories WHERE category_name = %s",
            (product["category_name"],)
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
                product_name, category_id, quantity, unit,
                purchase_date, expiry_date,
                storage_temperature, created_by
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                product["product_name"],
                category["category_id"],
                product["quantity"],
                product["unit"],
                product["purchase_date"],
                product["expiry_date"],
                product["temperature"],
                session["user_id"]
            )
        )

        product_id = cursor.lastrowid
        connection.commit()

        return jsonify({
            "status": "success",
            "message": "Product added successfully!",
            "product_id": product_id
        }), 201

    except Exception as error:
        connection.rollback()
        print("Add Product Error:", error)

        return jsonify({
            "status": "error",
            "message": "Unable to add product."
        }), 500

    finally:
        if cursor:
            cursor.close()
        connection.close()


# --------------------------------------------------
# STOCK: VIEW ACTIVE PRODUCTS
# --------------------------------------------------

@app.route("/api/products", methods=["GET"])
@login_required
def get_products():
    connection = get_db_connection()

    if not connection:
        return jsonify({
            "status": "error",
            "message": "Database connection failed."
        }), 500

    cursor = None

    try:
        cursor = connection.cursor(dictionary=True)
        products = get_product_details(cursor)

        for product in products:
            prepare_product(product)

        return jsonify({
            "status": "success",
            "products": products
        })

    except Exception as error:
        print("View Products Error:", error)
        return jsonify({
            "status": "error",
            "message": "Unable to retrieve products."
        }), 500

    finally:
        if cursor:
            cursor.close()
        connection.close()


# --------------------------------------------------
# STOCK: UPDATE PRODUCT
# --------------------------------------------------

@app.route("/api/products/<int:product_id>", methods=["PUT"])
@login_required
def update_product(product_id):
    data = request.get_json(silent=True) or {}

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
            SELECT product_id
            FROM products
            WHERE product_id = %s AND is_active = 1
            """,
            (product_id,)
        )

        existing = cursor.fetchone()

        if not existing:
            return jsonify({
                "status": "error",
                "message": "Active product not found."
            }), 404

        cursor.execute(
            """
            SELECT product_name, category_id, quantity, unit,
                   purchase_date, expiry_date, storage_temperature
            FROM products
            WHERE product_id = %s
            """,
            (product_id,)
        )
        old = cursor.fetchone()

        # Use existing values for fields omitted from the request.
        cursor.execute(
            """
            SELECT category_name
            FROM categories
            WHERE category_id = %s
            """,
            (old["category_id"],)
        )
        old_category = cursor.fetchone()

        merged = {
            "productName": data.get("productName", old["product_name"]),
            "category": data.get(
                "category",
                old_category["category_name"]
            ),
            "quantity": data.get("quantity", old["quantity"]),
            "unit": data.get("unit", old["unit"]),
            "purchaseDate": data.get(
                "purchaseDate",
                old["purchase_date"].isoformat()
                if old["purchase_date"] else None
            ),
            "expiryDate": data.get(
                "expiryDate",
                old["expiry_date"].isoformat()
            ),
            "temperature": data.get(
                "temperature",
                old["storage_temperature"]
            )
        }

        try:
            product = parse_product_data(merged)
        except (ValueError, TypeError):
            return jsonify({
                "status": "error",
                "message": "Invalid product details. Check quantity, dates and temperature."
            }), 400

        cursor.execute(
            """
            SELECT category_id
            FROM categories
            WHERE category_name = %s
            """,
            (product["category_name"],)
        )
        category = cursor.fetchone()

        if not category:
            return jsonify({
                "status": "error",
                "message": "Selected category does not exist."
            }), 400

        cursor.execute(
            """
            UPDATE products
            SET product_name = %s,
                category_id = %s,
                quantity = %s,
                unit = %s,
                purchase_date = %s,
                expiry_date = %s,
                storage_temperature = %s
            WHERE product_id = %s AND is_active = 1
            """,
            (
                product["product_name"],
                category["category_id"],
                product["quantity"],
                product["unit"],
                product["purchase_date"],
                product["expiry_date"],
                product["temperature"],
                product_id
            )
        )

        connection.commit()

        return jsonify({
            "status": "success",
            "message": "Product updated successfully!",
            "product_id": product_id
        })

    except Exception as error:
        connection.rollback()
        print("Update Product Error:", error)

        return jsonify({
            "status": "error",
            "message": "Unable to update product."
        }), 500

    finally:
        if cursor:
            cursor.close()
        connection.close()


# --------------------------------------------------
# STOCK: ARCHIVE PRODUCT (SOFT DELETE)
# --------------------------------------------------

@app.route("/api/products/<int:product_id>", methods=["DELETE"])
@login_required
def archive_product(product_id):
    connection = get_db_connection()

    if not connection:
        return jsonify({
            "status": "error",
            "message": "Database connection failed."
        }), 500

    cursor = None

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE products
            SET is_active = 0
            WHERE product_id = %s AND is_active = 1
            """,
            (product_id,)
        )

        if cursor.rowcount == 0:
            connection.rollback()
            return jsonify({
                "status": "error",
                "message": "Active product not found."
            }), 404

        connection.commit()

        return jsonify({
            "status": "success",
            "message": "Product archived successfully.",
            "product_id": product_id
        })

    except Exception as error:
        connection.rollback()
        print("Archive Product Error:", error)

        return jsonify({
            "status": "error",
            "message": "Unable to archive product."
        }), 500

    finally:
        if cursor:
            cursor.close()
        connection.close()


# --------------------------------------------------
# CATEGORIES: VIEW AND ADD
# --------------------------------------------------

@app.route("/api/categories", methods=["GET"])
@login_required
def get_categories():
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
            SELECT category_id, category_name,
                   min_storage_temp, max_storage_temp, near_expiry_days
            FROM categories
            ORDER BY category_name
            """
        )

        categories = cursor.fetchall()

        for category in categories:
            category["min_storage_temp"] = float(
                category["min_storage_temp"]
            )
            category["max_storage_temp"] = float(
                category["max_storage_temp"]
            )

        return jsonify({
            "status": "success",
            "categories": categories
        })

    except Exception as error:
        print("Categories Error:", error)
        return jsonify({
            "status": "error",
            "message": "Unable to retrieve categories."
        }), 500

    finally:
        if cursor:
            cursor.close()
        connection.close()


@app.route("/api/categories", methods=["POST"])
@admin_required
def add_category():
    data = request.get_json(silent=True) or {}

    name = str(data.get("categoryName", "")).strip()
    temperature = data.get("storageTemperature")

    if not name or temperature is None:
        return jsonify({
            "status": "error",
            "message": "Category name and storage temperature are required."
        }), 400

    if len(name) > 60:
        return jsonify({
            "status": "error",
            "message": "Category name is too long."
        }), 400

    try:
        temperature = float(temperature)

        if temperature < -50 or temperature > 100:
            raise ValueError

    except (ValueError, TypeError):
        return jsonify({
            "status": "error",
            "message": "Enter a valid storage temperature."
        }), 400

    connection = get_db_connection()

    if not connection:
        return jsonify({
            "status": "error",
            "message": "Database connection failed."
        }), 500

    cursor = None

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO categories
            (category_name, min_storage_temp, max_storage_temp)
            VALUES (%s, %s, %s)
            """,
            (name, temperature, temperature)
        )

        connection.commit()

        return jsonify({
            "status": "success",
            "message": "Category added successfully!",
            "category_id": cursor.lastrowid
        }), 201

    except Exception as error:
        connection.rollback()
        print("Add Category Error:", error)

        return jsonify({
            "status": "error",
            "message": "Unable to add category. It may already exist."
        }), 400

    finally:
        if cursor:
            cursor.close()
        connection.close()


# --------------------------------------------------
# DASHBOARD
# --------------------------------------------------

@app.route("/api/dashboard", methods=["GET"])
@login_required
def dashboard():
    connection = get_db_connection()

    if not connection:
        return jsonify({
            "status": "error",
            "message": "Database connection failed."
        }), 500

    cursor = None

    try:
        cursor = connection.cursor(dictionary=True)
        products = get_product_details(cursor)

        total = len(products)
        critical = 0
        high = 0
        expired = 0
        warning = 0

        for product in products:
            priority = get_priority(product)

            if priority == "CRITICAL":
                critical += 1
            elif priority == "HIGH":
                high += 1

            expiry = product["expiry_date"]

            if expiry < date.today():
                expired += 1

            if priority in (
                "CRITICAL", "HIGH", "MEDIUM", "INSPECTION"
            ):
                warning += 1

        return jsonify({
            "status": "success",
            "totalProducts": total,
            "criticalProducts": critical,
            "highProducts": high,
            "expiredProducts": expired,
            "warningProducts": warning
        })

    except Exception as error:
        print("Dashboard Error:", error)
        return jsonify({
            "status": "error",
            "message": "Unable to load dashboard."
        }), 500

    finally:
        if cursor:
            cursor.close()
        connection.close()


# --------------------------------------------------
# VERIFICATION
# --------------------------------------------------

@app.route("/api/verifications", methods=["GET", "POST"])
@login_required
def verifications():
    connection = get_db_connection()

    if not connection:
        return jsonify({
            "status": "error",
            "message": "Database connection failed."
        }), 500

    cursor = None

    try:
        cursor = connection.cursor(dictionary=True)

        if request.method == "GET":
            cursor.execute(
                """
                SELECT v.verification_id, v.product_id,
                       p.product_name, v.actual_temperature,
                       v.verification_status, v.remarks, v.verified_at,
                       u.full_name AS verified_by_name
                FROM verifications v
                JOIN products p ON p.product_id = v.product_id
                JOIN users u ON u.user_id = v.verified_by
                ORDER BY v.verification_id DESC
                """
            )

            records = cursor.fetchall()

            for record in records:
                if record["actual_temperature"] is not None:
                    record["actual_temperature"] = float(
                        record["actual_temperature"]
                    )

                if record["verified_at"]:
                    record["verified_at"] = record[
                        "verified_at"
                    ].isoformat()

            return jsonify({
                "status": "success",
                "verifications": records
            })

        data = request.get_json(silent=True) or {}

        product_id = data.get("product_id")
        product_name = str(data.get("productName", "")).strip()
        actual_temperature = data.get("temperature")

        try:
            actual_temperature = float(actual_temperature)

            if not -50 <= actual_temperature <= 100:
                raise ValueError

        except (ValueError, TypeError):
            return jsonify({
                "status": "error",
                "message": "Enter a valid actual temperature."
            }), 400

        if product_id:
            try:
                product_id = int(product_id)
            except (ValueError, TypeError):
                return jsonify({
                    "status": "error",
                    "message": "Invalid product ID."
                }), 400

            product = get_product_details(cursor, product_id)

        elif product_name:
            cursor.execute(
                """
                SELECT product_id
                FROM products
                WHERE product_name = %s AND is_active = 1
                ORDER BY product_id DESC
                LIMIT 1
                """,
                (product_name,)
            )

            found = cursor.fetchone()
            product = (
                get_product_details(cursor, found["product_id"])
                if found else None
            )

        else:
            product = None

        if not product:
            return jsonify({
                "status": "error",
                "message": "Active product not found."
            }), 404

        expiry = product["expiry_date"]
        today = date.today()
        days_left = (expiry - today).days

        minimum = float(product["min_storage_temp"])
        maximum = float(product["max_storage_temp"])

        if days_left < 0:
            status = "UNSAFE"
            remarks = "Product has expired."

        elif (
            actual_temperature < minimum
            or actual_temperature > maximum
        ):
            status = "WARNING"
            remarks = "Actual temperature is outside the category storage range."

        elif days_left <= int(product["near_expiry_days"]):
            status = "WARNING"
            remarks = "Product is near expiry."

        else:
            status = "SAFE"
            remarks = "Product is within the expiry and temperature limits."

        user_remarks = str(data.get("remarks", "")).strip()

        if user_remarks:
            remarks += " " + user_remarks

        remarks = remarks[:255]

        cursor.execute(
            """
            INSERT INTO verifications
            (
                product_id, verified_by, actual_temperature,
                verification_status, remarks
            )
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                product["product_id"],
                session["user_id"],
                actual_temperature,
                status,
                remarks
            )
        )

        add_history(
            cursor,
            product["product_id"],
            "PRODUCT VERIFIED",
            "Verification result: " + status
        )

        connection.commit()

        return jsonify({
            "status": "success",
            "message": "Product verification completed.",
            "verification_status": status,
            "remarks": remarks
        }), 201

    except Exception as error:
        connection.rollback()
        print("Verification Error:", error)

        return jsonify({
            "status": "error",
            "message": "Unable to process verification."
        }), 500

    finally:
        if cursor:
            cursor.close()
        connection.close()


# --------------------------------------------------
# PRIORITY
# --------------------------------------------------

@app.route("/api/priority", methods=["GET"])
@login_required
def priority_list():
    connection = get_db_connection()

    if not connection:
        return jsonify({
            "status": "error",
            "message": "Database connection failed."
        }), 500

    cursor = None

    try:
        cursor = connection.cursor(dictionary=True)
        products = get_product_details(cursor)

        result = []

        for product in products:
            prepared = prepare_product(product)
            result.append(prepared)

        filter_value = request.args.get("priority", "").upper()

        if filter_value:
            if filter_value == "INSPECTION NEEDED":
                filter_value = "INSPECTION"

            result = [
                product for product in result
                if product["priority"] == filter_value
            ]

        order = {
            "CRITICAL": 1,
            "HIGH": 2,
            "MEDIUM": 3,
            "INSPECTION": 4,
            "LOW": 5
        }

        result.sort(
            key=lambda product: order.get(product["priority"], 6)
        )

        return jsonify({
            "status": "success",
            "products": result
        })

    except Exception as error:
        print("Priority Error:", error)
        return jsonify({
            "status": "error",
            "message": "Unable to calculate priorities."
        }), 500

    finally:
        if cursor:
            cursor.close()
        connection.close()


# --------------------------------------------------
# ACTIONS: VIEW AND CREATE
# --------------------------------------------------

@app.route("/api/actions", methods=["GET", "POST"])
@login_required
def actions():
    connection = get_db_connection()

    if not connection:
        return jsonify({
            "status": "error",
            "message": "Database connection failed."
        }), 500

    cursor = None

    try:
        cursor = connection.cursor(dictionary=True)

        if request.method == "GET":
            cursor.execute(
                """
                SELECT a.action_id, a.product_id, p.product_name,
                       a.assigned_to, u.full_name AS assigned_to_name,
                       a.action_type, a.priority, a.action_status,
                       a.description, a.created_at, a.completed_at
                FROM actions a
                JOIN products p ON p.product_id = a.product_id
                LEFT JOIN users u ON u.user_id = a.assigned_to
                ORDER BY a.action_id DESC
                """
            )

            records = cursor.fetchall()

            for record in records:
                for field in ("created_at", "completed_at"):
                    if record.get(field):
                        record[field] = record[field].isoformat()

            return jsonify({
                "status": "success",
                "actions": records
            })

        data = request.get_json(silent=True) or {}

        product_id = data.get("product_id")
        product_name = str(data.get("productName", "")).strip()

        action_type = str(
            data.get("action_type", data.get("suggestedAction", ""))
        ).strip()

        description = str(
            data.get("description", data.get("remarks", ""))
        ).strip()

        if not action_type:
            return jsonify({
                "status": "error",
                "message": "Select an action."
            }), 400

        if len(action_type) > 100 or len(description) > 255:
            return jsonify({
                "status": "error",
                "message": "Action details are too long."
            }), 400

        if product_id:
            try:
                product_id = int(product_id)
            except (ValueError, TypeError):
                return jsonify({
                    "status": "error",
                    "message": "Invalid product ID."
                }), 400

            product = get_product_details(cursor, product_id)

        elif product_name:
            cursor.execute(
                """
                SELECT product_id
                FROM products
                WHERE product_name = %s AND is_active = 1
                ORDER BY product_id DESC
                LIMIT 1
                """,
                (product_name,)
            )

            found = cursor.fetchone()

            product = (
                get_product_details(cursor, found["product_id"])
                if found else None
            )

        else:
            product = None

        if not product:
            return jsonify({
                "status": "error",
                "message": "Active product not found."
            }), 404

        priority = get_priority(product)

        cursor.execute(
            """
            INSERT INTO actions
            (
                product_id, assigned_to, action_type,
                priority, description
            )
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                product["product_id"],
                session["user_id"],
                action_type,
                priority,
                description
            )
        )

        action_id = cursor.lastrowid

        add_history(
            cursor,
            product["product_id"],
            "ACTION CREATED",
            action_type
        )

        connection.commit()

        return jsonify({
            "status": "success",
            "message": "Action created successfully!",
            "action_id": action_id
        }), 201

    except Exception as error:
        connection.rollback()
        print("Actions Error:", error)

        return jsonify({
            "status": "error",
            "message": "Unable to process action."
        }), 500

    finally:
        if cursor:
            cursor.close()
        connection.close()


# --------------------------------------------------
# ACTIONS: UPDATE STATUS
# --------------------------------------------------

@app.route("/api/actions/<int:action_id>", methods=["PUT"])
@login_required
def update_action(action_id):
    data = request.get_json(silent=True) or {}

    new_status = str(
        data.get("action_status", data.get("status", ""))
    ).upper()

    if new_status not in ("PENDING", "IN_PROGRESS", "DONE"):
        return jsonify({
            "status": "error",
            "message": "Invalid action status."
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
            "SELECT product_id FROM actions WHERE action_id = %s",
            (action_id,)
        )

        action = cursor.fetchone()

        if not action:
            return jsonify({
                "status": "error",
                "message": "Action not found."
            }), 404

        completed_at = (
            datetime.now() if new_status == "DONE" else None
        )

        cursor.execute(
            """
            UPDATE actions
            SET action_status = %s, completed_at = %s
            WHERE action_id = %s
            """,
            (new_status, completed_at, action_id)
        )

        add_history(
            cursor,
            action["product_id"],
            "ACTION STATUS UPDATED",
            "Action " + str(action_id) + " changed to " + new_status
        )

        connection.commit()

        return jsonify({
            "status": "success",
            "message": "Action status updated."
        })

    except Exception as error:
        connection.rollback()
        print("Update Action Error:", error)

        return jsonify({
            "status": "error",
            "message": "Unable to update action."
        }), 500

    finally:
        if cursor:
            cursor.close()
        connection.close()


# --------------------------------------------------
# HISTORY
# --------------------------------------------------

@app.route("/api/history", methods=["GET"])
@login_required
def get_history():
    connection = get_db_connection()

    if not connection:
        return jsonify({
            "status": "error",
            "message": "Database connection failed."
        }), 500

    cursor = None

    try:
        cursor = connection.cursor(dictionary=True)
        search = request.args.get("search", "").strip()

        query = """
            SELECT h.history_id, h.product_id, p.product_name,
                   h.user_id, u.full_name, h.activity,
                   h.details, h.activity_time
            FROM history h
            JOIN products p ON p.product_id = h.product_id
            JOIN users u ON u.user_id = h.user_id
        """

        if search:
            query += """
                WHERE p.product_name LIKE %s
                   OR h.activity LIKE %s
                   OR h.details LIKE %s
                   OR u.full_name LIKE %s
            """

            value = "%" + search + "%"

            cursor.execute(
                query + " ORDER BY h.activity_time DESC",
                (value, value, value, value)
            )

        else:
            cursor.execute(
                query + " ORDER BY h.activity_time DESC"
            )

        records = cursor.fetchall()

        for record in records:
            if record["activity_time"]:
                record["activity_time"] = record[
                    "activity_time"
                ].isoformat()

        return jsonify({
            "status": "success",
            "history": records
        })

    except Exception as error:
        print("History Error:", error)

        return jsonify({
            "status": "error",
            "message": "Unable to retrieve history."
        }), 500

    finally:
        if cursor:
            cursor.close()
        connection.close()


# --------------------------------------------------
# USERS: VIEW AND CREATE
# --------------------------------------------------

@app.route("/api/users", methods=["GET", "POST"])
@admin_required
def users():
    connection = get_db_connection()

    if not connection:
        return jsonify({
            "status": "error",
            "message": "Database connection failed."
        }), 500

    cursor = None

    try:
        cursor = connection.cursor(dictionary=True)

        if request.method == "GET":
            cursor.execute(
                """
                SELECT user_id, full_name, username, role, created_at
                FROM users
                ORDER BY user_id
                """
            )

            records = cursor.fetchall()

            for record in records:
                if record["created_at"]:
                    record["created_at"] = record[
                        "created_at"
                    ].isoformat()

            return jsonify({
                "status": "success",
                "users": records
            })

        data = request.get_json(silent=True) or {}

        full_name = str(
            data.get("fullName", data.get("full_name", ""))
        ).strip()

        username = str(data.get("username", "")).strip()
        password = data.get("password", "")
        role_input = str(data.get("role", "STAFF")).strip().upper()

        role_map = {
            "ADMIN": "ADMIN",
            "MANAGER": "MANAGER",
            "STORE MANAGER": "MANAGER",
            "STAFF": "STAFF"
        }

        role = role_map.get(role_input)

        if not full_name or not username or not password or not role:
            return jsonify({
                "status": "error",
                "message": "Enter valid user details and role."
            }), 400

        if (
            len(full_name) > 100
            or len(username) > 50
            or len(password) < 6
        ):
            return jsonify({
                "status": "error",
                "message": "Check name, username and password length. Password must be at least 6 characters."
            }), 400

        password_hash = generate_password_hash(password)

        cursor.execute(
            """
            INSERT INTO users (full_name, username, password_hash, role)
            VALUES (%s, %s, %s, %s)
            """,
            (full_name, username, password_hash, role)
        )

        user_id = cursor.lastrowid
        connection.commit()

        return jsonify({
            "status": "success",
            "message": "User created successfully!",
            "user_id": user_id
        }), 201

    except Exception as error:
        connection.rollback()
        print("Users Error:", error)

        return jsonify({
            "status": "error",
            "message": "Unable to process user. Username may already exist."
        }), 400

    finally:
        if cursor:
            cursor.close()
        connection.close()


# --------------------------------------------------
# REPORTS
# --------------------------------------------------

@app.route("/api/reports", methods=["GET", "POST"])
@login_required
def reports():
    data = request.get_json(silent=True) or {}

    report_type = str(
        request.args.get("type")
        or data.get("reportType", "Stock Report")
    ).strip().lower()

    from_date = request.args.get("fromDate") or data.get("fromDate")
    to_date = request.args.get("toDate") or data.get("toDate")

    # Validate supplied dates.
    try:
        if from_date:
            datetime.strptime(from_date, "%Y-%m-%d")

        if to_date:
            datetime.strptime(to_date, "%Y-%m-%d")

        if from_date and to_date and from_date > to_date:
            raise ValueError

    except (ValueError, TypeError):
        return jsonify({
            "status": "error",
            "message": "Enter valid report dates."
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

        if report_type == "stock report":
            query = """
                SELECT p.product_id, p.product_name, c.category_name,
                       p.quantity, p.unit, p.purchase_date,
                       p.expiry_date, p.storage_temperature
                FROM products p
                JOIN categories c ON c.category_id = p.category_id
                WHERE p.is_active = 1
            """

            params = []

            if from_date:
                query += " AND p.created_at >= %s"
                params.append(from_date + " 00:00:00")

            if to_date:
                query += " AND p.created_at <= %s"
                params.append(to_date + " 23:59:59")

            cursor.execute(
                query + " ORDER BY p.product_id DESC",
                tuple(params)
            )

            records = cursor.fetchall()

        elif report_type == "expiry report":
            query = """
                SELECT p.product_id, p.product_name, c.category_name,
                       p.quantity, p.unit, p.expiry_date
                FROM products p
                JOIN categories c ON c.category_id = p.category_id
                WHERE p.is_active = 1
            """

            params = []

            if from_date:
                query += " AND p.expiry_date >= %s"
                params.append(from_date)

            if to_date:
                query += " AND p.expiry_date <= %s"
                params.append(to_date)

            cursor.execute(
                query + " ORDER BY p.expiry_date",
                tuple(params)
            )

            records = cursor.fetchall()

        elif report_type == "verification report":
            query = """
                SELECT v.verification_id, p.product_name,
                       v.actual_temperature, v.verification_status,
                       v.remarks, v.verified_at,
                       u.full_name AS verified_by
                FROM verifications v
                JOIN products p ON p.product_id = v.product_id
                JOIN users u ON u.user_id = v.verified_by
                WHERE 1=1
            """

            params = []

            if from_date:
                query += " AND v.verified_at >= %s"
                params.append(from_date + " 00:00:00")

            if to_date:
                query += " AND v.verified_at <= %s"
                params.append(to_date + " 23:59:59")

            cursor.execute(
                query + " ORDER BY v.verified_at DESC",
                tuple(params)
            )

            records = cursor.fetchall()

        elif report_type == "priority report":
            products = get_product_details(cursor)
            records = []

            for product in products:
                expiry = product["expiry_date"]

                if from_date and expiry.isoformat() < from_date:
                    continue

                if to_date and expiry.isoformat() > to_date:
                    continue

                records.append({
                    "product_id": product["product_id"],
                    "product_name": product["product_name"],
                    "quantity": product["quantity"],
                    "expiry_date": expiry,
                    "priority": get_priority(product)
                })

        else:
            return jsonify({
                "status": "error",
                "message": "Invalid report type."
            }), 400

        for record in records:
            for key, value in record.items():
                if isinstance(value, (date, datetime)):
                    record[key] = value.isoformat()

                elif key in (
                    "actual_temperature",
                    "storage_temperature"
                ):
                    if value is not None:
                        record[key] = float(value)

        return jsonify({
            "status": "success",
            "reportType": report_type,
            "count": len(records),
            "records": records
        })

    except Exception as error:
        print("Reports Error:", error)

        return jsonify({
            "status": "error",
            "message": "Unable to generate report."
        }), 500

    finally:
        if cursor:
            cursor.close()
        connection.close()


# --------------------------------------------------
# SETTINGS
# Requires the separate app_settings table.
# --------------------------------------------------

@app.route("/api/settings", methods=["GET", "PUT"])
@admin_required
def settings():
    connection = get_db_connection()

    if not connection:
        return jsonify({
            "status": "error",
            "message": "Database connection failed."
        }), 500

    cursor = None

    try:
        cursor = connection.cursor(dictionary=True)

        if request.method == "GET":
            cursor.execute(
                "SELECT setting_key, setting_value FROM app_settings"
            )

            rows = cursor.fetchall()

            values = {
                row["setting_key"]: row["setting_value"]
                for row in rows
            }

            return jsonify({
                "status": "success",
                "settings": values
            })

        data = request.get_json(silent=True) or {}

        allowed = (
            "expiryThreshold",
            "criticalThreshold",
            "defaultTemperature"
        )

        for key in allowed:
            if key not in data:
                continue

            value = str(data[key]).strip()

            if not value:
                return jsonify({
                    "status": "error",
                    "message": "Setting values cannot be empty."
                }), 400

            cursor.execute(
                """
                INSERT INTO app_settings (setting_key, setting_value)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE
                setting_value = VALUES(setting_value)
                """,
                (key, value)
            )

        connection.commit()

        return jsonify({
            "status": "success",
            "message": "Settings saved successfully."
        })

    except Exception as error:
        connection.rollback()
        print("Settings Error:", error)

        return jsonify({
            "status": "error",
            "message": "Unable to access settings. Check that the app_settings table has been created."
        }), 500

    finally:
        if cursor:
            cursor.close()
        connection.close()


# --------------------------------------------------
# RUN APPLICATION
# --------------------------------------------------

if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )
