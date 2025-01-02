import hashlib
import hmac
import json
import os
import random
import uuid
from datetime import datetime, timedelta
from os import error
from time import time

import requests
from flask import Flask, render_template, request, redirect, make_response, flash, jsonify, url_for, session
from flask_login import login_user, logout_user, current_user, login_required
import requests
from flask import Flask, render_template, request, redirect, make_response, flash, jsonify, url_for
from flask_login import login_user, logout_user, current_user
from flask_bcrypt import Bcrypt
from sqlalchemy import Integer, func
from sqlalchemy.exc import IntegrityError, PendingRollbackError
from sqlalchemy.testing.suite.test_reflection import users

from hotelapp import admin

from hotelapp import app, dao, login, db, admin
from hotelapp.decorators import loggedin
from hotelapp.models import Room, BookingForm, RoomStatus, BookingRoomDetails, Client, UserRole, Invoice, RoomType, \
    AdImage, \
    ClientType, Regulation, Status, PaymentMethod, ClientRoomDetails
from hotelapp.vnpay.vnpay import Vnpay

# Khởi tạo Bcrypt
bcrypt = Bcrypt(app)


@app.route('/')
def index():
    ad_images = AdImage.query.limit(5).all()  # Chỉ tải 5 ảnh ban đầu
    room_types = dao.get_room_types()
    max_passenger = 3
    today = datetime.now().date()
    regulation = db.session.query(Regulation).filter_by(key="max_booking_days").first()
    next_28_day = (datetime.now() + timedelta(days=regulation.value)).date()
    return render_template('index.html', ad_images=ad_images, room_types=room_types, today=today,
                           next_28_day=next_28_day, max_passenger=max_passenger)


@app.route('/api/load-content', methods=['GET'])
def load_content():
    offset = int(request.args.get('offset', 0))
    limit = int(request.args.get('limit', 5))

    ads = AdImage.query.offset(offset).limit(limit).all()
    ads_data = [{"url": ad.url, "alt": ad.alt_text} for ad in ads]

    return jsonify(ads_data)


@app.route('/login-admin', methods=['POST'])
def login_admin():
    username = request.form.get('username')
    password = request.form.get('password')

    # Xác thực tài khoản admin
    user = dao.auth_user(username=username, password=password)
    if user:
        user_role = dao.get_user_role(user)
        if user_role.type == "Admin":
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

            if user_role and user_role.type == "Guest" or user_role.type == "Receptionist":
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
    checkin = request.form.get('check_in_date')
    checkout = request.form.get('check_out_date')
    room_type_id = request.form.get('ticket_class')
    passengers = request.form.get('passengers')

    # Truy vấn trạng thái phòng "Có sẵn"
    available_status = RoomStatus.query.filter_by(status='Có sẵn').first()

    if not available_status:
        return render_template('rooms.html',
                               error="Trạng thái 'Có sẵn' không tồn tại trong cơ sở dữ liệu.")  # "The 'Available' status does not exist in the database."

    query = Room.query.filter_by(room_status_id=available_status.id)

    if room_type_id is None:
        # Lọc theo số lượng khách nếu room_type_id không được cung cấp
        if passengers:
            passengers = int(passengers)  # Đảm bảo passengers là một số nguyên
            if passengers <= 3 and passengers > 0:
                query = query.filter(Room.room_type.has(max_passenger=3))
            elif passengers == 0:
                query = query.filter(Room.room_type.has())  # Kiểm tra phòng không có giới hạn về số khách
            else:
                query = query.filter(Room.room_type.has(max_passenger=passengers))
    else:
        # Lọc theo loại phòng nếu room_type_id có giá trị
        query = query.filter(Room.room_type_id == room_type_id)

    if checkin and checkout:
        try:
            checkin_date = datetime.strptime(checkin, '%Y-%m-%d')
            checkout_date = datetime.strptime(checkout, '%Y-%m-%d')
            booking_subquery = (
                db.session.query(BookingRoomDetails.room_id)
                .join(BookingForm)
                .filter(
                    BookingForm.check_in_date < checkout_date,
                    BookingForm.check_out_date > checkin_date
                )
            )
            dao.update_room_status(checkin_date)
            query = query.filter(~Room.id.in_(booking_subquery))
        except ValueError:
            return "Invalid date format", 400
    rooms = query.all()

    return render_template('rooms.html', rooms=rooms)


@app.route('/rooms')
def rooms():
    dao.update_room_status(datetime.now())

    # Lấy danh sách loại phòng để hiển thị trong dropdown
    room_types = RoomType.query.all()

    # Lấy các tham số lọc từ query string
    checkin = request.args.get('check_in_date')
    checkout = request.args.get('check_out_date')
    stay_duration = 1  # Mặc định 1 ngày nếu không có thông tin ngày trả

    if checkin and checkout:
        check_in_date = datetime.strptime(checkin, '%Y-%m-%d')
        check_out_date = datetime.strptime(checkout, '%Y-%m-%d')
        stay_duration = (check_out_date - check_in_date).days
    room_type_id = request.args.get('ticket_class', type=int)

    # Lấy số trang và kích thước trang từ query string (mặc định page=1, per_page=10)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 9, type=int)

    # Truy vấn danh sách phòng
    query = Room.query

    # Lọc theo loại phòng nếu có
    if room_type_id:
        query = query.filter(Room.room_type_id == room_type_id)

    # Lọc theo ngày nhận và trả phòng
    if checkin and checkout:
        try:
            checkin_date = datetime.strptime(checkin, '%Y-%m-%d')
            checkout_date = datetime.strptime(checkout, '%Y-%m-%d')
            booking_subquery = (
                db.session.query(BookingRoomDetails.room_id)
                .join(BookingForm)
                .filter(
                    BookingForm.check_in_date < checkout_date,
                    BookingForm.check_out_date > checkin_date
                )
            )
            dao.update_room_status(checkin_date)
            query = query.filter(~Room.id.in_(booking_subquery))
        except ValueError:
            return "Invalid date format", 400

    # Áp dụng phân trang
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    rooms = pagination.items

    # Truyền dữ liệu sang template
    return render_template(
        'rooms.html',
        rooms=rooms,
        room_types=room_types,
        checkin=checkin,
        checkout=checkout,
        selected_room_type=room_type_id,
        pagination=pagination,
        stay_duration=stay_duration,
    )


