from flask import Flask, render_template, request, jsonify, session, redirect
from flask_socketio import SocketIO, emit
from functools import wraps
import json
import os
from datetime import datetime
import sqlite3

app = Flask(__name__)
app.config['SECRET_KEY'] = 'restaurant2026_mrdu_secret'
socketio = SocketIO(app, cors_allowed_origins="*")

DB_PATH = 'restaurant.db'

# ==================== 密码 ====================
STAFF_PASSWORD = 'ramen2026'
ADMIN_PASSWORD = 'djj19851204'

# 连入设备追踪
connected_devices = {}

# ==================== 登录验证 ====================
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect('/login')
        if session.get('role') != 'admin':
            return redirect('/')
        return f(*args, **kwargs)
    return decorated

# ==================== 数据库 ====================
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
        kitchen_status TEXT DEFAULT 'pending',
        bar_status TEXT DEFAULT 'pending',
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
            ('drinks','beer','生啤 0.3l','Murauer vom Fass 0.3l',3.90),
            ('drinks','beer','生啤 0.5l','Murauer vom Fass 0.5l',4.90),
            ('drinks','beer','Radler 0.5l','Radler 0.5l',4.90),
            ('drinks','beer','Tegernseer 0.5l','Tegernseer 0.5l',4.90),
            ('drinks','beer','无醇啤酒 0.5l','Alkoholfreies Bier 0.5l',4.90),
            ('drinks','beer','日本啤酒 0.33l','Div. Japanische Biere 0.33l',4.60),
            ('drinks','wine','青威特 1/8l','Gruener Veltliner Hauswein',3.50),
            ('drinks','wine','莱茵雷司令 1/8l','Rheinriesling',3.80),
            ('drinks','wine','霞多丽 1/8l','Chardonnay',3.80),
            ('drinks','wine','红葡萄酒 1/8l','Roter Hoellenpfad Hauswein',3.50),
            ('drinks','wine','蓝茨威格 1/8l','Blauer Zweigelt',3.80),
            ('drinks','wine','玫瑰红 1/8l','Zweigelt Rose',3.90),
            ('drinks','wine','起泡酒 0.1l','Frizzante Fritz Pittner',3.80),
            ('drinks','cocktail','浓缩咖啡马提尼','Espresso Martini',8.90),
            ('drinks','cocktail','大都会','Cosmopolitan',8.90),
            ('drinks','cocktail','内格罗尼','Negroni',8.50),
            ('drinks','cocktail','吉姆雷特','Gimlet',8.50),
            ('drinks','cocktail','威士忌酸','Whiskey Sour',8.50),
            ('drinks','cocktail','古典鸡尾酒','Old Fashioned',8.50),
            ('drinks','cocktail','金汤力','Gin Tonic',7.50),
            ('drinks','cocktail','威/朗姆可乐','Whiskey/Rum & Cola',7.50),
            ('drinks','cocktail','金巴利苏打','Campari Soda',5.70),
            ('drinks','cocktail','金巴利橙汁','Campari Orange',6.90),
            ('drinks','cocktail','白葡萄气泡 1/4l','Weisser Spritzer',3.80),
            ('drinks','cocktail','凯撒气泡 1/4l','Kaiser Spritzer',4.30),
            ('drinks','cocktail','紫罗兰气泡 1/4l','Veilchen Spritzer',4.30),
            ('drinks','cocktail','阿佩罗气泡 1/4l','Aperol Spritzer',6.50),
            ('drinks','cocktail','利莱气泡 1/4l','Lillet Spritzer',5.50),
            ('drinks','cocktail','杜先生苦艾 1/4l',"Mr. Du's Wermut Tonic",7.50),
            ('drinks','whisky','伏特加 2cl','Vodka Absolut 2cl',3.50),
            ('drinks','whisky','猎人 2cl','Jaegermeister 2cl',3.50),
            ('drinks','whisky','柏林之风 2cl','Berliner Luft 2cl',3.50),
            ('drinks','whisky','阿维纳 2cl','Averna 2cl',3.50),
            ('drinks','whisky','朗姆 2cl','Rum 2cl',3.50),
            ('drinks','whisky','龙舌兰 2cl','Tequila 2cl',3.50),
            ('drinks','coffee','浓缩咖啡','Espresso',2.90),
            ('drinks','coffee','双份浓缩','Doppelter Espresso',4.80),
            ('drinks','coffee','卡布奇诺','Melange / Cappuccino',4.20),
            ('drinks','coffee','拿铁','Latte Machiato',5.00),
            ('drinks','coffee','美式','Verlaengerter / Caffe americano',3.80),
            ('drinks','coffee','冰咖啡','Iced Coffee',3.80),
            ('drinks','coffee','阿芙佳朵','Affogato al caffe',4.50),
            ('drinks','coffee','红茶','Schwarzer Tee / Black Tea',3.80),
            ('drinks','coffee','绿茶','Gruener Tee / Green Tea',3.80),
            ('drinks','soft','矿泉水 0.33l','Roemerquelle 0.33l',3.30),
            ('drinks','soft','矿泉水 0.75l','Roemerquelle 0.75l',5.70),
            ('drinks','soft','可乐 0.33l','Coca-Cola 0.33l',3.60),
            ('drinks','soft','果汁饮料 0.35l','Fructade 0.35l',3.60),
            ('drinks','soft','柚子卡 0.33l','Yuzuka 0.33l',5.50),
            ('drinks','soft','汤力水 0.2l','Schweppes Tonic Water',3.50),
            ('drinks','soft','芦荟汁 0.5l','Aloe Vera 0.5l',3.80),
            ('drinks','soft','椰子汁 0.25l','Kokossaft 0.25l',3.80),
            ('drinks','soft','果汁 0.25l','Fruchtsaft 0.25l',3.50),
            ('drinks','soft','苏打水 0.25l','Sodawasser 0.25l',1.70),
            ('drinks','soft','苏打柠檬 0.25l','Soda Zitrone 0.25l',3.00),
            ('drinks','soft','卡尔必思 0.25l','Calpis 0.25l',4.20),
            ('drinks','soft','卡尔必思 0.5l','Calpis 0.5l',6.25),
            ('drinks','homemade','冰茶蜜瓜 0.5l','Ice Tea Green Melon',5.90),
            ('drinks','homemade','冰茶草莓 0.5l','Ice Tea Strawberry',5.90),
            ('drinks','homemade','冰茶柠檬 0.5l','Ice Tea Lemon',5.90),
            ('drinks','homemade','冰茶水蜜桃 0.5l','Ice Tea Peach',5.90),
            ('drinks','homemade','冰茶荔枝 0.5l','Ice Tea Lychee',5.90),
            ('drinks','homemade','冰茶苹果 0.5l','Ice Tea Apple',5.90),
            ('drinks','homemade','柠檬水葡萄 0.5l','Lemonade Grape',5.50),
            ('drinks','homemade','柠檬水百香果 0.5l','Lemonade Passion Fruit',5.50),
            ('drinks','homemade','柠檬水芒果 0.5l','Lemonade Mango',5.50),
            ('drinks','homemade','柠檬水橙子 0.5l','Lemonade Orange',5.50),
            ('drinks','homemade','柠檬水蓝莓 0.5l','Lemonade Blueberry',5.50),
            ('drinks','homemade','柠檬水柠檬 0.5l','Lemonade Lemon',5.50),
            ('drinks','sake','清酒 按需','Japanischer Sake auf Anfrage',0.00),
            ('starters','starters','毛豆','Edamame',4.90),
            ('starters','starters','黄瓜沙拉','Cucumber Salad / Gurkensalat',4.50),
            ('starters','starters','妈妈沙拉','Mamasalad / Chinakohl Seetang',4.90),
            ('starters','starters','泡菜/裙带菜沙拉','KIMCHI/WAKAME SALAT',4.90),
            ('starters','starters','泡菜萝卜','KIMCH-Rettich',4.50),
            ('starters','starters','味噌汤','Miso Suppe',4.80),
            ('starters','starters','东阴功汤','Tom Yum Goong',7.80),
            ('starters','starters','炸豆腐','Agedashi Tofu',6.50),
            ('starters','starters','春卷 6个','Fruehlingtsrollen 6St',5.50),
            ('starters','starters','小笼包','Home made Steamed Meat Buns',6.90),
            ('starters','starters','饺子 6个','Gyoza 6St',5.90),
            ('starters','starters','天妇罗虾 4个','Tempura Shrimps 4St',6.90),
            ('starters','starters','章鱼烧 5个','Takoyaki 5St',6.90),
            ('starters','starters','炸鸡块','Karaage Huehnchen',6.90),
            ('starters','starters','照烧炸鸡','Fried Chicken Teriyaki',7.50),
            ('mains','ramen','猪肉拉面','Pork Ramen',13.90),
            ('mains','ramen','辣牛肉拉面','Spicy Beef Ramen',14.90),
            ('mains','ramen','鸡肉拉面','Chicken Ramen',13.90),
            ('mains','ramen','蔬菜拉面','Vegetarische Ramen',13.90),
            ('mains','ramen','牛肉盖饭','GYUDON Rindfleisch Reis',14.90),
            ('mains','ramen','照烧鸡肉饭','TERIYAKI Haehnchen Teller',13.90),
            ('mains','ramen','鸡肉盖饭','Reisschuessel Haehnchen',13.90),
            ('mains','ramen','烤鳗鱼饭 100g','Gebratener Aal mit Reis 100g',19.80),
            ('mains','ramen','烤鳗鱼饭 200g','Gebratener Aal mit Reis 200g',29.80),
            ('mains','ramen','豆腐蔬菜','Tofu mit Gemuese',13.90),
            ('mains','sides','溏心蛋','Mariniertes Ei',3.20),
            ('mains','sides','叉烧 2片','Chashu 2 Stk',3.90),
            ('mains','sides','虾云吞 2个','Shrimp Wan Tan 2 Stk',3.50),
            ('mains','sides','溏心蛋(软)','Soft Marinated Egg',3.80),
            ('mains','sides','加面','Extra Noodles',3.50),
            ('mains','sides','豆腐','Tofu',3.90),
            ('mains','sides','腌竹笋','Marinated Bamboo',1.20),
            ('desserts','desserts','抹茶麻薯 2个','Matcha Mochi 2 Stk',6.50),
            ('desserts','desserts','大福 5个','YAMAMOTOYA DAIFUKU',6.90),
            ('desserts','desserts','芝麻糯米团 5个','Reisknoedel mit Sesam',3.80),
            ('desserts','desserts','芒果西米露','Mango Sago',7.50),
            # 午市套餐
            ('lunch','lunch','鸡肉面','Hühner-Nudelsuppe',9.90),
            ('lunch','lunch','猪肉面','Schweinefleisch-Nudelsuppe',10.90),
            ('lunch','lunch','素面','Vegetarische Nudelsuppe',10.90),
            ('lunch','lunch','照烧鸡腿饭','Teriyaki-Hähnchenschenkel mit Reis',9.90),
            ('lunch','lunch','素饺子米饭','Vegetarische Teigtaschen mit Reis',9.90),
            ('lunch','lunch','冬阴功汤+素饺子套餐','Tom Yum Suppe + Vegetarische Teigtaschen',11.90),
            ('lunch','lunch','冬阴功汤+猪肉饺子套餐','Tom Yum Suppe + Schweinefleisch-Teigtaschen',11.90),
        ]
        c.executemany('INSERT INTO menu (category, subcategory, name, name_de, price) VALUES (?, ?, ?, ?, ?)', default_menu)
    conn.commit()
    conn.close()

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ==================== 密码 ====================
STAFF_PASSWORD = 'ramen2026'
ADMIN_PASSWORD = 'djj19851204'
connected_devices = {}

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect('/login')
        if session.get('role') != 'admin':
            return redirect('/')
        return f(*args, **kwargs)
    return decorated

