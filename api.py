from flask import Blueprint, jsonify, request, session, g
from db import get_db

# Створюємо Blueprint версії 1
api_bp = Blueprint('api', __name__, url_prefix='/api/v1')

# Допоміжна функція: перетворення рядків БД у словник (JSON)
def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

@api_bp.route('/status', methods=['GET'])
def get_status():
    """
    Перевірка статусу API
    ---
    tags:
      - System
    responses:
      200:
        description: API працює
        schema:
          type: object
          properties:
            status:
              type: string
    """
    return jsonify({"status": "ok", "version": "1.0"})
@api_bp.route('/products', methods=['POST'])
def create_product():
    """
    Створити новий товар
    ---
    tags:
      - Products
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            name:
              type: string
            price:
              type: number
            category:
              type: string
            image:
              type: string
    responses:
      201:
        description: Створено
      400:
        description: Помилка валідації
    """
    if session.get('role') != 'admin':
        return jsonify({"error": "Admin only"}), 403

    data = request.get_json()
    
    # ВАЛІДАЦІЯ
    if not data or 'name' not in data or 'price' not in data:
        return jsonify({"error": "Missing name or price"}), 400
    if data['price'] < 0:
        return jsonify({"error": "Price cannot be negative"}), 400

    db = get_db()
    cursor = db.execute('INSERT INTO products (name, price, category, image) VALUES (?, ?, ?, ?)',
               (data['name'], data['price'], data.get('category', 'General'), data.get('image', '')))
    db.commit()
    
    return jsonify({"id": cursor.lastrowid, "message": "Created"}), 201

@api_bp.route('/products/<int:id>', methods=['PUT'])
def update_product(id):
    """
    Оновити товар
    ---
    tags:
      - Products
    parameters:
      - name: id
        in: path
        type: integer
        required: true
      - name: body
        in: body
        schema:
          type: object
          properties:
            price:
              type: number
    """
    if session.get('role') != 'admin': return jsonify({"error": "Admin only"}), 403
    
    data = request.get_json()
    db = get_db()
    
    if 'price' in data:
        if data['price'] < 0: return jsonify({"error": "Invalid price"}), 400
        db.execute('UPDATE products SET price = ? WHERE id = ?', (data['price'], id))
        db.commit()
        return jsonify({"message": "Updated"}), 200
        
    return jsonify({"error": "Nothing to update"}), 400
# --- ЗАМОВЛЕННЯ ---

@api_bp.route('/orders', methods=['POST'])
def create_order_api():
    """
    Створити замовлення
    ---
    tags:
      - Orders
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            user_id:
              type: integer
            items:
              type: array
              items:
                type: object
                properties:
                  product_id:
                    type: integer
                  quantity:
                    type: integer
    responses:
      201:
        description: Замовлення створено
    """
    data = request.get_json()
    if not data or 'items' not in data:
        return jsonify({"error": "No items provided"}), 400

    db = get_db()
    total = 0 
    # Рахуємо суму
    for item in data['items']:
        prod = db.execute('SELECT price FROM products WHERE id = ?', (item['product_id'],)).fetchone()
        if prod:
            total += prod['price'] * item['quantity']

    cursor = db.execute('INSERT INTO orders (user_id, total_price) VALUES (?, ?)', 
                        (data.get('user_id', 1), total))
    order_id = cursor.lastrowid

    for item in data['items']:
        db.execute('INSERT INTO order_items (order_id, product_id, quantity) VALUES (?, ?, ?)',
                   (order_id, item['product_id'], item['quantity']))
    
    db.commit()
    return jsonify({"order_id": order_id, "total": total, "status": "created"}), 201

@api_bp.route('/orders/<int:id>', methods=['GET'])
def get_order(id):
    """
    Отримати деталі замовлення
    ---
    tags:
      - Orders
    parameters:
      - name: id
        in: path
        required: true
        type: integer
    """
    db = get_db()
    db.row_factory = dict_factory
    order = db.execute('SELECT * FROM orders WHERE id = ?', (id,)).fetchone()
    if order:
        return jsonify(order), 200
    return jsonify({"error": "Order not found"}), 404