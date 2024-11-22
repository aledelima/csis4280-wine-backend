from flask import Blueprint

stock_manager_bp = Blueprint('warehouse_stock', __name__)

#function to return the total stock of a specific wine
def get_total_stock(warehouses_collection, wine_id: str) -> str:
    """
    Calculate the total stock for a given wine_id.
    :param warehouses_collection: The MongoDB collection for warehouses.
    :param wine_id: The wine_id to search for.
    :return: Total stock for the given wine_id.
    """
    pipeline = [
        {"$unwind": "$aisles"},  # Unwind aisles array
        {"$unwind": "$aisles.shelves"},  # Unwind shelves array
        {"$unwind": "$aisles.shelves.wines"},  # Unwind wines array
        {"$match": {"aisles.shelves.wines.wine_id": wine_id}},  # Filter by wine_id
        {
            "$group": {  # Group by wine_id and sum stock
                "_id": "$aisles.shelves.wines.wine_id",
                "total_stock": {"$sum": "$aisles.shelves.wines.stock"}
            }
        }
    ]

    # Execute the aggregation
    result = list(warehouses_collection.aggregate(pipeline))

    # Return the total stock if found, else return 0
    return result[0]["total_stock"] if result else "0"
    
#function to return wine's locations and stock in each location
def get_wine_locations_and_stock(warehouses_collection, wine_id: str) -> list:
    """
    Retrieve the locations (aisle and shelf) and stock for a given wine_id.
    :param warehouses_collection: The MongoDB collection for warehouses.
    :param wine_id: The wine_id to search for.
    :return: List of dictionaries with location and stock information for the given wine_id.
    """
    pipeline = [
        {"$unwind": "$aisles"},  # Unwind aisles array
        {"$unwind": "$aisles.shelves"},  # Unwind shelves array
        {"$unwind": "$aisles.shelves.wines"},  # Unwind wines array
        {"$match": {"aisles.shelves.wines.wine_id": wine_id}},  # Filter by wine_id
        {
            "$project": {
                "_id": 0,  # Exclude the document ID from the output
                "aisle": "$aisles.aisle",  # Include the aisle ID
                "shelf": "$aisles.shelves.shelf",  # Include the shelf ID
                "stock": "$aisles.shelves.wines.stock"  # Include the wine stock
            }
        }
    ]

    # Execute the aggregation
    result = list(warehouses_collection.aggregate(pipeline))

    # Return the list of wine locations and stocks
    return result
    
#function to update stock after sale. It returns ...
def update_stock_after_sale(warehouses_collection, wine_id: str, quantity_requested: int) -> list:
    """
    Deduct the sale amount from the stock of a specified wine_id and distribute it across locations (aisles and shelves).
    :param warehouses_collection: The MongoDB collection for warehouses.
    :param wine_id: The wine_id to search for.
    :param sale_amount: The amount of stock to deduct.
    :return: List of dictionaries with updated stock and location details.
    """
    pipeline = [
        {"$unwind": "$aisles"},  # Unwind aisles array
        {"$unwind": "$aisles.shelves"},  # Unwind shelves array
        {"$unwind": "$aisles.shelves.wines"},  # Unwind wines array
        {"$match": {"aisles.shelves.wines.wine_id": wine_id}},  # Filter by wine_id
        {
            "$project": {
                "_id": 0,
                "warehouse_id": "$_id",  # Include warehouse ID
                "aisle": "$aisles.aisle",  # Include aisle ID
                "shelf": "$aisles.shelves.shelf",  # Include shelf ID
                "stock": "$aisles.shelves.wines.stock"  # Include wine stock
            }
        },
        {"$sort": {"stock": 1}}  # Sort by stock in ascending order to deplete smallest stocks first
    ]

    # Retrieve wine locations and stocks
    locations = list(warehouses_collection.aggregate(pipeline))
    
    # verify if total stock fulfills sale
    if not locations:
        return [{"success": False, "stock": 0}]
    
    total_stock = sum(location["stock"] for location in locations)
    if total_stock < quantity_requested:
        return [{"success": False, "stock": total_stock}]
    
    remaining_sale = quantity_requested
    updated_locations = []
    updated_locations.append({"success": True})

    for location in locations:
        if remaining_sale <= 0:
            break

        deduct_amount = min(location["stock"], remaining_sale)
        remaining_sale -= deduct_amount
        
        # Update stock in the database
        warehouses_collection.update_one(
            {
                "_id": location["warehouse_id"],
                "aisles.aisle": location["aisle"],
                "aisles.shelves.shelf": location["shelf"],
                "aisles.shelves.wines.wine_id": wine_id
            },
            {"$inc": {"aisles.$[aisle].shelves.$[shelf].wines.$[wine].stock": -deduct_amount}},
            array_filters=[
                {"aisle.aisle": location["aisle"]},
                {"shelf.shelf": location["shelf"]},
                {"wine.wine_id": wine_id}
            ]
        )

        # Add updated location to the response
        updated_locations.append(
            f"warehouse_id: {location['warehouse_id']}\n"
            f"aisle: {location['aisle']}\n"
            f"shelf: {location['shelf']}"
        )

    return updated_locations
    
    '''
    Return Format:
    List of dictionaries, each containing:
        warehouse_id: The ID of the warehouse.
        aisle: The aisle ID.
        shelf: The shelf ID.
        remaining_stock: Updated stock after the sale.
        
    Call:
    update_stock_after_sale(warehouses_collection, "W001", 35)
    
    [ {"warehouse_id": "WH1", "aisle": "A1", "shelf": "S1", "stock": 10},
    {"warehouse_id": "WH1", "aisle": "A1", "shelf": "S2", "stock": 15},
    {"warehouse_id": "WH2", "aisle": "A2", "shelf": "S3", "stock": 20} ]
    
    [ {"warehouse_id": "WH1", "aisle": "A1", "shelf": "S1", "remaining_stock": 0},
    {"warehouse_id": "WH1", "aisle": "A1", "shelf": "S2", "remaining_stock": 0},
    {"warehouse_id": "WH2", "aisle": "A2", "shelf": "S3", "remaining_stock": 10} ]

    {"error": "Insufficient stock to fulfill the sale amount."}
    '''

