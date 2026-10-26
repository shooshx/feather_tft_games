# art_dino.py - the bigger Dino Run pictures: the dino and all the funny obstacles.
import math
import random
import art
from art import Art, K, WH, R, r, P, G, g, N, Y, y, O, o, S, s, d, C, BL, bl, CY, n, M

TW = 40      # obstacle tile size (things stand on the bottom row)
TH = 34


def _inner_outline(a, edge, body_colors):
    """Turn the outermost pixels of the shape into the edge color."""
    w, h, p = a.w, a.h, a.p
    edges = []
    for yy in range(h):
        for xx in range(w):
            if p[yy * w + xx] in body_colors:
                for ax, ay in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    if a.get(xx + ax, yy + ay) == 0:
                        edges.append(yy * w + xx)
                        break
    for i in edges:
        p[i] = edge


def _round_rect(a, x0, y0, x1, y1, c, rad=2):
    for yy in range(y0, y1 + 1):
        for xx in range(x0, x1 + 1):
            dx = max(x0 + rad - xx, 0, xx - (x1 - rad))
            dy = max(y0 + rad - yy, 0, yy - (y1 - rad))
            if dx * dx + dy * dy <= rad * rad + 0.5:
                a.px(xx, yy, c)


DINO_W = 40
DINO_H = 30


