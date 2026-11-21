
from flask import Flask, request, jsonify, session, send_from_directory
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps
from db import get_db_connection
from datetime import datetime, date
import os
import math

app = Flask(__name__)

# --------------------------------------------------
# APPLICATION CONFIGURATION
# --------------------------------------------------

app.secret_key = os.environ.get("FRESHFIRST_SECRET_KEY")

if not app.secret_key:
    raise RuntimeError("FRESHFIRST_SECRET_KEY environment variable is not set.")
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax"
)

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
        INSERT INTO history
        (product_id, user_id, activity, details)
        VALUES (%s, %s, %s, %s)
        """,
        (
            product_id,
            session["user_id"],
            activity,
            details
        )
    )


# --------------------------------------------------
# PRODUCT VALIDATION
# --------------------------------------------------


def parse_product_data(data):
    product_name = str(data.get("productName", "")).strip()
    category_name = str(data.get("category", "")).strip()

    quantity_value = data.get("quantity")
    unit = str(data.get("unit", "kg")).strip() or "kg"

    purchase_date = data.get("purchaseDate") or None
    expiry_date = data.get("expiryDate")

    # Accept both API field names.
    temperature = data.get(
        "storageTemperature",
        data.get("temperature")
    )

    if not product_name or not category_name:
        raise ValueError("Product name and category are required.")

    if quantity_value is None or not expiry_date:
        raise ValueError("Quantity and expiry date are required.")

    if len(product_name) > 120 or len(unit) > 20:
        raise ValueError("Product name or unit is too long.")

    if isinstance(quantity_value, bool):
        raise ValueError("Quantity must be a whole number.")

    quantity_text = str(quantity_value).strip()

    if not quantity_text.isdigit():
        raise ValueError("Quantity must be a positive whole number.")

    quantity = int(quantity_text)

    if quantity <= 0:
        raise ValueError("Quantity must be greater than zero.")

    try:
        expiry_object = datetime.strptime(
            expiry_date, "%Y-%m-%d"
        ).date()

        if purchase_date:
            purchase_object = datetime.strptime(
                purchase_date, "%Y-%m-%d"
            ).date()

            if purchase_object > expiry_object:
                raise ValueError(
                    "Purchase date cannot be after expiry date."
                )

    except (ValueError, TypeError):
        raise ValueError("Enter valid purchase and expiry dates.")

    if temperature is not None and temperature != "":
        try:
            temperature = float(temperature)

            if not math.isfinite(temperature):
                raise ValueError

            if temperature < -50 or temperature > 100:
                raise ValueError

        except (ValueError, TypeError):
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
    return send_from_directory(
        FRONTEND_FOLDER,
        page + ".html"
    )


@app.route("/<path:filename>")
def frontend_static(filename):
    return send_from_directory(
        FRONTEND_FOLDER,
        filename
    )


# --------------------------------------------------
# HEALTH CHECK
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


# --------------------------------------------------
# CURRENT USER
# --------------------------------------------------

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

    if not username or not isinstance(password, str) or not password:
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
            INSERT INTO products
            (
                product_name,
                category_id,
                quantity,
                unit,
                purchase_date,
                expiry_date,
                storage_temperature,
                created_by
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
            SELECT product_name, category_id, quantity, unit,
                   purchase_date, expiry_date, storage_temperature
            FROM products
            WHERE product_id = %s AND is_active = 1
            """,
            (product_id,)
        )

        old = cursor.fetchone()

        if not old:
            return jsonify({
                "status": "error",
                "message": "Active product not found."
            }), 404

        cursor.execute(
            """
            SELECT category_name
            FROM categories
            WHERE category_id = %s
            """,
            (old["category_id"],)
        )

        old_category = cursor.fetchone()

        if not old_category:
            return jsonify({
                "status": "error",
                "message": "Product category not found."
            }), 400

        merged = {
            "productName": data.get(
                "productName", old["product_name"]
            ),
            "category": data.get(
                "category", old_category["category_name"]
            ),
            "quantity": data.get(
                "quantity", old["quantity"]
            ),
            "unit": data.get(
                "unit", old["unit"]
            ),
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
                "temperature", old["storage_temperature"]
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
# CATEGORIES: VIEW
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
            SELECT
                category_id,
                category_name,
                min_storage_temp,
                max_storage_temp,
                near_expiry_days
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


# --------------------------------------------------
# CATEGORIES: ADD
# --------------------------------------------------

@app.route("/api/categories", methods=["POST"])
@admin_required
def add_category():
    data = request.get_json(silent=True) or {}

    name = str(data.get("categoryName", "")).strip()

    min_temperature = data.get("minStorageTemp")
    max_temperature = data.get("maxStorageTemp")

    # Support the existing frontend format.
    if min_temperature is None and max_temperature is None:
        old_temperature = data.get("storageTemperature")
        min_temperature = old_temperature
        max_temperature = old_temperature

    if (
        not name
        or min_temperature is None
        or max_temperature is None
    ):
        return jsonify({
            "status": "error",
            "message": "Category name and temperature limits are required."
        }), 400

    if len(name) > 60:
        return jsonify({
            "status": "error",
            "message": "Category name is too long."
        }), 400

    try:
        min_temperature = float(min_temperature)
        max_temperature = float(max_temperature)

        if (
            not math.isfinite(min_temperature)
            or not math.isfinite(max_temperature)
            or min_temperature < -50
            or max_temperature > 100
            or min_temperature > max_temperature
        ):
            raise ValueError

    except (ValueError, TypeError):
        return jsonify({
            "status": "error",
            "message": "Enter valid temperature limits. Minimum cannot exceed maximum."
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
            (
                category_name,
                min_storage_temp,
                max_storage_temp
            )
            VALUES (%s, %s, %s)
            """,
            (
                name,
                min_temperature,
                max_temperature
            )
        )

        category_id = cursor.lastrowid

        connection.commit()

        return jsonify({
            "status": "success",
            "message": "Category added successfully!",
            "category_id": category_id
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

        today = date.today()

        for product in products:
            priority = get_priority(product)

            if priority == "CRITICAL":
                critical += 1

            elif priority == "HIGH":
                high += 1

            expiry = product["expiry_date"]

            if expiry < today:
                expired += 1

            if priority in (
                "CRITICAL",
                "HIGH",
                "MEDIUM",
                "INSPECTION"
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


# ============================================================
# PART 4: VERIFICATION AND PRIORITY MANAGEMENT
# ============================================================

@app.route("/api/verifications", methods=["GET", "POST"])
@login_required
def manage_verifications():

    # GET: Display verification records
    if request.method == "GET":
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        try:
            cursor.execute("""
                SELECT
                    v.verification_id,
                    v.product_id,
                    p.product_name,
                    v.actual_temperature,
                    v.verification_status AS status,
                    v.remarks,
                    v.verified_at,
                    u.full_name AS verified_by
                FROM verifications v
                LEFT JOIN products p ON v.product_id = p.product_id
                LEFT JOIN users u ON v.verified_by = u.user_id
                ORDER BY v.verified_at DESC
            """)

            records = cursor.fetchall()

            for record in records:
                if record.get("verified_at"):
                    record["verified_at"] = record["verified_at"].isoformat(
                        sep=" ", timespec="seconds"
                    )

            return jsonify({
                "status": "success",
                "verifications": records
            })

        except Exception as error:
            return jsonify({
                "status": "error",
                "message": str(error)
            }), 500

        finally:
            cursor.close()
            connection.close()

    # POST: Add a new verification
    data = request.get_json(silent=True) or {}

    product_id = data.get("product_id") or data.get("productId")
    product_name = data.get("product_name") or data.get("productName")
    actual_temperature = (
        data.get("actualTemperature")
        if data.get("actualTemperature") is not None
        else data.get("temperature", data.get("actual_temperature"))
    )
    quantity_value = data.get("quantity")
    remarks = str(data.get("remarks", "")).strip()[:255]

    verified_quantity = None
    if quantity_value not in (None, ""):
        try:
            if isinstance(quantity_value, bool):
                raise ValueError
            verified_quantity = float(quantity_value)
            if not math.isfinite(verified_quantity) or verified_quantity <= 0:
                raise ValueError
        except (ValueError, TypeError):
            return jsonify({
                "status": "error",
                "message": "Enter a valid quantity greater than zero."
            }), 400

    if actual_temperature is None:
        return jsonify({
            "status": "error",
            "message": "Actual temperature is required."
        }), 400

    try:
        if isinstance(actual_temperature, bool):
            raise ValueError

        actual_temperature = float(actual_temperature)

        if not math.isfinite(actual_temperature):
            raise ValueError

        if actual_temperature < -50 or actual_temperature > 100:
            raise ValueError

    except (ValueError, TypeError):
        return jsonify({
            "status": "error",
            "message": "Enter a valid temperature between -50 and 100."
        }), 400

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        if product_id:
            cursor.execute("""
                SELECT
                    p.product_id,
                    p.product_name,
                    p.quantity,
                    p.expiry_date,
                    c.min_storage_temp,
                    c.max_storage_temp,
                    c.near_expiry_days
                FROM products p
                JOIN categories c ON p.category_id = c.category_id
                WHERE p.product_id = %s AND p.is_active = 1
            """, (product_id,))

        elif product_name:
            cursor.execute("""
                SELECT
                    p.product_id,
                    p.product_name,
                    p.quantity,
                    p.expiry_date,
                    c.min_storage_temp,
                    c.max_storage_temp,
                    c.near_expiry_days
                FROM products p
                JOIN categories c ON p.category_id = c.category_id
                WHERE p.product_name = %s AND p.is_active = 1
                LIMIT 1
            """, (product_name,))

        else:
            return jsonify({
                "status": "error",
                "message": "Select a product to verify."
            }), 400

        product = cursor.fetchone()

        if not product:
            return jsonify({
                "status": "error",
                "message": "Active product not found."
            }), 404

        today = date.today()
        expiry_date = product["expiry_date"]

        if isinstance(expiry_date, datetime):
            expiry_date = expiry_date.date()

        days_left = (expiry_date - today).days

        min_temp = float(product["min_storage_temp"])
        max_temp = float(product["max_storage_temp"])
        near_expiry_days = int(product["near_expiry_days"])

        quantity_mismatch = (
            verified_quantity is not None
            and verified_quantity != float(product["quantity"])
        )

        if days_left < 0:
            verification_status = "UNSAFE"
        elif (
            actual_temperature < min_temp
            or actual_temperature > max_temp
            or days_left <= near_expiry_days
            or quantity_mismatch
        ):
            verification_status = "WARNING"
        else:
            verification_status = "SAFE"

        if quantity_mismatch:
            quantity_note = (
                f"Quantity mismatch: entered {verified_quantity:g}, "
                f"recorded stock {float(product['quantity']):g}."
            )
            remarks = (remarks + " " + quantity_note).strip()[:255]

        cursor.execute("""
            INSERT INTO verifications
            (
                product_id,
                actual_temperature,
                verification_status,
                remarks,
                verified_by
            )
            VALUES (%s, %s, %s, %s, %s)
        """, (
            product["product_id"],
            actual_temperature,
            verification_status,
            remarks,
            session["user_id"]
        ))

        verification_id = cursor.lastrowid

        add_history(
            cursor,
            product["product_id"],
            "PRODUCT VERIFIED",
            "Verification result: " + verification_status
        )

        connection.commit()

        return jsonify({
            "status": "success",
            "message": "Product verification completed.",
            "verification_id": verification_id,
            "verificationStatus": verification_status
        }), 201

    except Exception as error:
        connection.rollback()
        return jsonify({
            "status": "error",
            "message": str(error)
        }), 500

    finally:
        cursor.close()
        connection.close()


# ============================================================
# PRODUCT PRIORITY MANAGEMENT
# ============================================================

@app.route("/api/priority", methods=["GET"])
@login_required
def get_priority_products():

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                p.*,
                c.category_name,
                c.min_storage_temp,
                c.max_storage_temp,
                c.near_expiry_days
            FROM products p
            JOIN categories c ON p.category_id = c.category_id
            WHERE p.is_active = 1
        """)

        products = cursor.fetchall()

        priority_order = {
            "CRITICAL": 1,
            "HIGH": 2,
            "MEDIUM": 3,
            "INSPECTION": 4,
            "LOW": 5
        }

        priority_products = []

        for product in products:
            prepared = prepare_product(product)
            priority_products.append(prepared)

        priority_products.sort(
            key=lambda item: (
                priority_order.get(
                    str(item.get("priority", "LOW")).upper(), 5
                ),
                item.get("daysLeft", 999999)
                if item.get("daysLeft") is not None else 999999
            )
        )

        selected_priority = request.args.get(
            "priority", ""
        ).strip().upper()

        if selected_priority == "INSPECTION NEEDED":
            selected_priority = "INSPECTION"

        if selected_priority:
            priority_products = [
                product for product in priority_products
                if str(product.get("priority", "")).upper()
                == selected_priority
            ]

        return jsonify({
            "status": "success",
            "count": len(priority_products),
            "products": priority_products
        })

    except Exception as error:
        return jsonify({
            "status": "error",
            "message": str(error)
        }), 500

    finally:
        cursor.close()
        connection.close()



# ============================================================
# PART 5: ACTION MANAGEMENT
# ============================================================

@app.route("/api/actions", methods=["GET"])
@login_required
def get_actions():
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                a.action_id,
                a.product_id,
                p.product_name,
                a.assigned_to,
                u.full_name AS assigned_name,
                a.action_type,
                a.priority,
                a.action_status AS status,
                a.action_status,
                a.description,
                a.created_at,
                a.completed_at
            FROM actions a
            LEFT JOIN products p
                ON a.product_id = p.product_id
            LEFT JOIN users u
                ON a.assigned_to = u.user_id
            ORDER BY a.created_at DESC
        """)

        actions = cursor.fetchall()

        return jsonify({
            "status": "success",
            "actions": actions
        }), 200

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@app.route("/api/actions", methods=["POST"])
@login_required
def add_action():
    connection = None
    cursor = None

    try:
        data = request.get_json(silent=True) or {}

        product_id = data.get("productId", data.get("product_id"))
        product_name = data.get("product_name", data.get("productName"))
        action_type = (
            data.get("actionType")
            or data.get("action_type")
            or data.get("suggested_action")
            or data.get("suggestedAction")
        )
        description = data.get("description", data.get("remarks", ""))
        priority = data.get("priority", "MEDIUM")
        assigned_to = data.get("assignedTo", data.get("assigned_to"))

        if (not product_id and not product_name) or not action_type:
            return jsonify({
                "status": "error",
                "message": "Product and suggested action are required."
            }), 400

        try:
            if product_id not in (None, ""):
                product_id = int(product_id)
            else:
                product_id = None
            if assigned_to not in (None, ""):
                assigned_to = int(assigned_to)
            else:
                assigned_to = None
        except (ValueError, TypeError):
            return jsonify({
                "status": "error",
                "message": "Invalid product ID or assigned user ID."
            }), 400

        allowed_priorities = [
            "CRITICAL", "HIGH", "MEDIUM", "LOW", "INSPECTION"
        ]

        priority = str(priority).upper()

        if priority not in allowed_priorities:
            return jsonify({
                "status": "error",
                "message": "Invalid priority."
            }), 400

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        if product_id is not None:
            cursor.execute("""
                SELECT product_id
                FROM products
                WHERE product_id = %s AND is_active = 1
            """, (product_id,))
        else:
            cursor.execute("""
                SELECT product_id
                FROM products
                WHERE product_name = %s AND is_active = 1
                ORDER BY product_id DESC
                LIMIT 1
            """, (str(product_name).strip(),))

        selected_product = cursor.fetchone()
        if not selected_product:
            return jsonify({
                "status": "error",
                "message": "Active product not found."
            }), 404

        product_id = selected_product["product_id"]

        if assigned_to is not None:
            cursor.execute("""
                SELECT user_id
                FROM users
                WHERE user_id = %s
            """, (assigned_to,))

            if not cursor.fetchone():
                return jsonify({
                    "status": "error",
                    "message": "Assigned user not found."
                }), 404

        # Set the actor for optional action-audit database triggers.
        cursor.execute(
            "SET @freshfirst_actor_user_id = %s",
            (session["user_id"],)
        )

        cursor.execute("""
            INSERT INTO actions
            (
                product_id,
                assigned_to,
                action_type,
                priority,
                action_status,
                description
            )
            VALUES (%s, %s, %s, %s, 'PENDING', %s)
        """, (
            product_id,
            assigned_to,
            str(action_type).strip(),
            priority,
            str(description).strip()
        ))

        action_id = cursor.lastrowid
        connection.commit()

        return jsonify({
            "status": "success",
            "message": "Action created successfully.",
            "action_id": action_id
        }), 201

    except Exception as e:
        if connection:
            connection.rollback()

        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@app.route("/api/actions/<int:action_id>", methods=["PUT"])
@login_required
def update_action(action_id):
    connection = None
    cursor = None

    try:
        data = request.get_json(silent=True) or {}

        new_status = data.get(
            "status",
            data.get("action_status")
        )

        allowed_statuses = [
            "PENDING", "IN_PROGRESS", "DONE"
        ]

        if not new_status:
            return jsonify({
                "status": "error",
                "message": "Action status is required."
            }), 400

        new_status = str(new_status).upper()

        if new_status not in allowed_statuses:
            return jsonify({
                "status": "error",
                "message": "Invalid action status."
            }), 400

        connection = get_db_connection()
        cursor = connection.cursor()

        # Set the actor for optional action-audit database triggers.
        cursor.execute(
            "SET @freshfirst_actor_user_id = %s",
            (session["user_id"],)
        )

        cursor.execute("""
            UPDATE actions
            SET
                action_status = %s,
                completed_at = CASE
                    WHEN %s = 'DONE' THEN CURRENT_TIMESTAMP
                    ELSE NULL
                END
            WHERE action_id = %s
        """, (new_status, new_status, action_id))

        if cursor.rowcount == 0:
            connection.rollback()

            return jsonify({
                "status": "error",
                "message": "Action not found."
            }), 404

        connection.commit()

        return jsonify({
            "status": "success",
            "message": "Action updated successfully."
        }), 200

    except Exception as e:
        if connection:
            connection.rollback()

        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


# ============================================================
# PART 6: USER AND HISTORY MANAGEMENT
# ============================================================


# -------------------- HISTORY API --------------------

@app.route("/api/history", methods=["GET"])
@login_required
def get_history():

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                h.history_id,
                h.product_id,
                p.product_name,
                h.user_id,
                u.full_name AS user_name,
                h.activity,
                h.details,
                h.activity_time
            FROM history h
            LEFT JOIN products p
                ON h.product_id = p.product_id
            LEFT JOIN users u
                ON h.user_id = u.user_id
            ORDER BY h.activity_time DESC
        """)

        history_records = cursor.fetchall()

        return jsonify({
            "status": "success",
            "history": history_records
        }), 200

    except Exception as e:

        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# -------------------- USERS API --------------------

@app.route("/api/users", methods=["GET"])
@admin_required
def get_users():

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                user_id,
                full_name,
                username,
                role
            FROM users
            ORDER BY user_id DESC
        """)

        users = cursor.fetchall()

        return jsonify({
            "status": "success",
            "users": users
        }), 200

    except Exception as e:

        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


@app.route("/api/users", methods=["POST"])
@admin_required
def add_user():

    connection = None
    cursor = None

    try:
        data = request.get_json(silent=True) or {}

        full_name = str(
            data.get("fullName", data.get("full_name", ""))
        ).strip()

        username = str(
            data.get("username", "")
        ).strip()

        password = data.get("password", "")

        role = str(
            data.get("role", "STAFF")
        ).strip().upper()

        allowed_roles = ["ADMIN", "MANAGER", "STAFF"]

        if not full_name or not username or not password:
            return jsonify({
                "status": "error",
                "message": "Full name, username and password are required."
            }), 400

        if len(username) > 50:
            return jsonify({
                "status": "error",
                "message": "Username must not exceed 50 characters."
            }), 400

        if role not in allowed_roles:
            return jsonify({
                "status": "error",
                "message": "Invalid user role."
            }), 400

        if len(str(password)) < 6:
            return jsonify({
                "status": "error",
                "message": "Password must contain at least 6 characters."
            }), 400

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT user_id
            FROM users
            WHERE username = %s
        """, (username,))

        if cursor.fetchone():
            return jsonify({
                "status": "error",
                "message": "Username already exists."
            }), 409

        password_hash = generate_password_hash(str(password))

        cursor.execute("""
            INSERT INTO users
            (
                full_name,
                username,
                password_hash,
                role
            )
            VALUES (%s, %s, %s, %s)
        """, (
            full_name,
            username,
            password_hash,
            role
        ))

        new_user_id = cursor.lastrowid

        connection.commit()

        return jsonify({
            "status": "success",
            "message": "User created successfully.",
            "user_id": new_user_id
        }), 201

    except Exception as e:

        if connection:
            connection.rollback()

        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()



