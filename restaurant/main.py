from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import json
import os
from datetime import datetime
import sqlite3

app = Flask(__name__)
app.config['SECRET_KEY'] = 'restaurant2026'
socketio = SocketIO(app, cors_allowed_origins="*")

DB_PATH = 'restaurant.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS tables (
        id INTEGER PRIMARY KEY,
        name TEXT,
        zone TEXT,
        status TEXT DEFAULT 'free'
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        table_id INTEGER,
        table_name TEXT,
        zone TEXT,
        items TEXT,
        status TEXT DEFAULT 'pending',
        created_at TEXT,
        notes TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS menu (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT,
        subcategory TEXT,
        name TEXT,
        name_de TEXT,
        price REAL
    )''')
    
    # 初始化桌号
    c.execute('SELECT COUNT(*) FROM tables')
    if c.fetchone()[0] == 0:
        tables = []
        for i in range(1, 6):
            tables.append((f'前厅{i}号', 'indoor'))
        for i in range(1, 5):
            tables.append((f'吧台{i}号', 'bar'))
        for i in range(1, 9):
            tables.append((f'内厅{i}号', 'inner'))
        for i in range(1, 11):
            tables.append((f'花园{i}号', 'garden'))
        tables.append(('打包', 'takeaway'))
        
        for t in tables:
            c.execute('INSERT INTO tables (name, zone, status) VALUES (?, ?, "free")', t)
    
    # 初始化菜单
    c.execute('SELECT COUNT(*) FROM menu')
    if c.fetchone()[0] == 0:
        default_menu = [
            # 酒水
            ('drinks', 'beer', '生啤', 'Fassbier', 4.50),
            ('drinks', 'beer', '瓶装啤酒', 'Flaschenbier', 3.50),
            ('drinks', 'wine', '红葡萄酒', 'Rotwein', 6.00),
            ('drinks', 'wine', '白葡萄酒', 'Weißwein', 6.00),
            ('drinks', 'sake', '日本清酒', 'Japanischer Sake', 7.00),
            ('drinks', 'whisky', '威士忌', 'Whisky', 8.00),
            ('drinks', 'cocktail', '鸡尾酒', 'Cocktail', 9.00),
            ('drinks', 'soft', '可乐', 'Cola', 3.00),
            ('drinks', 'soft', '矿泉水', 'Mineralwasser', 2.50),
            ('drinks', 'coffee', '美式咖啡', 'Americano', 3.50),
            ('drinks', 'coffee', '拿铁', 'Latte', 4.00),
            ('drinks', 'homemade', '自制柠檬水', 'Hausgemachte Limonade', 4.50),
            # 前菜
            ('starters', 'starters', '毛豆', 'Edamame', 4.00),
            ('starters', 'starters', '饺子', 'Gyoza', 7.00),
            ('starters', 'starters', '炸鸡翅', 'Gebratene Hühnerflügel', 8.00),
            # 主食/拉面
            ('mains', 'ramen', '酱油拉面', 'Shoyu Ramen', 13.50),
            ('mains', 'ramen', '味噌拉面', 'Miso Ramen', 13.50),
            ('mains', 'ramen', '豚骨拉面', 'Tonkotsu Ramen', 14.00),
            ('mains', 'ramen', '素食拉面', 'Veganes Ramen', 12.50),
            # 配菜
            ('mains', 'sides', '加蛋', 'Extra Ei', 1.50),
            ('mains', 'sides', '加叉烧', 'Extra Chashu', 3.00),
            ('mains', 'sides', '加葱', 'Extra Frühlingszwiebeln', 0.50),
            ('mains', 'sides', '不加辣', 'Ohne Schärfe', 0.00),
            # 甜品
            ('desserts', 'desserts', '抹茶冰淇淋', 'Matcha-Eis', 5.00),
            ('desserts', 'desserts', '麻薯', 'Mochi', 4.50),
            ('desserts', 'desserts', '芝士蛋糕', 'Käsekuchen', 5.50),
        ]
        c.executemany('INSERT INTO menu (category, subcategory, name, name_de, price) VALUES (?, ?, ?, ?, ?)', default_menu)
    
    conn.commit()
    conn.close()

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ==================== 路由 ====================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/order/<int:table_id>')
def order(table_id):
    return render_template('order.html', table_id=table_id)

@app.route('/kitchen')
def kitchen():
    return render_template('kitchen.html')

@app.route('/bar')
def bar():
    return render_template('bar.html')

@app.route('/admin')
def admin():
    return render_template('admin.html')

# ==================== API ====================

@app.route('/api/tables')
def get_tables():
    conn = get_db()
    tables = conn.execute('SELECT * FROM tables').fetchall()
    conn.close()
    return jsonify([dict(t) for t in tables])

@app.route('/api/table/<int:table_id>')
def get_table(table_id):
    conn = get_db()
    table = conn.execute('SELECT * FROM tables WHERE id=?', (table_id,)).fetchone()
    orders = conn.execute('SELECT * FROM orders WHERE table_id=? AND status != "paid" ORDER BY created_at DESC', (table_id,)).fetchall()
    conn.close()
    return jsonify({'table': dict(table), 'orders': [dict(o) for o in orders]})

@app.route('/api/menu')
def get_menu():
    conn = get_db()
    items = conn.execute('SELECT * FROM menu ORDER BY category, subcategory').fetchall()
    conn.close()
    return jsonify([dict(i) for i in items])

@app.route('/api/order', methods=['POST'])
def place_order():
    data = request.json
    conn = get_db()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    items_json = json.dumps(data['items'], ensure_ascii=False)
    
    conn.execute('''INSERT INTO orders (table_id, table_name, zone, items, status, created_at, notes)
                    VALUES (?, ?, ?, ?, "pending", ?, ?)''',
                 (data['table_id'], data['table_name'], data['zone'], items_json, now, data.get('notes', '')))
    
    conn.execute('UPDATE tables SET status="occupied" WHERE id=?', (data['table_id'],))
    conn.commit()
    
    order_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
    conn.close()
    
    order_data = {
        'id': order_id,
        'table_id': data['table_id'],
        'table_name': data['table_name'],
        'zone': data['zone'],
        'items': data['items'],
        'created_at': now,
        'notes': data.get('notes', '')
    }
    
    socketio.emit('new_order', order_data)
    return jsonify({'success': True, 'order_id': order_id})

@app.route('/api/order/<int:order_id>/complete', methods=['POST'])
def complete_order(order_id):
    data = request.json
    item_type = data.get('type', 'all')  # 'kitchen' or 'bar'
    conn = get_db()
    
    if item_type == 'kitchen':
        conn.execute('UPDATE orders SET status="kitchen_done" WHERE id=?', (order_id,))
    elif item_type == 'bar':
        conn.execute('UPDATE orders SET status="bar_done" WHERE id=?', (order_id,))
    else:
        conn.execute('UPDATE orders SET status="done" WHERE id=?', (order_id,))
    
    conn.commit()
    conn.close()
    socketio.emit('order_updated', {'order_id': order_id, 'type': item_type})
    return jsonify({'success': True})

@app.route('/api/table/<int:table_id>/checkout', methods=['POST'])
def checkout(table_id):
    conn = get_db()
    conn.execute('UPDATE orders SET status="paid" WHERE table_id=?', (table_id,))
    conn.execute('UPDATE tables SET status="free" WHERE id=?', (table_id,))
    conn.commit()
    conn.close()
    socketio.emit('table_updated', {'table_id': table_id, 'status': 'free'})
    return jsonify({'success': True})

@app.route('/api/table/swap', methods=['POST'])
def swap_tables():
    data = request.json
    from_id = data['from_id']
    to_id = data['to_id']
    conn = get_db()
    conn.execute('UPDATE orders SET table_id=? WHERE table_id=? AND status != "paid"', (to_id, from_id))
    conn.execute('UPDATE tables SET status="occupied" WHERE id=?', (to_id,))
    conn.execute('UPDATE tables SET status="free" WHERE id=?', (from_id,))
    conn.commit()
    conn.close()
    socketio.emit('tables_swapped', {'from_id': from_id, 'to_id': to_id})
    return jsonify({'success': True})

@app.route('/api/menu/update', methods=['POST'])
def update_menu():
    data = request.json
    conn = get_db()
    if data.get('id'):
        conn.execute('UPDATE menu SET name=?, name_de=?, price=?, category=?, subcategory=? WHERE id=?',
                     (data['name'], data['name_de'], data['price'], data['category'], data['subcategory'], data['id']))
    else:
        conn.execute('INSERT INTO menu (category, subcategory, name, name_de, price) VALUES (?, ?, ?, ?, ?)',
                     (data['category'], data['subcategory'], data['name'], data['name_de'], data['price']))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/menu/<int:item_id>', methods=['DELETE'])
def delete_menu_item(item_id):
    conn = get_db()
    conn.execute('DELETE FROM menu WHERE id=?', (item_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/kitchen/orders')
def kitchen_orders():
    conn = get_db()
    orders = conn.execute('''SELECT * FROM orders WHERE status IN ("pending", "kitchen_done") 
                             ORDER BY created_at ASC''').fetchall()
    conn.close()
    result = []
    for o in orders:
        od = dict(o)
        od['items'] = json.loads(od['items'])
        result.append(od)
    return jsonify(result)

@app.route('/api/bar/orders')
def bar_orders():
    conn = get_db()
    orders = conn.execute('''SELECT * FROM orders WHERE status IN ("pending", "bar_done") 
                             ORDER BY created_at ASC''').fetchall()
    conn.close()
    result = []
    for o in orders:
        od = dict(o)
        od['items'] = json.loads(od['items'])
        result.append(od)
    return jsonify(result)

if __name__ == '__main__':
    init_db()
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
