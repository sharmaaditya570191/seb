from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Room

# added
from django.db import models
import random

@login_required
def index(request):
    """
    Root page view. This is essentially a single-page app, if you ignore the
    login and admin parts.
    """

    random_room = GenerateRoomName()
    Room.objects.create(title=random_room)

    # Get a list of rooms, ordered alphabetically
    rooms = Room.objects.order_by("title")

    # Render that in the index template
    return render(request, "index.html", {
        "rooms": rooms,
    })

def GenerateRoomName():

    animal = ["orang utan", "tapir", "sloth", "cat", "bat", "coyote", "earthworm", "cow", "billy goat gruff"]
    furniture = ["chair", "table", "ottoman", "stool", "desk", "armchair", "cabinet", "kitchen counter", "bed"]

    noun = [animal, furniture]

    colour = ["red", "white", "blue", "violet", "orange", "yellow", "purple", "pink", "hazel"]
    size = ["tiny", "microscopic", "small", "big", "huge", "sizeable", "medium-sized"]

    adjective = [colour, size]

    # Get list of names of existing rooms.
    room_titles_list = Room.objects.all().values('title')
    room_titles_strings_list = [r['title'] for r in room_titles_list]

    while True:
        noun_list_pick = random.choice(noun)
        noun_pick = random.choice(noun_list_pick)

        adjective_list_pick = random.choice(adjective)
        adjective_pick = random.choice(adjective_list_pick)

        room_title = adjective_pick + " " + noun_pick

        if room_title not in room_titles_strings_list:
            return room_title
        else:
            pass


# Get list of logged in authenticated users.
# https://stackoverflow.com/questions/2723052/how-to-get-the-list-of-the-authenticated-users
# https://docs.djangoproject.com/en/2.0/howto/custom-template-tags/
from django.contrib.auth.models import User
from django.contrib.sessions.models import Session
from django.utils import timezone

def get_all_logged_in_users():
    # Query all non-expired sessions
    # use timezone.now() instead of datetime.now() in latest versions of Django
    sessions = Session.objects.filter(expire_date__gte=timezone.now())
    uid_list = []

    # Build a list of user ids from that query
    for session in sessions:
        data = session.get_decoded()
        uid_list.append(data.get('_auth_user_id', None))

    # print(uid_list)

    authenticated_staff = []
    for user in User.objects.filter(id__in=uid_list):
        if user.is_staff and user.is_authenticated:
            authenticated_staff.append(user.username)

    return authenticated_staff
    # Query all logged in users based on id list
    # return User.objects.filter(id__in=uid_list)

