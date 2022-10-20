from flask import Flask, request, render_template, redirect, url_for, session, flash, abort, jsonify
app = Flask(__name__)
import uuid, os, hashlib, pymysql

# Register the setup page and import create_connection()
from utils import create_connection, setup
app.register_blueprint(setup)

@app.before_request
def restrict():
    restricted_pages = ['dashboard', 'edit', 'delete', 'view_user']
    admin_only = ['list_users']

    if 'logged_in' not in session and request.endpoint in restricted_pages:
        flash("You are not logged in!")
        return redirect('/login')
    

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/subjects', methods=['GET', 'POST'])
def Subjects():
        with create_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM subjects")
                result = cursor.fetchall()
                if request.method == 'POST':

                    with create_connection() as connection:
                        with connection.cursor() as cursor:
                            sql = """INSERT INTO subjects 
                                (subject_name)
                                VALUES (%s)
                                """
                            values = (
                                request.form['subject_name']
                                )
                            cursor.execute(sql, values)
                            connection.commit()     
                    return redirect('/')
        return render_template('subjects.html', result=result)

@app.route('/WSDYW')
def WSDYW():
    if 'logged_in' in session:
        with create_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM picked_subjects WHERE user_id=%s", request.args['id'])
                result = cursor.fetchall()
                print(len(result), result)
                if len(result) <5:
                    sql = """INSERT INTO picked_subjects (subject_id, user_id) VALUES (%s, %s)"""
                    values = (request.args['id'], session['user_id'])
                    cursor.execute(sql, values)
                    connection.commit()
                    return redirect('/')
                else:
                    flash("You have 5 subjects already.")
                    return redirect('/')
    else:
        flash("You are not logged in!")
        return redirect('/login')

# This allows users to login.
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':

        password = request.form['password']
        encrypted_passsword = hashlib.sha256(password.encode()).hexdigest()

        with create_connection() as connection:
            with connection.cursor() as cursor:
                sql = "SELECT * FROM users WHERE email=%s AND password=%s"
                values = (
                    request.form['email'],
                    encrypted_passsword
                )
                cursor.execute(sql, values)
                result = cursor.fetchone()
        if result:
            session['logged_in'] = True
            session['First_Name'] = result['First_Name']
            session['role'] = result['role']
            session['user_id'] = result['user_id']
            print(result['user_id'])
            return redirect('/')
        else:
            flash("Invalid username or password!")
            return redirect('/login')
    else:
        return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# This allows people to create new users.
@app.route('/register', methods=['GET', 'POST'])
def add_user():
    if request.method == 'POST':

        password = request.form['password']
        encrypted_passsword = hashlib.sha256(password.encode()).hexdigest()

        with create_connection() as connection:
            with connection.cursor() as cursor:
                sql = """INSERT INTO users 
                    (first_name, last_name, email, password)
                    VALUES (%s, %s, %s, %s)
                    """
                values = (
                    request.form['first_name'], 
                    request.form['last_name'],
                    request.form['email'],
                    encrypted_passsword
                    )
                try:
                    cursor.execute(sql, values)
                    connection.commit()
                except pymysql.err.IntegrityError:
                    flash('Email has already been taken')
                    return redirect('/register')
        return redirect('/')
    return render_template('users_add.html')

# This is a dashboard that allows the admins to see all the users
@app.route('/dashboard')
def dashboard():
    if session['role'] != 'Admin':
        flash("You are not an Admin!")
        return redirect('/')
    with create_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM users JOIN picked_subjects ON users.user_id=picked_subjects.user_id JOIN subjects ON subjects.subject_id=picked_subjects.subject_id")
            result = cursor.fetchall()
    return render_template('users_dashboard.html', result=result)

# This allows the users to see which subjects they can see.
@app.route('/view')
def view_user():
    with create_connection() as connection:
        with connection.cursor() as cursor:
            # cursor.execute("SELECT * FROM users WHERE user_id=%s", request.args['id'])
            cursor.execute("SELECT * FROM users left JOIN picked_subjects ON users.user_id=picked_subjects.user_id left JOIN subjects ON subjects.subject_id=picked_subjects.subject_id WHERE users.user_id=%s", request.args['id'])
            result = cursor.fetchall()
    return render_template('users_view.html', result=result)

# This allows the admins to delete subjects if no users have picked the subject.
@app.route('/delete')
def delete():
    if session['role'] != 'Admin':
        flash("You are not an Admin!")
        return redirect('/')
    else:
        try:
            with create_connection() as connection:
                with connection.cursor() as cursor:
                    sql = """DELETE FROM subjects WHERE subject_id = %s"""
                    values = (request.args['id'])
                    cursor.execute(sql, values)
                    connection.commit()
            return redirect('/')
        except pymysql.err.IntegrityError:
            flash("Sorry but someone has selected this subject.")
            return redirect('/')

@app.route('/selected_delete')
def selected_delete():
    with create_connection() as connection:
        with connection.cursor() as cursor:
            sql = """DELETE FROM picked_subjects WHERE subject_id = %s"""
            values = (request.args['id'])
            cursor.execute(sql, values)
            connection.commit()
        return redirect('/')


# This allows users to edit their information.
@app.route('/edit', methods=['GET', 'POST'])
def edit():
    if session['role'] != 'admin' and str(session['id']) != request.args['id']:
        flash("You are not an admin!")
        return redirect('/')
    
    if request.method == 'POST':

        with create_connection() as connection:
            with connection.cursor() as cursor:
                sql = """UPDATE users SET
                    first_name = %s,
                    last_name = %s,
                    email = %s
                WHERE id = %s"""
                values = (
                    request.form['first_name'],
                    request.form['last_name'],
                    request.form['email'],
                    request.form['id']
                )
                cursor.execute(sql, values)
                connection.commit()
        return redirect('/view?id=' + request.form['id'])
    else:
        with create_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM users WHERE id = %s", request.args['id'])
                result = cursor.fetchone()
        return render_template('users_edit.html', result=result)

@app.route('/subject_edit', methods=['GET', 'POST'])
def subject_edit():
    if session['role'] != 'Admin' and str(session['user_id']) != request.args['user_id']:
        flash("You are not an admin!")
        return redirect('/')
    
    if request.method == 'POST':

        with create_connection() as connection:
            with connection.cursor() as cursor:
                sql = """UPDATE subjects SET
                    subject_name = %s
                WHERE subject_id = %s"""
                values = (
                    request.form['subject_name'],
                    request.form['id']
                )
                cursor.execute(sql, values)
                connection.commit()
        return redirect('/subjects')
    else:
        with create_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM subjects WHERE subject_id = %s", request.args['id'])
                result = cursor.fetchone()
        return render_template('subject_edit.html', result=result)

@app.route('/checkemail')
def check_email():
    with create_connection() as connection:
        with connection.cursor() as cursor:
            sql = "SELECT * FROM users WHERE email=%s"
            values = (
                request.args['email']
            )
            cursor.execute(sql, values)
            result = cursor.fetchone()
        if result:
            return jsonify({ 'status': 'Taken' })
        else:
            return jsonify({ 'status': 'OK' })


if __name__ == '__main__':
    import os

    # This is required to allow flashing messages.
    app.secret_key = os.urandom(32)

    HOST = os.environ.get('SERVER_HOST', 'localhost')
    try:
        PORT = int(os.environ.get('SERVER_PORT', '5555'))
    except ValueError:
        PORT = 5555
    app.run(HOST, PORT, debug=True)
