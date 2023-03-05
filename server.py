import asyncio
import zipfile
import os.path

import fastapi
from fastapi import FastAPI, WebSocket

app = FastAPI()


USERS: dict[str, list[WebSocket, str]] = dict()


@app.get("/")
async def send():
    if os.path.exists("chat.zip"):
        with zipfile.ZipFile('chat.zip', 'w') as zip:
            zip.write("client_textual.py")
            zip.write("client.tcss")
    else:
        with zipfile.ZipFile('chat.zip', 'x') as zip:
            zip.write("client_textual.py")
            zip.write("client.tcss")
    return fastapi.responses.FileResponse("chat.zip", filename="chat.zip")


@app.get("/ping")
async def ping():
    return "OK"


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while websocket.application_state == websocket.application_state.CONNECTED:
        global USERS
        recv = await websocket.receive_json()
        print(recv)
        match recv["op"]:
            case 'login':
                if recv['username'] not in USERS.keys():
                    USERS[recv['username']] = [websocket, "home"]
                    await websocket.send_json({'status': 'ok'})
                else:
                    await websocket.send_json({'status': 'ERROR'})
                for data in USERS.values():
                    data[0]: WebSocket
                    await data[0].send_json({"op": "new", "username": recv["username"]})

            case 'logout':
                await USERS[recv['username']][0].close()
                del USERS[recv['username']]
                for data in USERS.values():
                    data[0]: WebSocket
                    await data[0].send_json({"op": "leave", "username": recv["username"]})

            case 'send':
                for data in USERS.values():
                    data[0]: WebSocket
                    await data[0].send_json({"op": "msg", "username": recv["username"], "msg": recv["msg"]})
