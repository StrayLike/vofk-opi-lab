from flask import Blueprint, jsonify, request, session, g
from db import get_db

api_bp = Blueprint('api', __name__, url_prefix='/api/v1')

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

# --- ДОПОМІЖНА ФУНКЦІЯ ---
def get_user_by_credentials(username, email):
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE username = ? AND email = ?', (username, email)).fetchone()
    return user

# --- СИСТЕМА ---
@api_bp.route('/status', methods=['GET'])
def get_status():
    return jsonify({"status": "ok", "version": "1.0"}), 200

# [ЛАБА 9] Health Check для Docker/Production
@api_bp.route('/health', methods=['GET'])
def get_health():
    try:
        db = get_db()
        db.execute('SELECT 1').fetchone() # Перевірка БД
        return jsonify({"status": "healthy", "database": "connected"}), 200
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 500

# --- ТОВАРИ (PRODUCTS) ---
# [ЛАБА 9] Нова функція: Фільтрація в API
@api_bp.route('/products', methods=['GET'])
def get_products():
    """
    Отримати список товарів (з фільтрацією)
    ---
    parameters:
      - name: category
        in: query
        type: string
        required: false
    """
    category = request.args.get('category')
    db = get_db()
    db.row_factory = dict_factory
    
    if category:
        products = db.execute('SELECT * FROM products WHERE category = ?', (category,)).fetchall()
    else:
        products = db.execute('SELECT * FROM products').fetchall()
        
    return jsonify(products), 200

@api_bp.route('/products', methods=['POST'])
def create_product():
    if session.get('role') != 'admin': return jsonify({"error": "Admin only"}), 403
    data = request.get_json()
    if not data or 'name' not in data or 'price' not in data:
        return jsonify({"error": "Missing name or price"}), 400
    if data['price'] < 0: return jsonify({"error": "Price cannot be negative"}), 400

    db = get_db()
    cursor = db.execute('INSERT INTO products (name, price, category, image) VALUES (?, ?, ?, ?)',
               (data['name'], data['price'], data.get('category', 'General'), data.get('image', '')))
    db.commit()
    return jsonify({"id": cursor.lastrowid, "message": "Created"}), 201

@api_bp.route('/products/<int:id>', methods=['DELETE'])
def delete_product(id):
    if session.get('role') != 'admin': return jsonify({"error": "Unauthorized"}), 403
    db = get_db()
    db.execute('DELETE FROM products WHERE id = ?', (id,))
    db.commit()
    return jsonify({"message": "Deleted"}), 200

# --- ВІДГУКИ (FEEDBACK) ---
@api_bp.route('/feedback', methods=['GET'])
def get_feedbacks():
    db = get_db()
    db.row_factory = dict_factory
    feedbacks = db.execute('SELECT * FROM feedback ORDER BY created_at DESC').fetchall()
    return jsonify(feedbacks), 200

@api_bp.route('/feedback', methods=['POST'])
def create_feedback_api():
    data = request.get_json()
    required_fields = ['username', 'email', 'text', 'rating']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Відсутні обов'язкові поля"}), 400
    if not (1 <= data['rating'] <= 5):
        return jsonify({"error": "Оцінка повинна бути від 1 до 5"}), 400
        
    db = get_db()
    db.execute('INSERT INTO feedback (username, text, rating) VALUES (?, ?, ?)',
               (data['username'], data['text'], data['rating']))
    db.commit()
    return jsonify({"message": "Відгук успішно створено"}), 201

@api_bp.route('/feedback/<int:id>', methods=['DELETE'])
def delete_feedback(id):
    if session.get('role') != 'admin': return jsonify({"error": "Admin only"}), 403
    db = get_db()
    db.execute('DELETE FROM feedback WHERE id = ?', (id,))
    db.commit()
    return jsonify({"message": "Feedback deleted"}), 200

# --- ЗАМОВЛЕННЯ (ORDERS) ---
@api_bp.route('/orders', methods=['POST'])
def create_order_api():
    data = request.get_json()
    required_fields = ['username', 'email', 'items']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Відсутні обов'язкові поля для замовлення"}), 400
        
    user = get_user_by_credentials(data['username'], data['email'])
    if user is None:
        return jsonify({"error": "Користувач з такими ім'ям та email не знайдений."}), 400
        
    user_id = user['id']
    db = get_db()
    total = 0 
    for item in data['items']:
        prod = db.execute('SELECT price FROM products WHERE id = ?', (item['product_id'],)).fetchone()
        if prod: total += prod['price'] * item['quantity']
        
    cursor = db.execute('INSERT INTO orders (user_id, total_price) VALUES (?, ?)', (user_id, total))
    order_id = cursor.lastrowid
    
    for item in data['items']:
        db.execute('INSERT INTO order_items (order_id, product_id, quantity) VALUES (?, ?, ?)',
                   (order_id, item['product_id'], item['quantity']))
    db.commit()
    return jsonify({"order_id": order_id, "total": total, "message": "Замовлення успішно створено"}), 201

@api_bp.route('/orders', methods=['GET'])
def get_all_orders():
    if session.get('role') != 'admin': return jsonify({"error": "Admin only"}), 403
    db = get_db()
    db.row_factory = dict_factory
    orders = db.execute('''
        SELECT o.id, o.total_price, o.created_at, u.username 
        FROM orders o
        JOIN users u ON o.user_id = u.id
        ORDER BY o.created_at DESC
    ''').fetchall()
    return jsonify(orders), 200