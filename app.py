from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Database initialization
def init_db():
    if not os.path.exists('auction.db'):
        conn = sqlite3.connect('auction.db')
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                balance INTEGER DEFAULT 0
            )
        ''')
        cursor.execute('''
            CREATE TABLE cars (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                location TEXT NOT NULL,
                image_url TEXT NOT NULL,
                current_bid INTEGER NOT NULL,
                end_time INTEGER NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE bids (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                car_id INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(car_id) REFERENCES cars(id)
            )
        ''')
        
        # Insert sample cars
        sample_cars = [
            ("1965 Ford Mustang", "Bangalore, Karnataka", "https://i.imgur.com/ZVx8f1t.jpg", 120000, 1200),
            ("1957 Chevrolet Bel Air", "Bhubaneswar, Odisha", "https://i.imgur.com/BvF1bNw.jpg", 140000, 900),
            ("1963 Jaguar E-Type", "Udaipur, Rajasthan", "https://i.imgur.com/1n8pQ6t.jpg", 200000, 1500),
            ("1970 Dodge Charger", "Chittorgarh, Rajasthan", "https://i.imgur.com/8zQbQkI.jpg", 180000, 1100)
        ]
        cursor.executemany('INSERT INTO cars (name, location, image_url, current_bid, end_time) VALUES (?, ?, ?, ?, ?)', sample_cars)
        
        # Insert a test user
        cursor.execute('INSERT INTO users (username, password, balance) VALUES (?, ?, ?)', 
                      ('Sid', generate_password_hash('sid123'), 500000))
        
        conn.commit()
        conn.close()

init_db()

# Database helper functions
def get_db_connection():
    conn = sqlite3.connect('auction.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    if 'username' in session:
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (session['username'],)).fetchone()
        cars = conn.execute('SELECT * FROM cars').fetchall()
        bids = conn.execute('''
            SELECT cars.name, bids.amount 
            FROM bids 
            JOIN cars ON bids.car_id = cars.id 
            WHERE bids.user_id = ?
            ORDER BY bids.timestamp DESC
        ''', (user['id'],)).fetchall()
        conn.close()
        
        return render_template('index.html', 
                             logged_in=True,
                             username=session['username'],
                             balance=user['balance'],
                             cars=cars,
                             bids=bids)
    return render_template('index.html', logged_in=False)

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    conn.close()
    
    if user and check_password_hash(user['password'], password):
        session['username'] = username
        session['user_id'] = user['id']
        return jsonify({'success': True, 'message': 'Login successful'})
    else:
        return jsonify({'success': False, 'message': 'Invalid username or password'}), 401

@app.route('/signup', methods=['POST'])
def signup():
    username = request.form['username']
    password = request.form['password']
    
    if not username or not password:
        return jsonify({'success': False, 'message': 'Username and password are required'}), 400
    
    try:
        conn = get_db_connection()
        conn.execute('INSERT INTO users (username, password) VALUES (?, ?)',
                    (username, generate_password_hash(password)))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Registration successful. Please login.'})
    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'message': 'Username already exists'}), 400

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('user_id', None)
    return redirect(url_for('index'))

@app.route('/add_funds', methods=['POST'])
def add_funds():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    
    try:
        amount = int(request.form['amount'])
        if amount <= 0:
            raise ValueError
    except ValueError:
        return jsonify({'success': False, 'message': 'Invalid amount'}), 400
    
    conn = get_db_connection()
    conn.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (amount, session['user_id']))
    conn.commit()
    new_balance = conn.execute('SELECT balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()['balance']
    conn.close()
    
    return jsonify({'success': True, 'new_balance': new_balance})

@app.route('/place_bid', methods=['POST'])
def place_bid():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    
    try:
        car_id = int(request.form['car_id'])
        amount = int(request.form['amount'])
    except ValueError:
        return jsonify({'success': False, 'message': 'Invalid input'}), 400
    
    conn = get_db_connection()
    
    # Check car exists and auction hasn't ended
    car = conn.execute('SELECT * FROM cars WHERE id = ?', (car_id,)).fetchone()
    if not car:
        conn.close()
        return jsonify({'success': False, 'message': 'Car not found'}), 404
    
    # Check user balance
    user = conn.execute('SELECT balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    if amount > user['balance']:
        conn.close()
        return jsonify({'success': False, 'message': 'Insufficient funds'})
    
    # Check bid is higher than current
    if amount <= car['current_bid']:
        conn.close()
        return jsonify({'success': False, 'message': 'Bid must be higher than current bid'})
    
    # Place the bid
    conn.execute('UPDATE cars SET current_bid = ? WHERE id = ?', (amount, car_id))
    conn.execute('UPDATE users SET balance = balance - ? WHERE id = ?', (amount, session['user_id']))
    conn.execute('INSERT INTO bids (user_id, car_id, amount) VALUES (?, ?, ?)',
                (session['user_id'], car_id, amount))
    conn.commit()
    
    # Get updated data
    new_balance = conn.execute('SELECT balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()['balance']
    bids = conn.execute('''
        SELECT cars.name, bids.amount 
        FROM bids 
        JOIN cars ON bids.car_id = cars.id 
        WHERE bids.user_id = ?
        ORDER BY bids.timestamp DESC
    ''', (session['user_id'],)).fetchall()
    conn.close()
    
    return jsonify({
        'success': True,
        'new_balance': new_balance,
        'bids': [dict(bid) for bid in bids]
    })

if __name__ == '__main__':
    app.run(debug=True)