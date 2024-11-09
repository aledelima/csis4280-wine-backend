from flask import Blueprint, jsonify, request
from bson.objectid import ObjectId
from pymongo.errors import PyMongoError

wines_bp = Blueprint('wines', __name__)

def init_wine_routes(wines_collection):
    # Get all wines with pagination
    @wines_bp.route('/wines', methods=['GET'])
    def get_all_wines():
        # Get page and limit query parameters with defaults
        page = int(request.args.get('page', 1))  # Default to page 1
        limit = int(request.args.get('limit', 10))  # Default to 10 items per page
        skip = (page - 1) * limit

        # Query MongoDB with pagination
        wines = list(wines_collection.find().skip(skip).limit(limit))

        # Convert ObjectId to string for JSON serialization
        for wine in wines:
            wine['_id'] = str(wine['_id'])

        # Get the total count of wines
        total_count = wines_collection.count_documents({})

        # Prepare paginated response
        response = {
            "page": page,
            "limit": limit,
            "total_count": total_count,
            "total_pages": (total_count + limit - 1) // limit,
            "wines": wines
        }
        # return jsonify(response)
        return wines

    # Get a single wine by ID
    @wines_bp.route('/wines/<id>', methods=['GET'])
    def get_wine(id):
        wine = wines_collection.find_one({"_id": ObjectId(id)})
        if wine:
            wine['_id'] = str(wine['_id'])
            return jsonify(wine)
        return jsonify({"error": "Wine not found"}), 404

    # Create a new wine
    @wines_bp.route('/wines', methods=['POST'])
    def create_wine():
        data = request.json
        new_wine = {
            "image_path": data.get("image_path"),
            "name": data.get("name"),
            "producer": data.get("producer"),
            "type": data.get("type"),
            "country": data.get("country"),
            "harvest": data.get("harvest"),
            "description": data.get("description"),
            "price": data.get("price"),
            "discount": data.get("discount"),
            "taste_characteristics": data.get("taste_characteristics"),
            "rate": data.get("rate"),
            "food_pair": data.get("food_pair"),
            "reviews": data.get("reviews")
        }
        result = wines_collection.insert_one(new_wine)
        new_wine['_id'] = str(result.inserted_id)
        return jsonify(new_wine), 201

    # Update an existing wine
    @wines_bp.route('/wines/<id>', methods=['PATCH'])
    def update_wine(id):
        data = request.json
        updated_data = {key: value for key, value in data.items() if value is not None}
        result = wines_collection.update_one({"_id": ObjectId(id)}, {"$set": updated_data})
        if result.modified_count:
            return jsonify({"message": "Wine updated successfully"})
        return jsonify({"error": "Wine not found or no changes made"}), 404

    # Delete a wine
    @wines_bp.route('/wines/<id>', methods=['DELETE'])
    def delete_wine(id):
        result = wines_collection.delete_one({"_id": ObjectId(id)})
        if result.deleted_count:
            return jsonify({"message": "Wine deleted successfully"})
        return jsonify({"error": "Wine not found"}), 404

    # Search wines by partial name with pagination
    @wines_bp.route('/wines/search', methods=['GET'])
    def search_wines():
        query = request.args.get('q', '')  # 'q' is the search term
        page = int(request.args.get('page', 1))  # Default to page 1
        limit = int(request.args.get('limit', 10))  # Default to 10 items per page
        skip = (page - 1) * limit

        # Query MongoDB with regex and pagination
        wines = list(wines_collection.find({"name": {"$regex": query, "$options": "i"}}).skip(skip).limit(limit))
        for wine in wines:
            wine['_id'] = str(wine['_id'])

        # Get total count of wines matching the search query
        total_count = wines_collection.count_documents({"name": {"$regex": query, "$options": "i"}})

        # Prepare paginated response
        response = {
            "page": page,
            "limit": limit,
            "total_count": total_count,
            "total_pages": (total_count + limit - 1) // limit,
            "wines": wines
        }
        return jsonify(response)

    # Filter wines by type
    @wines_bp.route('/wines/filter', methods=['GET'])
    def filter_wines_by_type():
        wine_type = request.args.get('type')
        wines = list(wines_collection.find({"type": wine_type}))
        for wine in wines:
            wine['_id'] = str(wine['_id'])
        return jsonify(wines)
        
    
    # Remove all wines and create initial list
    @wines_bp.route('/wines/all', methods=['POST'])
    def create_initial_wines():
        
        #function to delete all existing wines on wine_warehouse
        delete_all_wines()
        
        data_list = request.json
        if not isinstance(data_list, list):
            return jsonify({"error": "Input data must be a list"}), 400
        wine_list = []
        for data in data_list:
            new_wine = {
                "image_path": data.get("image_path"),
                "name": data.get("name"),
                "producer": data.get("producer"),
                "type": data.get("type"),
                "country": data.get("country"),
                "harvest": data.get("harvest"),
                "description": data.get("description"),
                "price": data.get("price"),
                "discount": data.get("discount"),
                "taste_characteristics": data.get("taste_characteristics"),
                "rate": data.get("rate"),
                "food_pair": data.get("food_pair"),
                "reviews": data.get("reviews")
            }
            wine_list.append(new_wine)
        try:
            result = wines_collection.insert_many(wine_list)
            if result.inserted_ids:
                return jsonify({"message": "List of wines created successfully"}), 201
        except PyMongoError as e:
            return jsonify({"error": f"Failed to create list of wines: {str(e)}"}), 500
        return jsonify({"error": "Unknown error occurred"}), 500
        
    # Delete all wines
    @wines_bp.route('/wines', methods=['DELETE'])
    def delete_all_wines():
        result = wines_collection.delete_many({})
        if result.deleted_count > 0:
            return jsonify({"message": "All wines deleted successfully"}), 200
        return jsonify({"error": "No wines found to delete"}), 404