from flask_login import current_user


@app.route('/booking', methods=['POST'])
def booking():
    if not current_user.is_authenticated:
        return redirect('/login')
    room_ids = request.form.getlist('selected_rooms')  # Lấy danh sách các phòng được chọn
    check_in_date = datetime.strptime(request.form.get('check_in_date'), '%Y-%m-%d')
    check_out_date = datetime.strptime(request.form.get('check_out_date'), '%Y-%m-%d')

    # Tính số ngày ở
    stay_duration = (check_out_date - check_in_date).days

    max_capacity_surcharge_percentage = dao.get_regulation_by_key("max_capacity_surcharge_percentage")
    rooms = Room.query.filter(Room.id.in_(room_ids)).all()  # Lấy thông tin các phòng

    # Tạo booking form
    booking_form = BookingForm(
        check_in_date=check_in_date,
        check_out_date=check_out_date,
        client_id=current_user.client_id
    )
    db.session.add(booking_form)
    db.session.flush()

    for room in rooms:
        passengers = int(request.form.get(f'passengers-{room.id}'))
        is_reach_max = passengers == room.room_type.max_passenger
        is_contain_foreigner = False
        total = room.room_type.price_million * stay_duration  # Tính tổng tiền cơ bản (nhân số ngày ở)

        # Tạo booking details
        booking_details = BookingRoomDetails(
            booking_form_id=booking_form.id,
            room_id=room.id,
            passengers=passengers
        )
        db.session.add(booking_details)
        db.session.flush()

        for i in range(1, passengers + 1):
            guest_name = request.form.get(f'guest-{room.id}-{i}-name')
            guest_id = request.form.get(f'guest-{room.id}-{i}-id')
            guest_type = request.form.get(f'guest-{room.id}-{i}-type')
            guest_address = request.form.get(f'guest-{room.id}-{i}-address')

            client_type = dao.get_client_type_by_id(guest_type)
            if client_type.type == "Nước Ngoài":
                is_contain_foreigner = True

            guest = Client(
                full_name=guest_name,
                identification_code=guest_id,
                client_type_id=guest_type,
                address=guest_address
            )
            db.session.add(guest)
            db.session.flush()

            client_room_details = ClientRoomDetails(
                booking_details_id=booking_details.id,
                client_id=guest.client_id
            )
            db.session.add(client_room_details)

        # Tính tổng tiền với phụ phí
        if is_reach_max:
            total += room.room_type.price_million * max_capacity_surcharge_percentage.value * stay_duration
        if is_contain_foreigner:
            total += (room.room_type.price_million * dao.get_client_type_by_type("Nước Ngoài").coefficient - room.room_type.price_million) * stay_duration
        booking_details.total = total
        db.session.add(booking_details)

    db.session.commit()

    return redirect(url_for('booking_summary', form_id=booking_form.id))

    # room = Room.query.get(room_id)
    # booking_detail = BookingRoomDetails(
    #     booking_form_id=booking_form.id,
    #     room_id=room.id,
    #     passengers=passengers
    # )
    # db.session.add(booking_detail)
    # room_ids = request.form.getlist('selected_rooms')  # Lấy danh sách các phòng được chọn
    # client_types = dao.get_client_types()
    # checkin = request.form.get('check_in_date')
    # checkout = request.form.get('check_out_date')
    # # max_passenger = room.room_type.max_passenger
    # passengers_list = request.form.getlist('passengers')  # Lấy danh sách số lượng khách của từng phòng
    # print("Room IDs:", room_ids)
    # print("passe list: ", passengers_list)

    # if not room_ids or not checkin or not checkout:
    #     return "Vui lòng chọn phòng, nhập ngày nhận/trả phòng.", 400
    #
    # rooms = Room.query.filter(Room.id.in_(room_ids)).all()
    #
    # if not rooms:  # Kiểm tra nếu không tìm thấy phòng nào
    #     return "Không tìm thấy phòng nào trong danh sách đã chọn.", 404
    #
    # # Kiểm tra người dùng đã đăng nhập chưa
    # if current_user.is_authenticated:
    #     # Nếu người dùng đã đăng nhập, lấy thông tin client từ current_user
    #     client = dao.get_client_by_id(current_user.client_id)
    # else:
    #     # Nếu người dùng chưa đăng nhập, chuyển hướng đến trang đăng nhập
    #     return redirect('/login')
    #
    # try:
    #     # Chuyển đổi ngày check-in và check-out
    #     checkin_date = datetime.strptime(checkin, '%Y-%m-%d')
    #     checkout_date = datetime.strptime(checkout, '%Y-%m-%d')
    #
    #     if checkin_date >= checkout_date:
    #         return "Ngày trả phòng phải sau ngày nhận phòng.", 400
    #
    #     total_passengers = 0
    #     total_price = 0
    #
    #     # Tạo BookingForm duy nhất cho tất cả các phòng
    #     booking_form = BookingForm(
    #         check_in_date=checkin_date,
    #         check_out_date=checkout_date,
    #         client_id=client.client_id
    #     )
    #     db.session.add(booking_form)
    #     db.session.commit()
    #
    #     # Lặp qua danh sách các phòng để kiểm tra, lưu và tính toán
    #     for index, room_id in enumerate(room_ids):
    #         room = Room.query.get_or_404(room_id)
    #         available_status = RoomStatus.query.filter_by(status='Có sẵn').first()
    #
    #         if room.room_status_id != available_status.id:
    #             return f"Phòng {room.name} không khả dụng.", 400
    #
    #         # Số lượng hành khách cho phòng hiện tại
    #         passengers = int(passengers_list[index])
    #         if passengers < 1 or passengers > room.room_type.max_passenger:
    #             return f"Số lượng khách cho phòng {room.name} phải từ 1 đến {room.room_type.max_passenger}.", 400
    #
    #         total_passengers += passengers
    #
    #         # Tính giá phòng
    #         room_price = float(room.room_type.price_million)
    #         total_days = (checkout_date - checkin_date).days
    #
    #         # Tính phụ phí nếu đạt max_passenger
    #         regulation = db.session.query(Regulation).filter_by(key="max_capacity_surcharge_percentage").first()
    #         surcharge_percentage = float(regulation.value) if regulation else 0
    #
    #         if passengers == room.room_type.max_passenger:
    #             room_price *= (1 + surcharge_percentage / 100)
    #
    #         # Tạo BookingRoomDetails
    #         booking_detail = BookingRoomDetails(
    #             booking_form_id=booking_form.id,
    #             room_id=room.id,
    #             passengers=passengers,
    #             total=room_price * total_days
    #         )
    #         total_price += room_price * total_days
    #         db.session.add(booking_detail)
    #
    #         # Cập nhật trạng thái phòng thành "Đã đặt"
    #         room.room_status_id = RoomStatus.query.filter_by(status="Đã đặt").first().id
    #         db.session.commit()
    #
    #     # Tạo phiếu thanh toán (Invoice)
    #     invoice = Invoice(
    #         booking_form_id=booking_form.id,
    #         total=total_price,
    #         status=Status.PENDING  # Trạng thái chờ thanh toán
    #     )
    #     db.session.add(invoice)
    #     db.session.commit()
    #
    #     # Hiển thị trang thanh toán
    #     return render_template(
    #         'payment.html',
    #         booking_form=booking_form,
    #         invoice=invoice,
    #         total_passengers=total_passengers
    #     )
    #
    # except Exception as e:
    #     db.session.rollback()
    #     return f"Lỗi: {str(e)}", 500

    # if request.method == 'POST':
    #     try:
    #         # Lấy dữ liệu từ form
    #         full_name = request.form['full_name']
    #         phone_number = request.form['phone_number']
    #         email = request.form['email']
    #         identification_code = request.form['identification_code']
    #         address = request.form.get('address')
    #         client_type_id = request.form.get('client_type_id')
    #         passengers = request.form.get('passengers')
    #
    #         # Lấy ngày nhận và ngày trả phòng từ form
    #         checkin = request.form['check_in_date']
    #         checkout = request.form['check_out_date']
    #         # Kiểm tra các trường dữ liệu
    #         if not full_name:
    #             return render_template('booking.html', error="Vui lòng nhập tên khách hàng.")
    #         if not phone_number or not phone_number.isdigit() or len(phone_number) != 10:
    #             return render_template('booking.html', error="Số điện thoại không hợp lệ. Nhập 10 chữ số.")
    #         if not email or '@' not in email:
    #             return render_template('booking.html', error="Email không hợp lệ.")
    #         if not identification_code or not identification_code.isdigit() or len(identification_code) != 12:
    #             return render_template('booking.html', error="CCCD phải có đúng 12 chữ số.")
    #         if not client_type_id:
    #             return render_template('booking.html', error="Vui lòng chọn loại khách.")
    #         if not passengers.isdigit() or int(passengers) < 1 or int(passengers) > 3:
    #             return render_template('booking.html', error="Số lượng khách phải từ 1 đến 3.")
    #         if not checkin or not checkout:
    #             return render_template('booking.html', error="Vui lòng chọn ngày nhận và trả phòng.")
    #         if checkin >= checkout:
    #             return render_template('booking.html', error="Ngày trả phòng phải sau ngày nhận phòng.")
    #
    #         if checkin and checkout:
    #             try:
    #                 checkin_date = datetime.strptime(checkin, '%Y-%m-%d')  # Định dạng ngày tháng
    #                 checkout_date = datetime.strptime(checkout, '%Y-%m-%d')
    #
    #                 # Tránh phòng bị trùng lịch
    #                 booking_subquery = (
    #                     db.session.query(BookingRoomDetails)
    #                     .join(BookingForm)
    #                     .filter(
    #                         BookingRoomDetails.room_id == room_id,
    #                         BookingForm.check_in_date < checkin_date,
    #                         BookingForm.check_out_date > checkout_date
    #                     )
    #                     .exists()
    #                 )
    #
    #                 # Kiểm tra nếu phòng đã được đặt trong khoảng thời gian này
    #                 if db.session.query(booking_subquery).scalar():
    #                     return render_template('booking.html', room=room,
    #                                            error="Phòng đã được đặt trong khoảng thời gian này!")
    #
    #
    #
    #             except ValueError:
    #                 return render_template('booking.html', room=room, error="Định dạng ngày không hợp lệ!",
    #                                        client_types=client_types)
    #
    #         # Kiểm tra sự có sẵn của phòng
    #         available_status = RoomStatus.query.filter_by(status='Có sẵn').first()
    #         maintenance_status = RoomStatus.query.filter_by(status='Bảo trì').first()
    #
    #         if not available_status:
    #             raise ValueError("Trạng thái phòng 'Có sẵn' không tồn tại trong cơ sở dữ liệu.")
    #         if room.room_status_id == maintenance_status.id:
    #             return render_template('booking.html', room=room, error="Phòng này đang được bảo trì!")
    #         if room.room_status_id != available_status.id:
    #             return render_template('booking.html', room=room, error="Phòng này đã được đặt trước!")
    #
    #         # Kiểm tra thông tin khách hàng đã tồn tại chưa
    #         if not client:
    #             # Nếu chưa có, tạo mới khách hàng
    #             client = Client(
    #                 full_name=full_name,
    #                 phone_number=phone_number,
    #                 email=email,
    #                 address=address,
    #                 identification_code=identification_code,
    #                 client_type_id=client_type_id,
    #             )
    #             db.session.add(client)
    #             db.session.commit()
    #
    #         # Tạo đơn đặt phòng
    #         booking_form = BookingForm(
    #             check_in_date=checkin,
    #             check_out_date=checkout,
    #             client_id=client.client_id,
    #         )
    #         db.session.add(booking_form)
    #         db.session.commit()
    #         # Lặp qua các khách phụ
    #         for i in range(1, int(passengers)):  # Lặp cho mỗi khách phụ
    #             guest_full_name = request.form.get(f'full_name_{i}')
    #             guest_phone_number = request.form.get(f'phone_number_{i}')
    #             guest_identification_code = request.form.get(f'identification_code_{i}')
    #             guest_client_type_id = request.form.get(f'client_type_id_{i}')
    #
    #             # Kiểm tra thông tin khách phụ
    #             if not guest_full_name or not guest_phone_number or not guest_identification_code:
    #                 return render_template('booking.html', error=f"Thông tin khách hàng phụ {i + 1} chưa đầy đủ.")
    #
    #             guest = Guest(
    #                 full_name=request.form.get(f'full_name_{i}'),
    #                 phone_number=request.form.get(f'phone_number_{i}'),
    #                 identification_code=request.form.get(f'identification_code_{i}'),
    #                 client_type_id=request.form.get(f'client_type_id_{i}'),
    #                 booking_form_id=booking_form.id
    #             )
    #             db.session.add(guest)
    #             db.session.commit()
    #
    #         # Chuyển đổi giá phòng và số lượng hành khách
    #         room_price = float(room.room_type.price_million)  # Giá phòng phải là số thực
    #         passengers_count = int(passengers)  # Số lượng hành khách (kiểm tra chắc chắn có giá trị hợp lệ)
    #         client_type_id = int(client_type_id)  # ID loại khách
    #         # Tạo đối tượng BookingRoomDetails
    #         booking_detail = BookingRoomDetails(
    #             booking_form_id=booking_form.id,
    #             room_id=room.id,
    #             passengers=passengers_count,  # Số lượng hành khách
    #             total=0  # Giá trị ban đầu
    #         )
    #
    #
    #         # Thêm đối tượng vào session
    #         db.session.add(booking_detail)
    #         db.session.commit()
    #
    #
    #         regulation = db.session.query(Regulation).filter_by(key="max_capacity_surcharge_percentage").first()
    #         # Kiểm tra hệ số của các loại khách
    #         # Convert the string dates to datetime objects
    #         check_in = datetime.strptime(checkin, '%Y-%m-%d')
    #         check_out = datetime.strptime(checkout, '%Y-%m-%d')
    #
    #         # Calculate the difference between the two dates
    #         difference = check_out - check_in
    #
    #         # Get the number of days
    #         total_days = difference.days
    #
    #         if len(client_types) < 2:
    #             raise ValueError("Không đủ dữ liệu loại khách trong cơ sở dữ liệu.")
    #
    #         # Tính toán tổng giá trị dựa trên số lượng hành khách và loại khách
    #         from decimal import Decimal
    #         # Using filter with positional arguments
    #         # Query the BookingRoomDetails based on room_id
    #         booking_details = db.session.query(BookingRoomDetails).filter_by(room_id=room.id).first()
    #
    #
    #         # Extract booking_form_id safely
    #         booking_form = booking_details.booking_form_id
    #
    #         # Query the Guest using the booking_form_id
    #         guest = db.session.query(Guest).filter_by(booking_form_id=booking_form).first()
    #
    #
    #         # Chuyển đổi room_price và các hệ số từ client_types về Decimal để tính toán chính xác
    #         room_price_decimal = Decimal(room_price)  # Chuyển đổi room_price sang Decimal
    #         regulation_value = Decimal(regulation.value)  # Chuyển regulation.value sang Decimal
    #         total = 0
    #         # Tính toán với các trường hợp khác nhau
    #         if passengers_count == max_passenger:
    #             total = room_price_decimal * (1 + regulation_value) * Decimal(
    #                 total_days)  # Áp dụng phụ phí 25% khi số khách đạt tối đa
    #
    #         # Kiểm tra loại khách chính là người Việt (client_type_id == 1) hay người nước ngoài (client_type_id == 2)
    #         if client_type_id == 1:  # Khách Việt
    #             total = room_price_decimal * Decimal(client_types[0].coefficient) * Decimal(total_days)
    #         elif client_type_id == 2:  # Khách nước ngoài
    #             total = room_price_decimal * Decimal(client_types[1].coefficient) * Decimal(total_days)
    #
    #         # Kiểm tra nếu có khách phụ là người nước ngoài và áp dụng phụ phí thêm
    #
    #         if guest and guest.client_type_id == 2:  # Nếu khách phụ là người nước ngoài
    #             total *= Decimal(client_types[1].coefficient)  # Áp dụng phụ phí 1.5 cho khách nước ngoài
    #
    #         print(f"Tổng giá: {total}")
    #
    #         # Cập nhật giá mới sau khi tạo
    #         new_total =  total  # Hàm tính giá mới
    #         booking_detail.total = new_total
    #
    #         # Commit lại để lưu thay đổi
    #         db.session.commit()
    #
    #         db.session.add(booking_detail)
    #
    #
    #         # Cập nhật trạng thái phòng
    #         room.room_status_id = RoomStatus.query.filter_by(status="Vui lòng thanh toán").first().id
    #         db.session.commit()
    #
    #         # Sau khi đặt phòng thành công, render template payment.html
    #         booking_forms = BookingForm.query.filter_by(client_id=client.client_id).order_by(
    #             BookingForm.id.desc()).all()
    #         return render_template(
    #             'payment.html',
    #             booking_form=booking_form,
    #             booking_forms=booking_forms
    #         )
    #
    #     except Exception as e:
    #         db.session.rollback()
    #         return render_template('booking.html', room=room, error=f"Lỗi: {str(e)}", client_types=client_types,
    #                                client=client, max_passenger=max_passenger)
    #
    # return render_template('booking.html', room=room, client_types=client_types, client=client,
    #                        max_passenger=max_passenger)


