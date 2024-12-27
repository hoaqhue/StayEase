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
from flask import Flask, render_template, request, redirect, make_response, flash, jsonify, url_for
from flask_login import login_user, logout_user, current_user
import requests
from flask import Flask, render_template, request, redirect, make_response, flash, jsonify, url_for
from flask_login import login_user, logout_user, current_user
from flask_bcrypt import Bcrypt
from sqlalchemy import Integer
from sqlalchemy.exc import IntegrityError, PendingRollbackError
from sqlalchemy.testing.suite.test_reflection import users

from hotelapp import admin

from hotelapp import app, dao, login, db, admin
from hotelapp.decorators import loggedin
from hotelapp.models import Room, BookingForm, RoomStatus, BookingRoomDetails, Client, UserRole, Invoice, RoomType, \
    AdImage, \
    ClientType, Guest

# Khởi tạo Bcrypt
bcrypt = Bcrypt(app)


@app.route('/')
def index():
    ad_images = AdImage.query.all()
    room_types = dao.get_room_types()
    max_passenger = 6
    today = datetime.now().date()
    next_28_day = (datetime.now() + timedelta(days=28)).date()
    return render_template('index.html', ad_images=ad_images, room_types=room_types, today=today,
                           next_28_day=next_28_day, max_passenger=max_passenger)


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
    room_type_id = request.args.get('ticket_class', type=int)

    # Truy vấn danh sách phòng
    query = Room.query

    # Lọc theo loại phòng nếu có
    if room_type_id:
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
    # Lấy danh sách phòng sau khi áp dụng bộ lọc
    rooms = query.all()

    # Truyền dữ liệu sang template
    return render_template(
        'rooms.html',
        rooms=rooms,
        room_types=room_types,
        checkin=checkin,
        checkout=checkout,
        selected_room_type=room_type_id
    )


from flask_login import current_user


