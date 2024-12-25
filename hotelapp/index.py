import hashlib
import hmac
import json
import os
import random
import uuid
from datetime import datetime, timedelta
from time import time

import requests
from flask import Flask, render_template, request, redirect, make_response, flash, jsonify, url_for
from flask_login import login_user, logout_user, current_user
from flask_bcrypt import Bcrypt
from sqlalchemy.exc import IntegrityError, PendingRollbackError
from hotelapp import admin

from hotelapp import app, dao, login, db, admin
from hotelapp.decorators import loggedin
from hotelapp.models import Room, BookingForm, RoomStatus, BookingRoomDetails, Client, UserRole, Invoice

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
                    address="Chưa nhập",
                    identification_code=identification_code,

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


@app.route("/forms")
def forms():
    forms = dao.get_forms()
    return render_template("forms.html", forms=forms)


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
    amount = str((request.json.get('total')))
    print(amount)
    orderId = str((request.json.get('trans_id')))
    orderInfo = "pay with MoMo"
    requestType = "captureWallet"
    extraData = ""
    redirectUrl = str(app.config.get("SERVER_URL"))
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

    if result_code != 0:
        return jsonify({'error': "Thanh toán thất bại",
                        'status': 400})

    try:
        print("Thanh toán thành công!", orderId)
        # dao.update_invoices(orderId)
        return jsonify({'status': 200})
    except Exception as e:
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


if __name__ == "__main__":
    with app.app_context():
        app.run(debug=True)