# @app.route('/booking_finalize', methods=['POST'])
# def booking_finalize():
#     full_name = request.form.get('full_name')
#     phone_number = request.form.get('phone_number')
#     email = request.form.get('email')
#     selected_rooms = request.form.getlist('selected_rooms')
#     check_in_date = request.form.get('check_in_date')
#     check_out_date = request.form.get('check_out_date')
#
#     booking_form = BookingForm(
#         check_in_date=datetime.strptime(check_in_date, '%Y-%m-%d'),
#         check_out_date=datetime.strptime(check_out_date, '%Y-%m-%d'),
#         client_id=current_user.client_id
#     )
#     db.session.add(booking_form)
#     db.session.commit()
#
#     for room_id in selected_rooms:
#         passengers = int(request.form.get(f'passengers-{room_id}'))
#         for i in range(1, passengers + 1):
#             guest_name = request.form.get(f'guest-{room_id}-{i}-name')
#             guest_id = request.form.get(f'guest-{room_id}-{i}-id')
#             guest = Guest(
#                 full_name=guest_name,
#                 identification_code=guest_id,
#                 booking_form_id=booking_form.id
#             )
#             db.session.add(guest)
#
#         room = Room.query.get(room_id)
#         booking_detail = BookingRoomDetails(
#             booking_form_id=booking_form.id,
#             room_id=room.id,
#             passengers=passengers
#         )
#         db.session.add(booking_detail)
#         room.room_status_id = RoomStatus.query.filter_by(status="Đã đặt").first().id
#
#     db.session.commit()
#     return "Đặt phòng thành công!"


