"""Generates a rich enterprise demo database for eCommerce & HR."""

import sqlite3
from pathlib import Path
from typing import Union


def create_sample_database(db_path: Union[str, Path]) -> str:
    """Populates a realistic enterprise database with sample relational data."""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # If the database already exists and has tables, return early
    if db_path.exists() and db_path.stat().st_size > 0:
        return str(db_path)

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON;")

    # 1. Departments table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS departments (
        department_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        budget REAL NOT NULL,
        location TEXT NOT NULL
    );
    """)

    departments_data = [
        ("Engineering", 1500000.0, "Building A, Floor 4"),
        ("Sales", 850000.0, "Building B, Floor 2"),
        ("Marketing", 600000.0, "Building B, Floor 1"),
        ("Human Resources", 400000.0, "Building A, Floor 1"),
        ("Product & Design", 950000.0, "Building A, Floor 3"),
        ("Customer Support", 500000.0, "Remote / Building C"),
    ]
    cursor.executemany(
        "INSERT INTO departments (name, budget, location) VALUES (?, ?, ?);",
        departments_data
    )

    # 2. Employees table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS employees (
        employee_id INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        department_id INTEGER NOT NULL,
        role TEXT NOT NULL,
        salary REAL NOT NULL,
        hire_date TEXT NOT NULL,
        FOREIGN KEY (department_id) REFERENCES departments(department_id)
    );
    """)

    employees_data = [
        ("Alice", "Smith", "alice.smith@enterprise.com", 1, "Principal Engineer", 145000.0, "2021-03-15"),
        ("Bob", "Johnson", "bob.johnson@enterprise.com", 1, "Senior Backend Dev", 120000.0, "2022-01-10"),
        ("Charlie", "Brown", "charlie.brown@enterprise.com", 1, "Fullstack Engineer", 98000.0, "2023-06-01"),
        ("Diana", "Prince", "diana.prince@enterprise.com", 2, "Sales Director", 135000.0, "2020-11-20"),
        ("Evan", "Davis", "evan.davis@enterprise.com", 2, "Senior Account Exec", 95000.0, "2022-04-12"),
        ("Fiona", "Gallagher", "fiona.g@enterprise.com", 2, "Sales Representative", 68000.0, "2023-09-18"),
        ("George", "Clark", "george.c@enterprise.com", 3, "Marketing Lead", 110000.0, "2021-07-01"),
        ("Hannah", "Abbott", "hannah.a@enterprise.com", 3, "Growth Specialist", 75000.0, "2023-02-14"),
        ("Ian", "Malcolm", "ian.m@enterprise.com", 4, "HR Director", 115000.0, "2019-08-25"),
        ("Julia", "Roberts", "julia.r@enterprise.com", 4, "Talent Recruiter", 72000.0, "2022-08-01"),
        ("Kevin", "Bacon", "kevin.b@enterprise.com", 5, "Head of Product", 140000.0, "2021-05-15"),
        ("Laura", "Croft", "laura.c@enterprise.com", 5, "UI/UX Designer", 88000.0, "2023-01-20"),
        ("Michael", "Scott", "michael.s@enterprise.com", 6, "Support Manager", 82000.0, "2020-03-10"),
        ("Nina", "Simone", "nina.s@enterprise.com", 6, "Support Specialist", 52000.0, "2023-11-05"),
        ("Oscar", "Isaac", "oscar.i@enterprise.com", 1, "DevOps Engineer", 118000.0, "2022-10-01"),
    ]
    cursor.executemany(
        """INSERT INTO employees 
           (first_name, last_name, email, department_id, role, salary, hire_date) 
           VALUES (?, ?, ?, ?, ?, ?, ?);""",
        employees_data
    )

    # 3. Customers table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS customers (
        customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        country TEXT NOT NULL,
        city TEXT NOT NULL,
        join_date TEXT NOT NULL
    );
    """)

    customers_data = [
        ("Sarah", "Connor", "sarah.c@sky.net", "USA", "Los Angeles", "2023-01-15"),
        ("John", "Doe", "john.doe@example.com", "USA", "New York", "2023-02-20"),
        ("Elena", "Rostova", "elena.r@example.org", "UK", "London", "2023-03-10"),
        ("Akira", "Tanaka", "akira.t@tokyo.jp", "Japan", "Tokyo", "2023-04-05"),
        ("Marcus", "Aurelius", "marcus.a@rome.it", "Italy", "Rome", "2023-05-12"),
        ("Chloe", "Kim", "chloe.kim@snow.kr", "South Korea", "Seoul", "2023-06-25"),
        ("Liam", "Neeson", "liam.n@taken.ie", "Ireland", "Dublin", "2023-07-19"),
        ("Emma", "Watson", "emma.w@oxford.uk", "UK", "Oxford", "2023-08-04"),
        ("Carlos", "Santana", "carlos.s@music.mx", "Mexico", "Guadalajara", "2023-09-30"),
        ("Amara", "Okafor", "amara.o@lagos.ng", "Nigeria", "Lagos", "2023-10-14"),
    ]
    cursor.executemany(
        """INSERT INTO customers 
           (first_name, last_name, email, country, city, join_date) 
           VALUES (?, ?, ?, ?, ?, ?);""",
        customers_data
    )

    # 4. Products table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        product_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        unit_price REAL NOT NULL,
        stock_quantity INTEGER NOT NULL
    );
    """)

    products_data = [
        ("Quantum Pro Laptop 15-inch", "Electronics", 1299.99, 45),
        ("ErgoPeak Mechanical Keyboard", "Accessories", 149.50, 120),
        ("HyperView 27-inch 4K Monitor", "Electronics", 399.00, 30),
        ("AuraSound Wireless Noise-Cancelling Headphones", "Audio", 249.99, 85),
        ("OmniDesk Electric Standing Desk", "Furniture", 599.00, 15),
        ("Titanium Ergonomic Office Chair", "Furniture", 349.99, 25),
        ("PrecisionFlow Optical Mouse", "Accessories", 49.99, 200),
        ("StreamMaster HD Webcam 1080p", "Electronics", 79.99, 90),
        ("BassWave Portable Bluetooth Speaker", "Audio", 89.00, 110),
        ("SmartLED Desk Lamp with Qi Charger", "Accessories", 59.95, 75),
    ]
    cursor.executemany(
        """INSERT INTO products (name, category, unit_price, stock_quantity) 
           VALUES (?, ?, ?, ?);""",
        products_data
    )

    # 5. Orders table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        order_id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER NOT NULL,
        order_date TEXT NOT NULL,
        total_amount REAL NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('Completed', 'Pending', 'Processing', 'Cancelled', 'Shipped')),
        FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
    );
    """)

    orders_data = [
        (1, "2024-01-10", 1449.49, "Completed"),
        (2, "2024-01-15", 399.00, "Completed"),
        (3, "2024-02-01", 1698.99, "Completed"),
        (4, "2024-02-14", 948.99, "Completed"),
        (5, "2024-03-02", 599.00, "Completed"),
        (1, "2024-03-20", 249.99, "Completed"),
        (6, "2024-04-05", 149.50, "Completed"),
        (7, "2024-04-18", 1748.98, "Completed"),
        (8, "2024-05-01", 349.99, "Shipped"),
        (9, "2024-05-15", 138.99, "Shipped"),
        (10, "2024-06-01", 1299.99, "Processing"),
        (2, "2024-06-12", 49.99, "Pending"),
        (3, "2024-07-04", 648.99, "Cancelled"),
        (4, "2024-07-20", 1449.49, "Completed"),
        (5, "2024-08-10", 399.00, "Completed"),
    ]
    cursor.executemany(
        """INSERT INTO orders (customer_id, order_date, total_amount, status) 
           VALUES (?, ?, ?, ?);""",
        orders_data
    )

    # 6. Order items table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS order_items (
        order_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        unit_price REAL NOT NULL,
        FOREIGN KEY (order_id) REFERENCES orders(order_id),
        FOREIGN KEY (product_id) REFERENCES products(product_id)
    );
    """)

    order_items_data = [
        (1, 1, 1, 1299.99), # Laptop
        (1, 2, 1, 149.50),  # Keyboard
        (2, 3, 1, 399.00),  # Monitor
        (3, 1, 1, 1299.99), # Laptop
        (3, 3, 1, 399.00),  # Monitor
        (4, 5, 1, 599.00),  # Desk
        (4, 6, 1, 349.99),  # Chair
        (5, 5, 1, 599.00),  # Desk
        (6, 4, 1, 249.99),  # Headphones
        (7, 2, 1, 149.50),  # Keyboard
        (8, 1, 1, 1299.99), # Laptop
        (8, 4, 1, 249.99),  # Headphones
        (8, 7, 4, 49.99),   # Mouse x4
        (9, 6, 1, 349.99),  # Chair
        (10, 9, 1, 89.00),  # Speaker
        (10, 7, 1, 49.99),  # Mouse
        (11, 1, 1, 1299.99),# Laptop
        (12, 7, 1, 49.99),  # Mouse
        (13, 5, 1, 599.00),  # Desk
        (13, 7, 1, 49.99),  # Mouse
        (14, 1, 1, 1299.99),# Laptop
        (14, 2, 1, 149.50), # Keyboard
        (15, 3, 1, 399.00), # Monitor
    ]
    cursor.executemany(
        """INSERT INTO order_items (order_id, product_id, quantity, unit_price) 
           VALUES (?, ?, ?, ?);""",
        order_items_data
    )

    conn.commit()
    conn.close()
    return str(db_path)


if __name__ == "__main__":
    db = create_sample_database(Path(__file__).resolve().parent.parent.parent / "data" / "sample_enterprise.db")
    print(f"Sample enterprise database generated at: {db}")
