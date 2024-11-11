from flask import Blueprint, jsonify, request
from bson.objectid import ObjectId
from pymongo.errors import PyMongoError
from datetime import datetime

purchases_bp = Blueprint('purchases', __name__)

def init_purchase_routes(wines_collection, purchases_collection):
    @purchases_bp.route('/purchases', methods=['POST'])
    def create_purchase():
        data = request.json
        user_id = data.get("user_id")
        items = data.get("items", [])

        # Retrieve shipping address fields
        address = data.get("address")
        city = data.get("city")
        province = data.get("province")
        postal_code = data.get("postal_code")

        total_price = 0  # Initialize total price
        insufficient_stock_items = []
        processed_items = []

        for item in items:
            wine_id = item["wine_id"]
            quantity_requested = int(item["quantity"])

            # Fetch wine details to check stock and get price
            wine = wines_collection.find_one({"_id": ObjectId(wine_id)})
            if wine is None:
                return jsonify({"error": f"Wine with id {wine_id} not found"}), 404

            wine_stock = int(wine["stock"])
            if wine_stock < quantity_requested:
                insufficient_stock_items.append({
                    "wine_id": str(wine_id),
                    "available_stock": wine_stock,
                    "requested_quantity": quantity_requested
                })
            else:
                # Calculate discounted price and round to 2 decimal places
                price_per_unit = round(wine["price"] * (1 - wine["discount"]), 2)
                item_total = round(price_per_unit * quantity_requested, 2)
                total_price += item_total

                # Add full wine details for this purchase item
                processed_items.append({
                    "wine_id": str(wine_id),
                    "name": wine["name"],
                    "price": round(wine["price"], 2),  # Original price rounded
                    "discount": round(wine["discount"], 2),
                    "final_price_per_unit": price_per_unit,
                    "quantity": quantity_requested,
                    "item_total": item_total
                })

        # If any wine has insufficient stock, return an error response
        if insufficient_stock_items:
            return jsonify({
                "error": "Insufficient stock for some items",
                "insufficient_stock_items": insufficient_stock_items
            }), 400

        # Round the total price to 2 decimal places
        total_price = round(total_price, 2)

        # If stock is sufficient, update stock and create the purchase record
        try:
            # Deduct stock for each wine item
            for item in processed_items:
                wine_id = ObjectId(item["wine_id"])
                quantity_purchased = item["quantity"]
                wines_collection.update_one(
                    {"_id": wine_id},
                    {"$inc": {"stock": -quantity_purchased}}
                )

            # Record the purchase in the purchases collection
            new_purchase = {
                "user_id": ObjectId(user_id),
                "items": processed_items,
                "total_price": total_price,  # Calculated with discounts
                "purchase_date": datetime.utcnow(),  # Server timestamp
                # Include the shipping address information
                "address": address,
                "city": city,
                "province": province,
                "postal_code": postal_code
            }
            result = purchases_collection.insert_one(new_purchase)
            new_purchase["_id"] = str(result.inserted_id)
            new_purchase["user_id"] = str(new_purchase["user_id"])

            return jsonify(new_purchase), 201

        except PyMongoError as e:
            return jsonify({"error": f"Failed to create purchase: {str(e)}"}), 500
