from flask import Flask
from flask_cors import CORS
from flask_login import LoginManager
from flask_mail import Mail
from flask_sqlalchemy import SQLAlchemy
from urllib.parse import quote

from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.wsgi_app = ProxyFix(
    app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
)
app.secret_key = "1231231782889dbdyq8wdhqiwjkjnsa3casc"
app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://root:%s@localhost/hoteldb?charset=utf8mb4" % quote('Admin@123')
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = True
app.config["PAGE_SIZE"] = 2
app.config["CLOUDINARY_CLOUD_NAME"] = "dj4slrwsl"
app.config["CLOUDINARY_API_KEY"] = "179444416465962"
app.config["CLOUDINARY_API_SECRET"] = "FQBLsNVEVMPyozMSHih0PzYVxn8"
app.config["SERVER_URL"] = "https://3dff-113-180-221-214.ngrok-free.app"
app.config["MOMO_CREATE_URL"] = "https://test-payment.momo.vn/v2/gateway/api/create"
app.config["ZALO_CREATE_URL"] = "https://sb-openapi.zalopay.vn/v2/create"

db = SQLAlchemy(app)
login = LoginManager(app)
CORS(app)
mail = Mail(app)

from hotelapp import *
