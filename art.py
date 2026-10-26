# art.py - sprite drawing helpers and the shared color palette.
#
# Sprites are drawn either from text pictures (one character per pixel, see CHARS)
# or with little drawing functions (disk, ball, line...) into an Art canvas.
import math
import displayio

# ------------------------------------------------------------ master palette
# index: (char, color).  Index 0 / '.' is transparent.
COLORS = (
    ('.', 0x000000),  # 0 transparent
    ('K', 0x101010),  # 1 black
    ('W', 0xFFFFFF),  # 2 white
    ('R', 0xE8202A),  # 3 red
    ('r', 0x8C0A14),  # 4 dark red
    ('P', 0xFF9A9A),  # 5 pink
    ('G', 0x3CC23C),  # 6 green
    ('g', 0x16702A),  # 7 dark green
    ('N', 0x7A4A1A),  # 8 brown
    ('Y', 0xFFE23A),  # 9 yellow
    ('y', 0xC89A10),  # 10 dark yellow
    ('O', 0xFF8C1A),  # 11 orange
    ('o', 0xC05000),  # 12 dark orange
    ('V', 0x9A40E0),  # 13 purple
    ('v', 0x55188C),  # 14 dark purple
    ('L', 0xD8A8FF),  # 15 light purple
    ('M', 0xFF4A6A),  # 16 melon pink
    ('S', 0xC8C8C8),  # 17 light gray
    ('s', 0x808080),  # 18 gray
    ('d', 0x484848),  # 19 dark gray
    ('C', 0xA8F060),  # 20 light green
    ('B', 0x3A7AFF),  # 21 blue
    ('b', 0x1A3A9A),  # 22 dark blue
    ('c', 0x80E8FF),  # 23 cyan
    ('n', 0xC8873A),  # 24 light brown
    ('p', 0xFF5AC8),  # 25 hot pink
)
IDX = {}
for _i, (_ch, _c) in enumerate(COLORS):
    IDX[_ch] = _i
del _i, _ch, _c

# handy index names
T, K, WH, R, r, P, G, g, N, Y, y, O, o, V, v, L, M, S, s, d, C, BL, bl, CY, n, PK = range(26)

_master = None


def palette():
    """The shared palette (index 0 transparent)."""
    global _master
    if _master is None:
        _master = displayio.Palette(len(COLORS))
        for i, (_, c) in enumerate(COLORS):
            _master[i] = c
        _master.make_transparent(0)
    return _master


# ------------------------------------------------------------------- canvas
class Art:
    """A small canvas of palette indices."""

    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.p = bytearray(w * h)

    def px(self, x, y, c):
        x = int(x)
        y = int(y)
        if 0 <= x < self.w and 0 <= y < self.h:
            self.p[y * self.w + x] = c

    def get(self, x, y):
        if 0 <= x < self.w and 0 <= y < self.h:
            return self.p[y * self.w + x]
        return 0

    def text(self, rows, x0=0, y0=0):
        """Paste a text picture. '.' and ' ' are see-through."""
        for yy, row in enumerate(rows):
            for xx, ch in enumerate(row):
                if ch != '.' and ch != ' ':
                    self.px(x0 + xx, y0 + yy, IDX[ch])

    def rect(self, x0, y0, x1, y1, c):
        """Filled rectangle, x1/y1 inclusive."""
        for yy in range(y0, y1 + 1):
            for xx in range(x0, x1 + 1):
                self.px(xx, yy, c)

    def ellipse(self, cx, cy, rx, ry, c):
        for yy in range(max(0, int(cy - ry) - 1), min(self.h, int(cy + ry) + 2)):
            for xx in range(max(0, int(cx - rx) - 1), min(self.w, int(cx + rx) + 2)):
                dx = (xx + 0.5 - cx) / rx
                dy = (yy + 0.5 - cy) / ry
                if dx * dx + dy * dy <= 1:
                    self.p[yy * self.w + xx] = c

    def disk(self, cx, cy, rad, c):
        self.ellipse(cx, cy, rad, rad, c)

    def ball(self, cx, cy, rad, base, shade, hi, ry=None):
        """A shaded round thing (light comes from the top-left)."""
        ry = ry or rad
        for yy in range(max(0, int(cy - ry) - 1), min(self.h, int(cy + ry) + 2)):
            for xx in range(max(0, int(cx - rad) - 1), min(self.w, int(cx + rad) + 2)):
                nx = (xx + 0.5 - cx) / rad
                ny = (yy + 0.5 - cy) / ry
                dd = nx * nx + ny * ny
                if dd > 1:
                    continue
                hx = nx + 0.42
                hy = ny + 0.42
                if hx * hx + hy * hy < 0.07:
                    col = hi
                elif nx + ny > 0.75 or dd > 0.82 and nx + ny > 0:
                    col = shade
                else:
                    col = base
                self.px(xx, yy, col)

    def line(self, x0, y0, x1, y1, c):
        steps = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
        for i in range(steps + 1):
            t = i / steps
            self.px(round(x0 + (x1 - x0) * t), round(y0 + (y1 - y0) * t), c)

    def outline(self, c):
        """Draw color c around every non-transparent shape."""
        w, h, p = self.w, self.h, self.p
        add = []
        for yy in range(h):
            for xx in range(w):
                if p[yy * w + xx] == 0:
                    for ax, ay in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        if self.get(xx + ax, yy + ay) not in (0, c):
                            add.append((xx, yy))
                            break
        for xx, yy in add:
            self.px(xx, yy, c)