# ============================================================
# PART 7: REPORT MANAGEMENT
# ============================================================

@app.route("/api/reports", methods=["GET", "POST"])
@login_required
def manage_reports():

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # ----------------------------------------------------
        # GET: FETCH REPORTS
        # ----------------------------------------------------

        if request.method == "GET":

            report_type = request.args.get(
                "type", "stock"
            ).strip().lower()

            # STOCK REPORT
            if report_type == "stock":

                cursor.execute("""
                    SELECT
                        p.product_id,
                        p.product_name,
                        c.category_name,
                        p.quantity,
                        p.unit,
                        p.purchase_date,
                        p.expiry_date,
                        p.storage_temperature,
                        p.created_at
                    FROM products p
                    JOIN categories c
                        ON p.category_id = c.category_id
                    WHERE p.is_active = 1
                    ORDER BY p.expiry_date ASC
                """)

                records = cursor.fetchall()

            # VERIFICATION REPORT
            elif report_type == "verification":

                cursor.execute("""
                    SELECT
                        v.verification_id,
                        v.product_id,
                        p.product_name,
                        v.actual_temperature,
                        v.verification_status AS status,
                        v.remarks,
                        v.verified_at,
                        u.full_name AS verified_by
                    FROM verifications v
                    JOIN products p
                        ON v.product_id = p.product_id
                    LEFT JOIN users u
                        ON v.verified_by = u.user_id
                    ORDER BY v.verified_at DESC
                """)

                records = cursor.fetchall()

            # ACTION REPORT
            elif report_type == "actions":

                cursor.execute("""
                    SELECT
                        a.action_id,
                        a.product_id,
                        p.product_name,
                        a.assigned_to,
                        u.full_name AS assigned_name,
                        a.action_type,
                        a.priority,
                        a.description,
                        a.action_status AS status,
                        a.created_at,
                        a.completed_at
                    FROM actions a
                    LEFT JOIN products p
                        ON a.product_id = p.product_id
                    LEFT JOIN users u
                        ON a.assigned_to = u.user_id
                    ORDER BY a.created_at DESC
                """)

                records = cursor.fetchall()

            else:

                return jsonify({
                    "status": "error",
                    "message": "Invalid report type."
                }), 400

            # Convert dates and timestamps into JSON-friendly values
            for record in records:

                for field, value in list(record.items()):

                    if hasattr(value, "isoformat"):
                        record[field] = value.isoformat()

                    elif value is not None and not isinstance(
                        value, (str, int, float, bool)
                    ):
                        record[field] = str(value)

            return jsonify({
                "status": "success",
                "reportType": report_type,
                "count": len(records),
                "records": records
            }), 200

        # ----------------------------------------------------
        # POST: GENERATE REPORT REQUEST
        # ----------------------------------------------------

        data = request.get_json(silent=True) or {}

        report_type = str(
            data.get("type", "stock")
        ).strip().lower()

        allowed_types = [
            "stock",
            "verification",
            "actions"
        ]

        if report_type not in allowed_types:

            return jsonify({
                "status": "error",
                "message": "Invalid report type."
            }), 400

        return jsonify({
            "status": "success",
            "message": "Report request accepted.",
            "reportType": report_type,
            "reportUrl": "/api/reports?type=" + report_type
        }), 200

    except Exception as error:

        return jsonify({
            "status": "error",
            "message": str(error)
        }), 500

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# ============================================================
# APPLICATION SETTINGS
# ============================================================

