import sqlite3

# Connect to SQLite database (create new if not exists)
conn = sqlite3.connect('Emergenshe.db')

# Close connection
conn.close()
