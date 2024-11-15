from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
import os
from dotenv import load_dotenv

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

client = MongoClient(MONGO_URI)
db = client['wine_warehouse']
users_collection = db['users']

from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config

client = MongoClient(Config.MONGO_URI)
db = client["wine_warehouse"]
users_collection = db["users"]

def create_user(data):
    hashed_password = generate_password_hash(data['password'])
    user = {
        "firstName": data.get("firstName"),
        "lastName": data.get("lastName"),
        "email": data.get("email"),
        "password": hashed_password,
        "phone": data.get("phone"),
        "address": data.get("address", {})
    }
    result = users_collection.insert_one(user)
    user["_id"] = str(result.inserted_id)
    return user

def get_user_by_email(email):
    return users_collection.find_one({"email": email})

def verify_password(stored_password, provided_password):
    return check_password_hash(stored_password, provided_password)
