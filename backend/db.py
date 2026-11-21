import os
import mysql.connector
from mysql.connector import Error


def get_db_connection():
    """Create a MySQL connection using environment-based local settings.

    Defaults match the team's XAMPP setup (port 3307). Override with
    FRESHFIRST_DB_HOST, FRESHFIRST_DB_USER, FRESHFIRST_DB_PASSWORD,
    FRESHFIRST_DB_NAME, and FRESHFIRST_DB_PORT when needed.
    """
    try:
        connection = mysql.connector.connect(
            host=os.environ.get("FRESHFIRST_DB_HOST", "localhost"),
            user=os.environ.get("FRESHFIRST_DB_USER", "root"),
            password=os.environ.get("FRESHFIRST_DB_PASSWORD", ""),
            database=os.environ.get("FRESHFIRST_DB_NAME", "freshfirst_team"),
            port=int(os.environ.get("FRESHFIRST_DB_PORT", "3307")),
        )

        if connection.is_connected():
            return connection

    except (Error, ValueError) as error:
        print("Database Connection Error:", error)

    return None
