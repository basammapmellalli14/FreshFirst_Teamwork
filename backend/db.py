
import mysql.connector
from mysql.connector import Error

def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="freshfirst_team",
            port=3306
        )

        if connection.is_connected():
            return connection

    except Error as e:
        print("Database Connection Error:", e)

    return None
