"""
create_sample_db.py
Generates sample_store.db — a realistic e-commerce SQLite database
with customers, products, categories, orders and order_items tables.
Run: python create_sample_db.py
"""

import sqlite3
import random
from datetime import datetime, timedelta
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "sample_store.db")

# ── Remove old DB if it exists ─────────────────────────────────────────────
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

conn = sqlite3.connect(DB_PATH)
cur  = conn.cursor()

# ── Schema ─────────────────────────────────────────────────────────────────
cur.executescript("""
PRAGMA foreign_keys = ON;

CREATE TABLE categories (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL UNIQUE,
    description TEXT
);

CREATE TABLE products (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER NOT NULL REFERENCES categories(id),
    name        TEXT    NOT NULL,
    sku         TEXT    NOT NULL UNIQUE,
    price       REAL    NOT NULL,
    stock       INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT    NOT NULL
);

CREATE TABLE customers (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name TEXT    NOT NULL,
    last_name  TEXT    NOT NULL,
    email      TEXT    NOT NULL UNIQUE,
    city       TEXT,
    country    TEXT,
    joined_at  TEXT    NOT NULL
);

CREATE TABLE orders (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    status      TEXT    NOT NULL CHECK(status IN ('pending','processing','shipped','delivered','cancelled')),
    total       REAL    NOT NULL,
    created_at  TEXT    NOT NULL
);

CREATE TABLE order_items (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id   INTEGER NOT NULL REFERENCES orders(id),
    product_id INTEGER NOT NULL REFERENCES products(id),
    quantity   INTEGER NOT NULL,
    unit_price REAL    NOT NULL
);

CREATE TABLE reviews (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id  INTEGER NOT NULL REFERENCES products(id),
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    rating      INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
    comment     TEXT,
    created_at  TEXT    NOT NULL
);
""")

# ── Categories ─────────────────────────────────────────────────────────────
categories = [
    ("Electronics",   "Gadgets, devices and tech accessories"),
    ("Books",         "Fiction, non-fiction and educational books"),
    ("Clothing",      "Apparel for all ages and styles"),
    ("Home & Garden", "Furniture, decor and gardening supplies"),
    ("Sports",        "Equipment and apparel for sports and fitness"),
    ("Toys",          "Games and toys for children of all ages"),
]
cur.executemany("INSERT INTO categories (name, description) VALUES (?,?)", categories)

# ── Products ───────────────────────────────────────────────────────────────
products = [
    # Electronics (cat 1)
    (1, "Wireless Noise-Cancelling Headphones", "SKU-001", 149.99, 87),
    (1, "4K USB-C Monitor 27\"",                "SKU-002", 349.99, 22),
    (1, "Mechanical Keyboard TKL",              "SKU-003",  89.99, 56),
    (1, "Ergonomic Wireless Mouse",             "SKU-004",  49.99, 130),
    (1, "USB-C Hub 7-in-1",                     "SKU-005",  34.99, 200),
    (1, "Portable SSD 1TB",                     "SKU-006", 109.99,  44),
    # Books (cat 2)
    (2, "Clean Code",                           "SKU-007",  29.99, 300),
    (2, "Designing Data-Intensive Applications","SKU-008",  44.99, 180),
    (2, "The Pragmatic Programmer",             "SKU-009",  34.99, 220),
    (2, "Atomic Habits",                        "SKU-010",  16.99, 450),
    (2, "Deep Work",                            "SKU-011",  14.99, 390),
    # Clothing (cat 3)
    (3, "Slim-Fit Chino Trousers",              "SKU-012",  54.99, 160),
    (3, "Merino Wool Crew Neck Sweater",        "SKU-013",  79.99,  90),
    (3, "Classic Oxford Shirt",                 "SKU-014",  39.99, 210),
    (3, "Running Shorts",                       "SKU-015",  24.99, 340),
    # Home & Garden (cat 4)
    (4, "Ceramic Pour-Over Coffee Set",         "SKU-016",  44.99,  75),
    (4, "Bamboo Cutting Board Set",             "SKU-017",  29.99, 120),
    (4, "Cast Iron Skillet 10\"",               "SKU-018",  39.99,  88),
    (4, "Indoor Herb Garden Kit",               "SKU-019",  24.99, 100),
    # Sports (cat 5)
    (5, "Yoga Mat Pro 6mm",                     "SKU-020",  34.99, 140),
    (5, "Adjustable Dumbbell Set 2-20kg",       "SKU-021", 189.99,  30),
    (5, "Resistance Bands Set",                 "SKU-022",  19.99, 260),
    # Toys (cat 6)
    (6, "STEM Building Blocks 500pcs",          "SKU-023",  44.99,  95),
    (6, "Watercolour Paint Kit",                "SKU-024",  22.99, 170),
]

now = datetime.now()
product_rows = [
    (cat, name, sku, price, stock,
     (now - timedelta(days=random.randint(30, 730))).strftime("%Y-%m-%d %H:%M:%S"))
    for cat, name, sku, price, stock in products
]
cur.executemany(
    "INSERT INTO products (category_id, name, sku, price, stock, created_at) VALUES (?,?,?,?,?,?)",
    product_rows,
)

