from cambc import *
from config import *
from terrain.symmetry import *

def send_message(player, message):
    my_pos = player.ct.get_position()
    for d in DIRECTIONS:
        test_pos = my_pos.add(d)
        if player.ct.can_place_marker(test_pos):
            player.ct.place_marker(test_pos, message.value)
            return True
    return False

def read_symmetry_message(player, message):
    value = message & 3
    try:
        player.map.symmetry_calculator.possible_symmetries = {Symmetry(value)}
    except Exception as e:
        print("Unknown symmetry value of",value,"from message",message)
        print(e)

def receive_messages(player):
    for b in player.ct.get_nearby_buildings():
        if player.ct.get_entity_type(b) is EntityType.MARKER and player.ct.get_team(b) is player.ct.get_team():
            message = player.ct.get_marker_value(b)
            read_symmetry_message(player, message)

def communicate_symmetry(player):
    receive_messages(player)
    if len(player.map.symmetry_calculator.possible_symmetries) == 1:
        send_message(player, next(iter(player.map.symmetry_calculator.possible_symmetries)))
