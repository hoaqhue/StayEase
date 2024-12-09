from datetime import datetime, timedelta

from flask import Flask, render_template, request, redirect
from flask_login import login_user, logout_user

from hotelapp import app, dao, login, db
from hotelapp.decorators import loggedin

@app.route('/')
def index():
    room_types = dao.get_room_types()
    to_day = datetime.now().date()
    next_28_day = datetime.today() + timedelta(days=28)
    return render_template('index.html', room_types=room_types, to_day=to_day, next_28_day=next_28_day)


@app.route('/login-admin', methods=['POST'])
def login_admin():
    username = request.form.get('username')
    password = request.form.get('password')
    u = dao.auth_user(username=username, password=password)

    if u:
        login_user(user=u)

    return redirect('/admin')


from sqlalchemy.exc import IntegrityError, PendingRollbackError


@app.route('/register', methods=['get', 'post'])
def register_user():
    client_types = dao.get_client_types()
    err_msg = None
    if request.method.__eq__('POST'):
        name = request.form.get('name')
        username = request.form.get('username')
        identification_code = request.form.get('identification_code')
        phone_number = request.form.get('phoneNumber')
        email = request.form.get('email')
        address = request.form.get('address')
        password = request.form.get('password')
        confirm = request.form.get('confirm')
        client_type_id = request.form.get('client_type_id')

        if not all([name, username, password, confirm, client_type_id]):
            err_msg = "Vui lòng điền đầy đủ thông tin!"
        elif password != confirm:
            err_msg = "Sai mật khẩu xác nhận!"
        else:
            try:
                dao.create_user(
                    name,
                    username,
                    password,
                    identification_code,
                    phone_number,
                    email,
                    address,
                    client_type_id
                )
                return redirect('/login')
            except (IntegrityError, PendingRollbackError) as e:
                db.session.rollback()
                err_msg = "Tên đăng nhập đã tồn tại!"
            except Exception as e:
                db.session.rollback()
                app.logger.error(f"Registration error: {str(e)}")
                err_msg = "Đã xảy ra lỗi trong quá trình đăng ký. Vui lòng thử lại."

    return render_template('auth/register.html', err_msg=err_msg, client_types=client_types)


@app.route('/logout', methods=['get'])
def logout_my_user():
    logout_user()
    return redirect('/login')


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