# ==================== 路由 ====================

@app.route('/login', methods=['GET','POST'])
def login():
    error = ''
    if request.method == 'POST':
        password = request.form.get('password','')
        if password == ADMIN_PASSWORD:
            session['logged_in'] = True
            session['role'] = 'admin'
            ip = request.remote_addr
            connected_devices[ip] = {'ip':ip,'role':'管理员','time':datetime.now().strftime('%H:%M:%S')}
            return redirect('/')
        elif password == STAFF_PASSWORD:
            session['logged_in'] = True
            session['role'] = 'staff'
            ip = request.remote_addr
            connected_devices[ip] = {'ip':ip,'role':'员工','time':datetime.now().strftime('%H:%M:%S')}
            return redirect('/')
        else:
            error = '密码错误 / Falsches Passwort'
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    ip = request.remote_addr
    connected_devices.pop(ip, None)
    session.clear()
    return redirect('/login')

@app.route('/')
@login_required
def index():
    return render_template('index.html', role=session.get('role','staff'))

@app.route('/order/<int:table_id>')
@login_required
def order(table_id):
    return render_template('order.html', table_id=table_id)

@app.route('/kitchen')
@login_required
def kitchen():
    return render_template('kitchen.html')

@app.route('/bar')
@login_required
def bar():
    return render_template('bar.html')

