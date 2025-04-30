from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'

DB_PATH = os.path.join(os.path.dirname(__file__), 'database', 'food_business.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        first = request.form['first_name']
        last = request.form['last_name']
        birthdate = request.form['birthdate']
        address = request.form['address']
        contact = request.form['contact']
        password = request.form['password']

        full_name = f"{first} {last}"
        username = f"{first[0].lower()}{last.lower()}"

        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if username exists
        cursor.execute("SELECT * FROM Users WHERE Username = ?", (username,))
        if cursor.fetchone():
            flash("Username already exists.")
            return redirect(url_for('register'))

        # Insert user
        cursor.execute('''
            INSERT INTO Users (First_Name, Last_Name, Full_Name, Username, Password, Birthdate, Address, Contact)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (first, last, full_name, username, password, birthdate, address, contact))
        conn.commit()
        conn.close()

        # Success message and render success page
        flash("Registration successful! Your username is: " + username)
        return render_template('success.html', username=username)

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Users WHERE Username = ? AND Password = ?", (username, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            session['user'] = user['Username']
            session['full_name'] = user['Full_Name']  # store full name
            session['address'] = user['Address']      # store address
            return redirect(url_for('home'))
        else:
            flash("Invalid username or password.")
            return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

@app.route('/', methods=['GET', 'POST'])
@app.route('/', methods=['GET', 'POST'])
def home():
    if 'user' not in session:
        return redirect(url_for('login'))

    full_name = session.get('full_name')
    address = session.get('address')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Menu_Items WHERE Available_For IN ('1A', 'both')")
    menu_items = cursor.fetchall()

    if request.method == 'POST':
        customer_name = request.form['customer_name']
        office = request.form['office']  # This now refers to "address"
        selected_items = request.form.getlist('item')
        quantities = request.form.getlist('quantity')
        special_order = request.form['special_order']
        delivery_date = request.form['delivery_date']

        if not selected_items and not special_order:
            return "No items selected or special order."

        cursor.execute("SELECT Customer_ID FROM Customers WHERE Name = ? AND Office = ?", (customer_name, office))
        customer = cursor.fetchone()
        if customer:
            customer_id = customer['Customer_ID']
        else:
            cursor.execute("INSERT INTO Customers (Name, Office) VALUES (?, ?)", (customer_name, office))
            conn.commit()
            customer_id = cursor.lastrowid

        now = datetime.now()
        cursor.execute(
            "INSERT INTO Orders (Customer_ID, Order_Type, Date, Time_Ordered, Delivered) VALUES (?, ?, ?, ?, ?)",
            (customer_id, 'Office', now.date(), now.time(), False)
        )
        conn.commit()
        order_id = cursor.lastrowid

        for item_id, quantity in zip(selected_items, quantities):
            if int(quantity) > 0:
                cursor.execute("INSERT INTO Order_Items (Order_ID, Item_ID, Quantity) VALUES (?, ?, ?)",
                               (order_id, item_id, quantity))

        if special_order:
            cursor.execute(
                "INSERT INTO Special_Requests (Customer_ID, Request_Item, Request_Date, Time_Ordered, Approved) VALUES (?, ?, ?, ?, ?)",
                (customer_id, special_order, delivery_date, now, False))

        conn.commit()
        conn.close()
        return redirect(url_for('order_success'))

    return render_template('home.html', menu_items=menu_items, full_name=full_name, address=address)

@app.route('/order_success')
def order_success():
    return render_template('order_success.html')

# (other routes: owner_dashboard, view_orders, update_delivery_status, view_special_requests, approve_special_request, input_walk_in_order stay unchanged...)

if __name__ == '__main__':
    app.run(debug=True)