@app.route('/confirm_booking', methods=['POST'])
def confirm_booking():
    if not current_user.is_authenticated:
        return redirect('/login')
    room_ids = request.form.getlist('selected_rooms')  # Lấy danh sách các phòng được chọn
    room_ids = room_ids[0].split(',')
    print(room_ids)
    check_in_date = request.form.get('check_in_date')
    check_out_date = request.form.get('check_out_date')

    # Lấy thông tin các phòng từ database
    rooms = Room.query.filter(Room.id.in_(room_ids)).all()

    if not rooms:
        return "Không tìm thấy phòng nào đã chọn.", 404

    return render_template(
        'booking.html',
        rooms=rooms,
        check_in_date=check_in_date,
        check_out_date=check_out_date
    )


@app.route("/forms")
def forms():
    if not current_user.is_authenticated:
        return redirect('/login')
    # Lấy từ khóa tìm kiếm từ query string
    search_query = request.args.get('search', '').strip()

    # Nếu có từ khóa tìm kiếm, lọc theo tên khách hàng
    if search_query:
        forms = db.session.query(BookingForm).join(Client).filter(
            Client.full_name.ilike(f'%{search_query}%')  # Tìm kiếm không phân biệt chữ hoa/thường
        ).all()
    else:
        # Nếu không có từ khóa, hiển thị tất cả phiếu thuê
        forms = dao.get_forms()
    return render_template("forms.html", forms=forms)


