from typing import Union
from fastapi import FastAPI
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
    newItem['_id'] = ObjectId()

    assert storageLocation in ("Fridge", "Freezer", "Shelf")
    col.update_one({"User": userName}, {
                   "$push": {storageLocation: newItem}})
