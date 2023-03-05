# CircuitPython 8
import board
from analogio import AnalogIn
import digitalio
import neopixel
import time

from adafruit_led_animation.animation.comet import Comet
from adafruit_led_animation.animation.chase import Chase
from adafruit_led_animation.sequence import AnimationSequence
from adafruit_led_animation.color import PURPLE, JADE
from adafruit_led_animation.helper import PixelMap
from adafruit_led_animation.animation.rainbow import Rainbow
from adafruit_led_animation.animation.rainbowchase import RainbowChase
from adafruit_led_animation.animation.rainbowcomet import RainbowComet
from adafruit_led_animation.group import AnimationGroup
from adafruit_led_animation.animation.rainbowsparkle import RainbowSparkle
from adafruit_neopxl8 import NeoPxl8
from adafruit_debouncer import Debouncer


print("Hello, Scorpio:\n https://learn.adafruit.com/introducing-feather-rp2040-scorpio")
print(dir(board))
time.sleep(1)


class PairChase(Chase):
    def __init__(
        self, pixel_object, speed, color, size=2, spacing=3, reverse=False, name=None
    ):
        super().__init__(
            pixel_object,
            speed,
            color,
            size=size,
            spacing=spacing,
            reverse=reverse,
            name=name,
        )

    @staticmethod
    def make_space(red, green, blue):
        off_thresh = 20
        on_thresh = 220
        if red > on_thresh and blue < off_thresh and green < off_thresh:
            space = (0, 0, 255)
        elif blue > on_thresh and red < off_thresh and green < off_thresh:
            space = (255, 100, 0)
        elif green > on_thresh and red < off_thresh and blue < off_thresh:
            space = (180, 0, 255)
        elif red > on_thresh and blue > on_thresh and green < off_thresh:
            space = (10, 10, 255)
        elif (
            red > min(on_thresh + 10, 255)
            and green > min(on_thresh + 10, 255)
            and blue > min(on_thresh + 10, 255)
        ):
            # eliminate the noise that is occurring due to pots when all are all the way on
            space = (0, 0, 0)
        else:
            space = (255 - red, 255 - green, 255 - blue)
        return space

    def space_color(self, n, pixel_no=0):
        if isinstance(self.color[0], int):
            space_color = self.make_space(*self.color)
        else:
            space_color = (255, 0, 0)
        return space_color


class RollingValue:
    def __init__(self, window_size=20, precision=2):
        self._values = list()
        self.window_size = window_size
        self.precision = precision
        return

    @property
    def value(self):
        mean = sum(self._values) / len(self._values)
        if self.precision == 0:
            return int(mean)
        else:
            return round(mean, self.precision)

    @value.setter
    def value(self, val):
        while len(self._values) > self.window_size:
            self._values.pop(0)
        if self.precision == 0:
            self._values.append(int(val))
        else:
            self._values.append(val)
        return


def setup_pots():
    print("calling setup_pots")
    brightness = AnalogIn(board.A0)
    red = AnalogIn(board.A1)
    green = AnalogIn(board.A2)
    blue = AnalogIn(board.A3)
    return (brightness, red, green, blue)


def setup_button():
    print("calling setup_button")
    button = digitalio.DigitalInOut(board.SCK)
    button.direction = digitalio.Direction.INPUT
    button.pull = digitalio.Pull.UP
    debounced_button = Debouncer(button)
    return debounced_button


def strand(pixels, strand_idx, strand_len):
    return PixelMap(
        pixels,
        range(strand_idx * strand_len, (strand_idx + 1) * strand_len),
        individual_pixels=True,
    )


def setup_strands(pin_a, brightness, n=2, strand_len=60):
    print("calling setup_strands")
    npixels = n * strand_len
    pixels = NeoPxl8(
        pin_a, npixels, num_strands=n, auto_write=False, brightness=brightness
    )
    strands = [strand(pixels, idx, strand_len) for idx in range(n)]
    return (strands, pixels)


def set_rgb_led(rg_led, b_led, value):
    rg_led.value = value
    b_led.value = value
    return (rg_led, b_led)


def turn_on_rgb_led():
    rg_led = digitalio.DigitalInOut(board.D24)
    rg_led.direction = digitalio.Direction.OUTPUT
    rg_led.value = True

    b_led = digitalio.DigitalInOut(board.D25)
    b_led.direction = digitalio.Direction.OUTPUT
    b_led.value = True

    return (rg_led, b_led)


def power_up_led():
    led = digitalio.DigitalInOut(board.LED)
    led.direction = digitalio.Direction.OUTPUT
    led.value = True
    return led


power_up_led()
print(f"Main Logic: {time.monotonic()}")

