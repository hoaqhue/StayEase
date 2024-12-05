from datetime import datetime, timedelta

from flask import Flask, render_template, request, redirect
from flask_login import login_user

from hotelapp import app, dao, login
from hotelapp.decorators import loggedin

@app.route('/') #ai gõ :))) ém, ko cần chaykj lại ctrl S là đc
def index():
    room_types = dao.get_room_types()
    to_day = datetime.now().date()
    next_28_day = datetime.today() + timedelta(days=28) #mai mốt thay quy định zô
    return render_template('index.html', room_types=room_types, to_day=to_day, next_28_day=next_28_day)


@app.route('/login-admin', methods=['POST'])
def login_admin():
    username = request.form.get('username')
    password = request.form.get('password')
    u = dao.auth_user(username=username, password=password)

    if u:
        login_user(user=u)

    return redirect('/admin')

@loggedin
@app.route('/login', methods=['get', 'post'])
def login_my_user():
    err_msg = ''
    if request.method.__eq__('POST'):
        username = request.form.get('username')
        password = request.form.get('password')

        user = dao.auth_user(username=username, password=password)
        if user:
            login_user(user)

            next = request.args.get('next')
            return redirect(next if next else '/')
        else:
            err_msg = 'Username hoặc password không đúng!'

    return render_template('auth/login.html', err_msg=err_msg)

@login.user_loader
def load_user(user_id):
    return dao.get_user_by_id(int(user_id))

if __name__ == "__main__":
    with app.app_context():
        from hotelapp import admin
        app.run(debug=True)