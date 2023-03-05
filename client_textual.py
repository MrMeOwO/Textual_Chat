import asyncio
import random
from datetime import datetime
import rich
import json

import websockets.client
import websockets.exceptions
import websockets.legacy.client

from textual.app import App, ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import Static, Input, TextLog, Button
from textual import log
from textual.reactive import reactive


USERNAME = f"MrMeOwO"
ADRES = "ws://localhost:80/ws"


def render_str(text, **kwargs):
    return rich.get_console().render_str(text=text, **kwargs)


class RoomsWidget(Static):
    pass


class ChatWidget(Static):
    def compose(self) -> ComposeResult:
        yield TextLog(classes="chat")
        yield Horizontal(
            Input(classes="input_field",
                  id="chat_input_field"),
            Button("⤴",
                   classes="input_submit",
                   variant="primary",
                   id="chat_input_submit"),
            classes="input"
        )


class UsersWidget(Static):
    users = reactive(list())

    def watch_users(self, users):
        self.update(render_str('\n'.join(users)))

    def add_user(self, username):
        t = self.users.copy()
        t.append(username)
        self.users = t

    def remove_user(self, username):
        t = self.users.copy()
        t.remove(username)
        self.users = t


class ChatApp(App):
    CSS_PATH = "client.tcss"

    def __init__(self):
        super().__init__()

    def compose(self) -> ComposeResult:
        yield RoomsWidget("Rooms", classes="box rooms")
        yield ChatWidget("Chat", classes="box")
        yield UsersWidget("Users", classes="box users")

    async def on_mount(self):
        asyncio.create_task(self.handle_socket())

    async def on_unmount(self):
        await self.con.send(json.dumps({"op": "logout", "username": USERNAME}))
        await self.con.close()

    async def handle_socket(self):
        self.con = await websockets.client.connect(ADRES)
        await self.con.send(json.dumps({"op": "login", "username": USERNAME}))
        if json.loads(await self.con.recv())["status"] == "ERROR":
            quit()
        text_log = self.query_one(ChatWidget).query_one(TextLog)
        while True:
            try:
                recv = json.loads(await self.con.recv())
                log(recv)
                match recv['op']:
                    case "new":
                        text_log.write(render_str(f"[blue][{datetime.now().time().strftime('%H:%M:%S')}][/]Подключился {recv['username']}"))
                        self.query_one(UsersWidget).add_user(recv['username'])
                    case "leave":
                        text_log.write(render_str(f"[blue][{datetime.now().time().strftime('%H:%M:%S')}][/]Отключился {recv['username']}"))
                        self.query_one(UsersWidget).remove_user(recv['username'])
                    case "msg":
                        text_log.write(render_str(f"[yellow][{datetime.now().time().strftime('%H:%M:%S')}][/]{recv['username']}: {recv['msg']}🦊"))
            except websockets.exceptions.ConnectionClosedOK:
                pass
            except websockets.exceptions.ConnectionClosed:
                self.query_one(ChatWidget).query_one(Horizontal).styles.visibility = "hidden"
                seconds = 10
                while seconds != 0:
                    text_log.write(render_str(f"[bold red]DISCONNECTED[/] restarting in {seconds} seconds"))
                    seconds -= 1
                    await asyncio.sleep(1)
                try:
                    self.con = await websockets.client.connect(ADRES)
                except websockets.exceptions.ConnectionClosed:
                    self.exit()
                else:
                    text_log.write(render_str("[green]Connection restored![/]"))
                    self.query_one(ChatWidget).query_one(Horizontal).styles.visibility = "visible"

    async def on_input_submitted(self, event: Input.Submitted):
        if event.input.id == "chat_input_field":
            if event.input.value != "":
                await self.con.send(json.dumps({"op": "send", 'username': USERNAME, "msg": event.input.value}))
            event.input.value = ""

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "chat_input_submit":
            input_field = self.query_one(ChatWidget).query_one(Horizontal).query_one(Input)
            if input_field.value != "":
                await self.con.send(json.dumps({"op": "send", 'username': USERNAME, "msg": input_field.value}))
            input_field.value = ""


if __name__ == "__main__":
    app = ChatApp()
    app.run()
