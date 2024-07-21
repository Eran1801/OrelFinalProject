import sqlite3

def update_table_name():
    try:
        # Connect to your SQLite database
        conn = sqlite3.connect('Tables/Emergenshe.db')  # Update with the correct path to your database
        cursor = conn.cursor()

        # Rename the table from calls to Calls
        cursor.execute("ALTER TABLE calls RENAME TO Calls")

        # Commit the changes
        conn.commit()
        print("Table name updated successfully.")
    
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
        if conn:
            conn.rollback()
    
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    update_table_name()
