import os
import sqlite3 
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
# from tickers_data import get_tickers_with_cur_price

# Создание Flask-приложения
app = Flask(__name__)
app.secret_key = 'supersecretkey'

# 📁 Папка для загрузки изображений
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Настройки Flask-приложения
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # до 2MB

# ✅ Создаём папку, если её нет
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# Проверка разрешённого расширения
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


DB_NAME = 'database.db'


def add_image_column_if_missing():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE assets ADD COLUMN image TEXT")
        print("✅ Колонка image добавлена")
    except sqlite3.OperationalError as e:
        print("ℹ️ Колонка image уже существует или ошибка:", e)
    conn.commit()
    conn.close()

def get_user_orders(email, conn):
    cursor = conn.cursor()
    cursor.execute('SELECT id, symbol, price, status, amount FROM user_order_history WHERE email = ?', (email, ))
    data = cursor.fetchall()
    return data


def add_order_to_user(email, symbol, price, status, amount, conn):
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO user_order_history (email, symbol, price, status, amount)
        VALUES (?, ?, ?, ?, ?)
    ''', (email, symbol, price, status, amount))
    conn.commit()

def delete_order_from_user(order_id, conn):
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE status SET sell = ? WHERE id = ?
    ''', (order_id, )) 
    conn.commit()

