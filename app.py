# app.py (повністю оновлений файл)

import os
import functools
from flask import Flask, render_template, request, redirect, url_for, session, flash, g
from werkzeug.security import generate_password_hash, check_password_hash
from db import get_db, close_db, init_db, DATABASE
from flasgger import Swagger
from flask_cors import CORS
from api import api_bp # Припускаємо, що api.py існує і коректний

app = Flask(__name__)
# Ключ з ENV
app.secret_key = os.environ.get('SECRET_KEY', 'stardew_valley_secret_key_change_me')

CORS(app) 
Swagger(app)
app.register_blueprint(api_bp)
app.teardown_appcontext(close_db)

@app.before_request
def load_logged_in_user():
    user_id = session.get('user_id')
    if user_id is None:
        g.user = None
    else:
        g.user = get_db().execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    
    # [ФІКС AttributeError] Якщо кошик - це старий список, скидаємо його до {}
    # Це вирішує помилку, з якою ти зіткнувся.
    if isinstance(session.get('cart'), list):
        session['cart'] = {}
        session.modified = True # Позначаємо, що сесія була змінена

    # [ОНОВЛЕНО] Лічильник тепер сумує кількості товарів у словнику
    g.cart_count = sum(session.get('cart', {}).values())

def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('login'))
        return view(**kwargs)
    return wrapped_view

# --- МАРШРУТИ ---
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

@app.route('/manage')
@login_required
def manage():
    if session.get('role') != 'admin':
        flash("Доступ заборонено!")
        return redirect(url_for('home'))
    return render_template('manage.html')

@app.route('/register', methods=('GET', 'POST'))
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        # 💡 ТИМЧАСОВА ЗМІНА: Додаємо вибір ролі, за замовчуванням 'user'
        role = request.form.get('role', 'user') 
        
        db = get_db()
        error = None
        if not username: error = 'Login required.'
        elif not password: error = 'Password required.'
        if error is None:
            try:
                hashed_pw = generate_password_hash(password)
                # Зберігаємо роль, вибрану користувачем
                db.execute('INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)', 
                           (username, email, hashed_pw, role))
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
            error = 'Incorrect login.'
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

@app.route('/shop')
def shop():
    category = request.args.get('category')
    # [ЛАБА 9] Сортування
    sort_by = request.args.get('sort_by', 'id')
    order = request.args.get('order', 'ASC')

    db = get_db()
    
    valid_sorts = {'price': 'price', 'name': 'name', 'id': 'id'}
    sort_column = valid_sorts.get(sort_by, 'id')
    
    sort_order = 'DESC' if order == 'DESC' else 'ASC'

    query = "SELECT * FROM products"
    params = []

    if category:
        query += " WHERE category = ?"
        params.append(category)
    
    query += f" ORDER BY {sort_column} {sort_order}"

    products = db.execute(query, params).fetchall()
    return render_template('shop.html', products=products, sort_by=sort_by, order=order)

# [ОНОВЛЕНО] Додавання товару: зберігаємо кількість
@app.route('/add_to_cart/<int:id>', methods=('POST',))
def add_to_cart(id):
    id_str = str(id)
    if 'cart' not in session: session['cart'] = {}
    
    # Збільшуємо кількість на 1
    session['cart'][id_str] = session['cart'].get(id_str, 0) + 1
    session.modified = True
    flash("Товар додано до кошика!")
    return redirect(url_for('shop'))

# [ОНОВЛЕНО] Сторінка кошика: читаємо словник
@app.route('/cart')
def cart():
    # cart_items_dict має вигляд {'1': 2, '3': 1}
    cart_items_dict = session.get('cart', {})
    
    db = get_db()
    items_with_count = []
    total = 0
    
    if cart_items_dict:
        # Отримуємо ID товарів, які є в кошику
        product_ids = [int(p_id) for p_id in cart_items_dict.keys()]
        placeholders = ','.join('?' for _ in product_ids)
        
        # Завантажуємо дані про товари з БД
        products = db.execute(f'SELECT * FROM products WHERE id IN ({placeholders})', product_ids).fetchall()
        
        # Готуємо фінальний список з кількістю та проміжною сумою
        for product in products:
            count = cart_items_dict.get(str(product['id']), 0)
            if count > 0:
                items_with_count.append({
                    'id': product['id'],
                    'name': product['name'],
                    'price': product['price'],
                    'image': product['image'],
                    'category': product['category'],
                    'quantity': count, 
                    'subtotal': product['price'] * count
                })
                total += product['price'] * count
    
    return render_template('cart.html', cart_items=items_with_count, total=total)

