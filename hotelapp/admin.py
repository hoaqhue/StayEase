from datetime import date

from flask import redirect, request
from flask_admin import Admin, BaseView, expose
from flask_admin.contrib.sqla import ModelView
from flask_admin.model import InlineFormAdmin
from flask_login import logout_user, login_required, login_user, current_user
from hotelapp import app, db, dao
from hotelapp.models import *


class AuthenticatedView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.user_role.type == "Admin"


class LogoutView(BaseView):
    @expose('/')
    def __index__(self):
        logout_user()
        return redirect('/admin')

    def is_accessible(self):
        return current_user.is_authenticated

class RoomView(AuthenticatedView):
    column_list = ['id', 'name', 'room_status', 'room_type']
    column_searchable_list = ['name']
    column_filters = ['room_status', 'room_type']
    column_labels = {
        'id': "id",
        'name': 'Tên phòng',
        'room_type': 'Loại phòng',
        'room_status': 'Trạng thái',
    }

admin = Admin(app, name="Quản Lý Khách Sạn", template_mode="bootstrap4")

admin.add_view(RoomView(Room, db.session, name="Quản Lý Phòng"))
admin.add_view(LogoutView("Đăng Xuất"))