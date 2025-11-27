import psycopg2
import csv

# ---------- DATABASE CONFIGURATION ----------
DB_CONFIG = {
    "dbname": "phonebook",   # database you created in pgAdmin
    "user": "postgres",         # change if needed
    "password": "3657",# your PostgreSQL password
    "host": "localhost",
    "port": 5432
}


def get_connection():
    return psycopg2.connect(**DB_CONFIG)


# ---------- CREATE TABLE ----------
def create_table():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS phonebook (
            id         SERIAL PRIMARY KEY,
            first_name VARCHAR(50) NOT NULL,
            last_name  VARCHAR(50),
            phone      VARCHAR(20) NOT NULL UNIQUE
        );
    """)
    conn.commit()
    cur.close()
    conn.close()
    print("Table 'phonebook' is ready.")


# ---------- INSERT DATA FROM CONSOLE ----------
def insert_from_console():
    print("\n=== Add Contact From Console ===")
    first_name = input("First name: ").strip()
    last_name = input("Last name (optional): ").strip()
    if last_name == "":
        last_name = None
    phone = input("Phone: ").strip()

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO phonebook (first_name, last_name, phone)
            VALUES (%s, %s, %s)
            """,
            (first_name, last_name, phone)
        )
        conn.commit()
        print("Contact added.")
    except psycopg2.Error as e:
        conn.rollback()
        print("Error inserting contact:", e)
    finally:
        cur.close()
        conn.close()


# ---------- INSERT DATA FROM CSV ----------
# CSV format example:
# first_name,last_name,phone
# Sara,,+77001112233
# John,Doe,5551234567
def insert_from_csv():
    print("\n=== Import Contacts From CSV ===")
    path = input("Enter CSV file path: ").strip()

    conn = get_connection()
    cur = conn.cursor()

    try:
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                first_name = row.get("first_name")
                last_name = row.get("last_name") or None
                phone = row.get("phone")

                if not first_name or not phone:
                    print("Skipping row (missing first_name or phone):", row)
                    continue

                # If phone already exists → update instead
                cur.execute(
                    """
                    INSERT INTO phonebook (first_name, last_name, phone)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (phone)
                    DO UPDATE SET
                        first_name = EXCLUDED.first_name,
                        last_name  = EXCLUDED.last_name;
                    """,
                    (first_name, last_name, phone)
                )
                count += 1

        conn.commit()
        print(f"Imported/updated {count} contacts from CSV.")
    except FileNotFoundError:
        print("CSV file not found.")
    except psycopg2.Error as e:
        conn.rollback()
        print("Database error during CSV import:", e)
    finally:
        cur.close()
        conn.close()


# ---------- UPDATE FIRST NAME (BY PHONE) ----------
def update_first_name():
    print("\n=== Update First Name ===")
    phone = input("Enter phone number of the user: ").strip()
    new_first_name = input("New first name: ").strip()

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            UPDATE phonebook
            SET first_name = %s
            WHERE phone = %s
            """,
            (new_first_name, phone)
        )
        conn.commit()
        print(f"Updated rows: {cur.rowcount}")
    except psycopg2.Error as e:
        conn.rollback()
        print("Error updating first name:", e)
    finally:
        cur.close()
        conn.close()


# ---------- UPDATE PHONE (BY FIRST NAME) ----------
def update_phone():
    print("\n=== Update Phone Number ===")
    first_name = input("Enter first name of the user: ").strip()
    new_phone = input("New phone number: ").strip()

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            UPDATE phonebook
            SET phone = %s
            WHERE first_name = %s
            """,
            (new_phone, first_name)
        )
        conn.commit()
        print(f"Updated rows: {cur.rowcount}")
    except psycopg2.Error as e:
        conn.rollback()
        print("Error updating phone:", e)
    finally:
        cur.close()
        conn.close()


# ---------- QUERY: SHOW ALL CONTACTS ----------
def show_all():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, first_name, last_name, phone FROM phonebook ORDER BY id;")
    rows = cur.fetchall()
    print("\n=== All Contacts ===")
    for r in rows:
        print(f"{r[0]}: {r[1]} {r[2] or ''} - {r[3]}")
    cur.close()
    conn.close()


# ---------- QUERY: SEARCH BY NAME ----------
def search_by_name():
    print("\n=== Search By Name ===")
    pattern = input("Enter part of first or last name: ").strip()

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, first_name, last_name, phone
        FROM phonebook
        WHERE first_name ILIKE %s OR last_name ILIKE %s
        ORDER BY first_name;
        """,
        (f"%{pattern}%", f"%{pattern}%")
    )
    rows = cur.fetchall()

    if not rows:
        print("No matches found.")
    else:
        for r in rows:
            print(f"{r[0]}: {r[1]} {r[2] or ''} - {r[3]}")

    cur.close()
    conn.close()


# ---------- QUERY: SEARCH BY PHONE PREFIX ----------
def search_by_phone_prefix():
    print("\n=== Search By Phone Prefix ===")
    prefix = input("Enter phone prefix (e.g. +7700, 555): ").strip()

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, first_name, last_name, phone
        FROM phonebook
        WHERE phone LIKE %s
        ORDER BY phone;
        """,
        (prefix + "%",)
    )
    rows = cur.fetchall()

    if not rows:
        print("No matches found.")
    else:
        for r in rows:
            print(f"{r[0]}: {r[1]} {r[2] or ''} - {r[3]}")

    cur.close()
    conn.close()


# ---------- DELETE CONTACT ----------
def delete_by_name_or_phone():
    print("\n=== Delete Contact ===")
    value = input("Enter first name OR phone: ").strip()

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            DELETE FROM phonebook
            WHERE first_name = %s OR phone = %s;
            """,
            (value, value)
        )
        conn.commit()
        print(f"Deleted rows: {cur.rowcount}")
    except psycopg2.Error as e:
        conn.rollback()
        print("Error deleting contact:", e)
    finally:
        cur.close()
        conn.close()


# ---------- SEARCH MENU ----------
def search_menu():
    while True:
        print("\n--- Search Menu ---")
        print("1. Show all contacts")
        print("2. Search by name")
        print("3. Search by phone prefix")
        print("0. Back")
        c = input("Choose: ").strip()

        if c == "1":
            show_all()
        elif c == "2":
            search_by_name()
        elif c == "3":
            search_by_phone_prefix()
        elif c == "0":
            break
        else:
            print("Invalid choice.")


# ---------- MAIN MENU ----------
def main_menu():
    create_table()

    while True:
        print("\n=== PHONEBOOK APP ===")
        print("1. Add contact from console")
        print("2. Import contacts from CSV")
        print("3. Update first name (by phone)")
        print("4. Update phone number (by name)")
        print("5. Search / view contacts")
        print("6. Delete contact")
        print("0. Exit")

        choice = input("Choose an option: ").strip()

        if choice == "1":
            insert_from_console()
        elif choice == "2":
            insert_from_csv()
        elif choice == "3":
            update_first_name()
        elif choice == "4":
            update_phone()
        elif choice == "5":
            search_menu()
        elif choice == "6":
            delete_by_name_or_phone()
        elif choice == "0":
            print("Goodbye!")
            break
        else:
            print("Invalid selection, try again.")


if __name__ == "__main__":
    main_menu()
