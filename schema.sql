DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS feedback;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS order_items;

-- Таблиця користувачів
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL,
    password TEXT NOT NULL,
    role TEXT DEFAULT 'user'
);

-- Таблиця товарів
CREATE TABLE products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    price REAL NOT NULL,
    category TEXT NOT NULL,
    image TEXT NOT NULL
);

-- Таблиця відгуків
CREATE TABLE feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    text TEXT NOT NULL,
    rating INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблиця замовлень
CREATE TABLE orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    total_price REAL NOT NULL,
    status TEXT DEFAULT 'В обробці',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

-- Деталі замовлення (які саме товари купили)
CREATE TABLE order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER DEFAULT 1,
    FOREIGN KEY (order_id) REFERENCES orders (id),
    FOREIGN KEY (product_id) REFERENCES products (id)
);

-- ЗАПОВНЮЄМО МАГАЗИН ТОВАРАМИ (Початкові дані)
INSERT INTO products (name, price, category, image) VALUES 
('Зоряна крапля', 5000, 'Артефакти', 'https://stardewvalleywiki.com/mediawiki/images/a/a5/Stardrop.png'),
('Блакитна курка', 2000, 'Тварини', 'https://stardewvalleywiki.com/mediawiki/images/f/fd/Blue_Chicken.png'),
('Меч Галактики', 1500, 'Зброя', 'https://stardewvalleywiki.com/mediawiki/images/e/e9/Galaxy_Sword.png'),
('Золотий Гарбуз', 300, 'Насіння', 'https://stardewvalleywiki.com/mediawiki/images/6/64/Pumpkin.png');
