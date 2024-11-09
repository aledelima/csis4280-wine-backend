from flask import Flask, jsonify
from pymongo import MongoClient
from config import Config
from routes.wines import wines_bp, init_wine_routes  # Import the blueprint and init function

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Initialize MongoDB client with the configured URI
client = MongoClient(app.config["MONGO_URI"])
db = client['wine_warehouse']  # Replace 'wine_warehouse' with your actual database name
wines_collection = db['wines']  # Collection where wine data is stored

# Initialize wine routes with the wines_collection instance
init_wine_routes(wines_collection)
app.register_blueprint(wines_bp, url_prefix=app.config["BASE_URL"])

# Basic route to verify app is running
@app.route('/')
def index():
    return jsonify({"message": "Welcome to the Wine Warehouse API"}), 200

# Start the Flask app on all available IPs (host 0.0.0.0) on port 8888
if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=8888)