import csv
import os
import sqlite3

from app.app import DATABASE, ROOT_DIR


# Function to create a table in the SQLite database using column names from CSV headers
def create_table_from_csv_headers(csv_file, db_file, table_name):
    # Connect to SQLite database
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    # Read headers from CSV file
    with open(csv_file, 'r', newline='', encoding='utf-8') as file:
        csv_reader = csv.reader(file)
        headers = next(csv_reader)

    # Generate column names and types from headers
    columns = [f"{header.strip().replace(' ', '_')} TEXT" for header in headers]

    # Create the table if it doesn't exist
    cursor.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(columns)})")

    # Commit changes and close connection
    conn.commit()
    conn.close()


# Function to read data from CSV file and insert into SQLite database
def insert_data_from_csv(csv_file, db_file, table_name):
    # Connect to SQLite database
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    # Read data from CSV file and insert into database
    with open(csv_file, 'r', newline='', encoding='utf-8') as file:
        csv_reader = csv.reader(file)
        # Skip header
        next(csv_reader)
        for row in csv_reader:
            # Insert data into database
            cursor.execute(f"INSERT INTO {table_name} VALUES ({', '.join(['?'] * len(row))})", row)

    # Commit changes and close connection
    conn.commit()
    conn.close()


# Example usage

csv_file = os.path.join(ROOT_DIR, 'Tables','contact_list.csv')
db_file = DATABASE
table_name = 'contact_list'

# Create the table using column names from CSV headers
create_table_from_csv_headers(csv_file, db_file, table_name)

# Insert data from CSV file into the table
insert_data_from_csv(csv_file, db_file, table_name)
