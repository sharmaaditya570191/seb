from django.conf import settings

from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .exceptions import ClientError
from .utils import get_room_or_error

# added
from .models import Room
from .views import get_all_logged_in_users
import random
# import pdb
# pdb.set_trace()

from channels.consumer import AsyncConsumer

class EchoConsumer(AsyncConsumer):
    async def websocket_connect(self, event):
        await self.send({
            "type": "websocket.accept",
        })
    async def websocket_receive(self, event):
        await self.receive_json(event)
        # await self.send({
        #     "type": "websocket.send",
        #     "text": event["text"],
        # })

# added: keep track of which chatters are in which rooms
users_and_rooms = {}
users_and_channels = {}

# added: adds users to a list in a dictionary: {user: [rooms]}
def add_user_and_channels(self, user, channel_name):
    users_and_channels[user] = channel_name

# added: adds users to a list in a dictionary: {user: [rooms]}
def add_user_and_rooms(self, user, room_id):
    if users_and_rooms.get(user) == None:
        room_list = [room_id]
        users_and_rooms[user] = room_list
    else:
        users_and_rooms[user].append(room_id)

# added to delete users and rooms from users_and_rooms dict
def delete_user_and_rooms(self, user, room_id):
    users_and_rooms[user].remove(room_id)

class ChatConsumer(AsyncJsonWebsocketConsumer, EchoConsumer):
    """
    This chat consumer handles websocket connections for chat clients.

    It uses AsyncJsonWebsocketConsumer, which means all the handling functions
    must be async functions, and any sync work (like ORM access) has to be
    behind database_sync_to_async or sync_to_async. For more, read
    http://channels.readthedocs.io/en/latest/topics/consumers.html
    """

    ##### WebSocket event handlers

    async def connect(self):
        """
        Called when the websocket is handshaking as part of initial connection.
        """
        # Are they logged in?
        if self.scope["user"].is_anonymous:
            # Reject the connection
            await self.close()
        else:
            # Accept the connection
            await self.accept()
        # Store which rooms the user has joined on this connection
        self.rooms = set()

        add_user_and_channels(self, self.scope["user"].username, self.channel_name)
        print(users_and_channels)

    async def receive_json(self, content):
        """
        Called when we get a text frame. Channels will JSON-decode the payload
        for us and pass it as the first argument.
        """
        # Messages will have a "command" key we can switch on
        command = content.get("command", None)
        print(content)

        # added to work on how to direct clients to staff

        if self.scope["user"].is_staff:
            try:
                if command == "join":
                    # Make them join the room
                    await self.join_room(content["room"])
                elif command == "leave":
                    # Leave the room
                    await self.leave_room(content["room"])
                    # added to destroy room when leaving.
                    Room.objects.filter(id=content["room"]).delete()
                elif command == "send":
                    await self.send_room(content["room"], content["message"])

                # Added for random chat room.
                elif command == "join_random":
                    # Make them join the room
                    await self.join_room(content["room"])

                elif command == "leave_random":
                    # Leave the room
                    await self.leave_room(content["room"])
                    Room.objects.get(id=content["room"]).delete()

            except ClientError as e:
                # Catch any errors and send it back
                await self.send_json({"error": e.code})
        else:
            try:
                if command == "join":
                    # Make them join the room
                    await self.join_room_client(content["room"])
                elif command == "leave":
                    # Leave the room
                    await self.leave_room(content["room"])
                    # added to destroy room when leaving.
                    Room.objects.filter(id=content["room"]).delete()
                elif command == "send":
                    await self.send_room(content["room"], content["message"])

                # Added for random chat room.
                elif command == "join_random":
                    # Make them join the room
                    await self.join_room(content["room"])

                elif command == "leave_random":
                    # Leave the room
                    await self.leave_room(content["room"])
                    Room.objects.get(id=content["room"]).delete()

            except ClientError as e:
                # Catch any errors and send it back
                await self.send_json({"error": e.code})

    async def disconnect(self, code):
        """
        Called when the WebSocket closes for any reason.
        """
        # Leave all the rooms we are still in
        for room_id in list(self.rooms):
            try:
                await self.leave_room(room_id)
            except ClientError:
                pass

    ##### Command helper methods called by receive_json

    async def join_room(self, room_id):
        """
        Called by receive_json when someone sent a join command.
        """
        # The logged-in user is in our scope thanks to the authentication ASGI middleware
        room = await get_room_or_error(room_id, self.scope["user"])
        # Send a join message if it's turned on
        if settings.NOTIFY_USERS_ON_ENTER_OR_LEAVE_ROOMS:
            await self.channel_layer.group_send(
                room.group_name,
                {
                    "type": "chat.join",
                    "room_id": room_id,
                    "username": self.scope["user"].username,
                }
            )
            # Store that we're in the room
            self.rooms.add(room_id)
        # Add them to the group so they get room messages
        await self.channel_layer.group_add(
            room.group_name,
            self.channel_name,
        )
        # Instruct their client to finish opening the room
        await self.send_json({
            "join": str(room.id),
            "title": room.title,
        })
        # added to add user and rooms to user_and_rooms dict
        add_user_and_rooms(self, self.scope["user"].username, room_id)
        print(users_and_rooms)



    async def join_room_client(self, room_id):
        """
        Called by receive_json when someone sent a join command.
        """
        # The logged-in user is in our scope thanks to the authentication ASGI middleware
        room = await get_room_or_error(room_id, self.scope["user"])
        # Send a join message if it's turned on
        if settings.NOTIFY_USERS_ON_ENTER_OR_LEAVE_ROOMS:
            await self.channel_layer.group_send(
                room.group_name,
                {
                    "type": "chat.join",
                    "room_id": room_id,
                    "username": self.scope["user"].username,
                }
            )
        # Store that we're in the room
        self.rooms.add(room_id)
        # Add them to the group so they get room messages
        await self.channel_layer.group_add(
            room.group_name,
            self.channel_name,
        )
        # Instruct their client to finish opening the room
        await self.send_json({
            "join": str(room.id),
            "title": room.title,
        })

        # print("channel layer: " + self.channel_layer)
        print("group name: " + room.group_name)
        print("channel name: " + self.channel_name)
        # added to add user and rooms to user_and_rooms dict
        add_user_and_rooms(self, self.scope["user"].username, room_id)
        print(users_and_rooms)



        # added to find all staff who are logged in
        authenticated_staff = get_all_logged_in_users()

        # added to list all available staff in less than 3 chatrooms
        available_staff = []

        if len(authenticated_staff) > 0:

            for staff in authenticated_staff:
                if staff in users_and_rooms and len(users_and_rooms[staff]) in range(3):
                    available_staff.append(staff)
                    random_available_staff = random.choice(available_staff)

                    print(random_available_staff)

                    content = {
                        "command": "join",
                        "join": room_id,
                        "type": "chat.join",
                        # "type": "websocket.send",
                        "room_id": room_id,
                        "text": "Hello there!",
                        "username": random_available_staff,
                        "title": room.title,
                    }

                    #helps to open room in conjunction with chat_join()
                    from channels.layers import get_channel_layer

                    channel_layer = get_channel_layer()
                    await channel_layer.send(
                        users_and_channels[random_available_staff],
                        content
                    )

                    # added to add staff to chatroom
                    await self.channel_layer.group_add(
                        room.group_name,
                        users_and_channels[random_available_staff],
                    )


                else:
                    print("Counsellors are not yet ready.")

        else:
            print("There are no counsellors available.")





    async def leave_room(self, room_id):
        """
        Called by receive_json when someone sent a leave command.
        """
        # The logged-in user is in our scope thanks to the authentication ASGI middleware
        room = await get_room_or_error(room_id, self.scope["user"])
        # Send a leave message if it's turned on
        if settings.NOTIFY_USERS_ON_ENTER_OR_LEAVE_ROOMS:
            await self.channel_layer.group_send(
                room.group_name,
                {
                    "type": "chat.leave",
                    "room_id": room_id,
                    "username": self.scope["user"].username,
                }
            )
        # Remove that we're in the room
        self.rooms.discard(room_id)
        # Remove them from the group so they no longer get room messages
        await self.channel_layer.group_discard(
            room.group_name,
            self.channel_name,
        )
        # Instruct their client to finish closing the room
        await self.send_json({
            "leave": str(room.id),
        })
        # added to delete user and rooms to user_and_rooms dict
        delete_user_and_rooms(self, self.scope["user"].username, room_id)
        print(users_and_rooms)

    async def send_room(self, room_id, message):
        """
        Called by receive_json when someone sends a message to a room.
        """
        # Check they are in this room
        if room_id not in self.rooms:
            raise ClientError("ROOM_ACCESS_DENIED")
        # Get the room and send to the group about it
        room = await get_room_or_error(room_id, self.scope["user"])
        await self.channel_layer.group_send(
            room.group_name,
            {
                "type": "chat.message",
                "room_id": room_id,
                "username": self.scope["user"].username,
                "message": message,
            }
        )

    ##### Handlers for messages sent over the channel layer

    # These helper methods are named by the types we send - so chat.join becomes chat_join
    async def chat_join(self, event):
        """
        Called when someone has joined our chat.
        """
        # Send a message down to the client
        await self.send_json(
            {
                "msg_type": settings.MSG_TYPE_ENTER,
                "room": event["room_id"],
                "username": event["username"],
                # added
                "command": "join",
                "join": event["room_id"],
                "title": event["title"],
            },
        )

        # added to add staff to room
        if self.scope["user"].is_staff:
            self.rooms.add(event["room_id"])
        else:
            pass

    async def chat_leave(self, event):
        """
        Called when someone has left our chat.
        """
        # Send a message down to the client
        await self.send_json(
            {
                "msg_type": settings.MSG_TYPE_LEAVE,
                "room": event["room_id"],
                "username": event["username"],
            },
        )

    async def chat_message(self, event):
        """
        Called when someone has messaged our chat.
        """
        # Send a message down to the client
        await self.send_json(
            {
                "msg_type": settings.MSG_TYPE_MESSAGE,
                "room": event["room_id"],
                "username": event["username"],
                "message": event["message"],
            },
        )

