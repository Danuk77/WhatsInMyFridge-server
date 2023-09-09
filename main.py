from typing import Union
from fastapi import FastAPI
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

app = FastAPI()

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


# Get the users information
@app.get("/userInfo/{userName}")
async def getUserInfo(userName: str):
    data = col.find_one({"User": userName}, {'_id': 0})
    return {"body": data}
