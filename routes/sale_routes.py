from flask import Blueprint, jsonify, request
from pymongo.errors import PyMongoError
from bson.objectid import ObjectId
from .stock_manager import get_total_stock, update_stock_after_sale
from datetime import datetime

sales_bp = Blueprint('sales', __name__)

def init_sale_routes(sales_collection, wines_collection, warehouses_collection):
    
    #Get customer's orders.
    # @sales_bp.route('/sales/customer/<account_id>', methods=['GET'])
    # def get_orders_by_customerId(account_id):
        
    #     # Query MongoDB with account id
    #     orders = list(sales_collection.find(account_id))
        
            
    #     return jsonify()
        
    
    #Place customer's order.
    @sales_bp.route('/sales', methods=['POST'])
    def process_sales_cart():
        # Extract and validate JSON data
        data = request.get_json()
    
        account_id = data.get("account_id")
    
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
            "invoice": None,
            "sale_refused": insufficient_stock_items
        }
    
        # Issue new invoice
        if processed_items:
            new_invoice = {
                "account_id": ObjectId(account_id),
                "items": processed_items,
                "total_price": round(total_price, 2),
                "sales_date": str(datetime.utcnow()),
                "shipping_address": shipping_address
            }
            result = sales_collection.insert_one(new_invoice)
            new_invoice["_id"] = str(result.inserted_id)
            new_invoice["account_id"] = str(new_invoice["account_id"])
    
            response["invoice"] = new_invoice

        return jsonify(response), 200