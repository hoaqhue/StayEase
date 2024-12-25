import cloudinary
import cloudinary.uploader
import cloudinary.api

from flask import redirect, request, flash
from flask_admin import Admin, BaseView, expose, form
from flask_admin.contrib.sqla import ModelView
from flask_login import logout_user, current_user
from markupsafe import Markup
from wtforms.fields.simple import MultipleFileField

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


# Admin setup
admin = Admin(app, name="Quản Lý Khách Sạn", template_mode="bootstrap4")
admin.add_view(RoomView(Room, db.session, name="Quản Lý Phòng"))
admin.add_view(ClientView(Client, db.session, name="Quản Lý Khách Hàng"))

admin.add_view(RoomTypeView(RoomType, db.session, name="Quản Lý Loại Phòng"))
admin.add_view(LogoutView(name="Đăng Xuất"))
