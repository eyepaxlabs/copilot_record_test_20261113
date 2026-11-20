from datetime import date

def calculate_age(birth_year):
    return date.today().year - birth_year

def validate_email(email):
    return "@" in email and "." in email.split("@")[-1]

def create_user_profile(name, email, birth_year):
    """Validate and normalize user details into a profile dictionary."""
    clean_name = name.strip() if isinstance(name, str) else ""
    clean_email = email.strip().lower() if isinstance(email, str) else ""
    current_year = date.today().year
    if not clean_name:
        raise ValueError("Name cannot be empty.")
    if not validate_email(clean_email):
        raise ValueError("Please enter a valid email address.")
    if not isinstance(birth_year, int) or isinstance(birth_year, bool):
        raise ValueError("Birth year must be an integer.")
    if not 1900 <= birth_year <= current_year:
        raise ValueError("Please enter a realistic birth year.")
    age = current_year - birth_year
    return {
        "name": clean_name,
        "email": clean_email,
        "birth_year": birth_year,
        "age": age,
    }

def get_user_details():
    name = input("Enter your full name: ").strip()
    email = input("Enter your email: ").strip()
    year_text = input("Enter your birth year: ").strip()
    gender = input("Enter your gender: ").strip()
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
