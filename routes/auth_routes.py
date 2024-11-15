from flask import Blueprint, request, jsonify
from models.user_model import create_user, get_user_by_email, verify_password

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/signup', methods=['POST'])
def signup():
    data = request.json
    if get_user_by_email(data["email"]):
        return jsonify({"error": "User already exists"}), 400

    user = create_user(data)
    return jsonify({"message": "User registered successfully", "user": user}), 201

@auth_bp.route('/signin', methods=['POST'])
def signin():
    data = request.get_json()
    print("Received data:", data)
    user = get_user_by_email(data["email"])
    if user:
        print("User found:", user)
        if verify_password(user["password"], data["password"]):
            print("Password verification successful")
            return jsonify({"message": "Login successful"}), 200
        else:
            print("Password verification failed")
    else:
        print("User not found")
    return jsonify({"error": "Invalid email or password"}), 401