@app.route('/booking/<int:room_id>', methods=['GET', 'POST'])
def booking(room_id):
    room = Room.query.get_or_404(room_id)
    client_types = dao.get_client_types()
    max_passenger = room.room_type.max_passenger

    # Kiểm tra người dùng đã đăng nhập chưa
    if current_user.is_authenticated:
        # Nếu người dùng đã đăng nhập, lấy thông tin client từ current_user
        client = dao.get_client_by_id(current_user.client_id)
    else:
        # Nếu người dùng chưa đăng nhập, chuyển hướng đến trang đăng nhập
        return redirect('/login')

    if request.method == 'POST':
        try:
            # Lấy dữ liệu từ form
            full_name = request.form['full_name']
            phone_number = request.form['phone_number']
            email = request.form['email']
            identification_code = request.form['identification_code']
            address = request.form.get('address')
            client_type_id = request.form.get('client_type_id')
            passengers = request.form.get('passengers')

            # Lấy ngày nhận và ngày trả phòng từ form
            checkin = request.form['check_in_date']
            checkout = request.form['check_out_date']
            # Kiểm tra các trường dữ liệu
            if not full_name:
                return render_template('booking.html', error="Vui lòng nhập tên khách hàng.")
            if not phone_number or not phone_number.isdigit() or len(phone_number) != 10:
                return render_template('booking.html', error="Số điện thoại không hợp lệ. Nhập 10 chữ số.")
            if not email or '@' not in email:
                return render_template('booking.html', error="Email không hợp lệ.")
            if not identification_code or not identification_code.isdigit() or len(identification_code) != 12:
                return render_template('booking.html', error="CCCD phải có đúng 12 chữ số.")
            if not client_type_id:
                return render_template('booking.html', error="Vui lòng chọn loại khách.")
            if not passengers.isdigit() or int(passengers) < 1 or int(passengers) > 3:
                return render_template('booking.html', error="Số lượng khách phải từ 1 đến 3.")
            if not checkin or not checkout:
                return render_template('booking.html', error="Vui lòng chọn ngày nhận và trả phòng.")
            if checkin >= checkout:
                return render_template('booking.html', error="Ngày trả phòng phải sau ngày nhận phòng.")

            if checkin and checkout:
                try:
                    checkin_date = datetime.strptime(checkin, '%Y-%m-%d')  # Định dạng ngày tháng
                    checkout_date = datetime.strptime(checkout, '%Y-%m-%d')

                    # Tránh phòng bị trùng lịch
                    booking_subquery = (
                        db.session.query(BookingRoomDetails)
                        .join(BookingForm)
                        .filter(
                            BookingRoomDetails.room_id == room_id,
                            BookingForm.check_in_date < checkin_date,
                            BookingForm.check_out_date > checkout_date
                        )
                        .exists()
                    )

                    # Kiểm tra nếu phòng đã được đặt trong khoảng thời gian này
                    if db.session.query(booking_subquery).scalar():
                        return render_template('booking.html', room=room,
                                               error="Phòng đã được đặt trong khoảng thời gian này!")

                    # Cập nhật trạng thái phòng hết hạn
                    dao.update_room_status(checkin_date)

                except ValueError:
                    return render_template('booking.html', room=room, error="Định dạng ngày không hợp lệ!",
                                           client_types=client_types)

            # Kiểm tra sự có sẵn của phòng
            available_status = RoomStatus.query.filter_by(status='Có sẵn').first()
            maintenance_status = RoomStatus.query.filter_by(status='Bảo trì').first()

            if not available_status:
                raise ValueError("Trạng thái phòng 'Có sẵn' không tồn tại trong cơ sở dữ liệu.")
            if room.room_status_id == maintenance_status.id:
                return render_template('booking.html', room=room, error="Phòng này đang được bảo trì!")
            if room.room_status_id != available_status.id:
                return render_template('booking.html', room=room, error="Phòng này đã được đặt trước!")

            # Kiểm tra thông tin khách hàng đã tồn tại chưa
            if not client:
                # Nếu chưa có, tạo mới khách hàng
                client = Client(
                    full_name=full_name,
                    phone_number=phone_number,
                    email=email,
                    address=address,
                    identification_code=identification_code,
                    client_type_id=client_type_id,
                )
                db.session.add(client)
                db.session.commit()

            # Tạo đơn đặt phòng
            booking_form = BookingForm(
                check_in_date=checkin,
                check_out_date=checkout,
                client_id=client.client_id,
            )
            db.session.add(booking_form)
            db.session.commit()
            # Lặp qua các khách phụ
            for i in range(1, int(passengers)):  # Lặp cho mỗi khách phụ
                guest_full_name = request.form.get(f'full_name_{i}')
                guest_phone_number = request.form.get(f'phone_number_{i}')
                guest_identification_code = request.form.get(f'identification_code_{i}')
                guest_client_type_id = request.form.get(f'client_type_id_{i}')

                # Kiểm tra thông tin khách phụ
                if not guest_full_name or not guest_phone_number or not guest_identification_code:
                    return render_template('booking.html', error=f"Thông tin khách hàng phụ {i + 1} chưa đầy đủ.")

                guest = Guest(
                    full_name=request.form.get(f'full_name_{i}'),
                    phone_number=request.form.get(f'phone_number_{i}'),
                    identification_code=request.form.get(f'identification_code_{i}'),
                    client_type_id=request.form.get(f'client_type_id_{i}'),
                    booking_form_id=booking_form.id
                )
                db.session.add(guest)
                db.session.commit()

            # Chuyển đổi giá phòng và số lượng hành khách
            room_price = float(room.room_type.price_million)  # Giá phòng phải là số thực
            passengers_count = int(passengers)  # Số lượng hành khách (kiểm tra chắc chắn có giá trị hợp lệ)
            client_type_id = int(client_type_id)  # ID loại khách

            # Kiểm tra hệ số của các loại khách
            if len(client_types) < 2:
                raise ValueError("Không đủ dữ liệu loại khách trong cơ sở dữ liệu.")
            total=0
            # Tính toán tổng giá trị dựa trên số lượng hành khách và loại khách
            if passengers_count == max_passenger:
                total += room_price * (1 + 0.25)  # Tính giá với hệ số từ loại khách
            elif client_type_id == 2:
                total += room_price * (1 + client_types[2].coefficient)  # Nếu là loại khách đặc biệt, áp dụng hệ số
            else:
                total += room_price  # Giá mặc định

            # Tạo đối tượng BookingRoomDetails
            booking_detail = BookingRoomDetails(
                booking_form_id=booking_form.id,
                room_id=room.id,
                passengers=passengers_count,  # Số lượng hành khách đã chuyển thành int
                total=total  # Gán giá trị tổng đã tính
            )
            db.session.add(booking_detail)
            print(f"Total: {total}, Booking Form ID: {booking_form.id}")

            # Cập nhật trạng thái phòng
            room.room_status_id = RoomStatus.query.filter_by(status="Vui lòng thanh toán").first().id
            db.session.commit()

            # Sau khi đặt phòng thành công, render template payment.html
            booking_forms = BookingForm.query.filter_by(client_id=client.client_id).order_by(
                BookingForm.id.desc()).all()
            return render_template(
                'payment.html',
                booking_form=booking_form,
                booking_forms=booking_forms
            )

        except Exception as e:
            db.session.rollback()
            return render_template('booking.html', room=room, error=f"Lỗi: {str(e)}", client_types=client_types,
                                   client=client, max_passenger=max_passenger)

    return render_template('booking.html', room=room, client_types=client_types, client=client,
                           max_passenger=max_passenger)


