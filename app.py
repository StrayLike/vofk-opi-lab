import os
import functools
from flask import Flask, render_template, request, redirect, url_for, session, flash, g
from werkzeug.security import generate_password_hash, check_password_hash
from db import get_db, close_db, init_db
from flasgger import Swagger
from flask_cors import CORS  # [ЛАБА 6] Бібліотека для CORS
from api import api_bp       # Імпорт нашого API Blueprint

app = Flask(__name__)
app.secret_key = 'stardew_valley_secret_key_change_me'

# --- [ЛАБА 6] ІНІЦІАЛІЗАЦІЯ ---
CORS(app) # Активація CORS

# Документація API
Swagger(app)

# Реєстрація API Blueprint (підключаємо api.py)
app.register_blueprint(api_bp)

# Закриття з'єднання з БД
app.teardown_appcontext(close_db)

# --- АВТОРИЗАЦІЯ (Завантаження користувача) ---
@app.before_request
def load_logged_in_user():
    user_id = session.get('user_id')
    if user_id is None:
        g.user = None
    else:
        g.user = get_db().execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()

# Декоратор для захисту сторінок
def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('login'))
        return view(**kwargs)
    return wrapped_view

# --- ГОЛОВНІ СТОРІНКИ ---
@app.route('/')
def home(): return render_template('home.html')

@app.route('/about')
def about(): return render_template('about.html')

@app.route('/guides')
def guides(): return render_template('guides.html') 

@app.route('/characters')
def characters(): return render_template('characters.html')
    
@app.route('/map')
def map(): return render_template('map.html')

# --- [ЛАБА 6] АДМІН-ПАНЕЛЬ ---
@app.route('/manage')
@login_required
def manage():
    # 1. Перевірка: тільки адмін може сюди зайти
    if session.get('role') != 'admin':
        flash("Доступ заборонено! Це сторінка для адміністратора.")
        return redirect(url_for('home'))
    
    # 2. Рендеринг шаблону адмінки (переконайся, що файл manage.html існує!)
    return render_template('manage.html')

# --- РЕЄСТРАЦІЯ ТА ВХІД ---
@app.route('/register', methods=('GET', 'POST'))
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        db = get_db()
        error = None
        if not username: error = 'Login required.'
        elif not password: error = 'Password required.'
        
        if error is None:
            try:
                hashed_pw = generate_password_hash(password)
                db.execute('INSERT INTO users (username, email, password) VALUES (?, ?, ?)',
                           (username, email, hashed_pw))
                db.commit()
                return redirect(url_for('login'))
            except db.IntegrityError:
                error = f"User {username} already exists."
        flash(error)
    return render_template('register.html')

@app.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        error = None
        user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        
        if user is None or not check_password_hash(user['password'], password):
            error = 'Incorrect login or password.'
        
        if error is None:
            session.clear()
            session['user_id'] = user['id']
            session['role'] = user['role']
            return redirect(url_for('home'))
        
        flash(error)
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# --- МАГАЗИН І КОШИК ---
@app.route('/shop')
def shop():
    category = request.args.get('category')
    db = get_db()
    if category:
        products = db.execute('SELECT * FROM products WHERE category = ?', (category,)).fetchall()
    else:
        products = db.execute('SELECT * FROM products').fetchall()
    return render_template('shop.html', products=products)

@app.route('/add_to_cart/<int:id>', methods=('POST',))
def add_to_cart(id):
    if 'cart' not in session: session['cart'] = []
    session['cart'].append(id)
    session.modified = True
    return redirect(url_for('shop'))

@app.route('/cart')
def cart():
    cart_ids = session.get('cart', [])
    db = get_db()
    items = []
    total = 0
    if cart_ids:
        placeholders = ','.join('?' for _ in cart_ids)
        items = db.execute(f'SELECT * FROM products WHERE id IN ({placeholders})', cart_ids).fetchall()
        for item in items:
            count = cart_ids.count(item['id'])
            total += item['price'] * count
    return render_template('cart.html', cart_items=items, total=total)

@app.route('/checkout', methods=('POST',))
@login_required
def checkout():
    cart_ids = session.get('cart', [])
    if not cart_ids: return redirect(url_for('shop'))
    db = get_db()
    placeholders = ','.join('?' for _ in cart_ids)
    products = db.execute(f'SELECT * FROM products WHERE id IN ({placeholders})', cart_ids).fetchall()
    total = sum(p['price'] * cart_ids.count(p['id']) for p in products)
    
    cursor = db.execute('INSERT INTO orders (user_id, total_price) VALUES (?, ?)', (g.user['id'], total))
    order_id = cursor.lastrowid
    
    for p in products:
        count = cart_ids.count(p['id'])
        db.execute('INSERT INTO order_items (order_id, product_id, quantity) VALUES (?, ?, ?)',
                   (order_id, p['id'], count))
    db.commit()
    
    session.pop('cart', None)
    return redirect(url_for('home'))

@app.route('/feedback', methods=('GET', 'POST'))
def feedback():
    db = get_db()
    if request.method == 'POST':
        if g.user is None: return redirect(url_for('login'))
        text = request.form['text']
        rating = request.form['rating']
        db.execute('INSERT INTO feedback (username, text, rating) VALUES (?, ?, ?)',
                   (g.user['username'], text, rating))
        db.commit()
        return redirect(url_for('feedback'))
    feedbacks = db.execute('SELECT * FROM feedback ORDER BY created_at DESC').fetchall()
    return render_template('feedback.html', feedbacks=feedbacks)

# --- ЗАПУСК ДОДАТКА ---
if __name__ == '__main__':
    # Якщо бази немає, створюємо її та адміна
    if not os.path.exists('database.db'): 
        init_db()
        with app.app_context():
            db = get_db()
            hashed_pw = generate_password_hash('admin123')
            try:
                db.execute(
                    'INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)',
                    ('admin', 'admin@stardew.com', hashed_pw, 'admin')
                )
                db.commit()
                print("✅ АДМІНІСТРАТОР СТВОРЕНИЙ: Логін: admin, Пароль: admin123")
            except Exception as e:
                print(f"Адмін вже існує або помилка: {e}")

    app.run(debug=True)