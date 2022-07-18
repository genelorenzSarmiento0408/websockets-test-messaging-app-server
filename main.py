from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from json import dumps, loads
from pymongo import MongoClient, ReturnDocument
import os
from dotenv import load_dotenv
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
app = FastAPI()
hasher = PasswordHasher()
# MongoDB
load_dotenv()
CONNECTION_STRING = os.getenv("CONNECTION_STRING")
client = MongoClient(CONNECTION_STRING)
database = client["MFRPWMessagingDB"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def read_root():
    return {"Hello": "World"}

room_collection = database["Rooms"]
user_collection = database["Users"]
rooms = []
users = []
room_id_array = []
for roomInfo in room_collection.find():
    rooms.append(roomInfo)
for userInfo in user_collection.find():
    users.append(userInfo)


@app.websocket("/")
async def ws_root(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        loaded_data = loads(data)
        try:
            username_found = user_collection.find_one(
                {"username": loaded_data["username"]}
            )
            valid_entry_choices = [
                "Register",
                "Login"
            ]
            if loaded_data.get("entryChoice") is not None:
                # If the entry choice is Register
                if loaded_data["entryChoice"] == "Register":
                    # If the username founded by the database is present,
                    if username_found is not None:
                        # return a message saying the username has found
                        await websocket.send_text('{"error": "Username found, \
                        please register with another username again"}')
                        continue
                    # else, insert it into the database
                    user_collection.insert_one(
                        {"username": loaded_data["username"],
                         "password": hasher.hash(loaded_data["password"])}
                    )
                # If the entry choice is Login
                if loaded_data["entryChoice"] == "Login":
                    # If the username founded by the database is not present
                    if username_found is None:
                        # return user not found
                        await websocket.send_text(
                            '{"error": "User not found, please register!"}'
                        )
                        continue
                    # Verify the password, if the password doesn't match
                    try:
                        hasher.verify(
                            username_found["password"], loaded_data["password"]
                        )
                    except VerifyMismatchError:
                        # return a message, saying the error
                        await websocket.send_text(
                            '{"error": "Incorrect Password"}'
                        )
                        continue
                # If the entry choice is invalid; return "Invalid entry choice"
                if loaded_data["entryChoice"] not in valid_entry_choices:
                    await websocket.send_text(
                        '{"error": "Invalid entry choice"}'
                    )
                    continue

            new_room = {"roomId": loaded_data["roomId"], "messages": []}
            if len(rooms) == 0:
                rooms.append(new_room)
                room_collection.insert_one(new_room)
            for available_room in rooms:
                room_id_array.append(available_room["roomId"])
            if not loaded_data["roomId"] in room_id_array:
                rooms.append(new_room)
                room_collection.insert_one(new_room)
            for room in rooms:
                if loaded_data["roomId"] == room["roomId"]:
                    room["messages"].append(
                        {"username": loaded_data["username"],
                            "message": loaded_data["message"]}
                    )
                    print(room["messages"])
                    room_collection.find_one_and_update(
                        {"roomId": room["roomId"]},
                        {"$set": {"messages": room["messages"]}},
                        return_document=ReturnDocument.AFTER)
                    await websocket.send_text(dumps(room["messages"]))
        except KeyError:
            for room in rooms:
                if loaded_data["roomId"] == room["roomId"]:
                    await websocket.send_text(dumps(room["messages"]))
