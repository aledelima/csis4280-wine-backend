from flask import Flask, jsonify
from pymongo import MongoClient
from config import Config

#import endpoints
from routes.wine_routes import wines_bp, init_wine_routes
from routes.purchase_routes import purchases_bp, init_purchase_routes
from routes.account_routes import accounts_bp, init_account_routes

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Initialize MongoDB client with the configured URI
client = MongoClient(app.config["MONGO_URI"])
db = client['wine_warehouse']  # Replace 'wine_warehouse' with your actual database name
wines_collection = db['wines']  # Collection where wine data is stored
purchases_collection = db['purchases'] # Collection for purchase records
accounts_collection = db['account'] # collection for user accounts

# Initialize route endpoints with their collection instances
init_wine_routes(wines_collection)
init_purchase_routes(wines_collection, purchases_collection)
init_account_routes(accounts_collection)

app.register_blueprint(wines_bp, url_prefix=app.config["BASE_URL"])
app.register_blueprint(purchases_bp, url_prefix=app.config["BASE_URL"])
app.register_blueprint(accounts_bp, url_prefix=app.config["BASE_URL"])

# Basic route to verify app is running
@app.route('/')
def index():
    return jsonify({"message": "Welcome to the Wine Warehouse API"}), 200

# Start the Flask app on all available IPs (host 0.0.0.0) on port 8888
if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=8888)