def init_db():
    if not os.path.exists(DB_NAME):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
         # Создание таблиц
        cursor.execute('''
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                phone TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                balance REAL DEFAULT 0
            )
        ''')


        # status buy/sell
        cursor.execute('''
            CREATE TABLE user_order_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT,
                symbol TEXT,
                price REAL DEFAULT 0,
                status TEXT,
                amount INTEGER
            )
       ''')

        cursor.execute('''
            CREATE TABLE assets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                current_value REAL DEFAULT 0,
                image TEXT
            )
        ''')    

        for ticker in get_tickers_with_cur_price():
            cursor.execute('''
              INSERT INTO assets (name, current_value, image) VALUES (?, ?, ?)  
           ''', (ticker[0], ticker[1], ticker[2])
           ) 

        cursor.execute('''
            CREATE TABLE price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asset_id INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                value REAL NOT NULL,
                FOREIGN KEY (asset_id) REFERENCES assets(id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE asset_prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asset_id INTEGER,
                timestamp TEXT,
                value REAL,
                FOREIGN KEY (asset_id) REFERENCES assets(id)
            )
        ''')
    
        # status buy/journal
        cursor.execute('''
            CREATE TABLE user_assets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                asset_id INTEGER,
                asset_name TEXT,
                amount REAL DEFAULT 0,
                status TEXT,
                open_date TEXT,
                close_date TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (asset_id) REFERENCES assets(id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Стартовые активы
        cursor.executemany(
            'INSERT INTO assets (name, current_value) VALUES (?, ?)',
            [('Нефть', 7200), ('Газ', 3200), ('Золото', 5000),
             ('Криптовалюта', 15000), ('Акции', 8000)])

        conn.commit()
        conn.close()
        print("✅ База данных создана")
    else:
        # Если база уже есть, проверим наличие таблицы messages
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='messages'"
        )
        if not cursor.fetchone():
            cursor.execute('''
                CREATE TABLE messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sender TEXT NOT NULL,
                    user_id INTEGER NOT NULL,
                    message TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
            print("✅ Таблица messages добавлена")
        conn.close()


init_db()


def add_image_column_if_missing():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(assets)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'image' not in columns:
        cursor.execute("ALTER TABLE assets ADD COLUMN image TEXT")
        print("✅ Колонка image добавлена")
        conn.commit()
    else:
        print("ℹ️ Колонка image уже существует")
    conn.close()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect('/dashboard')

    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        phone = request.form['phone']
        email = request.form['email']
        password = request.form['password']

        # Проверка латиницы
        if not first_name.isascii() or not last_name.isascii():
             flash("Имя и фамилия должны быть на английском!")
             return render_template('register.html')


        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        try:
            cursor.execute(
                '''
                INSERT INTO users (first_name, last_name, phone, email, password)
                VALUES (?, ?, ?, ?, ?)
            ''', (first_name, last_name, phone, email, password))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            flash('Email уже зарегистрирован!')
            return render_template('register.html')
        conn.close()
        # Очистим предыдущую сессию и установим новую
        session.clear()
        session['user_id'] = cursor.lastrowid
        session['user_email'] = email

        return redirect('/dashboard')
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM users WHERE email = ? AND password = ?',
                       (email, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            session['user_id'] = user[0]
            session['user_email'] = email
            return redirect('/dashboard')
        else:
            flash('Неверный email или пароль')
            return redirect('/login')

    return render_template('login.html')



@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    user_email = session['user_email']

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Получаем имя и баланс пользователя
    cursor.execute('SELECT first_name, balance FROM users WHERE id = ?',
                   (user_id, ))
    user_data = cursor.fetchone()
    first_name = user_data[0]
    balance = user_data[1]

    # Получаем список всех доступных активов, включая путь к изображению
    cursor.execute('SELECT id, name, current_value, image FROM assets')
    assets = cursor.fetchall()
    ic(assets)
    user_orders = get_user_orders(user_email, conn)
    ic(user_orders)
    
    # Получаем активы, которые есть у пользователя
    user_assets = {row[0]: row[1] for row in cursor.fetchall()}

    conn.close()

    return render_template('dashboard.html',
                           first_name=first_name,
                           balance=balance,
                           assets=assets,
                           user_assets=user_assets)


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        password = request.form['password']
        if password == 'admin123':
            session['is_admin'] = True
            return redirect('/admin')
        else:
            return 'Неверный пароль'
    return render_template('admin_login.html')


@app.route('/update_balance', methods=['POST'])
def update_balance():
    if not session.get('is_admin'):
        return redirect('/admin_login')

    user_id = request.form['user_id']
    new_balance = request.form['new_balance']

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET balance = ? WHERE id = ?',
                   (new_balance, user_id))
    conn.commit()
    conn.close()

    return redirect('/admin')


@app.route('/edit_assets/<int:user_id>', methods=['GET', 'POST'])
def edit_assets(user_id):
    if not session.get('is_admin'):
        return redirect('/admin_login')

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    if request.method == 'POST':
        for asset_id, amount in request.form.items():
            cursor.execute(
                'SELECT id FROM user_assets WHERE user_id = ? AND asset_id = ?',
                (user_id, asset_id))
            if cursor.fetchone():
                cursor.execute(
                    'UPDATE user_assets SET amount = ? WHERE user_id = ? AND asset_id = ?',
                    (amount, user_id, asset_id))
            else:
                cursor.execute(
                    'INSERT INTO user_assets (user_id, asset_id, amount) VALUES (?, ?, ?)',
                    (user_id, asset_id, amount))

        conn.commit()
        conn.close()
        return redirect('/admin')

    # GET — показать текущие активы
    cursor.execute('SELECT id, name FROM assets')
    all_assets = cursor.fetchall()

    cursor.execute(
        'SELECT asset_id, amount FROM user_assets WHERE user_id = ?',
        (user_id, ))
    user_assets = {row[0]: row[1] for row in cursor.fetchall()}

    conn.close()

    return render_template('edit_assets.html',
                           user_id=user_id,
                           all_assets=all_assets,
                           user_assets=user_assets)

@app.route('/toggle_asset', methods=['POST'])
def toggle_asset():
    email = session.get('user_email')
    user_id = session.get('user_id')

    amount = int(request.form['asset_amount'])
    asset_name = request.form['asset_name']
    asset_id = request.form['asset_id']
    price = float(request.form['asset_price'])
    action = request.form['action']

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT balance FROM users WHERE email = ?', (email, ))
    
    
    if amount <= 0:
        flash("Количество должно быть больше нуля.")
        return redirect('/dashboard')
    
    if action == 'buy':
        total_backs = price * amount
        balance = cursor.fetchall()[0][0]

        if total_backs >= balance:
            flash('Недостаточно средств на балансе')
            return redirect('/dashboard')

        final_user_balance = balance - total_backs

        cursor.execute('UPDATE users SET balance = ? WHERE email = ?',
                       (final_user_balance, email))
        add_order_to_user(email, asset_name, price, 'buy', amount, conn)
        conn.commit()
        conn.close()
        flash(f'Куплено {amount} {asset_name}')

    else:
        orders = get_user_orders(user_email, conn)
        delete_order_from_user(order_id, conn)
        flash('Продано 0')
         
    return redirect('/dashboard') 


@app.route('/asset/<asset_name>')
def view_asset(asset_name):
    if 'user_id' not in session:
        return redirect('/login')

    return render_template('asset.html',
                           asset_name=asset_name)

from icecream import ic
@app.route('/admin')
def admin():
    ic(session.get('is_admin'))
    if session.get('is_admin') != True:
        return redirect('/admin_login')

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Получаем всех пользователей
    cursor.execute(
        'SELECT id, first_name, last_name, email, balance FROM users')
    users = cursor.fetchall()

    # Получаем активы для выдачи
    cursor.execute('SELECT id, name FROM assets')
    all_assets = cursor.fetchall()

    # Получаем все активы с ценой и изображением
    cursor.execute('SELECT id, name, current_value, image FROM assets')
    assets = cursor.fetchall()

    # Получаем историю цен
    cursor.execute('SELECT * FROM price_history')
    price_history = cursor.fetchall()

    conn.close()

    # Группируем историю цен по asset_id
    asset_prices = {}
    for row in price_history:
        asset_id = row[1]
        if asset_id not in asset_prices:
            asset_prices[asset_id] = []
        asset_prices[asset_id].append(row)

    return render_template('admin.html',
                           users=users,
                           all_assets=all_assets,
                           assets=assets,
                           asset_prices=asset_prices)


@app.route('/admin/delete_user', methods=['POST'])
def delete_user():
    user_id = int(request.form['user_id'])

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Удаляем активы пользователя и самого пользователя
    cursor.execute('DELETE FROM user_assets WHERE user_id = ?', (user_id, ))
    cursor.execute('DELETE FROM users WHERE id = ?', (user_id, ))
    conn.commit()
    conn.close()

    return redirect('/admin?password=admin123')


@app.route('/admin/update_price', methods=['POST'])
def update_price():
    asset_id = int(request.form['asset_id'])
    new_price = float(request.form['new_price'])

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute('UPDATE assets SET current_value = ? WHERE id = ?',
                   (new_price, asset_id))
    conn.commit()
    conn.close()

    return redirect('/admin?password=admin123')


@app.route('/admin/add_price_history', methods=['POST'])
def add_price_history():
    asset_id = int(request.form['asset_id'])
    value = float(request.form['value'])
    timestamp = request.form['timestamp']

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        'INSERT INTO asset_prices (asset_id, timestamp, value) VALUES (?, ?, ?)',
        (asset_id, timestamp, value))
    conn.commit()
    conn.close()

    return redirect('/admin?password=admin123')


