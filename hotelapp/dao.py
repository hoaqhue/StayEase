import hashlib

from flask import Flask
from hotelapp import app
from hotelapp.models import *

def load_rooms():
    return Room.query.all()


def auth_user(username, password):
    password = str(hashlib.md5(password.strip().encode('utf-8')).hexdigest())
    return User.query.filter(User.username.__eq__(username.strip()), User.password.__eq__(password)).first()


def get_user_by_id(id):
    return User.query.get(id)


def get_room_types():
    return RoomType.query.all()


def get_user_role(role):
    return UserRole.query.filter(UserRole.type.__eq__(role)).first()


def create_user(name, username, password, identification_code, phone_number, email, address, client_type_id):
    role = get_user_role('Client')
    password = str(hashlib.md5(password.strip().encode('utf-8')).hexdigest())
    client = Client(full_name=name, identification_code=identification_code, address=address, phone_number=phone_number, email=email, client_type_id=client_type_id)
    db.session.add(client)
    db.session.flush()
    user = User(username=username, password=password, user_role_id=role.id, client_id=client.id)
    db.session.add(user)
    db.session.commit()


def get_client_types():
    return ClientType.query.all()

if __name__ == "__main__":
    with app.app_context():
        print(auth_user("admin", "123456"))
        print("Database loaded successfully!")