@app.route('/booking_success', methods=['POST', 'GET'])
def booking_success():
    # Lấy client_id từ đối tượng người dùng đã đăng nhập
    if current_user.is_authenticated:
        client_id = current_user.client_id  # client_id là id của người dùng hiện tại
    else:
        # Xử lý khi người dùng chưa đăng nhập
        return redirect(url_for('login'))

    # Lấy đơn đặt phòng mới nhất của khách hàng
    booking_form = BookingForm.query.filter_by(client_id=client_id).order_by(BookingForm.id.desc()).first()

    # Lấy tất cả các đơn đặt phòng của khách hàng
    booking_forms = BookingForm.query.filter_by(client_id=client_id).order_by(BookingForm.id.desc()).all()

    # Render trang thanh toán và truyền dữ liệu booking_form và booking_forms vào template
    return render_template(
        'payment.html',
        booking_form=booking_form,  # Đơn đặt phòng vừa được tạo
        booking_forms=booking_forms  # Tất cả các đơn đặt phòng của khách hàng
    )



@app.route('/booking-details/<int:form_id>')
def booking_details(form_id):
    # Lấy thông tin phiếu đặt phòng
    form = BookingForm.query.get_or_404(form_id)

    # Lấy danh sách khách ở cùng từ bảng Guest
    guests = dao.get_clients_of_booking_form(form_id)

    # Lấy thông tin các phòng đặt
    booking_rooms = BookingRoomDetails.query.filter_by(booking_form_id=form_id).all()

    # Tính tổng giá tiền
    total_price = sum([room.total for room in booking_rooms])

    return render_template(
        'booking_details.html',
        form=form,
        guests=guests,
        booking_rooms=booking_rooms,
        total_price=total_price
    )



