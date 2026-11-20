from datetime import date

def calculate_age(birth_year):
    return date.today().year - birth_year

def validate_email(email):
    return "@" in email and "." in email.split("@")[-1]

def create_user_account(name, email, birth_year, gender, zodiac_sign):
    """Validate and normalize user details into a profile dictionary."""
    clean_name = name.strip() if isinstance(name, str) else "user"
    clean_email = email.strip().lower() if isinstance(email, str) else ""
    current_year = date.today().year
    gender = gender.strip() if isinstance(gender, str) else ""
    zodiac_sign = zodiac_sign.strip() if isinstance(zodiac_sign, str) else ""
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
        "gender": gender,
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


def calculate_zodiac_sign(month, day):
    signs = [
        (1, 20, "Aquarius"), (2, 19, "Pisces"),
        (3, 21, "Aries"), (4, 20, "Taurus"),
        (5, 21, "Gemini"), (6, 21, "Cancer"),
        (7, 23, "Leo"), (8, 23, "Virgo"),
        (9, 23, "Libra"), (10, 23, "Scorpio"),
        (11, 22, "Sagittarius"), (12, 22, "Capricorn")
    ]
    date(2000, month, day)
    for start_month, start_day, sign in reversed(signs):
        if (month, day) >= (start_month, start_day):
            return sign
    return "Capricorn"
