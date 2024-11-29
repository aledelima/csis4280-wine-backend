from flask import Blueprint, request, jsonify
from pymongo.errors import PyMongoError
from datetime import datetime, timedelta
import calendar

finance_bp = Blueprint("finance", __name__)

def init_finance_routes(sales_collection, purchases_collection):

    @finance_bp.route("/financeReport", methods=["GET"])
    def get_finance_report():
        """
        Fetch the finance report for a given date range or the current month.
        """
        try:
            # Retrieve optional query parameters for filtering by date range
            start_date = request.args.get("start_date")
            end_date = request.args.get("end_date")

            # If no start_date and end_date are provided, calculate for the current month
            now = datetime.utcnow()
            if not start_date and not end_date:
                start_date = datetime(now.year, now.month, 1)
                end_date = datetime(now.year, now.month, calendar.monthrange(now.year, now.month)[1])
            else:
                # Parse dates from query parameters
                start_date = datetime.strptime(start_date, "%Y-%m-%d") if start_date else None
                end_date = datetime.strptime(end_date, "%Y-%m-%d") if end_date else None

            # Validate that both dates are provided if one is specified
            if (start_date and not end_date) or (end_date and not start_date):
                return jsonify({"error": "Both start_date and end_date must be provided."}), 400

            # MongoDB aggregation pipelines for sales and purchases
            sales_pipeline = [
                {"$match": {"sales_date": {"$gte": start_date, "$lte": end_date}}},
                {"$group": {"_id": None, "total_sales": {"$sum": "$total_price"}}},
            ]
            purchases_pipeline = [
                {"$match": {"purchase_date": {"$gte": start_date, "$lte": end_date}}},
                {"$group": {"_id": None, "total_purchases": {"$sum": "$total_cost"}}},
            ]

            # Calculate total sales
            sales_result = list(sales_collection.aggregate(sales_pipeline))
            total_sales = sales_result[0]["total_sales"] if sales_result else 0

            # Calculate total purchases
            purchases_result = list(purchases_collection.aggregate(purchases_pipeline))
            total_purchases = purchases_result[0]["total_purchases"] if purchases_result else 0

            # Calculate financial balance
            financial_balance = total_sales - total_purchases

            # Return the finance report
            return jsonify({
                "total_sales": total_sales,
                "total_purchases": total_purchases,
                "financial_balance": financial_balance,
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
            }), 200

        except PyMongoError as e:
            # Handle MongoDB errors
            return jsonify({"error": f"Database error: {str(e)}"}), 500
        except Exception as e:
            # Handle unexpected errors
            return jsonify({"error": f"Unexpected error: {str(e)}"}), 500


