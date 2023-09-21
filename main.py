from typing import Union
from fastapi import FastAPI, HTTPException
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from pydantic import BaseModel
from bson import ObjectId

app = FastAPI(docs_url="/docs")

# For switching between development and production environments
dev = True

# Change this to a tls authentication later
if (dev):
    uri = "mongodb://localhost:27017"
    client = MongoClient(uri, server_api=ServerApi('1'))
else:
    uri = "Enter the mongo DB key"
    client = MongoClient(uri, server_api=ServerApi('1'))

db = client["WhatsInMyFridge"]
col = db["UserInformation"]

# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
    print("Connected to the local server")
except Exception as e:
    print(e)


class FoodItem(BaseModel):
    name: str
    type: str
    expirationDate: str
    startDate: str
    quantity: int
    expirationType: str


class NewLocation(BaseModel):
    newLocation: str


STORAGE_LOCATIONS = ("Fridge", "Freezer", "Shelf")

# Recursively convert objectID's to string


def convert_objectid_to_str(data):
    if isinstance(data, ObjectId):
        return str(data)
    elif isinstance(data, list):
        return [convert_objectid_to_str(item) for item in data]
    elif isinstance(data, dict):
        return {key: convert_objectid_to_str(value) for key, value in data.items()}
    else:
        return data


# Get the users information
@app.get("/userInfo/{userName}")
async def getUserInfo(userName: str):
    data = col.find_one({"User": userName})
    data = convert_objectid_to_str(data)

    return {"body": data}


# Add new fooditem (generates unique ID)
@app.post("/userItems/{userName}/{storageLocation}")
async def postNewItem(userName: str, storageLocation: str, foodItem: FoodItem):

    newItem = dict(foodItem)
    newID = ObjectId()
    newItem['id'] = newID

    assert storageLocation in STORAGE_LOCATIONS
    result = col.update_one({"User": userName}, {
                            "$push": {storageLocation: dict(newItem)}})

    if result.matched_count == 0:
        raise ValueError(f'user "{userName}" not found')
    # return result.matched_count > 0

    return {"id": str(newID)}

# delete food item


@app.delete("/userItems/{userName}/{storageLocation}/{id}")
async def removeItem(userName: str, storageLocation: str, id: str):

    id = ObjectId(id)

    assert storageLocation in STORAGE_LOCATIONS

    # look for the item
    result = col.update_one({"User": userName}, {
        "$pull": {
            storageLocation: {
                "id": {
                    "$eq": id
                }
            }
        }
    })

    if result.modified_count != 1:
        raise ValueError(f"{result.modified_count} items were modified!")


@app.post("/userItems/{userName}/{storageLocation}/{id}")
async def moveItem(userName: str, storageLocation: str, id: str, values: NewLocation):
    """Move food item from one storage location to another

    Args:
        userName (str): User name
        storageLocation (str): Move from this location
        id (str): id of food item
        values (NewLocation): Obj containing field `newLocation` - move to this location

    Raises:
        HTTPException: 
        RuntimeError: Unable to update DB properly
    """
    try:
        id = ObjectId(id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

    if storageLocation not in STORAGE_LOCATIONS:
        raise HTTPException(
            status_code=404, detail=f"Storage location {storageLocation} does not exist")
    if values.newLocation not in STORAGE_LOCATIONS:
        raise HTTPException(
            status_code=400, detail=f"Storage location {values.newLocation} does not exist")

    query = col.aggregate([
        {"$match": {"User": userName}},   # all documents with this userName
        # remove other fields that we don't need
        {"$project": {storageLocation: 1}},
        # duplicate for each item in the storageLocation array,
        {"$unwind": f"${storageLocation}"},
        # with the array replaced with that item
        {"$match": {f"{storageLocation}.id": id}},  # match with the correct id
    ])

    # unwrap from iterator and get the item only
    item = next((x[storageLocation] for x in query), None)

    # check that item exists
    if not item:
        raise HTTPException(
            status_code=404, detail=f"Item with id {id} does not exist in {storageLocation} for user {userName}")

    # update db. "$elemMatch" used in case the db has changed since the query
    result = col.update_one({"User": userName, storageLocation: {"$elemMatch": item}},
                            {"$pull": {storageLocation: item},
                             "$push": {values.newLocation: item}})

    if result.modified_count != 1:
        raise RuntimeError(f"{result.modified_count} items were modified!")


@app.post("/userItems/edit/{userName}/{storageLocation}/{id}")
async def editItem(userName: str, storageLocation: str, id: str, newInfo: FoodItem):

    # Verify that the id is of correct format
    try:
        id = ObjectId(id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

    # Convert the item into a dictionary
    newValues = dict(newInfo)
    newValues['id'] = id

    # Mongo query elements
    query = {"User": userName, f"{storageLocation}.id": id}
    update = {"$set": {f"{storageLocation}.$": newValues}}

    # Validating the information the user has sent
    assert storageLocation in STORAGE_LOCATIONS

    try:
        # Check if an item with the specific id at the storage location exist
        if (not col.find_one(query)):
            raise HTTPException(
                status_code=404, detail=f"Item with id {id} does not exist in {storageLocation} for user {userName}")
    except HTTPException as e:
        raise
    else:
        # If no exceptions handle the update
        col.update_one(query, update)


# Function for general testing mongodb usage
@app.get("/userItems/edit/{userName}/{storageLocation}/{id}")
async def testing(userName: str, storageLocation: str, id: str):

    # Verify that the id is of correct format
    try:
        id = ObjectId(id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

    assert storageLocation in STORAGE_LOCATIONS
    query = {"User": userName, f"{storageLocation}.id": id}

    result = col.find_one(query)

    print(result)