@app.route('/admin')
@admin_required
def admin():
    return render_template('admin.html')

@app.route('/api/devices')
@admin_required
def get_devices():
    return jsonify(list(connected_devices.values()))

# ==================== API ====================

@app.route('/api/tables')
@login_required
def get_tables():
    conn = get_db()
    tables = conn.execute('SELECT * FROM tables').fetchall()
    conn.close()
    return jsonify([dict(t) for t in tables])

@app.route('/api/table/<int:table_id>')
@login_required
def get_table(table_id):
    conn = get_db()
    table = conn.execute('SELECT * FROM tables WHERE id=?', (table_id,)).fetchone()
    orders = conn.execute('SELECT * FROM orders WHERE table_id=? AND status != "paid" ORDER BY created_at DESC', (table_id,)).fetchall()
    conn.close()
    return jsonify({'table': dict(table), 'orders': [dict(o) for o in orders]})

@app.route('/api/menu')
@login_required
def get_menu():
    conn = get_db()
    items = conn.execute('SELECT * FROM menu ORDER BY category, subcategory').fetchall()
    conn.close()
    return jsonify([dict(i) for i in items])

@app.route('/api/order', methods=['POST'])
@login_required
def place_order():
    data = request.json
    conn = get_db()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    items_json = json.dumps(data['items'], ensure_ascii=False)
    conn.execute('''INSERT INTO orders (table_id, table_name, zone, items, status, created_at, notes)
                    VALUES (?, ?, ?, ?, "pending", ?, ?)''',
                 (data['table_id'], data['table_name'], data['zone'], items_json, now, data.get('notes','')))
    conn.execute('UPDATE tables SET status="occupied" WHERE id=?', (data['table_id'],))
    conn.commit()
    order_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
    conn.close()
    order_data = {'id':order_id,'table_id':data['table_id'],'table_name':data['table_name'],'zone':data['zone'],'items':data['items'],'created_at':now,'notes':data.get('notes','')}
    socketio.emit('new_order', order_data)
    return jsonify({'success':True,'order_id':order_id})

