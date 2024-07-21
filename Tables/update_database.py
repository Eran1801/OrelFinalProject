import sqlite3


def update_contacts_password():
    try:
        # Connect to your SQLite database
        conn = sqlite3.connect('Tables/Emergenshe.db')  # Update with the correct path to your database
        cursor = conn.cursor()

        # Update all contacts with a default password and set them as active
        cursor.execute("""
            UPDATE contact_list
            SET Password = 'Aa1234', is_active = 'active'
        """)

        # Commit the changes
        conn.commit()
        print("Contacts updated successfully.")

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
        if conn:
            conn.rollback()

    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    update_contacts_password()
