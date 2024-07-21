import sqlite3

# Function to drop the Contacts table from the SQLite database
def drop_contacts_table(db_file):
    # Connect to SQLite database
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    # Drop the Contacts table if it exists
    cursor.execute("DROP TABLE IF EXISTS Contacts")

    # Commit changes and close connection
    conn.commit()
    conn.close()

# Function to create the Contacts table in the SQLite database
def create_contacts_table_and_insert_data(db_file):
    # Connect to SQLite database
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    # Create the Contacts table
    cursor.execute('''CREATE TABLE Contacts (
                        ID INTEGER PRIMARY KEY,
                        UserID INTEGER,
                        First_Name TEXT,
                        Last_Name TEXT,
                        Phone_Number TEXT,
                        Email TEXT,
                        password TEXT,
                        is_active TEXT
                    )''')

    # Insert data into the Contacts table
    contacts_data = [
        (1, 1, 'Mary', 'Johnson', '5551112222', 'mary1@example.com', 'mary1', 'active'),
        (2, 2, 'Michael', 'Williams', '4442223333', 'michael2@example.com', 'michael2', 'active'),
        (3, 3, 'Sarah', 'Brown', '3335556666', 'sarah3@example.com', 'sarah3', 'active'),
        (4, 4, 'Chris', 'Taylor', '2223334444', 'chris4@example.com', 'chris4', 'active'),
        (5, 5, 'Emily', 'Garcia', '1114445555', 'emily5@example.com', 'emily5', 'active'),
        (6, 6, 'Kevin', 'Martinez', '6669998888', 'kevin6@example.com', 'kevin6', 'active'),
        (7, 7, 'Ashley', 'Anderson', '7778889999', 'ashley7@example.com', 'ashley7', 'active'),
        (8, 8, 'Jessica', 'Thomas', '8887776666', 'jessica8@example.com', 'jessica8', 'active'),
        (9, 9, 'Daniel', 'Hernandez', '9998887777', 'daniel9@example.com', 'daniel9', 'active'),
        (10, 10, 'Megan', 'Lopez', '1234567890', 'megan99@example.com', 'megan10', 'active')
    ]
    cursor.executemany('INSERT INTO Contacts VALUES (?, ?, ?, ?, ?, ?, ?, ?)', contacts_data)

    # Commit changes and close connection
    conn.commit()
    conn.close()

# Example usage
db_file = 'Emergenshe.db'

# Drop the Contacts table (if exists)
drop_contacts_table(db_file)

# Create the Contacts table and insert data
create_contacts_table_and_insert_data(db_file)
