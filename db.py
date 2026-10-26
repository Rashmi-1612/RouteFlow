
import mysql.connector
from mysql.connector import Error


def get_connection():
    """Connect to the courier_optimizer MySQL database."""
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="root",  # Enter your MySQL password here if you have one.
            database="courier_optimizer"
        )

        if connection.is_connected():
            return connection

    except Error as error:
        print("MySQL connection failed:", error)

    return None


if __name__ == "__main__":
    connection = get_connection()

    if connection:
        print("MySQL connection successful!")
        print("Connected database:", connection.database)
        connection.close()
    else:
        print("Could not connect to MySQL.")