def _dino(legs="stand", oops=False):
    a = Art(DINO_W, DINO_H)
    # tail: thick near the body, thin at the tip, pointing up-left
    for xx in range(0, 12):
        t = xx / 11
        top = int(8 + t * 5)
        bot = int(10 + t * 11)
        a.rect(xx, top, xx, bot, G)
    a.ellipse(17, 18, 9.5, 7.5, G)                 # body
    a.rect(19, 9, 26, 17, G)                       # neck
    _round_rect(a, 20, 0, 35, 9, G, 3)             # head
    _round_rect(a, 21, 8, 31, 11, G, 1)            # lower jaw
    a.rect(26, 16, 29, 17, G)                      # little arm
    a.rect(28, 18, 29, 19, G)
    # legs
    if legs == "stand":
        a.rect(10, 23, 14, 27, G)
        a.rect(10, 28, 16, 29, G)
        a.rect(19, 23, 23, 27, G)
        a.rect(19, 28, 25, 29, G)
    elif legs == "run1":                           # back leg up
        a.rect(10, 23, 14, 25, G)
        a.rect(12, 25, 17, 26, G)
        a.rect(19, 23, 23, 27, G)
        a.rect(19, 28, 25, 29, G)
    else:                                          # front leg up
        a.rect(10, 23, 14, 27, G)
        a.rect(10, 28, 16, 29, G)
        a.rect(19, 23, 23, 25, G)
        a.rect(21, 25, 26, 26, G)
    _inner_outline(a, g, (G,))
    # belly and details
    for yy in range(16, 25):
        for xx in range(15, 25):
            if a.get(xx, yy) == G:
                dx = (xx + 0.5 - 20) / 4.5
                dy = (yy + 0.5 - 20.5) / 4.5
                if dx * dx + dy * dy <= 1:
                    a.px(xx, yy, C)
    for xx in (8, 11, 14):                         # back bumps
        a.px(xx + 1, 11 + (14 - xx) // 4, C)
    a.px(34, 3, g)                                 # nostril
    if oops:
        for i in range(4):                         # X eye
            a.px(24 + i, 2 + i, K)
            a.px(27 - i, 2 + i, K)
        a.rect(27, 9, 33, 10, r)                   # open mouth
    else:
        a.rect(24, 2, 27, 5, WH)
        a.rect(26, 3, 27, 5, K)
        a.rect(27, 9, 34, 9, g)                    # mouth line
    return a


def _dino_duck(step):
    a = Art(DINO_W, DINO_H)
    for xx in range(0, 9):
        t = xx / 8
        a.rect(xx, int(16 + t * 2), xx, int(18 + t * 5), G)
    a.ellipse(18, 22, 12, 5.5, G)                 # long low body
    _round_rect(a, 26, 13, 39, 21, G, 3)           # head stretched forward
    a.rect(26, 20, 35, 23, G)                      # jaw
    if step == 0:
        a.rect(10, 26, 13, 28, G)
        a.rect(10, 29, 15, 29, G)
        a.rect(20, 26, 23, 27, G)
        a.rect(22, 27, 26, 28, G)
    else:
        a.rect(10, 26, 13, 27, G)
        a.rect(12, 27, 16, 28, G)
        a.rect(20, 26, 23, 28, G)
        a.rect(20, 29, 25, 29, G)
    _inner_outline(a, g, (G,))
    a.ellipse(18, 24, 6, 2.5, C)
    a.rect(30, 15, 33, 17, WH)
    a.rect(32, 15, 33, 17, K)
    a.rect(31, 21, 38, 21, g)
    _inner_outline(a, g, (G, C))
    return a


def dino_frames():
    """Frames: 0 stand/jump, 1 run1, 2 run2, 3 duck1, 4 duck2, 5 oops."""
    return [_dino("stand"), _dino("run1"), _dino("run2"),
            _dino_duck(0), _dino_duck(1), _dino("stand", oops=True)]


def _arc(a, cx, cy, rx, ry, a0, a1, c, steps=24):
    for i in range(steps + 1):
        t = math.radians(a0 + (a1 - a0) * i / steps)
        a.px(round(cx + rx * math.cos(t)), round(cy + ry * math.sin(t)), c)


def _tile():
    return Art(TW, TH)


def _cactus(trunk_w, height, arms):
    a = _tile()
    x0 = (TW - trunk_w) // 2
    x1 = x0 + trunk_w - 1
    top = TH - height
    _round_rect(a, x0, top, x1, TH - 1, G, trunk_w // 2)
    a.rect(x0, top + trunk_w // 2, x1, TH - 1, G)
    for side, ay, ah, aw in arms:          # side -1 left, +1 right
        if side < 0:
            ox1 = x0
            ox0 = x0 - 6
            col0 = ox0
        else:
            ox0 = x1
            ox1 = x1 + 6
            col0 = ox1 - aw + 1
        _round_rect(a, ox0, ay, ox1, ay + aw - 1, G, 1)
        _round_rect(a, col0, ay - ah, col0 + aw - 1, ay + aw - 1, G, aw // 2)
    _inner_outline(a, g, (G,))
    # a light stripe and a dark stripe make it look round
    for yy in range(top + 2, TH - 1):
        if a.get(x0 + 2, yy) == G:
            a.px(x0 + 2, yy, C)
        if trunk_w >= 8 and a.get(x1 - 2, yy) == G:
            a.px(x1 - 2, yy, g)
    return a


def small_cactus():
    return _cactus(7, 22, ((-1, 19, 7, 4),))


def big_cactus():
    return _cactus(8, 32, ((-1, 14, 8, 4), (1, 18, 7, 4)))


def rock():
    a = _tile()
    a.ball(20, 27, 13, s, d, S, ry=7)
    for yy in range(TH):                        # flat bottom
        a.p[(TH - 1) * TW: TH * TW] = a.p[(TH - 2) * TW: (TH - 1) * TW]
        break
    a.line(14, 25, 18, 28, d)
    a.line(18, 28, 17, 31, d)
    a.ellipse(26, 24, 2.5, 1.5, S)
    a.ellipse(9, 32, 3, 1.6, s)
    a.outline(d)
    return a


def mushroom():
    a = _tile()
    _round_rect(a, 15, 20, 25, 33, WH, 3)        # stem
    a.rect(23, 21, 24, 32, S)
    a.rect(17, 26, 18, 27, K)                   # cute face on the stem
    a.rect(22, 26, 23, 27, K)
    a.rect(19, 29, 21, 29, K)
    for yy in range(4, 21):                     # cap: top half of an ellipse
        for xx in range(TW):
            dx = (xx + 0.5 - 20) / 15
            dy = (yy + 0.5 - 20) / 15
            if dx * dx + dy * dy <= 1:
                a.px(xx, yy, r if dx + dy * 0.3 > 0.7 else R)
    a.rect(6, 19, 34, 20, P)                    # rim under the cap
    for cx, cy, rad in ((13, 13, 2.6), (21, 8, 2.2), (28, 13, 2.4), (20, 15, 1.6)):
        a.disk(cx, cy, rad, WH)
    a.outline(r)
    return a


def bird(frame):
    a = _tile()
    a.ellipse(19, 11, 10, 4.5, BL)              # body
    for xx in range(27, 36):                    # tail
        a.rect(xx, 8 + (xx - 27) // 3, xx, 13 - (xx - 27) // 4, BL)
    a.disk(9, 9, 4.5, BL)                       # head
    a.text(("..OO", "OOOOO", "..OO"), 1, 8)        # beak
    if frame == 0:                              # wings up
        for i in range(8):
            a.rect(14 + i // 2, 7 - i, 23 - i // 3, 7 - i, BL)
    else:                                       # wings down
        for i in range(8):
            a.rect(14 + i // 2, 14 + i, 23 - i // 3, 14 + i, BL)
    _inner_outline(a, bl, (BL,))
    a.rect(8, 7, 9, 8, WH)
    a.px(8, 8, K)
    a.ellipse(19, 12, 5, 1.6, CY)
    return a


# ------------------------------------------------------------------ faces
FCX = 20
FCY = 22
FR = 11


def _face():
    a = _tile()
    a.ball(FCX, FCY, FR, Y, y, WH)
    return a


def face_smile():
    a = _face()
    a.ellipse(FCX - 4, FCY - 3, 1.4, 2.4, K)
    a.ellipse(FCX + 4, FCY - 3, 1.4, 2.4, K)
    _arc(a, FCX, FCY + 1, 6, 5, 20, 160, K)
    _arc(a, FCX, FCY + 1, 6, 4.4, 30, 150, K)
    return a


def face_laugh():
    a = _face()
    _arc(a, FCX - 4, FCY - 2, 2.5, 2, 200, 340, K)       # closed happy eyes ^ ^
    _arc(a, FCX + 4, FCY - 2, 2.5, 2, 200, 340, K)
    for yy in range(FCY + 1, FCY + 8):
        for xx in range(FCX - 7, FCX + 8):
            dx = (xx + 0.5 - FCX) / 7
            dy = (yy + 0.5 - (FCY + 1)) / 6.5
            if dx * dx + dy * dy <= 1:
                col = K
                if yy == FCY + 1:
                    col = WH                               # teeth
                elif dy > 0.6:
                    col = r                                # tongue
                a.px(xx, yy, col)
    for tx in (FCX - 11, FCX + 10):                        # tears of joy
        a.ellipse(tx + 0.5, FCY - 0.5, 1.6, 2.6, CY)
        a.px(tx, FCY - 1, WH)
    return a


def face_cool():
    a = _face()
    a.rect(FCX - 9, FCY - 5, FCX + 8, FCY - 5, K)
    a.ellipse(FCX - 4.5, FCY - 3, 3.8, 2.8, K)
    a.ellipse(FCX + 4.5, FCY - 3, 3.8, 2.8, K)
    a.px(FCX - 6, FCY - 4, WH)
    a.px(FCX + 3, FCY - 4, WH)
    _arc(a, FCX + 1, FCY + 2, 5, 3.5, 10, 140, K)
    return a


def face_tongue():
    a = _face()
    _arc(a, FCX - 4, FCY - 3, 2.5, 1.5, 20, 160, K)       # wink
    a.ellipse(FCX + 4, FCY - 3, 1.4, 2.4, K)
    a.rect(FCX - 6, FCY + 3, FCX + 6, FCY + 3, K)
    a.ellipse(FCX + 2, FCY + 6, 2.8, 3, M)
    a.px(FCX + 2, FCY + 5, r)
    a.px(FCX + 2, FCY + 6, r)
    return a


def face_hearts():
    a = _face()
    heart = ("RR.RR",
             "RRRRR",
             "RRRRR",
             ".RRR.",
             "..R..")
    a.text(heart, FCX - 8, FCY - 6)
    a.text(heart, FCX + 3, FCY - 6)
    for yy in range(FCY + 2, FCY + 7):
        for xx in range(FCX - 6, FCX + 7):
            dx = (xx + 0.5 - FCX) / 6
            dy = (yy + 0.5 - (FCY + 2)) / 5
            if dx * dx + dy * dy <= 1:
                a.px(xx, yy, r if dy > 0.5 else K)
    return a


# ---------------------------------------------------------- other things
def poop():
    a = _tile()
    a.ellipse(20, 29, 12, 4.8, N)
    a.ellipse(20, 23.5, 9.5, 4, N)
    a.ellipse(20.5, 18.5, 7, 3.4, N)
    a.ellipse(22, 14.5, 3.2, 2.6, N)
    a.px(24, 11, N)
    a.px(25, 11, N)
    for cx, cy, rx in ((15, 27.5, 3), (16, 22, 2.5), (18, 17.5, 2)):
        a.ellipse(cx, cy, rx, 1, n)
    for ex in (16, 24):
        a.ellipse(ex + 0.5, 23.5, 2.2, 2.5, WH)
        a.px(ex + 1, 24, K)
        a.px(ex + 1, 23, K)
    _arc(a, 20.5, 28, 4, 2.2, 10, 170, K)
    a.outline(K)
    return a


def alien():
    a = _tile()
    a.line(16, 7, 13, 1, C)
    a.line(24, 7, 27, 1, C)
    a.disk(13, 1.5, 1.6, Y)
    a.disk(27, 1.5, 1.6, Y)
    a.rect(16, 20, 24, 28, G)
    a.line(16, 22, 11, 27, G)
    a.line(24, 22, 29, 27, G)
    a.rect(16, 28, 18, 33, g)
    a.rect(22, 28, 24, 33, g)
    a.ball(20, 13, 9.5, C, G, WH, ry=8)
    a.ellipse(16, 14, 2.8, 3.8, K)
    a.ellipse(24, 14, 2.8, 3.8, K)
    a.px(15, 12, WH)
    a.px(23, 12, WH)
    _arc(a, 20, 17.5, 2.5, 1.5, 20, 160, g)
    a.outline(g)
    return a


def _wheel(a, cx, cy):
    a.disk(cx, cy, 3.6, K)
    a.disk(cx, cy, 1.6, S)


def car():
    a = _tile()
    a.rect(10, 16, 28, 22, R)
    a.rect(12, 17, 18, 21, CY)
    a.rect(20, 17, 26, 21, CY)
    a.rect(1, 22, 38, 29, R)
    a.rect(1, 29, 38, 29, r)
    a.rect(0, 26, 1, 28, s)
    a.rect(38, 26, 39, 28, s)
    a.rect(1, 23, 2, 24, Y)
    a.rect(37, 23, 38, 24, r)
    a.rect(4, 22, 34, 22, P)
    _wheel(a, 9.5, 30)
    _wheel(a, 30.5, 30)
    return a


def truck():
    a = _tile()
    a.rect(13, 8, 39, 27, S)
    a.rect(13, 8, 39, 8, WH)
    a.rect(13, 27, 39, 27, s)
    a.rect(16, 14, 36, 18, O)
    a.rect(1, 16, 12, 28, BL)
    a.rect(2, 18, 8, 22, CY)
    a.rect(1, 24, 2, 25, Y)
    a.rect(0, 28, 39, 29, d)
    _wheel(a, 7.5, 30)
    _wheel(a, 23.5, 30)
    _wheel(a, 33.5, 30)
    return a


def rocket(frame):
    a = _tile()
    a.ball(19, 8, 13, WH, S, WH, ry=5)
    for i in range(7):                       # red nose cone on the left
        a.rect(2 + i, 8 - i // 2, 2 + i, 8 + i // 2, R)
    a.rect(4, 8, 8, 8, r)
    a.disk(14, 8, 3, BL)
    a.disk(14, 8, 2, CY)
    a.text(("RRR", ".RRR", "..RR"), 26, 0)
    a.text(("..RR", ".RRR", "RRR"), 26, 14)
    flame = (("OOY", "OYYW", "OOY"), ("OYY", "OYYYW", "OYY"))[frame]
    a.text(flame, 32 + frame, 7)
    return a


def turtle():
    """A cute turtle walking left: yellow skin, green shell, dark outline."""
    a = _tile()
    # legs and tail (drawn first, the shell covers their tops)
    _round_rect(a, 9, 26, 14, 33, Y, 2)
    _round_rect(a, 26, 26, 31, 33, Y, 2)
    a.rect(33, 25, 36, 27, Y)
    a.px(37, 26, Y)
    # head on a neck
    a.rect(6, 22, 11, 26, Y)
    a.ellipse(5.5, 19.5, 5.5, 4.8, Y)
    # shell: a dome
    for yy in range(8, 28):
        for xx in range(6, 36):
            dx = (xx + 0.5 - 21) / 14.5
            dy = (yy + 0.5 - 27) / 18
            if dy <= 0 and dx * dx + dy * dy <= 1:
                a.px(xx, yy, g if dx * 0.6 - dy * 0.2 > 0.6 else G)
    a.rect(6, 26, 36, 27, n)                       # shell rim
    a.outline(K)
    # shell plates
    for cx, cy, rx, ry in ((21, 15, 4.5, 3.5), (13, 21, 3.5, 3), (21, 22.5, 3.8, 2.8),
                           (29, 21, 3.5, 3)):
        a.ellipse(cx, cy, rx, ry, g)
        a.ellipse(cx, cy, rx - 1, ry - 1, C)
        a.ellipse(cx - 0.8, cy - 0.8, rx * 0.35, ry * 0.3, WH)
    # face
    a.rect(2, 17, 4, 19, WH)
    a.rect(2, 18, 3, 19, K)
    a.px(1, 22, K)
    a.rect(2, 22, 5, 22, o)                        # smile
    a.px(5, 20, P)                                 # rosy cheek
    a.px(6, 20, P)
    return a


def snail():
    a = _tile()
    a.rect(5, 29, 36, 32, P)
    a.rect(4, 31, 37, 33, M)
    a.line(8, 29, 6, 21, P)
    a.line(10, 29, 11, 21, P)
    a.disk(6, 21, 1.3, K)
    a.disk(11, 21, 1.3, K)
    a.ball(24, 22, 9, n, N, Y)
    _arc(a, 24, 22, 6, 6, 0, 300, N)
    _arc(a, 25, 22, 3, 3, 0, 300, N)
    a.px(25, 22, N)
    return a


def duck(frame):
    a = _tile()
    if frame == 0:
        a.line(18, 31, 16, 33, O)
        a.line(25, 31, 27, 33, O)
    else:
        a.line(19, 31, 19, 33, O)
        a.line(24, 31, 24, 33, O)
    a.ball(23, 25, 10, Y, y, WH, ry=6.5)
    a.ball(12, 15, 5.5, Y, y, WH)
    a.rect(4, 15, 7, 17, O)
    a.rect(5, 18, 7, 18, o)
    a.px(11, 13, K)
    a.ellipse(25, 24, 5, 2.5, y)
    a.px(33, 21, Y)
    a.px(34, 20, Y)
    return a


def fire(frame):
    random.seed(40 + frame)
    a = _tile()
    for layer, col, scale in ((0, R, 1.0), (1, O, 0.7), (2, Y, 0.42)):
        for yy in range(TH):
            t = (yy - 4) / (TH - 4)          # 0 at the top, 1 at the bottom
            if t < 0:
                continue
            width = 11 * scale * math.sin(min(1.0, t * 1.25) * math.pi * 0.62) + 1
            if layer == 0 and yy < 16:
                width += random.uniform(-1.5, 1.5)
            wob = math.sin(yy * 0.5 + frame * 2.5) * 2 * (1 - t)
            for xx in range(TW):
                if abs(xx + 0.5 - 20 - wob) <= width * (0.6 + 0.4 * t):
                    if yy > TH - 30 * scale:
                        a.px(xx, yy, col)
    for _ in range(3):                         # sparks
        a.px(random.randint(12, 28), random.randint(0, 8), O)
    return a


# ------------------------------------------------------------ the list
GROUND = 0
HOP = 1      # bounces up and down while it comes
FLY = 2      # flies high (duck under it) or low (jump over it)


def kinds():
    """Returns (tile arts, list of kinds).
    Each kind: [first tile, frame count, how it moves, speed factor, min score, hitbox]."""
    tiles = []
    out = []

    def add(frames, mode, speed=1.0, min_score=0):
        first = len(tiles)
        tiles.extend(frames)
        bx, by, bw, bh = art.bbox(frames[0])
        shrink = 3
        box = (bx + shrink, by + shrink, max(2, bw - 2 * shrink), max(2, bh - 2 * shrink))
        out.append((first, len(frames), mode, speed, min_score, box))

    add([small_cactus()], GROUND)
    add([big_cactus()], GROUND, 1.0, 40)
    add([rock()], GROUND)
    add([mushroom()], GROUND)
    add([poop()], GROUND)
    add([face_smile()], HOP)
    add([face_laugh()], HOP)
    add([face_cool()], HOP, 1.0, 30)
    add([face_tongue()], HOP, 1.0, 30)
    add([face_hearts()], HOP, 1.0, 30)
    add([turtle()], GROUND, 0.9)
    add([snail()], GROUND, 0.85)
    add([fire(0), fire(1)], GROUND, 1.0, 20)
    add([duck(0), duck(1)], GROUND, 1.1, 60)
    add([alien()], HOP, 1.0, 60)
    add([car()], GROUND, 1.35, 80)
    add([truck()], GROUND, 1.3, 120)
    add([bird(0), bird(1)], FLY, 1.15, 120)
    add([rocket(0), rocket(1)], FLY, 1.5, 160)
    return tiles, out
