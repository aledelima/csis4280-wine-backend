from flask import Blueprint, jsonify
from routes.stock_manager import get_total_stock, get_wine_locations_and_stock

stock_bp = Blueprint('stock', __name__)

def init_stock_routes(wines_collection, warehouses_collection):
    """
    Initialize stock-related routes.
    """

    @stock_bp.route('/report', methods=['GET'])
    def get_stock_report():
        """
        Generate a stock report for all wines, including total stock and locations.
        """
        try:
            wines = list(wines_collection.find({}, {"_id": 1, "name": 1, "sale_price": 1}))
            stock_report = []

            for wine in wines:
                wine_id = str(wine["_id"])
                wine_name = wine.get("name", "Unknown")
                sale_price = wine.get("sale_price", 0.0)

                total_stock = get_total_stock(warehouses_collection, wine_id)
                locations = get_wine_locations_and_stock(warehouses_collection, wine_id)

                stock_report.append({
                    "wine_id": wine_id,
                    "name": wine_name,
                    "sale_price": float(sale_price),
                    "total_stock": int(total_stock),
                    "locations": locations,
                })

            return jsonify({"stock_report": stock_report}), 200

        except Exception as e:
            return jsonify({"error": f"Failed to generate stock report: {str(e)}"}), 500
        

    @stock_bp.route('/low-stock', methods=['GET'])
    def get_low_stock_wines():
        """
        Fetch wines with stock less than 10 units.
        """
        try:
            wines = list(wines_collection.find({}, {"_id": 1, "name": 1}))
            low_stock_wines = []

            for wine in wines:
                wine_id = str(wine["_id"])
                wine_name = wine.get("name", "Unknown")
                total_stock = int(get_total_stock(warehouses_collection, wine_id))

                if total_stock < 10:
                    low_stock_wines.append({
                        "wine_id": wine_id,
                        "name": wine_name,
                        "total_stock": total_stock
                    })

            return jsonify({"low_stock_wines": low_stock_wines}), 200

        except Exception as e:
            return jsonify({"error": f"Failed to fetch low stock wines: {str(e)}"}), 500
