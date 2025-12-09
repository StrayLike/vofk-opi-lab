import os
import functools
from flask import Flask, render_template, request, redirect, url_for, session, flash, g
from werkzeug.security import generate_password_hash, check_password_hash
from db import get_db, close_db, init_db, DATABASE
from flasgger import Swagger
from flask_cors import CORS
from api import api_bp

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
        db = get_db()
        error = None
        if not username: error = 'Login required.'
        elif not password: error = 'Password required.'
        if error is None:
            try:
                hashed_pw = generate_password_hash(password)
                db.execute('INSERT INTO users (username, email, password) VALUES (?, ?, ?)', (username, email, hashed_pw))
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
        db.execute('INSERT INTO order_items (order_id, product_id, quantity) VALUES (?, ?, ?)', (order_id, p['id'], count))
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
        db.execute('INSERT INTO feedback (username, text, rating) VALUES (?, ?, ?)', (g.user['username'], text, rating))
        db.commit()
        return redirect(url_for('feedback'))
    feedbacks = db.execute('SELECT * FROM feedback ORDER BY created_at DESC').fetchall()
    return render_template('feedback.html', feedbacks=feedbacks)

# [ЛАБА 8] Функція ініціалізації при старті
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

# Ініціалізація
init_db_on_startup()

if __name__ == '__main__':
    # ВАЖЛИВО: host='0.0.0.0' для доступу через Nginx
    app.run(debug=True, host='0.0.0.0', port=5000)