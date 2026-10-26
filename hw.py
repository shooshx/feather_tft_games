# hw.py - shared hardware for all games:
#   display, the I2C gamepad (seesaw), the D0/D1/D2 side buttons and frame timing.
import time
import board
import displayio
import keypad
from micropython import const

display = board.DISPLAY
display.auto_refresh = False   # we call display.refresh() once per frame
W = display.width              # 240
H = display.height             # 135

# ---------------------------------------------------------------- gamepad
# Bit numbers of the buttons on the Mini I2C Gamepad (seesaw @ 0x50)
_X = const(6)
_Y = const(2)
_A = const(5)
_B = const(1)
_SELECT = const(0)
_START = const(16)

# Use these masks in games: pad.tap(hw.A), pad.held(hw.B) ...
X = 1 << _X
Y = 1 << _Y
A = 1 << _A
B = 1 << _B
SELECT = 1 << _SELECT
START = 1 << _START
_MASK = X | Y | A | B | SELECT | START

# If the joystick moves things the wrong way, flip these:
FLIP_X = False
FLIP_Y = False
DEAD_ZONE = 0.18        # ignore small stick movements around the center
SEESAW_DELAY = 0.002    # seconds per I2C read (library default is 0.008 = slow)


class Pad:
    """Gamepad state. x/y are -1..1 (x: right is +, y: down is +, like the screen)."""

    def __init__(self):
        self.ok = False
        self.down = 0       # buttons held now
        self.pressed = 0    # buttons that went down this frame
        self.released = 0   # buttons that went up this frame
        self.x = 0.0
        self.y = 0.0
        self.cx = 512
        self.cy = 512
        self.turn = 0       # see rotate()
        try:
            from adafruit_seesaw.seesaw import Seesaw
            self.ss = Seesaw(i2c(), addr=0x50)
            self.ss.pin_mode_bulk(_MASK, self.ss.INPUT_PULLUP)
            # calibrate the stick center (assumes nobody touches it at boot)
            sx = sy = 0
            for _ in range(4):
                ax, ay = self._read_stick()
                sx += ax
                sy += ay
            self.cx = sx // 4
            self.cy = sy // 4
            self.ok = True
        except Exception as e:  # no gamepad plugged in - menu still works
            print("Gamepad not found:", e)

    def _read_stick(self):
        ax = 1023 - self.ss.analog_read(14, delay=SEESAW_DELAY)
        ay = 1023 - self.ss.analog_read(15, delay=SEESAW_DELAY)
        return ax, ay

    @staticmethod
    def _norm(v):
        v = v / 400
        if v > 1:
            v = 1.0
        elif v < -1:
            v = -1.0
        if -DEAD_ZONE < v < DEAD_ZONE:
            return 0.0
        if v > 0:
            return (v - DEAD_ZONE) / (1 - DEAD_ZONE)
        return (v + DEAD_ZONE) / (1 - DEAD_ZONE)

    def update(self):
        if not self.ok:
            return
        try:
            raw = self.ss.digital_read_bulk(_MASK, delay=SEESAW_DELAY)
            ax, ay = self._read_stick()
        except (OSError, RuntimeError):
            return
        down = ~raw & _MASK
        self.pressed = down & ~self.down
        self.released = self.down & ~down
        self.down = down
        x = self._norm(ax - self.cx)
        y = -self._norm(ay - self.cy)
        if FLIP_X:
            x = -x
        if FLIP_Y:
            y = -y
        # when the device (and the gamepad) is turned, turn the stick too
        if self.turn == 270:
            x, y = -y, x
        elif self.turn == 90:
            x, y = y, -x
        elif self.turn == 180:
            x, y = -x, -y
        self.x = x
        self.y = y

    def tap(self, mask):
        """True only in the frame the button was pressed."""
        return bool(self.pressed & mask)

    def held(self, mask):
        return bool(self.down & mask)


# ----------------------------------------------------------- side buttons
# D0 reads LOW when pressed, D1/D2 read HIGH when pressed.
class Side:
    def __init__(self):
        self._k0 = keypad.Keys((board.D0,), value_when_pressed=False, pull=True)
        self._k12 = keypad.Keys((board.D1, board.D2), value_when_pressed=True, pull=True)
        self._ev = keypad.Event()
        self.pressed = []   # side buttons (0, 1, 2) pressed since last update

    def update(self):
        p = []
        while self._k0.events.get_into(self._ev):
            if self._ev.pressed:
                p.append(0)
        while self._k12.events.get_into(self._ev):
            if self._ev.pressed:
                p.append(self._ev.key_number + 1)
        self.pressed = p


