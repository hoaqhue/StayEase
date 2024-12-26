import cloudinary
import cloudinary.uploader
import cloudinary.api

from flask import redirect, request, flash
from flask_admin import Admin, BaseView, expose, form
from flask_admin.contrib.sqla import ModelView
from flask_login import logout_user, current_user
from markupsafe import Markup
from wtforms.fields.simple import MultipleFileField


from flask_admin import BaseView, expose
from flask import request
from datetime import datetime
from sqlalchemy import func
from flask_login import current_user

from flask import request, flash
from datetime import datetime

from flask import request, flash
from datetime import datetime
from sqlalchemy import func

from hotelapp.models import *


class AuthenticatedView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.user_role.type == "Admin"


class LogoutView(BaseView):
    @expose('/')
    def __index__(self):
        logout_user()
        return redirect('/')

    def is_accessible(self):
        return current_user.is_authenticated


class RoomView(AuthenticatedView):
    column_list = ['id', 'name', 'room_status', 'room_type', 'images']
    column_searchable_list = ['name']
    column_filters = ['room_status', 'room_type']
    column_labels = {
        'id': "ID",
        'name': 'Tên phòng',
        'room_type': 'Loại phòng',
        'room_status': 'Trạng thái',
        'images': 'Hình ảnh'
    }

    # Configure Cloudinary
    def __init__(self, *args, **kwargs):
        cloudinary.config(
            cloud_name=app.config.get('CLOUDINARY_CLOUD_NAME'),
            api_key=app.config.get('CLOUDINARY_API_KEY'),
            api_secret=app.config.get('CLOUDINARY_API_SECRET')
        )
        super(RoomView, self).__init__(*args, **kwargs)

    # Configure form to include image upload
    form_extra_fields = {
        'images': MultipleFileField('Tải lên các ảnh của phòng')
    }

    def _list_images(view, context, model, name):
        # Retrieve images for the room
        images = Image.query.filter_by(room_id=model.id).all()

        # If no images, return empty string
        if not images:
            return ''

        # Create HTML to display images
        image_html = []
        for img in images:
            image_html.append(
                f'<img src="{img.url}" style="max-width:100px; max-height:100px; margin:5px;" />'
            )

        # Return HTML with multiple images
        return Markup(''.join(image_html))

    # Add this to display images in list view
    column_formatters = {
        'images': _list_images
    }

    # Similar formatter for detail view
    def get_details_columns(self):
        return [
            ('images', self._list_images)
        ]

    def create_model(self, form):
        """Override to handle image uploads and Cloudinary."""
        try:
            # Create the room instance
            room = Room(
                name=form.name.data,
                room_status_id=form.room_status.data.id,
                room_type_id=form.room_type.data.id
            )
            db.session.add(room)
            db.session.flush()  # To get the room ID before committing

            # Handle image uploads
            uploaded_files = request.files.getlist('images')
            for file in uploaded_files:
                if file:
                    upload_result = cloudinary.uploader.upload(file)
                    image_url = upload_result['secure_url']

                    # Create Image instance
                    image = Image(url=image_url, room_id=room.id)
                    db.session.add(image)

            db.session.commit()
            return room
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating room: {e}', 'error')
            return False

    def update_model(self, form, model):
        """Override to handle image updates."""
        try:
            # Update the room details
            model.name = form.name.data
            model.room_status_id = form.room_status.data.id
            model.room_type_id = form.room_type.data.id

            # Handle new image uploads
            uploaded_files = request.files.getlist('images')
            for file in uploaded_files:
                if file:
                    upload_result = cloudinary.uploader.upload(file)
                    image_url = upload_result['secure_url']

                    # Add new image
                    image = Image(url=image_url, room_id=model.id)
                    db.session.add(image)

            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating room: {e}', 'error')
            return False


# Other views
class ClientView(AuthenticatedView):
    column_list = ['client_id', 'full_name', 'identification_code', 'address', 'email', 'phone_number',
                   'client_type.type']
    column_searchable_list = ['full_name', 'email', 'phone_number', 'identification_code']
    column_filters = ['client_type.type']
    column_labels = {
        'client_id': "ID",
        'full_name': 'Tên Khách Hàng',
        'identification_code': 'CCCD',
        'address': 'Địa chỉ',
        'email': 'Email',
        'phone_number': 'Số Điện Thoại',
        'client_type.type': 'Loại Khách Hàng'
    }

    def delete_model(self, model):
        if current_user.is_authenticated and current_user.client_id == model.client_id:
            flash("Không thể xóa khách hàng vì bạn đang là người dùng đang đăng nhập.", "error")
            return False
        try:
            super().delete_model(model)
        except Exception as e:
            flash(f"Không thể xóa khách hàng: {str(e)}", "error")
            return False
        return True


