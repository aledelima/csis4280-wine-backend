from flask import Blueprint, jsonify, request
from werkzeug.security import generate_password_hash, check_password_hash
from pymongo.errors import PyMongoError

accounts_bp = Blueprint('account', __name__)

def init_account_routes(accounts_collection):
    @accounts_bp.route('/account/signup', methods=['POST'])
    def signup():
        data = request.get_json()
        if get_account_by_email(data["email"]):
            return jsonify({
                "message": "User already exists",
                "request_status": False
            }), 400
    
        def create_account(data):
            hashed_password = generate_password_hash(data['password'])
            new_account = {
                "first_name": data.get("first_name"),
                "last_name": data.get("last_name"),
                "email": data.get("email"),
                "password": hashed_password,
                "phone": data.get("phone"),
                "status": data.get("status"),
                "type": data.get("type"),
                "address": data.get("address")
            }
            result = accounts_collection.insert_one(new_account)
            new_account["_id"] = str(result.inserted_id)
            return new_account
            
        account = create_account(data)
        
        # Prepare response with account data
        response = {
            "message": "Account registered successfully",
            "request_status": True,
            "_account": account
        }
        return jsonify(response), 201
    
    @accounts_bp.route('/account/signin', methods=['POST'])
    def signin():
        data = request.get_json()
        account = get_account_by_email(data["email"])
        
        if account:
            if verify_password(account["password"], data["password"]):
                # Prepare response
                response = {
                    "message": "Account successfully Authenticated and validated",
                    "request_status": True,
                    "_account": account
                }
                return jsonify(response), 201
            else:
                # Prepare response
                response = {
                    "message": "Invalid email or password",
                    "request_status": False
                }
                return jsonify(response), 401
        # Prepare response
        response = {
            "message": "Invalid email or password",
            "request_status": False
        }
        return jsonify(response), 401

    def get_account_by_email(email):
        account = accounts_collection.find_one({"email": email})
        if account:
            # Convert _id to string to make it JSON serializable
            account["_id"] = str(account["_id"])
        return account
    
    def verify_password(stored_password, provided_password):
        return check_password_hash(stored_password, provided_password)