# [НОВА ФУНКЦІЯ] Зміна кількості в кошику
@app.route('/update_cart_item/<int:id>/<action>', methods=('POST',))
def update_cart_item(id, action):
    id_str = str(id) 
    
    if 'cart' not in session: session['cart'] = {}

    current_count = session['cart'].get(id_str, 0)

    if action == 'increase':
        session['cart'][id_str] = current_count + 1
        flash(f"Кількість товару збільшено.")
    
    elif action == 'decrease':
        if current_count > 1:
            session['cart'][id_str] = current_count - 1
            flash(f"Кількість товару зменшено.")
        elif current_count == 1:
            # Видаляємо товар повністю, якщо кількість 1
            session['cart'].pop(id_str, None) 
            flash(f"Товар видалено з кошика.")
            
    session.modified = True
    return redirect(url_for('cart'))

# [НОВА ФУНКЦІЯ] Очищення кошика
@app.route('/clear_cart', methods=('POST',))
def clear_cart():
    session.pop('cart', None)
    session.modified = True
    flash("Кошик успішно очищено!") # Повідомлення про очищення
    return redirect(url_for('cart'))

# [ОНОВЛЕНО] Оформлення замовлення
@app.route('/checkout', methods=('POST',))
@login_required
def checkout():
    cart_items_dict = session.get('cart', {})
    if not cart_items_dict: 
        flash("Кошик порожній, нічого оформлювати.")
        return redirect(url_for('shop'))
        
    db = get_db()
    
    product_ids = [int(p_id) for p_id in cart_items_dict.keys()]
    placeholders = ','.join('?' for _ in product_ids)
    
    products = db.execute(f'SELECT * FROM products WHERE id IN ({placeholders})', product_ids).fetchall()
    
    total = 0
    # Розраховуємо загальну суму
    for p in products:
        count = cart_items_dict.get(str(p['id']), 0)
        total += p['price'] * count

    # Створюємо замовлення та елементи замовлення
    cursor = db.execute('INSERT INTO orders (user_id, total_price) VALUES (?, ?)', (g.user['id'], total))
    order_id = cursor.lastrowid
    
    for p in products:
        count = cart_items_dict.get(str(p['id']), 0)
        if count > 0:
            db.execute('INSERT INTO order_items (order_id, product_id, quantity) VALUES (?, ?, ?)', (order_id, p['id'], count))
            
    db.commit()
    session.pop('cart', None)
    session.modified = True
    
    # Повідомлення про успішне оформлення
    flash("Замовлення успішно оформлено! Дякуємо за покупку!")
    return redirect(url_for('home'))

@app.route('/feedback', methods=('GET', 'POST'))
def feedback():
    db = get_db()
    if request.method == 'POST':
        if g.user is None: return redirect(url_for('login'))
        text = request.form['text']
        rating = request.form['rating']
        db.execute('INSERT INTO feedback (username, text, rating) VALUES (?, ?, ?)', (g.user['username'], text, rating))
        db.commit()
        return redirect(url_for('feedback'))
    feedbacks = db.execute('SELECT * FROM feedback ORDER BY created_at DESC').fetchall()
    return render_template('feedback.html', feedbacks=feedbacks)

def init_db_on_startup():
    if not os.path.exists(DATABASE): 
        print("💡 База даних не знайдена. Ініціалізація...")
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
                print("✅ АДМІН СТВОРЕНИЙ: admin / admin123")
            except Exception:
                pass

init_db_on_startup()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)