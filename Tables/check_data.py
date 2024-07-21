import sqlite3

from app.app import DATABASE

# Connect to the SQLite database file
conn = sqlite3.connect(DATABASE)

# Create a cursor object to execute SQL queries
cursor = conn.cursor()

# Execute a SQL query to select all data from the contact_list table where UserID=5
cursor.execute('''
SELECT * FROM contact_list WHERE UserID="1";
''')

# Fetch all rows from the result of the query
rows = cursor.fetchall()

# Print the rows
for row in rows:
    print(row)

# Close the cursor and the connection
cursor.close()
conn.close()