# ── Customers ──────────────────────────────────────────────────────────────
first_names = [
    "Alice","Bob","Carol","David","Emma","Frank","Grace","Henry",
    "Isla","Jack","Karen","Liam","Mia","Noah","Olivia","Peter",
    "Quinn","Rachel","Sam","Tara","Uma","Victor","Wendy","Xander",
    "Yara","Zoe","Aaron","Bella","Chris","Diana",
]
last_names = [
    "Smith","Jones","Williams","Brown","Taylor","Davies","Evans",
    "Wilson","Thomas","Roberts","Johnson","White","Martin","Anderson",
    "Thompson","Garcia","Martinez","Robinson","Clark","Lewis",
]
cities_countries = [
    ("London","UK"), ("Manchester","UK"), ("Edinburgh","UK"),
    ("New York","US"), ("Los Angeles","US"), ("Chicago","US"),
    ("Toronto","CA"), ("Vancouver","CA"),
    ("Sydney","AU"), ("Melbourne","AU"),
    ("Berlin","DE"), ("Munich","DE"),
    ("Paris","FR"), ("Lyon","FR"),
]

customer_rows = []
emails_used: set[str] = set()
for i in range(120):
    fn = random.choice(first_names)
    ln = random.choice(last_names)
    base_email = f"{fn.lower()}.{ln.lower()}{random.randint(1,999)}@example.com"
    while base_email in emails_used:
        base_email = f"{fn.lower()}.{ln.lower()}{random.randint(1,9999)}@example.com"
    emails_used.add(base_email)
    city, country = random.choice(cities_countries)
    joined = (now - timedelta(days=random.randint(1, 1095))).strftime("%Y-%m-%d %H:%M:%S")
    customer_rows.append((fn, ln, base_email, city, country, joined))

cur.executemany(
    "INSERT INTO customers (first_name, last_name, email, city, country, joined_at) VALUES (?,?,?,?,?,?)",
    customer_rows,
)

# ── Orders + Order Items ───────────────────────────────────────────────────
statuses = ["pending","processing","shipped","delivered","cancelled"]
status_weights = [0.05, 0.10, 0.20, 0.60, 0.05]

order_rows = []
item_rows  = []
product_count = len(products)

for order_id in range(1, 351):
    customer_id = random.randint(1, 120)
    status      = random.choices(statuses, weights=status_weights, k=1)[0]
    created_at  = (now - timedelta(days=random.randint(1, 730),
                                   hours=random.randint(0, 23),
                                   minutes=random.randint(0, 59))
                   ).strftime("%Y-%m-%d %H:%M:%S")

    # 1–5 line items per order
    n_items   = random.randint(1, 5)
    prod_ids  = random.sample(range(1, product_count + 1), min(n_items, product_count))
    total     = 0.0

    for pid in prod_ids:
        qty        = random.randint(1, 4)
        # Look up price from product_rows (0-indexed, pid is 1-indexed)
        unit_price = product_rows[pid - 1][3]
        total     += qty * unit_price
        item_rows.append((order_id, pid, qty, unit_price))

    order_rows.append((customer_id, status, round(total, 2), created_at))

cur.executemany(
    "INSERT INTO orders (customer_id, status, total, created_at) VALUES (?,?,?,?)",
    order_rows,
)
cur.executemany(
    "INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES (?,?,?,?)",
    item_rows,
)

# ── Reviews ────────────────────────────────────────────────────────────────
comments = [
    "Absolutely love it!", "Great value for money.", "Exceeded my expectations.",
    "Good but could be better.", "Exactly as described.", "Fast delivery, great product.",
    "Would recommend to a friend.", "Decent quality.", "Not what I expected.",
    "Five stars, will buy again!", None, None,   # Some reviews have no comment
]
review_rows = []
seen_reviews: set[tuple] = set()
for _ in range(200):
    pid = random.randint(1, product_count)
    cid = random.randint(1, 120)
    if (pid, cid) in seen_reviews:
        continue
    seen_reviews.add((pid, cid))
    rating     = random.choices([1,2,3,4,5], weights=[2,5,15,40,38], k=1)[0]
    comment    = random.choice(comments)
    created_at = (now - timedelta(days=random.randint(1, 500))).strftime("%Y-%m-%d %H:%M:%S")
    review_rows.append((pid, cid, rating, comment, created_at))

cur.executemany(
    "INSERT INTO reviews (product_id, customer_id, rating, comment, created_at) VALUES (?,?,?,?,?)",
    review_rows,
)

conn.commit()
conn.close()

print(f"[OK] Created: {DB_PATH}")
print()
print("Tables created:")
print("  - categories  : 6 rows")
print(f"  - products    : {len(products)} rows")
print(f"  - customers   : {len(customer_rows)} rows")
print(f"  - orders      : {len(order_rows)} rows")
print(f"  - order_items : {len(item_rows)} rows")
print(f"  - reviews     : {len(review_rows)} rows")
print()
print("Try these natural-language queries in SQL Copilot:")
print('  > Show me the top 10 customers by total revenue')
print('  > What are the best-selling products by quantity sold?')
print('  > Average rating per product category')
print('  > How many orders were placed in each status?')
print('  > Which customers have placed more than 5 orders?')
print('  > Monthly revenue trend for the past 12 months')
