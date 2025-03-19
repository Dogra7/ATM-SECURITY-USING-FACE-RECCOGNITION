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

@app_atm.route('/pin_verify/<transaction_type>', methods=['GET', 'POST'])
def pin_verify(transaction_type):
    if request.method == 'POST':

        print(f"Request Form: {request.form}") # Add this line

        account_no = session.get('account_number')
        pin = request.form.get('e_pin', None) # Or some other default value
        if pin is None:
            flash("Please enter your PIN.")
            return redirect(url_for('atm.pin_verify', transaction_type=transaction_type)) 
               
        print(f"PIN: {pin}")
        print(f"Account Number: {account_no}")


        conn = get_db_connection()
        cur = conn.cursor()

        try:
            cur.execute('SELECT account_pin FROM customer1 WHERE cus_accountno = %s', (account_no,))
            correct_pin = cur.fetchone()

            print(f"Correct PIN from DB: {correct_pin}")

            if correct_pin and correct_pin[0] == int(pin):
                if transaction_type == 'withdrawl':
                    return redirect(url_for('atm.withdrawl'))
                elif transaction_type == 'deposit':
                    return redirect(url_for('atm.deposit'))
                elif transaction_type == 'balance':
                    return redirect(url_for('atm.balance'))
                elif transaction_type == 'statement':
                    return redirect(url_for('atm.statement'))
                else:
                    print("Invalid transaction type")
                    flash('Invalid transaction type.')
                    return redirect(url_for('home'))
            else:
                print("Incorrect PIN")
                flash('Incorrect PIN.')
                return redirect(url_for('atm.pin_verify', transaction_type=transaction_type))

        except psycopg2.Error as e:
            print(f"Database error: {e}")
            flash("An error occurred during PIN verification.")
            return redirect(url_for('home'))

        finally:
            cur.close()
            conn.close()

    return render_template('pin_verify.html', transaction_type=transaction_type)

@app_atm.route('/balance')
def balance():
    account_no = session.get('account_number')

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute('SELECT balance FROM accounts WHERE cus_accountno = %s', (account_no,))
    balance = cur.fetchone()

    cur.close()
    conn.close()

    if balance:
        return render_template('balance.html', balance=balance[0])
    else:
        # flash('Account not found')
        return redirect(url_for('home'))

@app_atm.route('/withdrawl', methods=['GET', 'POST'])
def withdrawl():
    if request.method == 'POST':
        account_no = session.get('account_number')
        amount = int(request.form['amount'])

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute('SELECT balance FROM accounts WHERE cus_accountno = %s', (account_no,))
        balance = cur.fetchone()

        if balance and balance[0] >= amount:
            new_balance = balance[0] - amount
            cur.execute('UPDATE accounts SET balance = %s WHERE cus_accountno = %s', (new_balance, account_no))
            cur.execute('INSERT INTO transactions (account_number, transaction_type, amount, transaction_date, balance_after_transaction) VALUES (%s, %s, %s, CURRENT_TIMESTAMP, %s)', (account_no, 'Withdrawal', amount, new_balance))
            conn.commit()
            # flash('Withdrawal successful!')
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
        amount = int(request.form['amount'])

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute('SELECT balance FROM accounts WHERE cus_accountno = %s', (account_no,))
        balance = cur.fetchone()

        new_balance = balance[0] + amount
        cur.execute('UPDATE accounts SET balance = %s WHERE cus_accountno = %s', (new_balance, account_no))
        cur.execute('INSERT INTO transactions (account_number, transaction_type, amount, transaction_date, balance_after_transaction) VALUES (%s, %s, %s, CURRENT_TIMESTAMP, %s)', (account_no, 'Deposit', amount, new_balance))

        conn.commit()
        # flash('Deposit successful!')

        cur.close()
        conn.close()

        return redirect(url_for('home'))

    return render_template('deposit.html')

@app_atm.route('/pinchange', methods=['GET', 'POST'])
def pin_change():
    if request.method == 'POST':
        account_no = session.get('account_number')
        new_pin = request.form['new_pin']
        current_pin = request.form['old_pin']

        print(f"Account Number: {account_no}")
        print(f"Current PIN: {current_pin}")
        print(f"New PIN: {new_pin}")

        conn = get_db_connection()
        cur = conn.cursor()

        try:
            cur.execute('SELECT account_pin FROM customer1 WHERE cus_accountno = %s', (account_no,))
            correct_pin = cur.fetchone()

            print(f"Correct PIN from DB: {correct_pin}")

            if correct_pin and correct_pin[0] == int(current_pin):
                print("PINs match, updating PIN...")
                cur.execute('UPDATE customer1 SET account_pin = %s WHERE cus_accountno = %s', (new_pin, account_no))
                conn.commit()
                # flash('PIN changed successfully!')
            else:
                print("Incorrect current PIN.")
                # flash('Incorrect current PIN.')

        except psycopg2.Error as e:
            print(f"Database error: {e}")
            conn.rollback()
            # flash("An error occurred during PIN change.")

        finally:
            cur.close()
            conn.close()

        return redirect(url_for('home'))

    return render_template('pinchange.html')

@app_atm.route('/statement')
def statement():
    account_no = session.get('account_number')
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute('SELECT amount, transaction_type, balance_after_transaction, transaction_date FROM transactions WHERE account_number = %s ORDER BY transaction_date DESC LIMIT 5', (account_no,))
    transactions = cur.fetchall()

    cur.close()
    conn.close()

    return render_template('statement.html', transactions=transactions)