@app.route("/api/settings", methods=["GET", "PUT"])
@login_required
def manage_settings():

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # ----------------------------------------------------
        # GET: FETCH SETTINGS
        # ----------------------------------------------------

        if request.method == "GET":

            cursor.execute("""
                SELECT
                    setting_key,
                    setting_value
                FROM app_settings
                ORDER BY setting_key
            """)

            rows = cursor.fetchall()

            settings = {
                row["setting_key"]: row["setting_value"]
                for row in rows
            }

            return jsonify({
                "status": "success",
                "settings": settings
            }), 200

        # ----------------------------------------------------
        # PUT: UPDATE SETTINGS
        # ----------------------------------------------------

        if session.get("role") != "ADMIN":

            return jsonify({
                "status": "error",
                "message": "Administrator access required."
            }), 403

        data = request.get_json(silent=True) or {}

        allowed_settings = {
            "expiryThreshold": (0, 365),
            "criticalThreshold": (0, 365),
            "defaultTemperature": (-50, 100)
        }

        if not data:

            return jsonify({
                "status": "error",
                "message": "Provide at least one setting to update."
            }), 400

        updates = []

        for key, value in data.items():

            if key not in allowed_settings:

                return jsonify({
                    "status": "error",
                    "message": "Unknown setting: " + str(key)
                }), 400

            try:

                if isinstance(value, bool):
                    raise ValueError

                number = float(value)

                if not math.isfinite(number):
                    raise ValueError

                minimum, maximum = allowed_settings[key]

                if number < minimum or number > maximum:
                    raise ValueError

                if key in (
                    "expiryThreshold",
                    "criticalThreshold"
                ):

                    if not number.is_integer():
                        raise ValueError

                    number = int(number)

                updates.append((key, str(number)))

            except (ValueError, TypeError):

                return jsonify({
                    "status": "error",
                    "message": "Invalid value for setting: " + key
                }), 400

        for key, value in updates:

            cursor.execute("""
                INSERT INTO app_settings
                (
                    setting_key,
                    setting_value
                )
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE
                    setting_value = VALUES(setting_value)
            """, (key, value))

        connection.commit()

        return jsonify({
            "status": "success",
            "message": "Settings updated successfully."
        }), 200

    except Exception as error:

        if connection:
            connection.rollback()

        return jsonify({
            "status": "error",
            "message": str(error)
        }), 500

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# ============================================================
# START FLASK APPLICATION
# ============================================================

if __name__ == "__main__":

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )
