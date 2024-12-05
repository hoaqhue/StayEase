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
    return RoomType.query.all() #r sep nữa

if __name__ == "__main__":
    with app.app_context():
        print(auth_user("admin", "123456"))
        print("Database loaded successfully!")