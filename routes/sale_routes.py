from flask import Blueprint, jsonify, request
from pymongo.errors import PyMongoError
from bson.objectid import ObjectId
from .stock_manager import get_total_stock, update_stock_after_sale
from datetime import datetime
import calendar

sales_bp = Blueprint('sales', __name__)

def init_sale_routes(sales_collection, wines_collection, warehouses_collection):
    
    # Get customer's orders by account id
    @sales_bp.route('/sales/customer/<account_id>', methods=['GET'])
    def get_orders_by_customer_id(account_id):
        try:
            # Query MongoDB with account id
            orders = list(sales_collection.find({"account_id": ObjectId(account_id)}))

            # Convert ObjectId to string for JSON serialization
            for order in orders:
                order['_id'] = str(order['_id'])
                order['account_id'] = str(order['account_id'])
            
            response = {
                "invoices": orders
            }
            return jsonify(response), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 400
            
    
    # Get customer's orders not dispatched.
    @sales_bp.route('/sales/customer/dispatch/<dispatch_status>', methods=['GET'])
    def get_orders_not_dispatched(dispatch_status):
        try:
            # Query MongoDB with account id
            orders = list(sales_collection.find({"dispatch_status": str(dispatch_status)}))

            # Convert ObjectId to string for JSON serialization
            for order in orders:
                order['_id'] = str(order['_id'])
                order['account_id'] = str(order['account_id'])
                
            response = {
                "invoices": orders
            }
            return jsonify(response), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 400
        
    #Place customer's order.
    @sales_bp.route('/sales', methods=['POST'])
    def process_sales_cart():
        # Extract and validate JSON data
        data = request.get_json()
    
        account = data.get("account")
    
        items = data.get("items", [])
        
        shipping_address = data.get("shipping_address")

        total_price = 0
        insufficient_stock_items = []
        processed_items = []

        for item in items:
            wine_id = item.get("wine_id")
            quantity_requested = item.get("quantity")
    
            # Update stock and process sale
            sale_item = update_stock_after_sale(warehouses_collection, wine_id, quantity_requested)
            
            if not sale_item or not isinstance(sale_item, list) or "success" not in sale_item[0]:
                return jsonify({"error": f"Failed to process item: {item}"}), 400
    
            if not sale_item[0]["success"]:
                insufficient_stock_items.append({
                    "wine_id": str(wine_id),
                    "available_stock": int(sale_item[0].get("stock", 0)),
                    "requested_quantity": int(quantity_requested)
                })
            else:
                wine = wines_collection.find_one({"_id": ObjectId(wine_id)})
    
                price_per_unit = round(wine["sale_price"] * (1 - wine["discount"]), 2)
                item_total = round(price_per_unit * quantity_requested, 2)
                total_price += item_total
    
                processed_items.append({
                    "wine_id": str(wine_id),
                    "name": wine["name"],
                    "sale_price": round(wine["sale_price"], 2),
                    "discount": round(wine["discount"], 2),
                    "final_price_per_unit": price_per_unit,
                    "quantity": quantity_requested,
                    "item_total": item_total,
                    "stock_location": sale_item[1:]
                })
                
        response = {
            "invoices": [],
            "sale_refused": insufficient_stock_items
        }
        
        # Issue new invoice
        if processed_items:
            new_invoice = {
                "account_id": ObjectId(account["account_id"]),
                "items": processed_items,
                "total_price": round(total_price, 2),
                "sales_date": datetime.utcnow(),   #"sales_date": str(datetime.utcnow()),
                "shipping_address": shipping_address,
                "dispatch_status": 0
            }
            result = sales_collection.insert_one(new_invoice)
            new_invoice["_id"] = str(result.inserted_id)
            new_invoice["account_id"] = str(new_invoice["account_id"])
        
            # Append the new invoice to the "invoices" list
            response["invoices"].append(new_invoice)

        return jsonify(response), 200
        
    # New route: Monthly sales comparison
    @sales_bp.route('/sales/comparison', methods=['GET'])
    def get_monthly_sales_comparison():
        """
        Fetch sales totals for the current and previous months.
        """
        try:
            # Get the start of the current month, the start of the previous month, and the end of the previous month
            now = datetime.utcnow()
            start_of_current_month = datetime(now.year, now.month, 1)
            
            # Calculate start and end of the previous month
            previous_month = start_of_current_month.month - 1
            previous_year = start_of_current_month.year if previous_month > 0 else start_of_current_month.year - 1
            previous_month = previous_month if previous_month > 0 else 12

            start_of_previous_month = datetime(previous_year, previous_month, 1)
            end_of_previous_month = datetime(
                previous_year,
            previous_month,
            calendar.monthrange(previous_year, previous_month)[1],
            23, 59, 59
            )

            # return sales of the current month
            current_month_sales_pipeline = [
                {"$match": {"sales_date": {"$gte": start_of_current_month}}},
                {"$group": {"_id": None, "total_sales": {"$sum": "$total_price"}}}
            ]
            current_month_sales_result = list(sales_collection.aggregate(current_month_sales_pipeline))
            current_month_sales = current_month_sales_result[0]["total_sales"] if current_month_sales_result else 0

            # return sales of the previous month
            previous_month_sales_pipeline = [
                {"$match": {
                    "sales_date": {"$gte": start_of_previous_month, "$lte": end_of_previous_month}
                }},
                {"$group": {"_id": None, "total_sales": {"$sum": "$total_price"}}}
            ]
            previous_month_sales_result = list(sales_collection.aggregate(previous_month_sales_pipeline))
            previous_month_sales = previous_month_sales_result[0]["total_sales"] if previous_month_sales_result else 0

            # Retorna os dados de comparação
            return jsonify({
                "current_month_sales": current_month_sales,
                "previous_month_sales": previous_month_sales
            }), 200

        except PyMongoError as e:
            return jsonify({"error": f"Database error: {str(e)}"}), 500
        except Exception as e:
            return jsonify({"error": f"Unexpected error: {str(e)}"}), 500
    
    # New route: sales report
    @sales_bp.route('/sales/report', methods=['GET'])
    def get_sales_report():
        """
        Fetch sales details within a specified date range.
        """
        try:
            # Parse start_date and end_date from query parameters
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')

            # Validate dates
            if not start_date or not end_date:
                return jsonify({"error": "Start date and end date are required."}), 400

            start_date = datetime.strptime(start_date, "%Y-%m-%d")
            end_date = datetime.strptime(end_date, "%Y-%m-%d")

            # Query sales within the date range
            sales = sales_collection.find({
                "sales_date": {"$gte": start_date, "$lte": end_date}
            })

            sales_data = []
            for sale in sales:
                sales_data.append({
                    "_id": str(sale["_id"]),
                    "account_id": str(sale["account_id"]),
                    "total_price": sale["total_price"],
                    "sales_date": sale["sales_date"].strftime("%Y-%m-%d"),
                    "items": [{
                        "wine_id": str(item["wine_id"]),
                        "name": item["name"],
                        "quantity": item["quantity"],
                        "item_total": item["item_total"]
                    } for item in sale["items"]]
                })

            return jsonify({
                "total_sales_count": len(sales_data),
                "total_sales_amount": sum(sale["total_price"] for sale in sales_data),
                "sales": sales_data
            }), 200

        except PyMongoError as e:
            return jsonify({"error": f"Database error: {str(e)}"}), 500
        except Exception as e:
            return jsonify({"error": f"Unexpected error: {str(e)}"}), 500