@app.route('/admin/update_balance', methods=['POST'])
def admin_update_balance():
    user_id = int(request.form['user_id'])
    balance = float(request.form['balance'])

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET balance = ? WHERE id = ?',
                   (balance, user_id))
    conn.commit()
    conn.close()

    return redirect('/admin?password=admin123')


@app.route('/admin/grant_asset', methods=['POST'])
def admin_grant_asset():
    user_id = int(request.form['user_id'])
    asset_id = int(request.form['asset_id'])
    amount = float(request.form['amount'])

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        'SELECT amount FROM user_assets WHERE user_id = ? AND asset_id = ?',
        (user_id, asset_id))
    row = cursor.fetchone()

    if row:
        cursor.execute(
            'UPDATE user_assets SET amount = amount + ? WHERE user_id = ? AND asset_id = ?',
            (amount, user_id, asset_id))
    else:
        cursor.execute(
            'INSERT INTO user_assets (user_id, asset_id, amount) VALUES (?, ?, ?)',
            (user_id, asset_id, amount))
    conn.commit()
    conn.close()

    return redirect('/admin?password=admin123')


@app.route('/admin/rename_asset', methods=['POST'])
def rename_asset():
    asset_id = int(request.form['asset_id'])
    new_name = request.form['new_name']

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('UPDATE assets SET name = ? WHERE id = ?',
                   (new_name, asset_id))
    conn.commit()
    conn.close()

    return redirect('/admin?password=admin123')


