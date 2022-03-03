"""
GOAL: home automation using macropad + autohotkey
(potential additional goal: remove autohotkey and do the monitoring with the script, to work as a standalone program)

MacroPad layout:
[0][1][2][3][4]{K}
(5 keys and a Knob)
Each key has shortPress / longPress action
Knob as shortPress / CW rotation / CCW rotation

Control Layout
    Short                   Long
[0] Switch TV Light         Enable TV mode
[1] Switch PC Light         Enable PC mode
[2]                         Enable PC color mode
[3] MediaPrev               Mute (+ set mode to Volume) # Handled from AHK side ?
[4] MediaNext               Play/Pause                  # Handled from AHK side ?

    Rotation                Short
{K} Inc/Dec selected mode   Enable Volume mode

Mode can be one of
    HUE_BRIGHTNESS_TV
    HUE_BRIGHTNESS_PC
    HUE_COLOR_PC
    VOLUME
Current Mode is stored in mode.conf file

Action can be one of
    HUE_SWITCH_TV
    HUE_SWITCH_PC
    HUE_SWITCH_PC_COLOR
    KNOB_CW
    KNOB_CCW

"""

""" Imports """
from enum import Enum
import win32api
import argparse
import requests
import json
import conf


""" Config """


""" Constants"""


class MODES(Enum):
    HUE_BRIGHTNESS_TV = "HUE_BRIGHTNESS_TV"
    HUE_BRIGHTNESS_PC = "HUE_BRIGHTNESS_PC"
    HUE_COLOR_PC = "HUE_COLOR_PC"
    VOLUME = "VOLUME"


class ACTIONS(Enum):
    HUE_SWITCH_TV = "HUE_SWITCH_TV"
    HUE_SWITCH_PC = "HUE_SWITCH_PC"
    HUE_SWITCH_PC_COLOR = "HUE_SWITCH_PC_COLOR"
    KNOB_CW = "KNOB_CW"
    KNOB_CCW = "KNOB_CCW"


class COLORS(Enum):
    AO = '{"bri": 255, "colormode": "xy", "xy": [0.2688, 0.4019]}'
    BLUE = '{"bri": 255, "colormode": "xy", "xy": [0.1677, 0.2220]}'
    GREEN = '{"bri": 255, "colormode": "xy", "xy": [0.2760, 0.5855]}'
    ORANGE = '{"bri": 255, "colormode": "xy", "xy": [0.3787, 0.4860]}'
    PINK = '{"bri": 255, "colormode": "xy", "xy": [0.5485, 0.2393]}'
    RED = '{"bri": 255, "colormode": "xy", "xy": [0.6713, 0.3068]}'
    YELLOW = '{"bri": 255, "colormode": "xy", "xy": [0.4809, 0.4773]}'

    def next(self):
        cls = self.__class__
        members = list(cls)
        index = members.index(self) + 1
        if index >= len(members):
            index = 0
        return members[index]

    def previous(self):
        cls = self.__class__
        members = list(cls)
        index = members.index(self) - 1
        if index < 0:
            index = len(members) - 1
        return members[index]


VK_MEDIA_VOLUME_MUTE = 0xAD
VK_MEDIA_VOLUME_DOWN = 0xAE
VK_MEDIA_VOLUME_UP = 0xAF
VK_MEDIA_NEXT = 0xB0
VK_MEDIA_PREV = 0xB1
VK_MEDIA_PLAY_PAUSE = 0xB3

mode_path = "./mode.conf"
color_path = "./color.conf"

HUE_LIGHT_TV = 2
HUE_LIGHT_PC = 4
HUE_API_USER = conf.HUE_API_USER
HUE_API_IP = conf.HUE_API_IP
HUE_API_URL_PUT = "/lights/{which_light}/state"
HUE_API_URL_GET = "/lights/{which_light}"

""" Methods """


def write_mode(new_mode):
    with open(mode_path, "w") as content:
        content.write(new_mode)


def read_mode():
    with open(mode_path, "r") as content:
        return content.read()


def write_color(new_color):
    with open(color_path, "w") as content:
        content.write(new_color)


def read_color():
    with open(color_path, "r") as content:
        return content.read()


def process_action(action):
    if action == ACTIONS.KNOB_CCW.value or action == ACTIONS.KNOB_CW.value:
        mode = read_mode()
        process_knob(mode, action)
    if action == ACTIONS.HUE_SWITCH_TV.value:
        switch_light(HUE_LIGHT_TV)
    if action == ACTIONS.HUE_SWITCH_PC.value:
        switch_light(HUE_LIGHT_PC)
    if action == ACTIONS.HUE_SWITCH_PC_COLOR.value:
        switch_light_color(HUE_LIGHT_PC)
    return


