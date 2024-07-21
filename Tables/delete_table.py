import sqlite3

from app.app import DATABASE

# Connect to the database
conn = sqlite3.connect(DATABASE)
cursor = conn.cursor()

try:
    # Drop (delete) the table
    cursor.execute("DROP TABLE IF EXISTS VolunteersLogs")

    # Commit the transaction
    conn.commit()
    print("Table 'VolunteersLogs' dropped successfully.")

except sqlite3.Error as e:
    print(f"An error occurred: {e}")

finally:
    # Close the connection
    conn.close()