@app.route('/api/order/<int:order_id>/complete', methods=['POST'])
@login_required
def complete_order(order_id):
    data = request.json
    item_type = data.get('type','all')
    conn = get_db()
    if item_type == 'kitchen':
        conn.execute('UPDATE orders SET kitchen_status="done" WHERE id=?', (order_id,))
    elif item_type == 'bar':
        conn.execute('UPDATE orders SET bar_status="done" WHERE id=?', (order_id,))
    else:
        conn.execute('UPDATE orders SET status="done" WHERE id=?', (order_id,))
    conn.commit()
    conn.close()
    socketio.emit('order_updated', {'order_id':order_id,'type':item_type})
    return jsonify({'success':True})

@app.route('/api/table/<int:table_id>/checkout', methods=['POST'])
@login_required
def checkout(table_id):
    conn = get_db()
    conn.execute('UPDATE orders SET status="paid" WHERE table_id=?', (table_id,))
    conn.execute('UPDATE tables SET status="free" WHERE id=?', (table_id,))
    conn.commit()
    conn.close()
    socketio.emit('table_updated', {'table_id':table_id,'status':'free'})
    return jsonify({'success':True})

@app.route('/api/table/swap', methods=['POST'])
@login_required
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
    socketio.emit('tables_swapped', {'from_id':from_id,'to_id':to_id})
    return jsonify({'success':True})

