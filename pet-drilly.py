#!/usr/bin/env python3

from dataclasses import dataclass
from math import sqrt
from playsound3 import playsound
from os.path import dirname
from pathlib import Path
from tkinter import *
from PIL import Image, ImageTk
from itertools import count
from random import randint, choice
from time import time
import psutil

# updated in logic
current_temp = 0
DRILLY_HOT_TEMP = 80

@dataclass
class DrillyVoiceLine:
    file: str
    text: str | None
    def can_play_now(self):
        return True

@dataclass
class DrillyOverheatingVoiceLine(DrillyVoiceLine):
    file: str
    text: str | None
    def can_play_now(self):
        return current_temp >= DRILLY_HOT_TEMP

@dataclass
class DrillyState:
    image: str
    average_time_ms: float | None
    voice_lines: list[str]
    transitions: dict[str, float]

# ====================
# Drilly configuration
# ====================

STATES = {
    "idle": DrillyState("DrillyNeutral.webp", 60000, [], {
        "idle": 5,
        "noises": 5,
        "happy": 5,
        "sleep": 1,
        "talk": 2,
    }),

    "noises": DrillyState("DrillyHappy.webp", None, [
        DrillyVoiceLine("Drilly_Giggle.mp3", None),
        DrillyVoiceLine("Drilly_Giggle2.mp3", None),
        DrillyVoiceLine("Drilly_Giggle3.mp3", None),
        DrillyVoiceLine("Drilly_Humming.mp3", None),
        DrillyVoiceLine("Drilly_R1.mp3", None),
        DrillyVoiceLine("Drilly_R2.mp3", None),
        DrillyVoiceLine("Drilly_R3.mp3", None),
        DrillyVoiceLine("Drilly_R4.mp3", None),
        DrillyVoiceLine("Drilly_R5.mp3", None),
        DrillyVoiceLine("Drilly_R6.mp3", None),
        DrillyVoiceLine("Drilly_R7.mp3", None),
    ], {
        "idle": 1,
    }),

    "happy": DrillyState("DrillyHappy.webp", 30000, [], {
        "idle": 1,
    }),

    "sleep": DrillyState("DrillySleep.webp", 120000, [], {
        "idle": 1,
    }),

    "talk": DrillyState("DrillyTalk.webp", None, [
        DrillyVoiceLine("Drilly_AreWeLost.mp3", "Are we lost?"),
        DrillyVoiceLine("Drilly_B2.mp3", "Are we there yet?"),
        DrillyVoiceLine("Drilly_B3.mp3", "Are we there yeeet?"),
        DrillyVoiceLine("Drilly_B4.mp3", "Are we there yet?"),
        DrillyVoiceLine("Drilly_B5.mp3", "Are we there yet?"),
        DrillyVoiceLine("Drilly_B6.mp3", "Are weeee there yet?"),
        DrillyVoiceLine("Drilly_B8.mp3", "Can we make a stop?"),
        DrillyOverheatingVoiceLine("Drilly_B9.mp3", "I'm overheating in here."),
        DrillyOverheatingVoiceLine("Drilly_B10.mp3", "It's so hot in here..."),
        DrillyVoiceLine("Drilly_Balls.ogg", "Balls! Heheheh. Sorry."),
        DrillyVoiceLine("Drilly_Different.mp3", "Something looks different!"),
        DrillyVoiceLine("Drilly_HowAreYou.mp3", "Oh, how are you?"),
        DrillyVoiceLine("Drilly_HowAreYou2.mp3", "How are you?"),
        DrillyVoiceLine("Drilly_OoWhatsThis.mp3", "Ooh, what's this?"),
        DrillyVoiceLine("Drilly_RigidBody.mp3", "I don't know what the point of this one is..."),
        DrillyVoiceLine("Drilly_Rings4.ogg", "You're doing great I think... Okay..."),
        DrillyVoiceLine("Drilly_Spooky.mp3", "Spooky! Heheheh."),
    ], {
        "idle": 1,
    }),
}

DEFAULT_STATE = "idle"

START_VOICE = "Drilly_Hi2.mp3"
EXIT_VOICE = "Drilly_Sad.mp3"

VOICE_DURATION = 3000

DRILLY_SIZE = 159
# These three are probably the most important options:
GLOBAL_SCALE = 0.5      # Tweak Drilly's size
GLOBAL_OFFS_LEFT = 0    # Move Drilly
GLOBAL_OFFS_BOTTOM = 44 # Move Drilly

PATTING_VELOCITY_THRESHOLD = 100 # pixels per second

TEMP_SENSOR = "k10temp"

VERBOSE_LOG = False

# ============
# Drilly logic
# ============

# The code quality only goes down from here. Beware.

def verbose_log(text):
    if VERBOSE_LOG:
        print(text)

DRILLY_SIZE = int(DRILLY_SIZE * GLOBAL_SCALE)

def probabilistic_select(variants: dict[str, int]):
    def selection_step(variant_list, value):
        variant, weight = variant_list[0]
        if value <= weight:
            return variant
        return selection_step(variant_list[1:], value - weight)

    maximum = sum(variants.values())
    return selection_step(list(variants.items()), randint(1, maximum))

