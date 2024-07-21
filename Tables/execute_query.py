import sqlite3

from app.app import DATABASE

# Connect to the database
conn = sqlite3.connect(DATABASE)
cursor = conn.cursor()

# Define the SQL query
sql_query = '''
    SELECT
        v.ID,
        v.first_name,
        v.last_name,
        SUM(
            CAST(SUBSTR(vl.logout_time, 12, 2) AS INTEGER) * 3600 +
            CAST(SUBSTR(vl.logout_time, 15, 2) AS INTEGER) * 60 +
            CAST(SUBSTR(vl.logout_time, 18, 2) AS INTEGER) -
            CAST(SUBSTR(vl.login_time, 12, 2) AS INTEGER) * 3600 -
            CAST(SUBSTR(vl.login_time, 15, 2) AS INTEGER) * 60 -
            CAST(SUBSTR(vl.login_time, 18, 2) AS INTEGER)
        ) AS total_seconds
    FROM
        Volunteers_list v
    LEFT JOIN VolunteersLogs vl ON v.ID = vl.volunteer_id
    WHERE
        vl.logout_time IS NOT NULL
    GROUP BY
        v.ID,
        v.first_name,
        v.last_name
'''

try:
    # Execute the query
    cursor.execute(sql_query)

    # Fetch all rows from the result set
    rows = cursor.fetchall()

    # Process and print or use the results as needed
    for row in rows:
        volunteer_id = row[0]
        first_name = row[1]
        last_name = row[2]
        total_seconds = row[3] or 0

        # Convert total_seconds to hours, minutes, seconds
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        # Format time display
        formatted_time = f"{hours:02}:{minutes:02}:{seconds:02}"
        print(f"Volunteer ID: {volunteer_id}, Name: {first_name} {last_name}, Total Hours: {formatted_time}")

except sqlite3.Error as e:
    print(f"Error executing SQL query: {e}")

finally:
    # Close the connection
    conn.close()