@app.route("/forms")
def forms():
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


@app.route('/checkin/<int:form_id>', methods=['GET', 'POST'])
def checkin(form_id):
    form = BookingForm.query.get_or_404(form_id)

    if not current_user.is_authenticated:
        flash("Bạn phải đăng nhập để thực hiện hành động này.", "danger")
        return redirect("/login")

    form.is_checked_in = True
    form.receipted_by = current_user.id
    db.session.commit()
    flash(f'Check-in thành công cho phiếu số {form_id}!', 'success')
    return redirect("/forms")


@app.route('/test-thanh-toan-momo/<int:form_id>', methods=['GET', 'POST'])
def pay(form_id):
    print("Form ID received: ", form_id)  # Debug
    form = BookingForm.query.get_or_404(form_id)

    if not current_user.is_authenticated:
        flash("Bạn phải đăng nhập để thực hiện hành động này.", "danger")
        return redirect("/login")

    trans_id = str(uuid.uuid4())
    invoice = dao.create_invoice(form_id, 1, trans_id)

    # Sử dụng url_for để tạo URL tuyệt đối cho API Momo-Pay
    momo_api_url = url_for('momo_pay', _external=True)

    try:
        response = requests.post(momo_api_url, json={
            "total": invoice.total,
            "trans_id": trans_id
        })
        response.raise_for_status()  # Kiểm tra nếu có lỗi HTTP
        # flash(f'Thanh toán thành công cho phiếu số {form_id}!', 'success')
        return redirect(response.json().get("payUrl"))

    except requests.exceptions.RequestException as e:
        flash(f'Lỗi thanh toán: {e}', 'danger')

    return redirect("/forms")


@app.route('/api/momo-pay', methods=['POST'])
def momo_pay():
    print(app.config.get("SERVER_URL"), app.config.get("MOMO_CREATE_URL"))
    endpoint = app.config.get("MOMO_CREATE_URL")
    partnerCode = "MOMO"
    accessKey = "F8BBA842ECF85"
    secretKey = "K951B6PE1waDMi640xX08PD3vg6EkVlz"
    requestId = str(uuid.uuid4())
    amount = str(int((request.json.get('total'))))
    print(amount)
    orderId = str((request.json.get('trans_id')))
    print(f"Received amount: {amount}, trans_id: {orderId}")
    orderInfo = "Pay with MoMo"
    requestType = "captureWallet"
    extraData = ""
    redirectUrl = str(app.config.get("SERVER_URL"))
    ipnUrl = (app.config.get("SERVER_URL") + "/api/momo-pay/ipn")
    rawSignature = "accessKey=" + accessKey + "&amount=" + amount + "&extraData=" + extraData + "&ipnUrl=" + ipnUrl + "&orderId=" + orderId + "&orderInfo=" + orderInfo + "&partnerCode=" + partnerCode + "&redirectUrl=" + redirectUrl + "&requestId=" + requestId + "&requestType=" + requestType
    h = hmac.new(bytes(secretKey, 'ascii'), bytes(rawSignature, 'ascii'), hashlib.sha256)
    signature = h.hexdigest()
    print(f"Raw signature: {rawSignature}")
    print(f"Generated signature: {signature}")

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
    print(f"Payload: {data}")

    # Gửi yêu cầu đến MoMo
    response = requests.post(endpoint, json=data, headers={'Content-Type': 'application/json'})
    if response.status_code == 200:
        response_data = response.json()
        print(f"MoMo response: {response_data}")
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
        print("Thanh toán thành công!", orderId)
        # Cập nhật trạng thái phòng chỉ khi thanh toán thành công
        booking_form = BookingForm.query.filter_by(order_id=orderId).first()
        if booking_form:
            room = Room.query.get_or_404(booking_form.room_id)

            # Cập nhật trạng thái phòng sau khi thanh toán thành công
            room.room_status_id = RoomStatus.query.filter_by(status="Đã đặt").first().id
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
    app_trans_id = "{:%y%m%d}_{}".format(datetime.today(), transID)
    print("t", app_trans_id)
    embeddata = json.dumps({"redirecturl": str(app.config.get("SERVER_URL"))})
    item = json.dumps([{}])
    amount = str((request.json.get('total')))
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
            print("update order's status = success where apptransid = " + dataJson['app_trans_id'])

            result['return_code'] = 1
            result['return_message'] = 'success'
            dao.update_invoices(dataJson['app_trans_id'])
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


if __name__ == "__main__":
    with app.app_context():
        app.run(debug=True)
