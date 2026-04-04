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
    c.execute('SELECT COUNT(*) FROM menu')
    if c.fetchone()[0] == 0:
        default_menu = [
            ('drinks', 'beer', 'Murauer vom Fass 0.3l', 'Murauer vom Fass 0.3l', 3.90),
            ('drinks', 'beer', 'Murauer vom Fass 0.5l', 'Murauer vom Fass 0.5l', 4.90),
            ('drinks', 'beer', 'Radler 0.5l', 'Radler 0.5l', 4.90),
            ('drinks', 'beer', 'Tegernseer 0.5l', 'Tegernseer 0.5l', 4.90),
            ('drinks', 'beer', 'Alkoholfreies Bier 0.5l', 'Alkoholfreies Bier 0.5l', 4.90),
            ('drinks', 'beer', 'Japanische Biere 0.33l', 'Div. Japanische Biere 0.33l', 4.60),
            ('drinks', 'wine', 'Gruener Veltliner Hauswein 1/8l', 'Gruener Veltliner Hauswein', 3.50),
            ('drinks', 'wine', 'Rheinriesling 1/8l', 'Rheinriesling', 3.80),
            ('drinks', 'wine', 'Chardonnay 1/8l', 'Chardonnay', 3.80),
            ('drinks', 'wine', 'Roter Hoellenpfad Hauswein 1/8l', 'Roter Hoellenpfad Hauswein', 3.50),
            ('drinks', 'wine', 'Blauer Zweigelt 1/8l', 'Blauer Zweigelt', 3.80),
            ('drinks', 'wine', 'Zweigelt Rose 1/8l', 'Zweigelt Rose', 3.90),
            ('drinks', 'wine', 'Frizzante Fritz Pittner 0.1l', 'Frizzante Fritz Pittner', 3.80),
            ('drinks', 'cocktail', 'Espresso Martini', 'Espresso Martini', 8.90),
            ('drinks', 'cocktail', 'Cosmopolitan', 'Cosmopolitan', 8.90),
            ('drinks', 'cocktail', 'Negroni', 'Negroni', 8.50),
            ('drinks', 'cocktail', 'Gimlet', 'Gimlet', 8.50),
            ('drinks', 'cocktail', 'Whiskey Sour', 'Whiskey Sour', 8.50),
            ('drinks', 'cocktail', 'Old Fashioned', 'Old Fashioned', 8.50),
            ('drinks', 'cocktail', 'Gin Tonic', 'Gin Tonic', 7.50),
            ('drinks', 'cocktail', 'Whiskey Rum Cola', 'Whiskey/Rum & Cola', 7.50),
            ('drinks', 'cocktail', 'Campari Soda', 'Campari Soda', 5.70),
            ('drinks', 'cocktail', 'Campari Orange', 'Campari Orange', 6.90),
            ('drinks', 'cocktail', 'Weisser Spritzer 1/4l', 'Weisser Spritzer', 3.80),
            ('drinks', 'cocktail', 'Kaiser Spritzer 1/4l', 'Kaiser Spritzer', 4.30),
            ('drinks', 'cocktail', 'Veilchen Spritzer 1/4l', 'Veilchen Spritzer', 4.30),
            ('drinks', 'cocktail', 'Aperol Spritzer 1/4l', 'Aperol Spritzer', 6.50),
            ('drinks', 'cocktail', 'Lillet Spritzer 1/4l', 'Lillet Spritzer', 5.50),
            ('drinks', 'cocktail', 'Mr Du Wermut Tonic 1/4l', 'Mr Du Wermut Tonic', 7.50),
            ('drinks', 'whisky', 'Vodka Absolut 2cl', 'Vodka Absolut 2cl', 3.50),
            ('drinks', 'whisky', 'Jaegermeister 2cl', 'Jaegermeister 2cl', 3.50),
            ('drinks', 'whisky', 'Berliner Luft 2cl', 'Berliner Luft 2cl', 3.50),
            ('drinks', 'whisky', 'Averna 2cl', 'Averna 2cl', 3.50),
            ('drinks', 'whisky', 'Rum 2cl', 'Rum 2cl', 3.50),
            ('drinks', 'whisky', 'Tequila 2cl', 'Tequila 2cl', 3.50),
            ('drinks', 'coffee', 'Espresso', 'Espresso', 2.90),
            ('drinks', 'coffee', 'Doppelter Espresso', 'Doppelter Espresso', 4.80),
            ('drinks', 'coffee', 'Melange Cappuccino', 'Melange / Cappuccino', 4.20),
            ('drinks', 'coffee', 'Latte Machiato', 'Latte Machiato', 5.00),
            ('drinks', 'coffee', 'Verlaengerter Caffe americano', 'Verlaengerter', 3.80),
            ('drinks', 'coffee', 'Iced Coffee', 'Iced Coffee', 3.80),
            ('drinks', 'coffee', 'Affogato al caffe', 'Affogato al caffe', 4.50),
            ('drinks', 'coffee', 'Schwarzer Tee Black Tea', 'Schwarzer Tee', 3.80),
            ('drinks', 'coffee', 'Gruener Tee Green Tea', 'Gruener Tee', 3.80),
            ('drinks', 'soft', 'Roemerquelle 0.33l', 'Roemerquelle still 0.33l', 3.30),
            ('drinks', 'soft', 'Roemerquelle 0.75l', 'Roemerquelle 0.75l', 5.70),
            ('drinks', 'soft', 'Coca-Cola 0.33l', 'Coca-Cola 0.33l', 3.60),
            ('drinks', 'soft', 'Fructade 0.35l', 'Fructade 0.35l', 3.60),
            ('drinks', 'soft', 'Yuzuka 0.33l', 'Yuzuka 0.33l', 5.50),
            ('drinks', 'soft', 'Schweppes Tonic Water 0.2l', 'Schweppes Tonic Water', 3.50),
            ('drinks', 'soft', 'Aloe Vera 0.5l', 'Aloe Vera 0.5l', 3.80),
            ('drinks', 'soft', 'Kokossaft Coco-Juice 0.25l', 'Kokossaft 0.25l', 3.80),
            ('drinks', 'soft', 'Fruchtsaft 0.25l', 'Fruchtsaft 0.25l', 3.50),
            ('drinks', 'soft', 'Sodawasser 0.25l', 'Sodawasser 0.25l', 1.70),
            ('drinks', 'soft', 'Soda Zitrone Himbeer Holunder 0.25l', 'Soda Zitrone 0.25l', 3.00),
            ('drinks', 'soft', 'Calpis 0.25l', 'Calpis 0.25l', 4.20),
            ('drinks', 'soft', 'Calpis 0.5l', 'Calpis 0.5l', 6.25),
            ('drinks', 'homemade', 'Ice Tea Green Melon 0.5l', 'Ice Tea Green Melon', 5.90),
            ('drinks', 'homemade', 'Ice Tea Strawberry 0.5l', 'Ice Tea Strawberry', 5.90),
            ('drinks', 'homemade', 'Ice Tea Lemon 0.5l', 'Ice Tea Lemon', 5.90),
            ('drinks', 'homemade', 'Ice Tea Peach 0.5l', 'Ice Tea Peach', 5.90),
            ('drinks', 'homemade', 'Ice Tea Lychee 0.5l', 'Ice Tea Lychee', 5.90),
            ('drinks', 'homemade', 'Ice Tea Apple 0.5l', 'Ice Tea Apple', 5.90),
            ('drinks', 'homemade', 'Lemonade Grape 0.5l', 'Lemonade Grape', 5.50),
            ('drinks', 'homemade', 'Lemonade Passion Fruit 0.5l', 'Lemonade Passion Fruit', 5.50),
            ('drinks', 'homemade', 'Lemonade Mango 0.5l', 'Lemonade Mango', 5.50),
            ('drinks', 'homemade', 'Lemonade Orange 0.5l', 'Lemonade Orange', 5.50),
            ('drinks', 'homemade', 'Lemonade Blueberry 0.5l', 'Lemonade Blueberry', 5.50),
            ('drinks', 'homemade', 'Lemonade Lemon 0.5l', 'Lemonade Lemon', 5.50),
            ('drinks', 'sake', 'Japanischer Sake auf Anfrage', 'Japanischer Sake auf Anfrage', 0.00),
            ('starters', 'starters', 'Edamame gesalzene Sojabohnen', 'Edamame', 4.90),
            ('starters', 'starters', 'Cucumber Salad Gurkensalat', 'Gurkensalat', 4.50),
            ('starters', 'starters', 'Mamasalad Chinakohl Seetang', 'Chinakohl Salat', 4.90),
            ('starters', 'starters', 'KIMCHI WAKAME SALAT', 'KIMCHI/WAKAME SALAT', 4.90),
            ('starters', 'starters', 'KIMCH-Rettich', 'KIMCH-Rettich', 4.50),
            ('starters', 'starters', 'Miso Suppe', 'Miso Suppe', 4.80),
            ('starters', 'starters', 'Tom Yum Goong Garnelen Kokosmilch', 'Tom Yum Goong', 7.80),
            ('starters', 'starters', 'Agedashi Tofu', 'Agedashi Tofu', 6.50),
            ('starters', 'starters', 'Spring Rolls Fruehlingsrollen 6St', 'Fruehlingtsrollen 6St', 5.50),
            ('starters', 'starters', 'Home made Steamed Meat Buns', 'Fleischbroetchen', 6.90),
            ('starters', 'starters', 'Gyoza Teigflaschen 6St', 'Gyoza 6St', 5.90),
            ('starters', 'starters', 'Tempura Frittierte Shrimps 4St', 'Tempura Shrimps 4St', 6.90),
            ('starters', 'starters', 'Takoyaki Frittierte Oktopusbaellchen 5St', 'Takoyaki 5St', 6.90),
            ('starters', 'starters', 'Karaage Frittierte Huehnchen Mayonnaise', 'Karaage Huehnchen', 6.90),
            ('starters', 'starters', 'Fried Chicken Teriyaki', 'Fried Chicken Teriyaki', 7.50),
            ('mains', 'ramen', 'Pork Ramen Schweinefleisch', 'Pork Ramen', 13.90),
            ('mains', 'ramen', 'Spicy Beef Ramen Rindfleisch Mais', 'Spicy Beef Ramen', 14.90),
            ('mains', 'ramen', 'Chicken Ramen Huehnerfleisch Ei', 'Chicken Ramen', 13.90),
            ('mains', 'ramen', 'Vegetarische Ramen Gemuesesorten', 'Vegetarische Ramen', 13.90),
            ('mains', 'ramen', 'GYUDON Rindfleisch Zwiebel Reis', 'GYUDON Rindfleisch Reis', 14.90),
            ('mains', 'ramen', 'TERIYAKI TELLER Haehnchen Gemuese', 'TERIYAKI Haehnchen Teller', 13.90),
            ('mains', 'ramen', 'Reisschuessel Haehnchen Gemuese', 'Reisschuessel Haehnchen', 13.90),
            ('mains', 'ramen', 'Grilled Eel Rice Gebratener Aal Reis 100g', 'Gebratener Aal mit Reis 100g', 19.80),
            ('mains', 'ramen', 'Grilled Eel Rice Gebratener Aal Reis 200g', 'Gebratener Aal mit Reis 200g', 29.80),
            ('mains', 'ramen', 'Tofu Gemuese', 'Tofu mit Gemuese', 13.90),
            ('mains', 'sides', 'Extra Marinated Egg Mariniertes Ei', 'Mariniertes Ei', 3.20),
            ('mains', 'sides', '2 Stk Chashu Schweinebauch', 'Chashu 2 Stk', 3.90),
            ('mains', 'sides', '2 Stk Shrimp Wan Tan', 'Shrimp Wan Tan 2 Stk', 3.50),
            ('mains', 'sides', 'Soft Marinated Egg', 'Soft Marinated Egg', 3.80),
            ('mains', 'sides', 'Extra Noodles', 'Extra Noodles', 3.50),
            ('mains', 'sides', 'Tofu', 'Tofu', 3.90),
            ('mains', 'sides', 'Marinated Bamboo', 'Marinated Bamboo', 1.20),
            ('desserts', 'desserts', 'Matcha Mochi kleine Mochi Ice 2 Stk', 'Matcha Mochi 2 Stk', 6.50),
            ('desserts', 'desserts', 'YAMAMOTOYA DAIFUKU Reiskuchen Sesam 5St', 'YAMAMOTOYA DAIFUKU', 6.90),
            ('desserts', 'desserts', 'Reisknoedel Sesamfuellung 5St', 'Reisknoedel mit Sesam', 3.80),
            ('desserts', 'desserts', 'Mango Sago Milch Koksmilch Mango Banane', 'Mango Sago', 7.50),
        ]
        c.executemany('INSERT INTO menu (category, subcategory, name, name_de, price) VALUES (?, ?, ?, ?, ?)', default_menu)
    conn.commit()
    conn.close()

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

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
    item_type = data.get('type', 'all')
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