@app.route('/admin/delete_asset', methods=['POST'])
def delete_asset():
    asset_id = int(request.form['asset_id'])

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM asset_prices WHERE asset_id = ?', (asset_id, ))
    cursor.execute('DELETE FROM user_assets WHERE asset_id = ?', (asset_id, ))
    cursor.execute('DELETE FROM assets WHERE id = ?', (asset_id, ))
    conn.commit()
    conn.close()

    return redirect('/admin?password=admin123')


@app.route('/admin/edit_price_history', methods=['POST'])
def edit_price_history():
    price_id = int(request.form['id'])
    timestamp = request.form['timestamp']
    value = float(request.form['value'])

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE asset_prices SET timestamp = ?, value = ? WHERE id = ?',
        (timestamp, value, price_id))
    conn.commit()
    conn.close()

    return redirect('/admin?password=admin123')


@app.route('/admin/delete_price_history', methods=['POST'])
def delete_price_history():
    price_id = int(request.form['id'])

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM asset_prices WHERE id = ?', (price_id, ))
    conn.commit()
    conn.close()

    return redirect('/admin?password=admin123')


@app.route('/admin/add_asset', methods=['POST'])
def add_asset():
    if not session.get('is_admin'):
        return redirect('/admin_login')

    name = request.form['name']
    file = request.files.get('image')  # Безопасно получаем файл
    image_path = None

    # Обработка только если файл выбран и допустим
    if file and file.filename != '' and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        image_path = f'static/uploads/{filename}'

    # ✅ Установка текущей цены по умолчанию — 1000, если не указано
    current_value = 1000.0

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO assets (name, current_value, image) VALUES (?, ?, ?)',
        (name, current_value, image_path))
    conn.commit()
    conn.close()

    return redirect('/admin?password=admin123')


@app.route('/admin/create_asset', methods=['POST'])
def create_asset():
    if not session.get('is_admin'):
        return redirect('/admin_login')

    name = request.form['name']

    # ✅ Безопасное извлечение цены
    try:
        current_value = float(request.form.get('current_value', '1000'))
    except:
        current_value = 1000.0

    file = request.files['image']
    image_path = None
    if file and allowed_file(file.filename):
        filename = file.filename
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(image_path)

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO assets (name, current_value, image) VALUES (?, ?, ?)',
        (name, current_value, image_path))
    conn.commit()
    conn.close()

    return redirect('/admin?password=admin123')


from flask import jsonify
import random
from datetime import datetime, timedelta


@app.route('/api/asset_data')
def api_asset_data():
    asset_id = request.args.get('id')
    if not asset_id:
        return jsonify([])

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Проверяем, есть ли хоть одна запись истории
    cursor.execute('SELECT COUNT(*) FROM asset_prices WHERE asset_id = ?',
                   (asset_id, ))
    count = cursor.fetchone()[0]
    print(f"🔎 В базе найдено {count} записей по активу {asset_id}")

    # Если истории нет — генерируем симулированные данные за 7 дней
    if count == 0:
        print(f"⏳ Генерация истории за 7 дней для актива {asset_id}")

        # Берём текущую цену
        cursor.execute('SELECT current_value FROM assets WHERE id = ?',
                       (asset_id, ))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return jsonify([])

        current_value = row[0]
        if current_value is None:
            print(
                f"⚠️ У актива {asset_id} нет начальной цены (None). Устанавливаю 1000."
            )
            current_value = 1000.0

        now = datetime.utcnow()
        start_time = now - timedelta(days=7)
        num_points = 1000
        interval = timedelta(seconds=60 * 10)  # каждые 10 минут

        value = current_value
        for i in range(num_points):
            timestamp = (start_time +
                         i * interval).isoformat(timespec='seconds')
            # Сглаженная симуляция: маленькие изменения
            delta = random.uniform(-1.5, 1.5)
            value = round(max(0, value + delta), 2)

            cursor.execute(
                'INSERT INTO asset_prices (asset_id, timestamp, value) VALUES (?, ?, ?)',
                (asset_id, timestamp, value))

        # Обновим текущую цену после симуляции
        cursor.execute('UPDATE assets SET current_value = ? WHERE id = ?',
                       (value, asset_id))

        conn.commit()

    # Теперь продолжаем как обычно — генерация новых точек каждые 10 секунд
    cursor.execute(
        'SELECT timestamp, value FROM asset_prices WHERE asset_id = ? ORDER BY timestamp DESC LIMIT 1',
        (asset_id, ))
    last = cursor.fetchone()

    if last:
        last_time = datetime.fromisoformat(last[0])
        last_value = last[1]
    else:
        # Теоретически не должно произойти после генерации
        last_time = datetime.utcnow() - timedelta(seconds=10)
        last_value = 1000

    now = datetime.utcnow()
    while (now - last_time).total_seconds() >= 10:
        last_time += timedelta(seconds=10)
        delta = random.uniform(-2, 2)
        last_value = round(max(0, last_value + delta), 2)
        timestamp_str = last_time.isoformat(timespec='seconds')

        cursor.execute(
            'INSERT INTO asset_prices (asset_id, timestamp, value) VALUES (?, ?, ?)',
            (asset_id, timestamp_str, last_value))
        cursor.execute('UPDATE assets SET current_value = ? WHERE id = ?',
                       (last_value, asset_id))

    conn.commit()

    # Возвращаем ВСЮ историю (включая симулированную)
    cursor.execute(
        'SELECT timestamp, value FROM asset_prices WHERE asset_id = ? ORDER BY timestamp',
        (asset_id, ))
    data = cursor.fetchall()
    conn.close()
    print(f"📦 Отправка {len(data)} точек для актива {asset_id}")

    return jsonify(data)