class RoomTypeView(AuthenticatedView):
    column_list = ['id', 'type', 'price_million']
    column_searchable_list = ['type']
    column_filters = ['price_million']
    column_labels = {
        'id': "ID",
        'type': 'Loại Phòng',
        'price_million': 'Giá'
    }



class RevenueReportView(BaseView):


    @expose('/')
    def index(self):
        # Lấy giá trị tháng từ query string (nếu có)
        month = request.args.get('month', datetime.today().strftime('%Y-%m'), type=str)

        try:
            # Đảm bảo 'month' là chuỗi và tách năm và tháng
            year, month = map(int, str(month).split('-'))

            # Kiểm tra giá trị tháng hợp lệ (1 <= month <= 12)
            if month < 1 or month > 12:
                raise ValueError(f"Tháng {month} không hợp lệ. Tháng phải nằm trong khoảng từ 1 đến 12.")

            # Tính tháng tiếp theo
            if month == 12:
                next_month_year = year + 1
                next_month = 1
            else:
                next_month_year = year
                next_month = month + 1

            # Sử dụng select_from() để chỉ định bảng gốc
            revenue_query = db.session.query(
                RoomType.type,
                func.sum(Booking.total_price).label('revenue'),
                func.count(Booking.id).label('rented_count')
            ).select_from(RoomType).join(Booking, Booking.room_id == RoomType.id).filter(
                Booking.start_date >= datetime(year, month, 1),
                Booking.end_date < datetime(next_month_year, next_month, 1)  # Dùng năm và tháng tiếp theo
            ).group_by(RoomType.id).all()

        except ValueError as e:
            # Thông báo lỗi nếu tháng không hợp lệ
            flash(f"Lỗi: {str(e)}", "error")
            # Đặt lại tháng mặc định là tháng hiện tại nếu có lỗi
            month = datetime.today().strftime('%Y-%m')
            year, month = map(int, str(month).split('-'))

            # Tính tháng tiếp theo
            if month == 12:
                next_month_year = year + 1
                next_month = 1
            else:
                next_month_year = year
                next_month = month + 1

            # Truy vấn lại với tháng hiện tại nếu có lỗi
            revenue_query = db.session.query(
                RoomType.type,
                func.sum(Booking.total_price).label('revenue'),
                func.count(Booking.id).label('rented_count')
            ).select_from(RoomType).join(Booking, Booking.room_id == RoomType.id).filter(
                Booking.start_date >= datetime(year, month, 1),
                Booking.end_date < datetime(next_month_year, next_month, 1)  # Dùng năm và tháng tiếp theo
            ).group_by(RoomType.id).all()

            # Kiểm tra kết quả của truy vấn
        if revenue_query:
            for row in revenue_query:
                print(f"Room Type: {row.type}, Revenue: {row.revenue}, Rented Count: {row.rented_count}")
        else:
            print("Không có dữ liệu.")

        total_revenue = sum([item.revenue for item in revenue_query])

        # Tính doanh thu theo loại phòng và số lượt thuê
        data = [{
            'type': item.type,
            'revenue': item.revenue,
            'rented_count': item.rented_count,
            'rate': (item.revenue / total_revenue) * 100 if total_revenue else 0
        } for item in revenue_query]

        return self.render('admin/revenue_report.html', data=data, month=f"{year}-{month:02d}",
                           total_revenue=total_revenue)






class RoomUsageReportView(BaseView):
    @expose('/')
    def index(self):
        # Lấy giá trị tháng từ query string (nếu có)
        month = request.args.get('month', datetime.today().strftime('%Y-%m'), type=str)
        year, month = map(int, month.split('-'))

        # Tính toán ngày đầu và ngày cuối tháng
        start_date = datetime(year, month, 1)
        # Nếu tháng là 12, tháng sau sẽ là tháng 1 của năm kế tiếp, còn nếu không thì chỉ cần cộng thêm 1 tháng
        if month == 12:
            next_month = datetime(year + 1, 1, 1)  # Tháng 1 năm sau
        else:
            next_month = datetime(year, month + 1, 1)  # Tháng tiếp theo trong cùng năm

        # Truy vấn các phòng và số ngày thuê
        room_usage_query = db.session.query(
            Room.name,
            func.sum(Booking.total_days).label('rented_days')
        ).join(Booking).filter(
            Booking.start_date >= start_date,
            Booking.end_date < next_month  # Dùng ngày tháng tiếp theo để tính toán đúng phạm vi
        ).group_by(Room.id).all()

        # Tính tổng số ngày thuê
        total_rented_days = sum([item.rented_days for item in room_usage_query])

        # Tính tỷ lệ sử dụng phòng
        data = [{
            'room': item.name,
            'rented_days': item.rented_days,
            'rate': (item.rented_days / total_rented_days) * 100 if total_rented_days else 0
        } for item in room_usage_query]

        # Trả lại kết quả cho template
        return self.render('admin/room_usage_report.html', data=data, month=f"{year}-{month:02d}", total_rented_days=total_rented_days)