@app.route('/checkin/<int:form_id>', methods=['GET', 'POST'])
def checkin(form_id):
    if not current_user.is_authenticated:
        return redirect('/login')
    form = BookingForm.query.get_or_404(form_id)

    if not current_user.is_authenticated:
        flash("Bạn phải đăng nhập để thực hiện hành động này.", "danger")
        return redirect("/login")

    form.is_checked_in = True
    form.receipted_by = current_user.id
    db.session.commit()
    flash(f'Check-in thành công cho phiếu số {form_id}!', 'success')
    return redirect("/forms")


@app.route('/booking-summary/<int:form_id>')
def booking_summary(form_id):
    if not current_user.is_authenticated:
        return redirect('/login')
    booking_form = BookingForm.query.get(form_id)
    max_capacity_surcharge_percentage = dao.get_regulation_by_key("max_capacity_surcharge_percentage").value
    foreigner_coefficient = dao.get_client_type_by_type("Nước Ngoài").coefficient

    check_in_date = booking_form.check_in_date
    check_out_date = booking_form.check_out_date
    stay_duration = (check_out_date - check_in_date).days

    details = BookingRoomDetails.query.filter_by(booking_form_id=booking_form.id).all()

    # Tính toán phụ thu và tổng tiền cho từng phòng
    for detail in details:
        is_foreigner_present = any(
            client_room.client.client_type.type == "Nước Ngoài"
            for client_room in ClientRoomDetails.query.filter_by(booking_details_id=detail.id)
        )
        is_reach_max_capacity = detail.passengers == detail.room.room_type.max_passenger

        surcharge = 0
        if is_reach_max_capacity:
            surcharge += detail.room.room_type.price_million * max_capacity_surcharge_percentage * stay_duration
        if is_foreigner_present:
            surcharge += (
                                     detail.room.room_type.price_million * foreigner_coefficient - detail.room.room_type.price_million) * stay_duration

        detail.is_foreigner_present = is_foreigner_present
        detail.is_reach_max_capacity = is_reach_max_capacity
        detail.surcharge = surcharge
        detail.total = (detail.room.room_type.price_million * stay_duration) + surcharge
        detail.stay_duration = stay_duration  # Thêm số ngày ở vào detail để dùng trong template

    payment_methods = PaymentMethod.query.all()
    total = sum(detail.total for detail in details)

    return render_template(
        'booking_summary.html',
        booking_form=booking_form,
        payment_methods=payment_methods,
        booking_room_details=details,
        max_capacity_surcharge_percentage=max_capacity_surcharge_percentage,
        foreigner_coefficient=foreigner_coefficient,
        total=total
    )


@app.route('/pay', methods=['POST'])
def pay():
    form_id = request.form.get('form_id')
    payment_method_id = request.form.get('payment_method')
    print("Form ID received: ", form_id)  # Debug
    form = BookingForm.query.get_or_404(form_id)

    if not current_user.is_authenticated:
        flash("Bạn phải đăng nhập để thực hiện hành động này.", "danger")
        return redirect("/login")

    payment_method = PaymentMethod.query.get(payment_method_id)
    if not payment_method:
        flash("Phương thức thanh toán không hợp lệ.", "danger")
        return redirect('/my-booking')

        # Nếu phương thức thanh toán là "Tiền Mặt" và người dùng là lễ tân
    if payment_method.type == 'Tiền Mặt' and current_user.user_role.type == 'Receptionist':
        try:
            # Đánh dấu hóa đơn đã thanh toán
            invoice = dao.create_invoice(form_id, payment_method.id, trans_id=f"cash-form-{form_id}")
            invoice.status = Status.SUCCESS
            form.is_paid = True  # Đánh dấu phiếu đặt phòng đã được thanh toán
            db.session.commit()


                    # Hiển thị thông báo thành công
            flash(f'Thanh toán thành công cho phiếu số {form_id}!', 'success')
            return redirect(url_for('my_booking'))  # Chuyển hướng về trang "my_booking"

        except requests.exceptions.RequestException as e:
                flash(f'Lỗi thanh toán: {e}', 'danger')


    # Các phương thức thanh toán khác (MomoPay, ZaloPay, VNPay, v.v.)
    trans_id = ""

    api_url = ""
    match payment_method.type:
        case "MomoPay":
            api_url = url_for('momo_pay', _external=True)
            trans_id = str(uuid.uuid4())
        case "ZaloPay":
            transID = random.randrange(1000000)
            api_url = url_for('zalo_pay', _external=True)
            trans_id = "{:%y%m%d}_{}".format(datetime.today(), transID)
        case "VNPay":
            trans_id = str(uuid.uuid4())
            api_url = url_for('vnpay_payment', _external=True)

    invoice = dao.create_invoice(form_id, payment_method.id, trans_id)
    try:
        response = requests.post(api_url, json={
            "total": invoice.total,
            "trans_id": trans_id
        })
        response.raise_for_status()  # Kiểm tra nếu có lỗi HTTP
        flash(f'Thanh toán thành công cho phiếu số {form_id}!', 'success')
        return redirect(response.json().get("payUrl"))

    except requests.exceptions.RequestException as e:
        flash(f'Lỗi thanh toán: {e}', 'danger')

    return redirect("/")


