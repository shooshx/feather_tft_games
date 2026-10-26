"""Play the games on your PC.

    pip install pygame numpy
    python simulator/play.py          (run it from the test_game folder, or anywhere)

The real game files in the folder above run unchanged. This script swaps in fake
versions of the CircuitPython modules (board, displayio, keypad, the gamepad...)
that draw into a window and read the keyboard.

Keys
    arrows / WASD        joystick
    Space or K           A          L   B
    J                    X          I   Y
    Enter                START      Backspace   SELECT
    1  2  3              side buttons D0  D1  D2   (Esc = D0 as well)
"""
import os
import sys
import time
import types
import runpy

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
GAME_DIR = os.path.dirname(HERE)
W, H = 240, 135
ZOOM = 4

# --------------------------------------------------------------- input state
class Input:
    x = 0.0
    y = 0.0
    buttons = set()           # names: A B X Y START SELECT
    side_events = []          # side buttons pressed: 0, 1, 2


INPUT = Input()
FRONTEND = None               # set by main(): object with .present(rgb_array)


def _mod(name):
    m = types.ModuleType(name)
    sys.modules[name] = m
    return m


# ------------------------------------------------------------------ displayio
class Bitmap:
    def __init__(self, width, height, value_count):
        self.width = int(width)
        self.height = int(height)
        self.value_count = value_count
        self.a = np.zeros((self.height, self.width), np.uint16)

    def __getitem__(self, i):
        if isinstance(i, tuple):
            return int(self.a[i[1], i[0]])
        return int(self.a.flat[i])

    def __setitem__(self, i, v):
        if isinstance(i, tuple):
            x, y = i
            if not (0 <= x < self.width and 0 <= y < self.height):
                raise IndexError("pixel out of bounds")
            self.a[y, x] = v
        else:
            self.a.flat[i] = v

    def fill(self, v):
        self.a[:, :] = v

    def dirty(self, *a):
        pass


class Palette:
    def __init__(self, color_count, *, dither=False):
        self.rgb = np.zeros((color_count, 3), np.uint8)
        self.clear = np.zeros(color_count, bool)
        self.raw = [0] * color_count

    def __len__(self):
        return len(self.raw)

    def __setitem__(self, i, c):
        if isinstance(c, (tuple, list)):
            c = (c[0] << 16) | (c[1] << 8) | c[2]
        self.raw[i] = c
        self.rgb[i] = ((c >> 16) & 255, (c >> 8) & 255, c & 255)

    def __getitem__(self, i):
        return self.raw[i]

    def make_transparent(self, i):
        self.clear[i] = True

    def make_opaque(self, i):
        self.clear[i] = False

    def is_transparent(self, i):
        return bool(self.clear[i])


def _blit(fb, rgb, mask, x, y):
    """Copy rgb (h,w,3) where mask is True into framebuffer at x,y with clipping."""
    h, w = mask.shape
    fh, fw = fb.shape[:2]
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(fw, x + w), min(fh, y + h)
    if x0 >= x1 or y0 >= y1:
        return
    sub_m = mask[y0 - y:y1 - y, x0 - x:x1 - x]
    sub_c = rgb[y0 - y:y1 - y, x0 - x:x1 - x]
    region = fb[y0:y1, x0:x1]
    region[sub_m] = sub_c[sub_m]


