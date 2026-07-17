from dotenv import load_dotenv
load_dotenv()

from flask import Flask

app = Flask(__name__)

from app import db
db.init_db()

from app import routes  # noqa: E402,F401