@app.route('/api/momo-pay', methods=['POST'])
def momo_pay():
    endpoint = app.config.get("MOMO_CREATE_URL")
    partnerCode = "MOMO"
    accessKey = "F8BBA842ECF85"
    secretKey = "K951B6PE1waDMi640xX08PD3vg6EkVlz"
    requestId = str(uuid.uuid4())
    amount = str(int((request.json.get('total'))))

    orderId = str((request.json.get('trans_id')))

    orderInfo = "Pay with MoMo"
    requestType = "captureWallet"
    extraData = ""

    redirectUrl = str(app.config.get("SERVER_URL")) + "/my-booking"
    ipnUrl = (app.config.get("SERVER_URL") + "/api/momo-pay/ipn")
    rawSignature = "accessKey=" + accessKey + "&amount=" + amount + "&extraData=" + extraData + "&ipnUrl=" + ipnUrl + "&orderId=" + orderId + "&orderInfo=" + orderInfo + "&partnerCode=" + partnerCode + "&redirectUrl=" + redirectUrl + "&requestId=" + requestId + "&requestType=" + requestType
    h = hmac.new(bytes(secretKey, 'ascii'), bytes(rawSignature, 'ascii'), hashlib.sha256)
    signature = h.hexdigest()

    data = {
        'partnerCode': partnerCode,
        'partnerName': "Stay Ease",
        'requestId': requestId,
        'amount': amount,
        'orderId': orderId,
        'orderInfo': orderInfo,
        'redirectUrl': redirectUrl,
        'ipnUrl': ipnUrl,
        'lang': "vi",
        'extraData': extraData,
        'requestType': requestType,
        'signature': signature
    }

    # Gửi yêu cầu đến MoMo
    response = requests.post(endpoint, json=data, headers={'Content-Type': 'application/json'})
    if response.status_code == 200:
        response_data = response.json()

        print(response_data)
        return jsonify({
            'ok': '200',
            'payUrl': response_data.get('payUrl'),
            'orderId': response_data.get('orderId')
        })
    else:
        print(f"MoMo response error: {response.status_code}, {response.text}")
        return jsonify({'error': 'Error from MoMo', 'details': response.json()}), response.status_code

    data = json.dumps(data)
    print(data)

    clen = len(data)
    response = requests.post(endpoint, data=data,
                             headers={'Content-Type': 'application/json', 'Content-Length': str(clen)})
    if response.status_code == 200:

        response_data = response.json()

        print(response.json())
        return jsonify({'ok': '200',
                        'payUrl': response_data.get('payUrl'),
                        'orderId': response_data.get('orderId')
                        })
        # return redirect(response_data.get('payUrl'))

    else:
        print(response.json())
        return jsonify({'error': 'Invalid request method'})


@app.route('/api/momo-pay/ipn', methods=['POST'])
def momo_ipn():
    data = json.loads(request.get_data(as_text=True))
    print(data)
    result_code = data["resultCode"]
    orderId = data['orderId']

    if result_code != 0:  # Thanh toán thất bại
        return jsonify({'error': "Thanh toán thất bại", 'status': 400})

    try:
        invoice = Invoice.query.filter_by(transaction_id=orderId).first()
        if invoice:
            # print(invoice.booking_form)
            # room = Room.query.get_or_404(invoice.booking_form_id.room_id.id)
            invoice.status = Status.SUCCESS
            form = BookingForm.query.get(invoice.booking_form_id)
            form.is_paid = True

            # Cập nhật trạng thái phòng sau khi thanh toán thành công
            # room.room_status_id = RoomStatus.query.filter_by(status="Đã đặt").first().id
            db.session.commit()

        return jsonify({'status': 200})  # Thanh toán thành công và trạng thái phòng đã được cập nhật
    except Exception as e:
        print(f"Error while processing payment: {e}")
        return jsonify({'status': 500, 'error': str(e)})


@app.route('/api/zalo-pay', methods=['POST'])
def zalo_pay():
    endpoint = app.config.get("ZALO_CREATE_URL")
    appid = 2553
    key1 = "PcY4iZIKFCIdgZvA6ueMcMHHUbRLYjPL"
    appuser = "user123"
    transID = random.randrange(1000000)
    apptime = int(round(time() * 1000))  # miliseconds

    app_trans_id = str((request.json.get('trans_id')))
    amount = str(int((request.json.get('total'))))
    embeddata = json.dumps({"redirecturl": str(app.config.get("SERVER_URL")) + "/my-booking"})
    item = json.dumps([{}])

    callback_url = (app.config.get("SERVER_URL") + "/api/zalo-pay/callback")

    # Tạo chuỗi dữ liệu theo định dạng yêu cầu
    raw_data = "{}|{}|{}|{}|{}|{}|{}".format(appid, app_trans_id, appuser, amount, apptime, embeddata, item)

    # Tính toán MAC bằng cách sử dụng HMAC
    mac = hmac.new(key1.encode(), raw_data.encode(), hashlib.sha256).hexdigest()

    # Dữ liệu gửi đi
    data = {
        "app_id": appid,
        "app_user": appuser,
        "app_time": apptime,
        "amount": amount,
        "app_trans_id": app_trans_id,
        "embed_data": embeddata,
        "item": item,
        "description": "Lazada - Payment for the order #" + str(transID),
        "bank_code": "zalopayapp",
        "mac": mac,
        "callback_url": callback_url
    }

    # Gửi yêu cầu tạo
    response = requests.post(url=endpoint, data=data)

    if response.status_code == 200:
        response_data = response.json()
        print(response_data)
        return jsonify({'ok': '200', 'orderId': app_trans_id, 'payUrl': response_data.get('order_url')})
    else:
        return jsonify({'error': 'Invalid request method'}), 400