def paste(dst, src, x0, y0):
    """Copy the non-transparent pixels of src into dst at x0, y0."""
    for yy in range(src.h):
        for xx in range(src.w):
            c = src.p[yy * src.w + xx]
            if c:
                dst.px(x0 + xx, y0 + yy, c)


def scale15(a):
    """Make a picture 1.5 times bigger (nearest pixel)."""
    w = (a.w * 3 + 1) // 2
    h = (a.h * 3 + 1) // 2
    b = Art(w, h)
    for yy in range(h):
        sy = yy * 2 // 3
        for xx in range(w):
            b.p[yy * w + xx] = a.p[sy * a.w + xx * 2 // 3]
    return b


def bbox(a):
    """(x, y, w, h) of the non-transparent part."""
    xs = []
    ys = []
    for yy in range(a.h):
        for xx in range(a.w):
            if a.p[yy * a.w + xx]:
                xs.append(xx)
                ys.append(yy)
    if not xs:
        return (0, 0, 0, 0)
    return (min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1)


def from_text(rows, w=None, h=None):
    w = w or max(len(rw) for rw in rows)
    h = h or len(rows)
    a = Art(w, h)
    a.text(rows)
    return a


def sheet(arts):
    """Pack same-sized Art canvases side by side into one Bitmap (one tile each)."""
    tw = arts[0].w
    th = arts[0].h
    bmp = displayio.Bitmap(tw * len(arts), th, len(COLORS))
    for i, a in enumerate(arts):
        ox = i * tw
        for yy in range(th):
            row = yy * a.w
            for xx in range(tw):
                c = a.p[row + xx]
                if c:
                    bmp[ox + xx, yy] = c
    return bmp, tw, th


def sprite(arts, x=0, y=0, pal=None):
    """Make a TileGrid from one Art (or a list of frames). Change frame with tg[0] = n."""
    if not isinstance(arts, (list, tuple)):
        arts = [arts]
    bmp, tw, th = sheet(arts)
    return displayio.TileGrid(bmp, pixel_shader=pal or palette(),
                              tile_width=tw, tile_height=th, x=x, y=y)


def tile_sprite(bmp, tw, th, x=0, y=0, tile=0, pal=None):
    """Another TileGrid that shares a sheet made with sheet()."""
    return displayio.TileGrid(bmp, pixel_shader=pal or palette(),
                              tile_width=tw, tile_height=th, x=x, y=y, default_tile=tile)


# ====================================================================== FRUIT
def fruit_arts():
    """Nine 16x16 fruits."""
    out = []

    # apple
    a = Art(16, 16)
    a.ball(7.5, 9.5, 6.5, R, r, P)
    a.px(7, 3, r)
    a.px(8, 3, r)
    a.line(8, 0, 7, 3, N)
    a.ellipse(11, 1.8, 2.4, 1.2, G)
    out.append(a)

    # orange
    a = Art(16, 16)
    a.ball(7.5, 9, 6.8, O, o, Y)
    for xx, yy in ((5, 8), (9, 6), (10, 11), (6, 12), (12, 8)):
        a.px(xx, yy, o)
    a.px(7, 1, g)
    a.px(8, 1, g)
    a.ellipse(10, 1.5, 2, 1, G)
    out.append(a)

    # banana
    out.append(from_text((
        "................",
        "................",
        "............NN..",
        "............NY..",
        "...........YYy..",
        "...........YYy..",
        "..........YYYy..",
        "..........YYYy..",
        ".........YYYYy..",
        "........YYYYy...",
        ".......YYYYYy...",
        ".....YYYYYYy....",
        "..NYYYYYYYy.....",
        "..yyYYYYyy......",
        "....yyyy........",
        "................",
    )))

    # grapes
    a = Art(16, 16)
    for cy, xs in ((5.5, (3.5, 7.5, 11.5)), (9.2, (5.5, 9.5)), (12.9, (7.5,))):
        for cx in xs:
            a.ball(cx, cy, 2.5, V, v, L)
    a.line(8, 0, 7, 3, N)
    a.ellipse(10.5, 1.5, 2.2, 1.1, G)
    out.append(a)

    # cherries
    a = Art(16, 16)
    a.line(4, 10, 9, 2, g)
    a.line(11, 10, 9, 2, g)
    a.ball(4.5, 12, 3.2, R, r, P)
    a.ball(11.5, 11.5, 3.2, R, r, P)
    a.ellipse(11.5, 2, 2.5, 1.2, G)
    out.append(a)

    # strawberry
    a = Art(16, 16)
    for yy in range(3, 16):
        if yy < 6:
            hw = 7 - (6 - yy) * 1.2
        else:
            hw = 7 * (1 - (yy - 6) / 10) ** 0.8
        for xx in range(16):
            dx = xx + 0.5 - 8
            if abs(dx) <= hw:
                col = r if dx > hw - 1.6 else R
                if yy % 3 == 1 and (xx + yy) % 4 == 0 or yy % 3 == 2 and (xx + yy) % 4 == 2:
                    col = Y
                a.px(xx, yy, col)
    a.text((
        "......g..g......",
        "....gGGgGGGg....",
        "...GGgGGGgGG....",
        "....g..GG..g....",
    ))
    out.append(a)

    # watermelon slice
    a = Art(16, 16)
    for yy in range(4, 13):
        for xx in range(16):
            dx = xx + 0.5 - 8
            dy = yy + 0.5 - 4
            dist = math.sqrt(dx * dx + dy * dy)
            if dist <= 8:
                if dist > 7:
                    col = g
                elif dist > 6:
                    col = C
                else:
                    col = M
                a.px(xx, yy, col)
    for xx, yy in ((4, 6), (8, 7), (11, 6), (6, 9), (10, 9), (8, 10)):
        a.px(xx, yy, K)
    out.append(a)

    # pear
    a = Art(16, 16)
    a.ball(7.5, 11, 4.8, C, G, Y)
    a.ball(7.5, 6.5, 3.4, C, G, Y)
    a.line(8, 0, 8, 3, N)
    a.ellipse(10.5, 2, 2, 1, G)
    out.append(a)

    # lemon
    a = Art(16, 16)
    a.ball(7.5, 8.5, 6.5, Y, y, WH, ry=5)
    a.px(0, 8, y)
    a.px(15, 8, y)
    a.px(14, 7, y)
    out.append(a)
    return out


def bomb_art():
    a = Art(16, 16)
    a.ball(7.5, 9.5, 6, d, K, S)
    a.rect(9, 3, 11, 4, s)
    a.line(11, 3, 13, 1, n)
    a.px(14, 0, Y)
    a.px(13, 0, O)
    a.px(15, 1, O)
    a.px(14, 1, Y)
    a.outline(R)          # red glow so it is easy to see (and looks dangerous)
    return a


def basket_art():
    a = Art(28, 12)
    for yy in range(12):
        inset = yy // 4
        for xx in range(inset, 28 - inset):
            if yy < 2:
                col = N
            else:
                col = n if (xx // 3 + yy // 2) % 2 else N
            a.px(xx, yy, col)
    return a


HEART = (
    ".RR...RR.",
    "RPRR.RRRR",
    "RPRRRRRRR",
    "RRRRRRRRR",
    ".RRRRRRR.",
    "..RRRRR..",
    "...RRR...",
    "....R....",
)


def cloud_art():
    a = Art(32, 14)
    for cx, cy, rad in ((8, 9, 4.5), (15, 6, 5.5), (23, 8.5, 4.8), (16, 10, 4)):
        a.disk(cx, cy, rad, WH)
    for i in range(len(a.p)):
        if a.p[i] and i // 32 >= 11:
            a.p[i] = S
    return a


# ==================================================================== BALLOON
def balloon_arts(w=15, h=30, body=1, shade=2, hi=3, string=4):
    """Round balloon, heart balloon and 'pop' burst (same size, 3 tiles).
    The color numbers are palette indices so every balloon can have its own palette."""
    bh = int(h * 0.6)            # height of the balloon body
    cx = w / 2
    cy = bh / 2

    def knot_and_string(a):
        k = int(cx)
        a.px(k - 1, bh, shade)
        a.px(k, bh, shade)
        a.px(k + 1, bh, shade)
        a.px(k, bh + 1, shade)
        for yy in range(bh + 2, h):
            a.px(k + round(math.sin(yy * 0.7)), yy, string)

    # round balloon (a bit narrower at the bottom)
    rnd = Art(w, h)
    rx = w / 2 - 0.2
    ry = bh / 2
    for yy in range(bh):
        for xx in range(w):
            ny = (yy + 0.5 - cy) / ry
            rxe = rx * (1 - 0.14 * max(0.0, ny))
            nx = (xx + 0.5 - cx) / rxe
            if nx * nx + ny * ny <= 1:
                rnd.px(xx, yy, shade if nx * 0.8 + ny * 0.6 > 0.62 else body)
    rnd.ellipse(cx - rx * 0.42, cy - ry * 0.45, max(1.0, rx * 0.17), max(1.2, ry * 0.25), hi)
    knot_and_string(rnd)

    # heart balloon
    hrt = Art(w, h)
    for yy in range(bh):
        for xx in range(w):
            u = (xx + 0.5 - cx) / (w / 2 / 1.15)
            vv = 1.25 - (yy + 0.5) / (bh / 2.25)
            f = (u * u + vv * vv - 1) ** 3 - u * u * vv ** 3
            if f <= 0:
                hrt.px(xx, yy, shade if u * 0.7 - vv * 0.5 > 0.55 else body)
    hrt.ellipse(cx - w * 0.25, bh * 0.25, max(1.0, w * 0.08), max(1.2, bh * 0.1), hi)
    knot_and_string(hrt)

    # pop burst
    pop = Art(w, h)
    for i in range(8):
        ang = i * math.pi / 4 + 0.3
        for rr in range(3, int(w / 2) + 1):
            pop.px(cx + math.cos(ang) * rr, cy + math.sin(ang) * rr, body if rr % 3 else hi)
    return [rnd, hrt, pop]


CROSSHAIR = (
    "....KKK....",
    "..KK...KK..",
    ".K.......K.",
    ".K.......K.",
    "K.........K",
    "K....R....K",
    "K.........K",
    ".K.......K.",
    ".K.......K.",
    "..KK...KK..",
    "....KKK....",
)

# ======================================================================= DINO
_DINO_BODY = (
    "...........ggggggg",
    "..........gGGGGGGGg",
    "..........gGWKGGGGg",
    "..........gGWWGGGGg",
    "..........gGGGGGGGg",
    "..........gGGGGgggg",
    "..........gGGGGGg",
    "g........gGGGGg",
    "gg......gGGGGGGgg",
    "gGg....gGGGGGGgGg",
    "gGGg..gGGGGGGGg.g",
    "gGGGggGGGGGGGGg",
    ".gGGGGGGCCGGGGg",
    "..gGGGGGCCCGGg",
    "...gGGGGGCCGGg",
    "....gGGGGGGGg",
)
_LEGS = {
    'stand': (".....gGGg.gGGg",
              ".....gGg...gGg",
              ".....gGg...gGg",
              ".....gGGg..gGGg"),
    'run1': (".....gGGg.gGGg",
             ".....ggg...gGg",
             "...........gGg",
             "...........gGGg"),
    'run2': (".....gGGg.gGGg",
             ".....gGg...ggg",
             ".....gGg",
             ".....gGGg"),
}
_DUCK = (
    "..................gggggggg",
    "gg.........ggggggggGGWKGGg",
    "gGgg.....ggGGGGGGGGGGGGGGg",
    "gGGGgggggGGGGGGGGGGGGGgggg",
    ".gGGGGGGGGGGGGGGCCGGGGGGg.",
    "..ggGGGGGGGGGGGCCCGGGg.g..",
    "....ggGGGGGGGGGGGGGGg.....",
    "......gGGgggggggGGg.......",
)
DINO_W = 26
DINO_H = 20


def dino_arts():
    """Frames: 0 stand, 1 run1, 2 run2, 3 duck1, 4 duck2, 5 oops."""
    out = []
    for leg in ('stand', 'run1', 'run2'):
        a = Art(DINO_W, DINO_H)
        a.text(_DINO_BODY)
        a.text(_LEGS[leg], 0, 16)
        out.append(a)
    for legs in ((".....gGGg.......gGGg", ".....ggg........gGGGg"),
                 (".....gGGg.......gGGg", ".....gGGGg.......ggg")):
        a = Art(DINO_W, DINO_H)
        a.text(_DUCK, 0, 10)
        a.text(legs, 0, 18)
        out.append(a)
    a = Art(DINO_W, DINO_H)
    a.text(_DINO_BODY)
    a.text(_LEGS['stand'], 0, 16)
    a.rect(12, 2, 13, 3, G)
    a.px(12, 1, K)
    a.px(14, 1, K)
    a.px(13, 2, K)
    a.px(12, 3, K)
    a.px(14, 3, K)
    out.append(a)
    return out


OBST_W = 18
OBST_H = 24


def _cactus(trunk_w, height, arms):
    a = Art(OBST_W, OBST_H)
    x0 = (OBST_W - trunk_w) // 2
    top = OBST_H - height
    a.rect(x0, top + 1, x0 + trunk_w - 1, OBST_H - 1, G)
    a.rect(x0 + 1, top, x0 + trunk_w - 2, top, G)
    for side, ay, ah in arms:          # side -1 left, +1 right
        if side < 0:
            ax0, ax1 = x0 - 4, x0 - 1
        else:
            ax0, ax1 = x0 + trunk_w, x0 + trunk_w + 3
        a.rect(ax0, ay, ax1, ay + 2, G)               # horizontal part
        col = ax0 if side < 0 else ax1 - 2
        a.rect(col, ay - ah, col + 2, ay, G)          # vertical part
    # stripes
    for yy in range(top + 2, OBST_H - 1, 3):
        a.px(x0 + trunk_w // 2, yy, C)
    a.outline(g)
    return a


def obstacle_arts():
    """Tiles: 0 small cactus, 1 big cactus, 2 rock, 3 mushroom, 4 bird up, 5 bird down."""
    out = [
        _cactus(4, 15, ((-1, 14, 4),)),
        _cactus(6, 22, ((-1, 10, 5), (1, 13, 4))),
    ]
    a = Art(OBST_W, OBST_H)
    a.ball(9, 19.5, 8, s, d, S, ry=4.5)
    a.px(6, 19, d)
    a.px(11, 21, d)
    out.append(a)
    a = Art(OBST_W, OBST_H)
    a.rect(7, 17, 10, 23, WH)
    a.rect(10, 17, 10, 23, S)
    a.ball(9, 15, 7, R, r, P, ry=4.5)
    for xx, yy in ((5, 14), (9, 12), (12, 15)):
        a.px(xx, yy, WH)
        a.px(xx + 1, yy, WH)
    a.outline(r)
    out.append(a)
    out.append(from_text((
        "........bb",
        "........bBb",
        ".........bBb",
        "...bb.....bBb",
        "..bBKbbbbbbBBbbb",
        "OObBBBBBBBBBBBBBbb",
        "..bbBBBBBBBBBBbb",
        "....bbbbbbbbbb",
    ), OBST_W, OBST_H))
    out.append(from_text((
        "",
        "",
        "",
        "...bb",
        "..bBKbbbbbbbbbbb",
        "OObBBBBBBBBBBBBBbb",
        "..bbBBBBBBBBBBbb",
        "....bbbbbBBbbb",
        ".........bBb",
        "........bBb",
        "........bb",
    ), OBST_W, OBST_H))
    return out


# ====================================================================== SPACE
SHIP = (
    "...bb...........",
    "...bBBb.........",
    "...bBBBbb.......",
    ".ddSSSSSSSbb....",
    "dSSSSSSScccSbb..",
    "dSSSSSSSccWcSSSb",
    "dSSSSSSScccSbb..",
    ".ddSSSSSSSbb....",
    "...bBBBbb.......",
    "...bBBb.........",
    "...bb...........",
)
FLAMES = (
    ("....OY",
     "..OOYY",
     "OOOYYW",
     "..OOYY",
     "....OY"),
    ("......",
     "...OYY",
     ".OOYYW",
     "...OYY",
     "......"),
)
UFO = (
    "......cccc......",
    "....ccWccccc....",
    "...cccccccccc...",
    ".ssSSSSSSSSSSss.",
    "sSSYSSRSSYSSRSSs",
    ".ssssssssssssss.",
    "....dd....dd....",
)


def rock_arts(seed, count, radius, size=18):
    """Bumpy space rocks."""
    import random
    random.seed(seed)
    out = []
    for _ in range(count):
        a = Art(size, size)
        p1 = random.random() * 6.28
        p2 = random.random() * 6.28
        c = size / 2
        for yy in range(size):
            for xx in range(size):
                dx = xx + 0.5 - c
                dy = yy + 0.5 - c
                ang = math.atan2(dy, dx)
                rr = radius * (1 + 0.16 * math.sin(3 * ang + p1) + 0.1 * math.sin(5 * ang + p2))
                dist = math.sqrt(dx * dx + dy * dy)
                if dist <= rr:
                    lit = (dx + dy) / (rr + 0.01)
                    col = S if lit < -0.7 else (d if lit > 0.45 else s)
                    a.px(xx, yy, col)
        for _ in range(int(radius // 2)):
            a.disk(c + random.uniform(-radius, radius) * 0.5,
                   c + random.uniform(-radius, radius) * 0.5,
                   max(0.8, radius / 5), d)
        out.append(a)
    return out


def cracked(arts, seed=11):
    """Copies of rocks with glowing cracks - used after a rock was hit once."""
    import random
    random.seed(seed)
    out = []
    for a in arts:
        b = Art(a.w, a.h)
        b.p[:] = a.p
        c = a.w / 2
        for _ in range(3):
            ang = random.random() * 6.28
            x, y = c, c
            for _ in range(int(a.w / 2)):
                x += math.cos(ang)
                y += math.sin(ang)
                ang += random.uniform(-0.6, 0.6)
                if b.get(int(x), int(y)):
                    b.px(x, y, O if random.random() < 0.6 else Y)
        out.append(b)
    return out


def boom_arts(size=18):
    import random
    random.seed(7)
    out = []
    c = size / 2
    for k, (rad, cols) in enumerate(((3, (WH, Y)), (5, (Y, O)), (7, (O, o)), (8, (s, d)))):
        a = Art(size, size)
        for yy in range(size):
            for xx in range(size):
                dx = xx + 0.5 - c
                dy = yy + 0.5 - c
                dist = math.sqrt(dx * dx + dy * dy)
                if dist <= rad and random.random() < (1.0 if k < 2 else 0.55):
                    a.px(xx, yy, cols[0] if dist < rad * 0.6 else cols[1])
        out.append(a)
    return out


# ===================================================================== ICONS
ICON_PAINT = (
    "................",
    "............ddd.",
    "...........dPPPd",
    "..........dSPPd.",
    ".........dBSSd..",
    "........dBBBd...",
    ".......dBBBd....",
    "......dBBBd.....",
    ".....dBBBd......",
    "....dBBBd.......",
    "...dnnnd........",
    "...dnnd.........",
    "..dBnd..........",
    "..dBd...RR.YY...",
    "..dd..RR..Y..GG.",
    "...........GG...",
)
ICON_SNAKE = (
    "................",
    "..........YYYY..",
    ".........YYYYYY.",
    ".........YYKYKYR",
    ".........YYYYYY.",
    ".....OYYYYYYYY..",
    "....OOYYYYYYY...",
    "...OOO..........",
    "...OOO..........",
    "....OOOOOOOOO...",
    ".....OOOOOOOOO..",
    "............oo..",
    ".............oo.",
    "...ooooooooooo..",
    "..ooooooooooo...",
    "................",
)
ICON_BREAKOUT = (
    "................",
    ".RRRR.OOOO.YYYY.",
    ".RRRR.OOOO.YYYY.",
    "................",
    ".GGGG.BBBB.VVVV.",
    ".GGGG.BBBB.VVVV.",
    "................",
    "................",
    "..........WW....",
    "..........WW....",
    "................",
    "................",
    "................",
    "....SSSSSSSS....",
    "....ssssssss....",
    "................",
)
ICON_TETRIS = (
    "................",
    "..cccccccc......",
    "..cccccccc......",
    "................",
    "..........YYYY..",
    "..........YYYY..",
    "..VV......YYYY..",
    "..VV......YYYY..",
    "..VVVV..........",
    "..VVVV..........",
    "..VVGGGGRRRRBBBB",
    "..VVGGGGRRRRBBBB",
    "GGGGGGRRRRBBBBBB",
    "GGGGGGRRRRBBBBBB",
    "OOOOOOOOOOOOOOOO",
    "OOOOOOOOOOOOOOOO",
)
