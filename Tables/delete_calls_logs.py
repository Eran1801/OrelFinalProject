import sqlite3

DATABASE = 'Tables/Emergenshe.db'

# Connect to the database
conn = sqlite3.connect(DATABASE)
cursor = conn.cursor()

# Print the current rows in the Calls table
print("Rows before deletion:")
cursor.execute("SELECT * FROM calls")
rows = cursor.fetchall()
for row in rows:
    print(row)

# Query to delete all rows in the Calls table
query = '''
DELETE FROM calls;
'''

# Execute the SQL statement
cursor.execute(query)

# Commit the transaction
conn.commit()

# Print the rows in the Calls table after deletion to verify
print("\nRows after deletion:")
cursor.execute("SELECT * FROM calls")
rows = cursor.fetchall()
for row in rows:
    print(row)

# Close the connection
conn.close()