@app.route('/api/zalo-pay/callback', methods=['POST'])
def callback():
    result = {}
    key2 = 'kLtgPl8HHhfvMuDHPwKfgfsY4Ydm9eIz'
    try:
        cbdata = request.json
        mac = hmac.new(key2.encode(), cbdata['data'].encode(), hashlib.sha256).hexdigest()

        # kiểm tra callback hợp lệ (đến từ ZaloPay server)
        if mac != cbdata['mac']:
            # callback không hợp lệ
            result['return_code'] = -1
            result['return_message'] = 'mac not equal'
        else:
            # thanh toán thành công
            # merchant cập nhật trạng thái cho đơn hàng
            dataJson = json.loads(cbdata['data'])
            orderId = dataJson['app_trans_id']
            print("update order's status = success where apptransid = " + dataJson['app_trans_id'])
            invoice = Invoice.query.filter_by(transaction_id=orderId).first()
            if invoice:
                # print(invoice.booking_form)
                # room = Room.query.get_or_404(invoice.booking_form.room_id.id)
                invoice.status = Status.SUCCESS
                form = BookingForm.query.get(invoice.booking_form_id)
                form.is_paid = True
                # Cập nhật trạng thái phòng sau khi thanh toán thành công
                # room.room_status_id = RoomStatus.query.filter_by(status="Đã đặt").first().id
                db.session.commit()
            result['return_code'] = 1
            result['return_message'] = 'success'

    except Exception as e:
        result['return_code'] = 0  # ZaloPay server sẽ callback lại (tối đa 3 lần)
        result['return_message'] = str(e)

    # thông báo kết quả cho ZaloPay server
    print(result)
    return jsonify(result)


# Định nghĩa filter 'currency'
@app.template_filter('currency')
def currency_filter(value):
    """Chuyển giá trị thành định dạng tiền tệ."""
    try:
        return f"{value:,.0f} đ"  # Định dạng tiền tệ theo kiểu VND
    except (ValueError, TypeError):
        return value  # Nếu không phải kiểu số, trả lại giá trị gốc


@app.route("/my-booking")
def my_booking():
    # print("methods:", payment_methods)
    if current_user.is_authenticated:
        client = dao.get_client_by_id(current_user.client_id)
    else:
        return redirect('/login')
    booking_form = BookingForm.query.filter_by(client_id=client.client_id).order_by(BookingForm.id.desc()).first()
    booking_forms = BookingForm.query.filter_by(client_id=client.client_id).order_by(BookingForm.id.desc()).all()
    return render_template(
        'payment.html',
        booking_form=booking_form,
        booking_forms=booking_forms
    )


@app.context_processor
def common_attributes():
    return {
        'payment_methods': PaymentMethod.query.all(),
        'client_types': ClientType.query.all()
    }


# vnpay
vnpay = Vnpay(
    tmn_code=app.config.get("VNPAY_TMN_CODE"),
    secret_key=app.config.get("VNPAY_HASH_SECRET_KEY"),
    return_url=app.config.get("SERVER_URL"),
    vnpay_payment_url=app.config.get("VNPAY_PAYMENT_URL"),
    api_url=app.config.get("VNPAY_API_URL")
)


@app.route("/vnpay_payment", methods=["GET", "POST"])
def vnpay_payment():
    txn_ref = str((request.json.get('trans_id')))
    amount = str(int((request.json.get('total'))) * 100)
    print("VNPAY: ", txn_ref)
    try:
        # Prepare VNPAY request data
        req = {
            "vnp_Version": "2.1.0",
            "vnp_Command": "pay",
            "vnp_TmnCode": app.config.get("VNPAY_TMN_CODE"),
            "vnp_Amount": amount,  # Amount in VND multiplied by 100 (VNPAY format)
            "vnp_CurrCode": "VND",
            "vnp_TxnRef": txn_ref,  # Unique transaction reference
            "vnp_OrderInfo": "Payment for order #123123",
            "vnp_OrderType": "billpayment",
            "vnp_Locale": "vn",
            "vnp_BankCode": "NCB",
            "vnp_CreateDate": datetime.now().strftime('%Y%m%d%H%M%S'),
            "vnp_IpAddr": request.remote_addr,
        }
        # Add return URL
        req['vnp_ReturnUrl'] = app.config.get("SERVER_URL") + "/my-booking"
        # Get payment URL
        payment_url = vnpay.get_payment_url(req)

        # Redirect to VNPAY payment gateway
        return jsonify({'ok': '200', 'orderId': txn_ref, 'payUrl': payment_url})

    except Exception as e:
        # Handle and log errors
        app.logger.error(f"Error during VNPAY payment: {e}")
        return jsonify({"error": "An error occurred while processing your payment request."}), 500


@app.route("/vnpay_payment_return", methods=["GET"])
def vnpay_payment_return():
    print("callback called")
    try:
        # Get response parameters
        response_data = request.args.to_dict()

        # Validate response
        if vnpay.validate_response(response_data):
            # Payment successful
            vnp_TxnRef = response_data.get("vnp_TxnRef")
            print(vnp_TxnRef)
            vnp_Amount = response_data.get("vnp_Amount")
            vnp_ResponseCode = response_data.get("vnp_ResponseCode")

            if vnp_ResponseCode == "00":  # Success code
                invoice = Invoice.query.filter_by(transaction_id=vnp_TxnRef).first()
                print(invoice)

                if invoice:
                    # print(invoice.booking_form)
                    # room = Room.query.get_or_404(invoice.booking_form_id.room_id.id)
                    invoice.status = Status.SUCCESS
                    form = BookingForm.query.get(invoice.booking_form_id)
                    form.is_paid = True
                    # Cập nhật trạng thái phòng sau khi thanh toán thành công
                    # room.room_status_id = RoomStatus.query.filter_by(status="Đã đặt").first().id
                    db.session.commit()
                app.logger.info(f"Payment success for transaction: {vnp_TxnRef}")
                return "Payment successful!"
            else:
                # Handle specific error codes
                app.logger.warning(f"Payment failed with response code: {vnp_ResponseCode}")
                return f"Payment failed with response code: {vnp_ResponseCode}"


        else:
            # Invalid response
            app.logger.error("VNPAY response validation failed.")
            return "Invalid payment response received."

    except Exception as e:
        # Handle and log errors
        app.logger.error(f"Error in VNPAY payment return: {e}")
        return "An error occurred while processing the payment response.", 500


if __name__ == "__main__":
    with app.app_context():
        app.run(debug=True)
