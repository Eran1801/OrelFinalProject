import sqlite3

from app.app import DATABASE

# Connect to the database
conn = sqlite3.connect(DATABASE)
cursor = conn.cursor()

try:
    # Create the table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS VolunteersLogs (
        id INTEGER PRIMARY KEY,
        volunteer_id INTEGER,
        login_time TEXT,
        logout_time TEXT
    )
    """)
    print("Table 'VolunteersLogs' created successfully.")

    # Sample data to insert
    sample_data = [
        (1, 1, "20/04/2024 16:00", "20/04/2024 17:30"),
        (2, 1, "21/04/2024 16:00", "21/04/2024 18:30"),
        (3, 2, "23/04/2024 16:00", "23/04/2024 18:30"),
        (4, 3, "21/04/2024 16:00", "21/04/2024 20:30"),
        (5, 4, "22/04/2024 16:00", "22/04/2024 18:00"),
        (6, 5, "21/04/2024 16:00", "21/04/2024 18:30")
    ]

    # Insert the sample data into the table
    cursor.executemany("INSERT INTO VolunteersLogs (id, volunteer_id, login_time, logout_time) VALUES (?, ?, ?, ?)", sample_data)
    conn.commit()
    print("Sample data inserted successfully.")

except sqlite3.Error as e:
    print(f"An error occurred: {e}")

finally:
    # Close the connection
    conn.close()
