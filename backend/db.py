import os
import mysql.connector
from mysql.connector import Error

def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host=os.environ.get("DB_HOST", "localhost"),
            user=os.environ.get("DB_USER", "root"),
            password=os.environ.get("DB_PASSWORD", ""),
            database=os.environ.get("DB_NAME", "freshfirst_team"),
            port=int(os.environ.get("DB_PORT", "3306"))
        )

        if connection.is_connected():
            return connection

    except Error as e:
        print("Database Connection Error:", e)

    return None