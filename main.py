from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from json import dumps, loads
app = FastAPI()

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

available_rooms = []

@app.websocket("/")
async def ws_root(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        loaded_data = loads(data)
        if len(available_rooms) == 0:
            available_rooms.append({"roomId": loaded_data["roomId"], "messages": []})
        for room in available_rooms:
            if loaded_data["roomId"] == room["roomId"]:
                try:
                    if loaded_data["message"]:
                        room["messages"].append({"username": loaded_data["username"],"message": loaded_data["message"]})
                        await websocket.send_text(dumps(room["messages"]))
                except KeyError:
                    await websocket.send_text(dumps(room["messages"]))
            else:
                available_rooms.append({"roomId": loaded_data["roomId"], "messages": []})
        print(available_rooms)