class TileGrid:
    def __init__(self, bitmap, *, pixel_shader, width=1, height=1, tile_width=None,
                 tile_height=None, default_tile=0, x=0, y=0):
        self.bitmap = bitmap
        self.pixel_shader = pixel_shader
        self.width = width
        self.height = height
        self.tile_width = tile_width or bitmap.width
        self.tile_height = tile_height or bitmap.height
        self.tiles = [default_tile] * (width * height)
        self.x = int(x)
        self.y = int(y)
        self.hidden = False
        self.flip_x = False
        self.flip_y = False
        self.transpose_xy = False

    def _idx(self, i):
        if isinstance(i, tuple):
            return i[1] * self.width + i[0]
        return i

    def __getitem__(self, i):
        return self.tiles[self._idx(i)]

    def __setitem__(self, i, v):
        self.tiles[self._idx(i)] = int(v)

    def contains(self, t):
        return (self.x <= t[0] < self.x + self.width * self.tile_width and
                self.y <= t[1] < self.y + self.height * self.tile_height)

    def draw(self, fb, ox, oy, scale):
        if self.hidden:
            return
        tw, th = self.tile_width, self.tile_height
        per_row = self.bitmap.width // tw
        pal = self.pixel_shader
        src_all = self.bitmap.a
        for ty in range(self.height):
            for tx in range(self.width):
                t = self.tiles[ty * self.width + tx]
                sx = (t % per_row) * tw
                sy = (t // per_row) * th
                src = src_all[sy:sy + th, sx:sx + tw]
                if self.flip_x:
                    src = src[:, ::-1]
                if self.flip_y:
                    src = src[::-1, :]
                mask = ~pal.clear[src]
                rgb = pal.rgb[src]
                if scale != 1:
                    mask = mask.repeat(scale, 0).repeat(scale, 1)
                    rgb = rgb.repeat(scale, 0).repeat(scale, 1)
                _blit(fb, rgb, mask, ox + (self.x + tx * tw) * scale,
                      oy + (self.y + ty * th) * scale)


class Group:
    def __init__(self, *, scale=1, x=0, y=0):
        self.scale = scale
        self.x = int(x)
        self.y = int(y)
        self.hidden = False
        self._items = []

    def append(self, o):
        self._items.append(o)

    def insert(self, i, o):
        self._items.insert(i, o)

    def remove(self, o):
        self._items.remove(o)

    def pop(self, i=-1):
        return self._items.pop(i)

    def index(self, o):
        return self._items.index(o)

    def __len__(self):
        return len(self._items)

    def __getitem__(self, i):
        return self._items[i]

    def __setitem__(self, i, o):
        self._items[i] = o

    def __delitem__(self, i):
        del self._items[i]

    def __contains__(self, o):
        return o in self._items

    def __iter__(self):
        return iter(self._items)

    def __bool__(self):
        return True

    def draw(self, fb, ox, oy, scale):
        if self.hidden:
            return
        ox += self.x * scale
        oy += self.y * scale
        scale *= self.scale
        for it in self._items:
            it.draw(fb, ox, oy, scale)


# ---------------------------------------------------------------------- text
# The real terminalio.FONT is Terminus 6x12. These are its glyphs for ASCII 32..126,
# 12 rows per character, one byte per row (top 6 bits used).
_TERMINUS = bytes.fromhex(
    "00000000000000000000000000002020202020002020000000505050000000000000000000005050f85050f850500000"
    "00002070a8a07028a8702000000048a85010202854480000000020505020689090680000002020200000000000000000"
    "000010204040404020100000000040201010101020400000000000005020f82050000000000000002020f82020000000"
    "000000000000000020204000000000000000f80000000000000000000000000020200000000008081010202040400000"
    "0000708898a8c88888700000000020602020202020700000000070888808102040f80000000070880830080888700000"
    "00000818284888f8080800000000f88080f00808887000000000708080f08888887000000000f8080810102020200000"
    "000070888870888888700000000070888888780808700000000000002020000020200000000000002020000020204000"
    "00000008102040201008000000000000f80000f800000000000000402010081020400000000070888810200020200000"
    "0000708898a8a89880780000000070888888f888888800000000f08888f0888888f00000000070888080808088700000"
    "0000e0908888888890e000000000f88080f0808080f800000000f88080f0808080800000000070888080b88888700000"
    "0000888888f888888888000000007020202020202070000000003810101010909060000000008890a0c0c0a090880000"
    "000080808080808080f80000000088d8a8a888888888000000008888c8a8988888880000000070888888888888700000"
    "0000f0888888f080808000000000708888888888a87008000000f0888888f0a090880000000070888070080888700000"
    "0000f8202020202020200000000088888888888888700000000088888850505020200000000088888888a8a8d8880000"
    "0000888850202050888800000000888850502020202000000000f8081020408080f80000000070404040404040700000"
    "00004040202010100808000000007010101010101070000000205088000000000000000000000000000000000000f800"
    "40200000000000000000000000000000700878888878000000008080f088888888f00000000000007088808088700000"
    "000008087888888888780000000000007088f88080780000000018207020202020200000000000007888888888780870"
    "00008080f088888888880000002020006020202020700000000808001808080808084830000040404850606050480000"
    "00006020202020202070000000000000f0a8a8a8a8a8000000000000f088888888880000000000007088888888700000"
    "00000000f088888888f0808000000000788888888878080800000000b8c0808080800000000000007880700808f00000"
    "000020207020202020180000000000008888888888780000000000008888505020200000000000008888a8a8a8700000"
    "00000000885020205088000000000000888888888878087000000000f810204080f80000000018202040202020180000"
    "000020202020202020200000000060101008101010600000000000000048a89000000000"
)
LINE_SPACING = 15        # adafruit_display_text default: 1.25 * 12
_TEXT_CACHE = {}


def _text_mask(txt):
    """A (h, w) bool array of txt drawn with the terminalio font."""
    if txt in _TEXT_CACHE:
        return _TEXT_CACHE[txt]
    lines = txt.split("\n")
    cols = max(len(l) for l in lines)
    mask = np.zeros((12 + LINE_SPACING * (len(lines) - 1), 6 * max(1, cols)), bool)
    for li, line in enumerate(lines):
        for ci, ch in enumerate(line):
            code = ord(ch)
            if not 32 <= code < 127:
                code = ord("?")
            g = _TERMINUS[(code - 32) * 12:(code - 31) * 12]
            for row, bits in enumerate(g):
                for b in range(6):
                    if bits & (0x80 >> b):
                        mask[li * LINE_SPACING + row, ci * 6 + b] = True
    _TEXT_CACHE[txt] = mask
    return mask


class Label:
    def __init__(self, font=None, *, text="", color=0xFFFFFF, scale=1, background_color=None,
                 padding_left=0, padding_right=0, padding_top=0, padding_bottom=0,
                 anchor_point=None, anchored_position=None, x=0, y=0, **kw):
        self._text = text
        self.color = color
        self.scale = scale
        self.background_color = background_color
        self.pad = (padding_left, padding_right, padding_top, padding_bottom)
        self.hidden = False
        self.x = x
        self.y = y
        self._ap = anchor_point
        self._apos = anchored_position
        self._place()

    def _size(self):
        lines = self._text.split("\n")
        w = 6 * max(len(l) for l in lines) + self.pad[0] + self.pad[1]
        h = 12 + LINE_SPACING * (len(lines) - 1) + self.pad[2] + self.pad[3]
        return w, h

    def _place(self):
        if self._ap is None or self._apos is None:
            return
        w, h = self._size()
        self.x = int(round(self._apos[0] - self._ap[0] * w * self.scale))
        self.y = int(round(self._apos[1] - self._ap[1] * h * self.scale)) + (h * self.scale) // 2

    @property
    def text(self):
        return self._text

    @text.setter
    def text(self, t):
        self._text = str(t)
        self._place()

    @property
    def anchor_point(self):
        return self._ap

    @anchor_point.setter
    def anchor_point(self, v):
        self._ap = v
        self._place()

    @property
    def anchored_position(self):
        return self._apos

    @anchored_position.setter
    def anchored_position(self, v):
        self._apos = v
        self._place()

    @property
    def bounding_box(self):
        w, h = self._size()
        return (0, -h // 2, w, h)

    @property
    def width(self):
        return self._size()[0]

    @property
    def height(self):
        return self._size()[1]

    def draw(self, fb, ox, oy, scale):
        if self.hidden or not self._text:
            return
        s = scale * self.scale
        w, h = self._size()
        top = oy + (self.y * scale) - (h * s) // 2
        left = ox + self.x * scale
        if self.background_color is not None:
            c = self.background_color
            bg = np.empty((h * s, w * s, 3), np.uint8)
            bg[:] = ((c >> 16) & 255, (c >> 8) & 255, c & 255)
            _blit(fb, bg, np.ones((h * s, w * s), bool), left, top)
        m = _text_mask(self._text)
        if s != 1:
            m = m.repeat(s, 0).repeat(s, 1)
        c = self.color
        rgb = np.empty(m.shape + (3,), np.uint8)
        rgb[:] = ((c >> 16) & 255, (c >> 8) & 255, c & 255)
        _blit(fb, rgb, m, left + self.pad[0] * s, top + self.pad[2] * s)


# ------------------------------------------------------- the fake board etc.
class Display:
    """The 240x135 screen.  rotation 90/270 makes it 135x240 (device turned).
    The simulator window always shows the picture upright."""

    def __init__(self):
        self.root_group = None
        self.auto_refresh = True
        self.rotation = 0
        self.brightness = 1.0

    @property
    def width(self):
        return H if self.rotation in (90, 270) else W

    @property
    def height(self):
        return W if self.rotation in (90, 270) else H

    def refresh(self, *a, **kw):
        fb = np.zeros((self.height, self.width, 3), np.uint8)
        if self.root_group is not None:
            self.root_group.draw(fb, 0, 0, 1)
        if FRONTEND is not None:
            FRONTEND.present(fb)
        return True


def install_fakes():
    board = _mod("board")
    board.DISPLAY = Display()
    board.D0, board.D1, board.D2 = "D0", "D1", "D2"
    board.STEMMA_I2C = lambda: "i2c"
    board.I2C = lambda: "i2c"

    dio = _mod("displayio")
    dio.Bitmap = Bitmap
    dio.Palette = Palette
    dio.TileGrid = TileGrid
    dio.Group = Group
    dio.release_displays = lambda: None

    _mod("terminalio").FONT = "terminalio"
    _mod("micropython").const = lambda v: v

    bt = _mod("bitmaptools")

    def fill_region(bmp, x1, y1, x2, y2, value):
        x1, x2 = sorted((x1, x2))
        y1, y2 = sorted((y1, y2))
        bmp.a[max(0, y1):max(0, min(bmp.height, y2)), max(0, x1):max(0, min(bmp.width, x2))] = value

    def draw_line(bmp, x1, y1, x2, y2, value):
        n = max(abs(x2 - x1), abs(y2 - y1))
        for i in range(n + 1):
            t = i / n if n else 0
            x = round(x1 + (x2 - x1) * t)
            y = round(y1 + (y2 - y1) * t)
            if 0 <= x < bmp.width and 0 <= y < bmp.height:
                bmp.a[y, x] = value

    bt.fill_region = fill_region
    bt.draw_line = draw_line

    kp = _mod("keypad")

    class Event:
        def __init__(self, key_number=0, pressed=True):
            self.key_number = key_number
            self.pressed = pressed
            self.released = not pressed

    class _Events:
        def __init__(self, pins):
            self.pins = pins

        def get_into(self, ev):
            for i, b in enumerate(INPUT.side_events):
                name = "D%d" % b
                if name in self.pins:
                    INPUT.side_events.pop(i)
                    ev.key_number = self.pins.index(name)
                    ev.pressed = True
                    ev.released = False
                    return True
            return False

        def get(self):
            ev = Event()
            return ev if self.get_into(ev) else None

        def clear(self):
            pass

    class Keys:
        def __init__(self, pins, *, value_when_pressed, pull=True, **kw):
            self.events = _Events(list(pins))

    kp.Event = Event
    kp.Keys = Keys

    pkg = _mod("adafruit_display_text")
    pkg.__path__ = []
    lab = _mod("adafruit_display_text.label")
    lab.Label = Label
    pkg.label = lab
    bl = _mod("adafruit_display_text.bitmap_label")
    bl.Label = Label
    pkg.bitmap_label = bl

    # pretend battery gauge (MAX17048): 76% at 3.9 V, charging at +5 %/hour
    bd = _mod("adafruit_bus_device")
    bd.__path__ = []
    i2cd = _mod("adafruit_bus_device.i2c_device")

    class I2CDevice:
        REGS = {0x02: int(3.9 / 78.125e-6), 0x04: 76 * 256, 0x16: int(5 / 0.208)}

        def __init__(self, i2c, addr, probe=True):
            self.addr = addr

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def write_then_readinto(self, out, buf, **kw):
            v = self.REGS.get(out[0], 0)
            buf[0] = (v >> 8) & 255
            buf[1] = v & 255

    i2cd.I2CDevice = I2CDevice
    bd.i2c_device = i2cd

    ss_pkg = _mod("adafruit_seesaw")
    ss_pkg.__path__ = []
    ss = _mod("adafruit_seesaw.seesaw")
    bits = dict(X=6, Y=2, A=5, B=1, SELECT=0, START=16)

    class Seesaw:
        INPUT_PULLUP = 2

        def __init__(self, i2c, addr=0x49, **kw):
            pass

        def pin_mode_bulk(self, mask, mode):
            pass

        def digital_read_bulk(self, mask, delay=0.008):
            v = mask
            for b in INPUT.buttons:
                v &= ~(1 << bits[b])
            return v

        def analog_read(self, pin, delay=0.008):
            # matches hw.py: x = 1023 - raw, screen y = -(1023 - raw - center)
            if pin == 14:
                return int(511 - 400 * INPUT.x)
            return int(511 + 400 * INPUT.y)

    ss.Seesaw = Seesaw
    ss_pkg.seesaw = ss


def set_stick(kx, ky):
    """Keyboard arrows are in the upright picture's frame. When the device is turned
    (display.rotation 90/270) the gamepad is turned with it, so convert back to the
    gamepad's own frame - hw.py turns it upright again."""
    r = sys.modules["board"].DISPLAY.rotation
    if r == 270:
        INPUT.x, INPUT.y = ky, -kx
    elif r == 90:
        INPUT.x, INPUT.y = -ky, kx
    elif r == 180:
        INPUT.x, INPUT.y = -kx, -ky
    else:
        INPUT.x, INPUT.y = kx, ky


# ------------------------------------------------------------ pygame window
class PygameFrontend:
    HELP = ("arrows/WASD: stick   Space/K: A   L: B   J: X   I: Y   "
            "Enter: Start   1/2/3: D0/D1/D2   Esc: back")

    def __init__(self):
        import pygame
        self.pg = pygame
        pygame.init()
        self.screen = pygame.display.set_mode((W * ZOOM, H * ZOOM + 28))
        pygame.display.set_caption("Feather game box simulator")
        self.font = pygame.font.SysFont("arial", 14)
        self.surf = pygame.Surface((W, H))
        self.keymap = {
            pygame.K_SPACE: "A", pygame.K_k: "A", pygame.K_l: "B",
            pygame.K_j: "X", pygame.K_i: "Y",
            pygame.K_RETURN: "START", pygame.K_BACKSPACE: "SELECT",
        }
        self.side = {pygame.K_1: 0, pygame.K_2: 1, pygame.K_3: 2, pygame.K_ESCAPE: 0}

    def present(self, fb):
        pg = self.pg
        for e in pg.event.get():
            if e.type == pg.QUIT:
                pg.quit()
                sys.exit(0)
            if e.type == pg.KEYDOWN and e.key in self.side:
                INPUT.side_events.append(self.side[e.key])
        keys = pg.key.get_pressed()
        INPUT.buttons = {name for k, name in self.keymap.items() if keys[k]}
        kx = float((keys[pg.K_RIGHT] or keys[pg.K_d]) - (keys[pg.K_LEFT] or keys[pg.K_a]))
        ky = float((keys[pg.K_DOWN] or keys[pg.K_s]) - (keys[pg.K_UP] or keys[pg.K_w]))
        set_stick(kx, ky)

        h, w = fb.shape[:2]
        size = (w * ZOOM, h * ZOOM + 28)
        if self.screen.get_size() != size:
            self.screen = pg.display.set_mode(size)
            self.surf = pg.Surface((w, h))
        pg.surfarray.blit_array(self.surf, fb.swapaxes(0, 1))
        self.screen.fill((30, 30, 30))
        self.screen.blit(pg.transform.scale(self.surf, (w * ZOOM, h * ZOOM)), (0, 0))
        help_text = self.HELP if w > h else "arrows: stick  Space: A  L: B  J: X  Esc: back"
        self.screen.blit(self.font.render(help_text, True, (200, 200, 200)), (8, h * ZOOM + 6))
        pg.display.flip()


class HeadlessFrontend:
    """For testing without a window: python play.py --headless 300 out.png"""

    def __init__(self, frames, out):
        self.left = frames
        self.out = out

    def present(self, fb):
        self.left -= 1
        if self.left <= 0:
            from PIL import Image
            h, w = fb.shape[:2]
            Image.fromarray(fb).resize((w * 3, h * 3), Image.NEAREST).save(self.out)
            raise SystemExit(0)


def main():
    global FRONTEND
    install_fakes()
    if len(sys.argv) > 1 and sys.argv[1] == "--headless":
        FRONTEND = HeadlessFrontend(int(sys.argv[2]), sys.argv[3])
    else:
        FRONTEND = PygameFrontend()
    sys.path.insert(0, GAME_DIR)
    os.chdir(GAME_DIR)
    runpy.run_path(os.path.join(GAME_DIR, "code.py"), run_name="__main__")


if __name__ == "__main__":
    main()
