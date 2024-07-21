import sqlite3

def add_feedback_column():
    conn = sqlite3.connect("Tables/Emergenshe.db")
    cursor = conn.cursor()
    
    # Check if the feedback column already exists
    cursor.execute("PRAGMA table_info(App_rating)")
    columns = cursor.fetchall()
    column_names = [column[1] for column in columns]
    
    if 'feedback' not in column_names:
        cursor.execute("ALTER TABLE App_rating ADD COLUMN feedback TEXT")
        print("Column 'feedback' added to App_rating table.")
    else:
        print("Column 'feedback' already exists in App_rating table.")
    
    conn.commit()
    cursor.close()
    conn.close()

if __name__ == "__main__":
    add_feedback_column()