class BookingRoomDetailsView(AuthenticatedView):
    column_list = ['id', 'booking_form.client.full_name', 'total', 'booking_form.check_in_date',
                   'booking_form.check_out_date', 'room.name', 'passengers']
    column_searchable_list = ['booking_form.client.full_name', 'booking_form.check_in_date',
                              'booking_form.check_out_date', 'room.name']
    column_filters = ['booking_form.client.full_name', 'booking_form.check_in_date', 'booking_form.check_out_date',
                      'room.name']
    column_labels = {
        'id': 'ID',
        'booking_form.client.full_name': 'Tên Khách Hàng',
        'total': 'Tổng cộng',
        'booking_form.check_in_date': 'Ngày Check In',
        'booking_form.check_out_date': 'Ngày Check Out',
        'room.name': 'Tên Phòng',
        'passengers': 'Số lượng hành khách',
    }


class ClientTypeView(AuthenticatedView):
    column_list = ['id', 'type', 'coefficient']
    column_searchable_list = ['type', 'coefficient']
    column_filters = ['type', 'coefficient']
    column_labels = {
        'id': 'ID',
        'type': 'Loại Khách Hàng',
        'coefficient': 'Hệ Số'
    }


class AdImageView(AuthenticatedView):
    column_list = ['id', 'url']
    column_searchable_list = ['url']
    column_filters = ['url']
    column_labels = {
        'id': 'ID',
        'url': 'Ảnh quảng cáo',
    }


class UserView(AuthenticatedView):
    column_list = ['id', 'username', 'password', 'user_role.type', 'client.full_name']
    column_searchable_list = ['username', 'user_role.type', 'client.full_name']
    column_filters = ['username', 'user_role.type', 'client.full_name']
    column_labels = {
        'id': 'ID',
        'username': 'Username',
        'password': 'Password',
        'user_role.type': 'Vai trò',
        'client.full_name': 'Tên người dùng'
    }


class InvoiceView(AuthenticatedView):
    column_list = ['id', 'booking_form.client.full_name',  'payment_method.type', 'booking_form.booking_room_details.total','created_date', 'status']
    column_searchable_list = [ 'booking_form.client.full_name',  'payment_method.type', 'created_date', 'status']
    column_filters = ['booking_form.client.full_name',  'payment_method.type', 'created_date', 'status']
    column_labels = {
        'id': 'ID',
        'booking_form.client.full_name': 'Tên người dùng',
        'payment_method.type': 'Phương thức',
        'booking_form.booking_room_details.total': 'Tổng tiền',
        'status': "Trạng thái",
        'created_date': 'Ngày tạo'
    }


# Admin setup
admin = Admin(app, name="Quản Lý Khách Sạn", template_mode="bootstrap4")

# Thêm các view với tên và endpoint rõ ràng
admin.add_view(UserView(User, db.session, name="Tài Khoản", endpoint="user_view"))
admin.add_view(RoomView(Room, db.session, name="Phòng", endpoint="room_view"))

admin.add_view(RoomTypeView(RoomType, db.session, name="Loại Phòng", endpoint="room_type_view"))
admin.add_view(ClientView(Client, db.session, name="Khách Hàng", endpoint="client_view"))
admin.add_view(ClientTypeView(ClientType, db.session, name="Loại Khách Hàng", endpoint="client_type_view"))
admin.add_view(
    BookingRoomDetailsView(BookingRoomDetails, db.session, name="Đặt Phòng", endpoint="booking_room_details_view"))
admin.add_view(InvoiceView(Invoice, db.session, name="Hóa đơn", endpoint="invoice_view"))
admin.add_view(AdImageView(AdImage, db.session, name="Quảng cáo", endpoint="AdImage_view"))

# Thêm view đăng xuất
admin.add_view(LogoutView(name="Đăng Xuất", endpoint="logout"))
admin.add_view(RevenueReportView(name="Báo Cáo Doanh Thu"))
admin.add_view(RoomUsageReportView(name="Báo Cáo Mật Độ Sử Dụng Phòng"))

admin.add_view(RoomTypeView(RoomType, db.session, name="Quản Lý Loại Phòng"))
admin.add_view(LogoutView(name="Đăng Xuất"))
