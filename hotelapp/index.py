from datetime import datetime, timedelta

from flask import Flask, render_template, request, redirect
from flask_login import login_user, logout_user
from flask_bcrypt import Bcrypt
from sqlalchemy.exc import IntegrityError, PendingRollbackError
from hotelapp import admin

from hotelapp import app, dao, login, db, admin
from hotelapp.decorators import loggedin
from hotelapp.models import Room, BookingForm, RoomStatus, BookingRoomDetails, Client, UserRole

# Khởi tạo Bcrypt
bcrypt = Bcrypt(app)


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

    # Xác thực tài khoản admin
    user = dao.auth_user(username=username, password=password)
    if user:
        user_role = dao.get_user_role(user)
        if user_role and user_role.type == "Admin":
            login_user(user)
            return redirect('/admin')

    # Xử lý lỗi khi không phải admin
    return render_template('auth/login.html', err_msg="Không có quyền truy cập admin.")


@loggedin
@app.route('/login', methods=['GET', 'POST'])
def login_my_user():
    err_msg = ''
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Xác thực người dùng
        user = dao.auth_user(username=username, password=password)
        if user:
            user_role = dao.get_user_role(user)

            if user_role and user_role.type == "Guest":
                login_user(user)
            elif user_role and user_role.type == "Admin":
                login_user(user)
                return redirect('/admin')
            else:
                err_msg = 'Người dùng không có vai trò hợp lệ!'
                return render_template('auth/login.html', err_msg=err_msg)

            # Điều hướng an toàn
            next_url = request.args.get('next')
            if not next_url or not next_url.startswith('/'):
                next_url = '/'
            return redirect(next_url)
        else:
            err_msg = 'Tên đăng nhập hoặc mật khẩu không đúng!'  # "Username or password is incorrect."

    return render_template('auth/login.html', err_msg=err_msg)


@login.user_loader
def load_user(user_id):
    return dao.get_user_by_id(int(user_id))


@app.route('/register', methods=['get', 'post'])
def register_user():
    client_types = dao.get_client_types()
    err_msg = None
    if request.method == 'POST':
        name = request.form.get('name')
        username = request.form.get('username')
        identification_code = request.form.get('identification_code')
        phone_number = request.form.get('phoneNumber')
        email = request.form.get('email')
        address = request.form.get('address')
        password = request.form.get('password')
        confirm = request.form.get('confirm')
        client_type_id = request.form.get('client_type_id')

        # Kiểm tra thông tin đầu vào
        if not all([name, username, password, confirm, client_type_id]):
            err_msg = "Vui lòng điền đầy đủ thông tin!"  # "Please fill out all fields!"
        elif password != confirm:
            err_msg = "Sai mật khẩu xác nhận!"  # "Confirmation password is incorrect!"
        else:
            try:
                # Kiểm tra xem số CCCD đã tồn tại chưa
                existing_identification_code = dao.get_client_by_identification_code(identification_code)
                if existing_identification_code:
                    err_msg = "Số CCCD đã được đăng ký!"  # "Identification code already registered!"
                else:
                    # Kiểm tra xem email đã tồn tại chưa
                    existing_email = dao.get_client_by_email(email)
                    if existing_email:
                        err_msg = "Email đã được đăng ký!"  # "Email already registered!"
                    else:
                        # Kiểm tra xem số điện thoại đã tồn tại chưa
                        existing_phone = dao.get_client_by_phone(phone_number)
                        if existing_phone:
                            err_msg = "Số điện thoại đã được đăng ký!"  # "Phone number already registered!"
                        else:

                            # Tạo người dùng mới
                            dao.create_user(
                                name,
                                username,
                                password,  # Use the hashed password
                                identification_code,
                                phone_number,
                                email,
                                address,
                                client_type_id
                            )
                            return redirect('/login')

            except IntegrityError as e:
                db.session.rollback()
                err_msg = "Tên đăng nhập đã tồn tại!"  # "Username already exists!"
            except Exception as e:
                db.session.rollback()
                app.logger.error(f"Registration error: {str(e)}")
                err_msg = "Đã xảy ra lỗi trong quá trình đăng ký. Vui lòng thử lại."  # "An error occurred during registration. Please try again."

    return render_template('auth/register.html', err_msg=err_msg, client_types=client_types)