#function to return warehouse id
def get_warehouse_id(warehouses_collection, warehouse_name: str) -> str:
    # Query to find the document by location
    query = {"location": warehouse_name}
    projection = {"_id": 1}  # Only return the _id field

    # Fetch the document
    document = warehouses_collection.find_one(query, projection)

    # If the document is not found, create it and return its _id
    if document is None:
        # Create a new document with the specified location
        new_document = {"location": warehouse_name}
        result = warehouses_collection.insert_one(new_document)
        return result.inserted_id

    # Return the _id of the existing document
    return document["_id"]
    
#function to update stock at the warehouse
def update_wine_stock(
    warehouses_collection,
    warehouse_id: str,
    aisle: str,
    shelf: str,
    wine_id: str,
    stock_to_add: int) -> dict:
    """
    Add or update the stock of a wine at a specified location (warehouse, aisle, shelf).
    If the location doesn't exist, create it and set the wine with the given stock.
    :param warehouses_collection: The MongoDB collection for warehouses.
    :param warehouse_id: The ID of the warehouse.
    :param aisle: The aisle ID where the wine should be added or updated.
    :param shelf: The shelf ID where the wine should be added or updated.
    :param wine_id: The ID of the wine to add or update.
    :param stock_to_add: The stock to add to the wine.
    :return: A dictionary indicating success or failure of the operation.
    """
    # Step 1: Try to update the stock if the wine_id already exists at the location
    result = warehouses_collection.update_one(
        {
            "_id": warehouse_id,  # Match the warehouse
            "aisles.aisle": aisle,  # Match the aisle
            "aisles.shelves.shelf": shelf,  # Match the shelf
            "aisles.shelves.wines.wine_id": wine_id  # Match the wine
        },
        {
            "$inc": {  # Increment the stock by stock_to_add
                "aisles.$[aisle].shelves.$[shelf].wines.$[wine].stock": stock_to_add
            }
        },
        array_filters=[
            {"aisle.aisle": aisle},  # Array filter for the aisle
            {"shelf.shelf": shelf},  # Array filter for the shelf
            {"wine.wine_id": wine_id}  # Array filter for the wine
        ]
    )

    # Step 2: If the wine_id doesn't exist, check if the location exists
    if result.matched_count == 0:
        # Try to add the wine to an existing location
        result = warehouses_collection.update_one(
            {
                "_id": warehouse_id,  # Match the warehouse
                "aisles.aisle": aisle,  # Match the aisle
                "aisles.shelves.shelf": shelf  # Match the shelf
            },
            {
                "$addToSet": {  # Add the new wine
                    "aisles.$[aisle].shelves.$[shelf].wines": {
                        "wine_id": wine_id,
                        "stock": stock_to_add
                    }
                }
            },
            array_filters=[
                {"aisle.aisle": aisle},  # Array filter for the aisle
                {"shelf.shelf": shelf}  # Array filter for the shelf
            ]
        )

        # Step 3: If the location itself doesn't exist, create it
        if result.matched_count == 0:
            result = warehouses_collection.update_one(
                {"_id": warehouse_id},  # Match the warehouse
                {
                    "$addToSet": {  # Add a new aisle and shelf with the wine
                        "aisles": {
                            "aisle": aisle,
                            "shelves": [
                                {
                                    "shelf": shelf,
                                    "wines": [
                                        {"wine_id": wine_id, "stock": stock_to_add}
                                    ]
                                }
                            ]
                        }
                    }
                }
            )

            if result.matched_count == 0:
                return {"success": False, "message": "Warehouse not found."}

    # Step 4: Return success response
    if result.modified_count > 0:
        return {"success": True, "message": "Wine stock updated or added successfully."}
    else:
        return {"success": False, "message": "Operation failed, no changes were made."}
