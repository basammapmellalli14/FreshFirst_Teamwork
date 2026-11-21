
from db import get_db_connection

connection = get_db_connection()

if connection:
    print("SUCCESS: Flask backend connected to MySQL!")
    connection.close()
    print("Database connection closed.")
else:
    print("FAILED: Database connection unsuccessful.")