@app.route('/logout', methods=['get'])
def logout_my_user():
    logout_user()
    return redirect('/login')


@app.route('/search_rooms', methods=['POST'])
def search_rooms():
    checkin_date = request.form.get('check_in_date')
    checkout_date = request.form.get('check_out_date')
    ticket_class = request.form.get('ticket_class')
    passengers = request.form.get('passengers')

    available_status = RoomStatus.query.filter_by(status='Có sẵn').first()
    if not available_status:
        return render_template('rooms.html',
                               error="Trạng thái 'Có sẵn' không tồn tại trong cơ sở dữ liệu.")  # "The 'Available' status does not exist in the database."

    rooms = Room.query.filter_by(room_type_id=ticket_class,
                                 room_status_id=available_status.id).all()
    return render_template('rooms.html', rooms=rooms)


@app.route('/rooms')
def rooms():
    rooms = Room.query.all()
    return render_template('rooms.html', rooms=rooms)


@app.route('/booking/<int:room_id>', methods=['GET', 'POST'])
def booking(room_id):
    room = Room.query.get_or_404(room_id)

    if request.method == 'POST':
        try:
            # Lấy dữ liệu từ form
            full_name = request.form['full_name']
            phone_number = request.form['phone_number']
            email = request.form['email']
            identification_code = request.form['identification_code']
            check_in_date = datetime.strptime(request.form['check_in_date'], '%Y-%m-%d')
            check_out_date = datetime.strptime(request.form['check_out_date'], '%Y-%m-%d')

            # Kiểm tra sự có sẵn của phòng
            available_status = RoomStatus.query.filter_by(status='Có sẵn').first()
            maintenance_status = RoomStatus.query.filter_by(status='Bảo trì').first()
            if not available_status:
                raise ValueError("Trạng thái phòng 'Có sẵn' không tồn tại trong cơ sở dữ liệu.")
            if room.room_status_id == maintenance_status.id:
                return render_template('booking.html', room=room,
                                       error="Phòng này đang được bảo trì!")
            if room.room_status_id != available_status.id:
                return render_template('booking.html', room=room,
                                       error="Phòng này đã được đặt trước!")

            # Kiểm tra thông tin khách hàng đã tồn tại chưa
            client = Client.query.filter_by(identification_code=identification_code).first()
            if not client:
                # Nếu chưa có, tạo mới khách hàng
                client = Client(
                    full_name=full_name,
                    phone_number=phone_number,
                    email=email,
                    identification_code=identification_code,
                    address="Chưa cung cấp",  # Hoặc lấy từ form nếu cần
                    client_type_id=1  # Đặt mặc định là loại khách hàng "Regular"
                )
                db.session.add(client)
                db.session.commit()

            # Tạo đơn đặt phòng
            booking_form = BookingForm(
                check_in_date=check_in_date,
                check_out_date=check_out_date,
                client_id=client.id
            )
            db.session.add(booking_form)
            db.session.commit()

            # Thêm chi tiết đặt phòng
            booking_detail = BookingRoomDetails(
                booking_form_id=booking_form.id,
                room_id=room.id,
                total=room.room_type.price_million
            )
            db.session.add(booking_detail)

            # Cập nhật trạng thái phòng
            room.room_status_id = RoomStatus.query.filter_by(status="Đã đặt").first().id
            db.session.commit()

            return render_template('booking.html', room=room,
                                   success="Đặt phòng thành công!")

        except Exception as e:
            db.session.rollback()
            return render_template('booking.html', room=room,
                                   error=f"Lỗi: {str(e)}")

    return render_template('booking.html', room=room)

if __name__ == "__main__":
    with app.app_context():
        app.run(debug=True)
