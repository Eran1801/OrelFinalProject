import sqlite3

def update_calls_table():
    conn = sqlite3.connect('Emergenshe.db')
    cursor = conn.cursor()
    
    try:
        # Rename Call_Rating to User_Call_Rating
        cursor.execute("ALTER TABLE calls RENAME COLUMN Call_Rating TO User_Call_Rating;")
        
        # Add new columns
        cursor.execute("ALTER TABLE calls ADD COLUMN Volunteer_Call_Rating INTEGER;")
        cursor.execute("ALTER TABLE calls ADD COLUMN Contact_Call_Rating INTEGER;")
        cursor.execute("ALTER TABLE calls ADD COLUMN User_Feedback TEXT;")
        cursor.execute("ALTER TABLE calls ADD COLUMN Volunteer_Feedback TEXT;")
        cursor.execute("ALTER TABLE calls RENAME TO Calls;")
        
        print("Table updated successfully")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        conn.commit()
        cursor.close()
        conn.close()

if __name__ == "__main__":
    update_calls_table()