def process_knob(mode, direction):
    if mode == MODES.VOLUME.value:
        if direction == ACTIONS.KNOB_CW.value:
            win32api.keybd_event(VK_MEDIA_VOLUME_UP, 0)
            return
        elif direction == ACTIONS.KNOB_CCW.value:
            win32api.keybd_event(VK_MEDIA_VOLUME_DOWN, 0)
            return
    if mode == MODES.HUE_BRIGHTNESS_TV.value:
        if direction == ACTIONS.KNOB_CW.value:
            set_light_brightness(HUE_LIGHT_TV, +10)
            return
        elif direction == ACTIONS.KNOB_CCW.value:
            set_light_brightness(HUE_LIGHT_TV, -10)
            return
    if mode == MODES.HUE_BRIGHTNESS_PC.value:
        if direction == ACTIONS.KNOB_CW.value:
            set_light_brightness(HUE_LIGHT_PC, +10)
            return
        elif direction == ACTIONS.KNOB_CCW.value:
            set_light_brightness(HUE_LIGHT_PC, -10)
            return
    if mode == MODES.HUE_COLOR_PC.value:
        set_light_color(HUE_LIGHT_PC, direction)
        return
    return


def set_light_brightness(light, change):
    info = get_light_info(light)
    target = HUE_API_IP + HUE_API_USER + HUE_API_URL_PUT.format(which_light=light)
    headers = {'Content-Type': 'application/json'}
    brightness = info["brightness"] + change
    if brightness > 255:
        brightness = 255
    if brightness < 0:
        brightness = 0
    payload = '{"on": true, "bri": ' + str(brightness) + '}'
    resp = requests.put(target, headers=headers, data=payload)
    print(resp.content)
    return


def get_light_info(light):
    target = HUE_API_IP + HUE_API_USER + HUE_API_URL_GET.format(which_light=light)
    headers = {'Content-Type': 'application/json'}
    resp = requests.get(target, headers=headers)
    data = json.loads(resp.content)
    status = data["state"]["on"]
    brightness = data["state"]["bri"]
    return {"status": status, "brightness": brightness}


def set_light_color(light, direction):
    current_color = read_color()
    if direction == ACTIONS.KNOB_CW.value:
        new_color = COLORS[current_color].next().name
    elif direction == ACTIONS.KNOB_CCW.value:
        new_color = COLORS[current_color].previous().name
    else:
        return
    write_color(new_color)
    apply_light_color(light)
    return


def apply_light_color(light):
    current_color = read_color()
    target = HUE_API_IP + HUE_API_USER + HUE_API_URL_PUT.format(which_light=light)
    headers = {'Content-Type': 'application/json'}
    payload = COLORS[current_color].value
    resp = requests.put(target, headers=headers, data=payload)
    # data = json.loads(resp.content)
    # print(data)
    return


def switch_light_color(light):
    info = get_light_info(light)
    target = HUE_API_IP + HUE_API_USER + HUE_API_URL_PUT.format(which_light=light)
    headers = {'Content-Type': 'application/json'}
    if info["status"]:
        payload = '{"on": false}'
        resp = requests.put(target, headers=headers, data=payload)
        # data = json.loads(resp.content)
        # print(data)
    else:
        apply_light_color(light)
    return


def switch_light(light):
    info = get_light_info(light)
    target = HUE_API_IP + HUE_API_USER + HUE_API_URL_PUT.format(which_light=light)
    headers = {'Content-Type': 'application/json'}
    if info["status"]:
        payload = '{"on": false}'
    else:
        payload = '{"on": true, "colormode": "ct", "ct": 367}'
    resp = requests.put(target, headers=headers, data=payload)
    # data = json.loads(resp.content)
    # print(data)
    return


""" Main """
""" 
parameters: 
-mode {mode}        change to the desired mode
-action {action}    process an action
"""
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    arg_group = parser.add_mutually_exclusive_group(required=True)
    arg_group.add_argument("-m", "--mode", help="switch the knob to the desired mode", choices=[e.value for e in MODES])
    arg_group.add_argument("-a", "--action", help="perform an action", choices=[e.value for e in ACTIONS])
    args = parser.parse_args()
    if args.mode:
        write_mode(args.mode)
        exit(0)
    if args.action:
        process_action(args.action)
        exit(0)