(brightness_pot, red_pot, green_pot, blue_pot) = setup_pots()
(rg_led, b_led) = turn_on_rgb_led()
button = setup_button()

(strands, pixels) = setup_strands(board.NEOPIXEL0, brightness=0.55)
pixels.fill((0, 0, 0))
pixels.show()

# Say hello to my lil friend
neopix = neopixel.NeoPixel(board.NEOPIXEL, 1)
neopix[0] = (0, 0, 255)
time.sleep(0.5)
neopix[0] = (255, 0, 0)
time.sleep(0.5)
neopix[0] = (0, 255, 0)
time.sleep(0.5)
neopix[0] = (255, 255, 255)
time.sleep(0.5)

chase_idx = -1
num_strands = 2

last_paint_time = -1

PAUSE_SECS = 0.25
ANIMATION_1_PAUSE_SECS = 0.05
ANIMATION_2_PAUSE_SECS = ANIMATION_1_PAUSE_SECS / 2
TWO_COLOR_PAUSE_SECS = 0.75
TWO_COLOR_IS_PRIMARY = True

COMET_SPEED = 0.025
CHASE_SPEED = 0.15
CHASE_SPEED_2 = 0.25

ANIMATION_IDX = 7
N_ANIMATIONS = 9
POWER_SAFE_ANIMATIONS = [3, 4, 5, 6, 7]

rolling_brightness = RollingValue(precision=2)
rolling_red = RollingValue(precision=0)
rolling_green = RollingValue(precision=0)
rolling_blue = RollingValue(precision=0)

animations = []
pair_chase_animations = []
color_chunk_chase_animations = []
chase_animations = []
for strand in strands:
    chase = Chase(strand, speed=CHASE_SPEED, size=3, spacing=6, color=(0, 0, 0))
    comet = Comet(strand, COMET_SPEED, (255, 20, 20), tail_length=10, ring=True)
    animations.append(chase)
    animations.append(comet)
    chase_animations.append(Chase(strand, CHASE_SPEED_2, (255, 255, 255)))
    pair_chase_animations.append(
        PairChase(strand, CHASE_SPEED_2, (0, 0, 0), size=3, spacing=2)
    )
    color_chunk_chase_animations.append(
        Chase(strand, CHASE_SPEED_2, (0, 0, 0), size=20, spacing=7)
    )
chase = AnimationGroup(*chase_animations)
pair_chase = AnimationGroup(*pair_chase_animations)
color_chunk_chase = AnimationGroup(*color_chunk_chase_animations)


for i, animation in enumerate(animations):
    if i % 2 != 0:
        animation._tail_start = 60 * 5 * i // 8

animation_group = AnimationGroup(*animations)

rainbow = Rainbow(pixels, speed=0.1, period=4)
rainbow_chase = RainbowChase(pixels, speed=CHASE_SPEED, size=20, spacing=6)
rainbow_comet = RainbowComet(pixels, speed=0.025, tail_length=69, bounce=True)
rainbow_sparkle = RainbowSparkle(pixels, speed=0.1, num_sparkles=15)


rainbow_animations = AnimationSequence(
    rainbow,
    rainbow_chase,
    rainbow_comet,
    rainbow_sparkle,
    advance_interval=20,
    auto_clear=True,
)

strandbows = []
for strand in strands:
    a = Rainbow(strand, 0.1)
    strandbows.append(a)
strandbows = AnimationGroup(*strandbows)


