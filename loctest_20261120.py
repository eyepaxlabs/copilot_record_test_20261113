from datetime import date

def calculate_age(birth_year):
    return date.today().year - birth_year

def validate_email(email):
    return "@" in email and "." in email.split("@")[-1]

def get_user_details():
    name = input("Enter your name: ").strip()
    email = input("Enter your email: ").strip()
    year_text = input("Enter your birth year: ").strip()
    if not name:
        print("Name cannot be empty.")
        return
    if not validate_email(email):
        print("Please enter a valid email address.")
        return
    if not year_text.isdigit():
        print("Birth year must be a number.")
        return
    birth_year = int(year_text)
    if not 1900 <= birth_year <= date.today().year:
        print("Please enter a realistic birth year.")
        return
    print(f"Welcome to Eyepax AIT, {name}!")
    print(f"Email: {email}")
    print(f"Approximate age: {calculate_age(birth_year)}")
if __name__ == "__main__":
    get_user_details()
