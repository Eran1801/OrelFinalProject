'''In here will be all helper function that we use in the project'''

import yagmail


def send_email(subject, message, receiver_email):
    sender_email = "emergensheserivce@outlook.com"
    password = "it/_6VUECx@-huQ"

    try:
        # Initialize yagmail with the sender's email and password
        yag = yagmail.SMTP(user=sender_email, password=password, host='smtp.office365.com', port=587,
                           smtp_starttls=True, smtp_ssl=False)

        # Send the email
        yag.send(
            to=receiver_email,
            subject=subject,
            contents=message
        )
        print("Email sent successfully")
    except Exception as e:
        print(f"Error: {e}")


def check_valid_password(password):
    if len(password) < 6 or not any(c.isupper() for c in password) or not any(c.islower() for c in password) or not any(
            c.isdigit() for c in password):
        return "Password must be at least 6 characters long and contain at least one uppercase letter, one lowercase letter, and one number.", 400


def update_table_name(table_name):
    if table_name == 'User':
        return 'Users'
    elif table_name == 'Association Manager':
        return 'Manager'
    elif table_name == 'Volunteer':
        return 'Volunteers_list'
    elif table_name == "Contact":
        return 'contact_list'