@app.route('/api/menu/reset', methods=['POST'])
@admin_required
def reset_menu():
    conn = get_db()
    conn.execute('DELETE FROM menu')
    conn.commit()
    conn.close()
    init_db()
    return jsonify({'success': True, 'message': '菜单已重置'})

@app.route('/api/menu/update', methods=['POST'])
@admin_required
def update_menu():
    data = request.json
    conn = get_db()
    if data.get('id'):
        conn.execute('UPDATE menu SET name=?, name_de=?, price=?, category=?, subcategory=? WHERE id=?',
                     (data['name'],data['name_de'],data['price'],data['category'],data['subcategory'],data['id']))
    else:
        conn.execute('INSERT INTO menu (category, subcategory, name, name_de, price) VALUES (?, ?, ?, ?, ?)',
                     (data['category'],data['subcategory'],data['name'],data['name_de'],data['price']))
    conn.commit()
    conn.close()
    return jsonify({'success':True})

@app.route('/api/menu/<int:item_id>', methods=['DELETE'])
@admin_required
def delete_menu_item(item_id):
    conn = get_db()
    conn.execute('DELETE FROM menu WHERE id=?', (item_id,))
    conn.commit()
    conn.close()
    return jsonify({'success':True})

@app.route('/api/kitchen/orders')
@login_required
def kitchen_orders():
    conn = get_db()
    orders = conn.execute('''SELECT * FROM orders WHERE status != "paid" AND kitchen_status = "pending" ORDER BY created_at ASC''').fetchall()
    conn.close()
    result = []
    for o in orders:
        od = dict(o)
        od['items'] = json.loads(od['items'])
        result.append(od)
    return jsonify(result)

@app.route('/api/bar/orders')
@login_required
def bar_orders():
    conn = get_db()
    orders = conn.execute('''SELECT * FROM orders WHERE status != "paid" AND bar_status = "pending" ORDER BY created_at ASC''').fetchall()
    conn.close()
    result = []
    for o in orders:
        od = dict(o)
        od['items'] = json.loads(od['items'])
        result.append(od)
    return jsonify(result)

if __name__ == '__main__':
    # 账单历史 - 只管理员可查
    pass

@app.route('/api/orders/history')
@admin_required
def orders_history():
    conn = get_db()
    orders = conn.execute('''SELECT * FROM orders WHERE status = "paid" ORDER BY created_at DESC LIMIT 100''').fetchall()
    conn.close()
    result = []
    for o in orders:
        od = dict(o)
        od['items'] = json.loads(od['items'])
        result.append(od)
    return jsonify(result)

@app.route('/qr')
def qr_page():
    return render_template('qr.html')

if __name__ == '__main__':
    init_db()
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