# ----------------------------------------------------------------- battery
class Battery:
    """The battery gauge chip on the Feather (MAX17048 at I2C address 0x36).
    percent() returns 0..100, or None when there is no gauge or no battery."""

    def __init__(self):
        self.dev = None
        self.buf = bytearray(2)
        try:
            from adafruit_bus_device.i2c_device import I2CDevice
            self.dev = I2CDevice(i2c(), 0x36)
        except Exception as e:
            print("No battery gauge:", e)

    def _read(self, reg):
        with self.dev:
            self.dev.write_then_readinto(bytes((reg,)), self.buf)
        return (self.buf[0] << 8) | self.buf[1]

    def voltage(self):
        if self.dev is None:
            return None
        try:
            return self._read(0x02) * 78.125 / 1000000
        except OSError:
            return None

    def percent(self):
        if self.dev is None:
            return None
        try:
            v = self._read(0x02) * 78.125 / 1000000
            if v < 2.5:              # nothing plugged into the battery socket
                return None
            p = self._read(0x04) / 256
        except OSError:
            return None
        return max(0, min(100, int(p + 0.5)))

    def charging(self):
        """True when the battery is filling up.  Uses the gauge's charge rate
        (register 0x16, 0.208 % per hour per step, negative = draining)."""
        if self.dev is None:
            return False
        try:
            rate = self._read(0x16)
        except OSError:
            return False
        if rate >= 0x8000:
            rate -= 0x10000
        return rate * 0.208 > CHARGE_RATE_MIN


CHARGE_RATE_MIN = 0.5    # % per hour; above this we call it "charging"


_i2c = None


def i2c():
    """The I2C bus shared by the gamepad and the battery gauge."""
    global _i2c
    if _i2c is None:
        _i2c = board.STEMMA_I2C()
    return _i2c


pad = Pad()
side = Side()
battery = Battery()

# ----------------------------------------------------------------- frames
dt = 0.0          # seconds since the previous frame (use it to move things)
_last = time.monotonic_ns()


def show(group):
    """Put a group on the screen and restart the frame clock."""
    global _last
    display.root_group = group
    side.update()           # forget side buttons pressed earlier
    side.pressed = []
    _last = time.monotonic_ns()


def frame(fps=30):
    """Draw the frame, wait for the next one and read the inputs.
    Returns False when a side button was pressed (= go back to the menu)."""
    global _last, dt
    display.refresh()
    target = _last + 1000000000 // fps
    now = time.monotonic_ns()
    if now < target:
        time.sleep((target - now) / 1000000000)
        now = time.monotonic_ns()
    dt = (now - _last) / 1000000000
    if dt > 0.1:
        dt = 0.1
    _last = now
    pad.update()
    side.update()
    return not side.pressed


_base_rotation = display.rotation


def rotate(turn=0, pad_too=True):
    """Turn the picture for games played with the device on its side.
    turn=270: the screen's right edge becomes the bottom.  turn=0: back to normal.
    pad_too: the gamepad is turned together with the screen."""
    display.rotation = (_base_rotation + turn) % 360
    pad.turn = turn if pad_too else 0


def solid(w, h, color):
    """A plain rectangle sprite (TileGrid). Change its color with tg.pixel_shader[0]."""
    bmp = displayio.Bitmap(w, h, 1)
    pal = displayio.Palette(1)
    pal[0] = color
    return displayio.TileGrid(bmp, pixel_shader=pal)


def text(txt, x, y, color=0xFFFFFF, scale=1, anchor=(0, 0), bg=None):
    """A text label placed by its anchor point (0,0 = top-left, 0.5,0.5 = center)."""
    import terminalio
    from adafruit_display_text import label
    if bg is None:
        t = label.Label(terminalio.FONT, text=txt, color=color, scale=scale)
    else:
        t = label.Label(terminalio.FONT, text=txt, color=color, scale=scale,
                        background_color=bg, padding_left=3, padding_right=3,
                        padding_top=1, padding_bottom=1)
    t.anchor_point = anchor
    t.anchored_position = (x, y)
    return t


def banner(txt, color=0xFFFFFF, bg=0x202040, scale=2):
    """A centered message box (hidden = True to remove it)."""
    return text(txt, W // 2, H // 2, color, scale, (0.5, 0.5), bg)


def reseed():
    """Make random numbers random again (drawing code uses fixed seeds for its pictures)."""
    import random
    random.seed(time.monotonic_ns() & 0x7FFFFFFF)
