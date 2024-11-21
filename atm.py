# atm_website.py
from flask import Blueprint
from flask import render_template, request, redirect, url_for, flash, session
import psycopg2

app_atm = Blueprint('atm', __name__)

@app_atm.route('/pinchange')
def atm_index():
    return render_template('pin.html')


@app_atm.route('/uploadface')
def uploadface():
    return render_template('admin.html')

@app_atm.route('/cancel')
def cancel():
    return render_template('account.html')


def get_db_connection():
    conn = psycopg2.connect(
        dbname="ATM SECURITY",
        user="postgres",
        password="deep1234",
        host="localhost"
    )
    return conn

@app_atm.route('/balance')
def balance():
    account_no = session.get('account_number')
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Fetch balance
    cur.execute('SELECT balance FROM accounts WHERE cus_accountno = %s', (account_no,))
    balance = cur.fetchone()
    
    cur.close()
    conn.close()
    
    if balance:
        return render_template('balance.html', balance=balance[0])
    else:
        flash('Account not found')
        return redirect(url_for('home'))

@app_atm.route('/withdrawl', methods=['GET', 'POST'])
def withdrawl():
    if request.method == 'POST':

        account_no = session.get('account_number')
        amount = int(request.form['amount'])  # Get withdrawal amount

        conn = get_db_connection()
        cur = conn.cursor()
        
        # Fetch current balance
        cur.execute('SELECT balance FROM accounts WHERE cus_accountno = %s', (account_no,))
        balance = cur.fetchone()
        
        if balance and balance[0] >= amount:
            # Update balance after withdrawal
            new_balance = balance[0] - amount
            cur.execute('UPDATE accounts SET balance = %s WHERE cus_accountno = %s', (new_balance, account_no))
            conn.commit()
            flash('Withdrawal successful!')
        else:
            flash('Insufficient balance or account not found')
        
        cur.close()
        conn.close()
        
        return redirect(url_for('home'))
    
    return render_template('withdrawl.html')

@app_atm.route('/deposit', methods=['GET', 'POST'])
def deposit():
    if request.method == 'POST':
        account_no = session.get('account_number')
        amount = int(request.form['amount'])  # Get deposit amount

        conn = get_db_connection()
        cur = conn.cursor()
        
        # Fetch current balance
        cur.execute('SELECT balance FROM accounts WHERE cus_accountno = %s', (account_no,))
        balance = cur.fetchone()
        
    
        new_balance = balance[0] + amount
        cur.execute('UPDATE accounts SET balance = %s WHERE cus_accountno = %s', (new_balance, account_no))
        conn.commit()
        flash('Withdrawal successful!')

        
        cur.close()
        conn.close()
        
        return redirect(url_for('home'))
    
    return render_template('deposit.html')


@app_atm.route('/pinchange', methods=['GET', 'POST'])
def pin_change():
    if request.method == 'POST':
        account_no = session.get('account_number')
        new_pin = request.form['new_pin']

        conn = get_db_connection()
        cur = conn.cursor()

        # Update PIN
        cur.execute('UPDATE customer1 SET account_pin = %s WHERE cus_accountno = %s', (new_pin, account_no))
        conn.commit()

        cur.close()
        conn.close()

        flash('PIN changed successfully!')
        return redirect(url_for('home'))
    
    return render_template('pinchange.html')



# @app_atm.route('/statement')
# def statement():
#     account_no = request.args.get('account_no')  # Get account number from session or request
#     conn = get_db_connection()
#     cur = conn.cursor()

#     # Fetch last 10 transactions
#     cur.execute('SELECT transaction, date_of_transac, time_of_transac, balance FROM account WHERE account_no = %s ORDER BY date_of_transac DESC, time_of_transac DESC LIMIT 10', (account_no,))
#     transactions = cur.fetchall()

#     cur.close()
#     conn.close()

#     return render_template('statement.html', transactions=transactions)