print("entering main loop")
while True:
    now = time.monotonic()
    button.update()
    if button.rose:
        print("just released")
        chase_idx = 0
        if ANIMATION_IDX == N_ANIMATIONS:
            ANIMATION_IDX = 1
            pixels.fill((0, 0, 0))
            pixels.show()
            continue
        else:
            ANIMATION_IDX += 1
            pixels.fill((0, 0, 0))
            pixels.show()
            continue

    if ANIMATION_IDX in POWER_SAFE_ANIMATIONS:
        rolling_brightness.value = round(brightness_pot.value / 65_535, 3)
    else:
        rolling_brightness.value = round(brightness_pot.value / (65_535 / 0.7), 3)

    brightness = float(rolling_brightness.value)

    rolling_red.value = min(int(red_pot.value / 255), 255)
    rolling_green.value = min(int(green_pot.value / 255), 255)
    rolling_blue.value = min(int(blue_pot.value / 255), 255)
    color = (rolling_red.value, rolling_green.value, rolling_blue.value)
    inverse_color = [255 - c for c in color]

    button_val = button.value

    if chase_idx % 25 == 0:
        pass
        # print(
        #     f"{chase_idx=} :: {ANIMATION_IDX=} :: {brightness=} :: {button_val=} "
        #     + f":: ({rolling_red.value}, {rolling_green.value}, {rolling_blue.value})\n"
        # )

    if ANIMATION_IDX == 1 and now > (ANIMATION_1_PAUSE_SECS + last_paint_time):
        (rg_led, b_led) = set_rgb_led(rg_led, b_led, True)
        if chase_idx == (len(pixels) / num_strands) - 1:
            chase_idx = 0
        else:
            chase_idx += 1
        neopix.brightness = brightness
        neopix[0] = color
        strands[0][chase_idx] = color
        strands[1][chase_idx] = color
        pixels.brightness = brightness
        pixels.show()
        last_paint_time = now
    elif ANIMATION_IDX == 2 and now > (ANIMATION_2_PAUSE_SECS + last_paint_time):
        (rg_led, b_led) = set_rgb_led(rg_led, b_led, True)
        if chase_idx == len(pixels) - 1:
            chase_idx = 0
        else:
            chase_idx += 1
        neopix.brightness = brightness
        neopix[0] = color
        pixels[chase_idx] = color
        pixels.brightness = brightness
        pixels.show()
        last_paint_time = now
    elif ANIMATION_IDX == 3 and now > (PAUSE_SECS + last_paint_time):
        (rg_led, b_led) = set_rgb_led(rg_led, b_led, True)
        if chase_idx == (len(pixels) / num_strands) - 1:
            chase_idx = 0
        else:
            chase_idx += 1
        neopix.brightness = brightness
        neopix[0] = color
        pixels.brightness = brightness
        animation_group.color = color
        animation_group.animate()
        pixels.show()
    elif ANIMATION_IDX == 4:
        (rg_led, b_led) = set_rgb_led(rg_led, b_led, True)
        if chase_idx == (len(pixels) / num_strands) - 1:
            chase_idx = 0
        else:
            chase_idx += 1
        if now > (TWO_COLOR_PAUSE_SECS + last_paint_time):
            if TWO_COLOR_IS_PRIMARY == True:
                neopix[0] = inverse_color
                TWO_COLOR_IS_PRIMARY = False
            else:
                neopix[0] = color
                TWO_COLOR_IS_PRIMARY = True
            last_paint_time = now

        neopix.brightness = brightness
        pixels.brightness = brightness
        # animations.color = color
        for i, animation in enumerate(animations):
            if i % 2 != 0:
                animation.color = color
            else:
                animation.color = inverse_color
            animation.animate()
        # animations.animate()
        pixels.show()
    elif ANIMATION_IDX == 5:
        if now > (PAUSE_SECS * 4 + last_paint_time):
            if rg_led.value == True:
                (rg_led, b_led) = set_rgb_led(rg_led, b_led, False)
            else:
                (rg_led, b_led) = set_rgb_led(rg_led, b_led, True)
            last_paint_time = now
        neopix[0] = (25, 25, 255)
        neopix.brightness = brightness
        pixels.brightness = brightness
        rainbow_animations.animate()
        pixels.show()
    elif ANIMATION_IDX == 6:
        if now > (PAUSE_SECS * 4 + last_paint_time):
            if rg_led.value == True:
                (rg_led, b_led) = set_rgb_led(rg_led, b_led, False)
            else:
                (rg_led, b_led) = set_rgb_led(rg_led, b_led, True)
            last_paint_time = now
        neopix[0] = (255, 25, 25)
        neopix.brightness = brightness
        pixels.brightness = brightness
        # rainbow.animate()
        strandbows.animate()
        pixels.show()
    elif ANIMATION_IDX == 7:
        (rg_led, b_led) = set_rgb_led(rg_led, b_led, True)
        neopix[0] = color
        neopix.brightness = brightness
        pixels.brightness = brightness
        chase.color = color
        chase.animate()
        pixels.show()
    elif ANIMATION_IDX == 8:
        (rg_led, b_led) = set_rgb_led(rg_led, b_led, True)
        if now > (TWO_COLOR_PAUSE_SECS + last_paint_time):
            if TWO_COLOR_IS_PRIMARY == True:
                neopix[0] = inverse_color
                TWO_COLOR_IS_PRIMARY = False
            else:
                neopix[0] = color
                TWO_COLOR_IS_PRIMARY = True
            last_paint_time = now
        neopix.brightness = brightness
        pixels.brightness = brightness
        pair_chase.color = color
        pair_chase.animate()
        pixels.show()
    elif ANIMATION_IDX == 9:
        (rg_led, b_led) = set_rgb_led(rg_led, b_led, True)
        neopix[0] = color
        neopix.brightness = brightness
        pixels.brightness = brightness
        color_chunk_chase.color = color
        color_chunk_chase.animate()
        pixels.show()

    else:
        pass