class ImageLabel(Label):
    timer = None

    def load(self, im, size):
        if isinstance(im, str):
            im = im
        self.loc = 0
        self.frames = []
        self.timer = None

        try:
            for i in count(1):
                self.frames.append(ImageTk.PhotoImage(im.copy().resize(size)))
                im.seek(i)
        except EOFError:
            pass

        try:
            self.delay = im.info["duration"]
        except:
            self.delay = 200

        if len(self.frames) == 1:
            self.config(image=self.frames[0])
        else:
            self.next_frame()

    def unload(self):
        self.config(image="")
        self.frames = None
        if timer := self.timer:
            self.after_cancel(timer)

    def next_frame(self):
        if self.frames:
            self.loc += 1
            self.loc %= len(self.frames)
            self.config(image=self.frames[self.loc])
            self.timer = self.after(self.delay, self.next_frame)

BASE_DIR = Path(dirname(__file__))
IMAGE_BASE_DIR = BASE_DIR / "images"
VOICE_BASE_DIR = BASE_DIR / "voice"

playsound(VOICE_BASE_DIR / START_VOICE, block=False)

drilly_window = Tk()
screen_height = drilly_window.winfo_screenheight()
y_of_window_top = screen_height - GLOBAL_OFFS_BOTTOM - DRILLY_SIZE
drilly_window.geometry(f"{DRILLY_SIZE}x{DRILLY_SIZE}+{GLOBAL_OFFS_LEFT}+{y_of_window_top}")
drilly_window.overrideredirect(1)
drilly_window.attributes("-topmost", True)

img = None
drilly_img = ImageLabel(drilly_window, borderwidth=0)
drilly_img.place(x=0, y=0)

def create_dialog_window(text: str):
    dialog_window = Toplevel(drilly_window)
    window_width = DRILLY_SIZE * 3
    dialog_window.geometry(f"{window_width}x{DRILLY_SIZE}+{GLOBAL_OFFS_LEFT + DRILLY_SIZE}+{y_of_window_top}")
    dialog_window.overrideredirect(1)
    dialog_window.attributes("-topmost", True)
    bg = "#4a6513"
    dialog_window.config(background=bg)

    font_size = int(20 * GLOBAL_SCALE)
    label = Label(dialog_window, bg=bg, fg="#5dffb4", text=text, font=("Joystix Monospace", font_size), wraplength=window_width)
    label.pack(expand=True)

    dialog_window.after(VOICE_DURATION, dialog_window.destroy)

drilly_state = DEFAULT_STATE
def drilly_choose_new_state():
    global drilly_state, img
    transitions = STATES[drilly_state].transitions
    drilly_state = probabilistic_select(transitions)
    verbose_log(f"State transition: {drilly_state}")

drilly_timer = None
drilly_sound = None
def drilly_update_state():
    global drilly_state, drilly_timer, drilly_sound, img
    state_info = STATES[drilly_state]

    if drilly_timer:
        drilly_window.after_cancel(drilly_timer)
    if drilly_sound:
        drilly_sound.stop()

    if img:
        img.close()
    img = Image.open(IMAGE_BASE_DIR / state_info.image)
    drilly_img.unload()
    drilly_img.load(img, (DRILLY_SIZE, DRILLY_SIZE))

    if avg_time := state_info.average_time_ms:
        time = randint(int(avg_time * 0.5), int(avg_time * 1.5))
        verbose_log(f"Next transition after {time} ms")
        drilly_timer = drilly_window.after(time, drilly_choose_and_update_state)
    else:
        while voice_line := choice(state_info.voice_lines):
            if not voice_line.can_play_now():
                continue
            drilly_sound = playsound(VOICE_BASE_DIR / voice_line.file, block=False)
            if voice_line.text:
                create_dialog_window(voice_line.text)
            break
        drilly_timer = drilly_window.after(VOICE_DURATION, drilly_choose_and_update_state)
        verbose_log(f"Next transition after {VOICE_DURATION} ms")

def drilly_choose_and_update_state():
    drilly_choose_new_state()
    drilly_update_state()

# has the added effect of waking up the thread at least every second to accept signals
def update_temperature():
    global current_temp
    current_temp = psutil.sensors_temperatures()[TEMP_SENSOR][0].current
    drilly_window.after(1000, update_temperature)

last_pos = None
distance_covered = 0
distance_timer = None

def motion_timeout():
    global last_pos, distance_covered, distance_timer, drilly_state
    if distance_covered > PATTING_VELOCITY_THRESHOLD:
        drilly_state = "noises"
        drilly_update_state()
    distance_timer = None
    distance_covered = 0
    last_pos = None

def cursor_motion(event):
    global last_pos, distance_covered, distance_timer
    x = event.x
    y = event.y
    if last_pos:
        last_x, last_y = last_pos
        distance = sqrt(((x - last_x) ** 2) + ((y - last_y) ** 2))
        distance_covered += distance
        if not distance_timer:
            distance_timer = drilly_window.after(1000, motion_timeout)
    last_pos = (x, y)

drilly_img.bind("<Motion>", cursor_motion)

drilly_update_state()
update_temperature()

try:
    drilly_window.mainloop()
except KeyboardInterrupt:
    pass

playsound(VOICE_BASE_DIR / EXIT_VOICE)