@app.route('/chat/messages')
def get_messages():
    if 'user_id' not in session:
        return jsonify([])
    user_id = session['user_id']
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        'SELECT sender, message, timestamp FROM messages WHERE user_id = ? ORDER BY timestamp ASC',
        (user_id, ))
    messages = cursor.fetchall()
    conn.close()
    return jsonify([{
        'sender': m[0],
        'message': m[1],
        'timestamp': m[2]
    } for m in messages])


@app.route('/chat/send', methods=['POST'])
def send_message():
    if 'user_id' not in session:
        return 'Unauthorized', 401
    user_id = session['user_id']
    data = request.get_json()
    message = data.get('message', '').strip()
    if not message:
        return 'Empty message', 400
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO messages (sender, user_id, message) VALUES (?, ?, ?)',
        ('user', user_id, message))
    conn.commit()
    conn.close()
    return 'OK'


@app.route('/admin/chat/<int:user_id>')
def admin_get_messages(user_id):
    if not session.get('is_admin'):
        return 'Unauthorized', 401
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        'SELECT sender, message, timestamp FROM messages WHERE user_id = ? ORDER BY timestamp ASC',
        (user_id, ))
    messages = cursor.fetchall()
    conn.close()
    return jsonify([{
        'sender': m[0],
        'message': m[1],
        'timestamp': m[2]
    } for m in messages])


@app.route('/admin/chat/send', methods=['POST'])
def admin_send_message():
    if not session.get('is_admin'):
        return 'Unauthorized', 401
    data = request.get_json()
    user_id = data.get('user_id')
    message = data.get('message', '').strip()
    if not message or not user_id:
        return 'Invalid', 400
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO messages (sender, user_id, message) VALUES (?, ?, ?)',
        ('admin', user_id, message))
    conn.commit()
    conn.close()
    return 'OK'


@app.route('/admin/search_users')
def search_users():
    if not session.get('is_admin'):
        return jsonify([])
    q = request.args.get('q', '').strip()
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    if q.isdigit():
        cursor.execute(
            'SELECT id, first_name, last_name FROM users WHERE id = ?',
            (int(q), ))
    else:
        q_lower = q.lower()
        q_like = f"%{q_lower}%"
        cursor.execute(
            '''
            SELECT id, first_name, last_name FROM users
            WHERE LOWER(first_name) LIKE ?
               OR LOWER(last_name) LIKE ?
               OR LOWER(first_name || " " || last_name) LIKE ?
        ''', (q_like, q_like, q_like))
    users = cursor.fetchall()
    conn.close()
    return jsonify([{
        'id': u[0],
        'first_name': u[1],
        'last_name': u[2]
    } for u in users])


import sqlite3

conn = sqlite3.connect('database.db')  # убедись, что путь к базе верный
cursor = conn.cursor()

for row in cursor.fetchall():
    print(row)

conn.close()

if __name__ == '__main__':
    init_db()  # <-- вот это добавляем
    app.run(host='0.0.0.0', port=5000, debug=True)
