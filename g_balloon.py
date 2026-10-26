# Balloon Pop - move the crosshair with the joystick, press A to pop balloons.
# Heart balloons are worth 3 points.  Nobody loses in this game :)
import math
import random
import displayio
import hw
import art

SKY = 0x9FE0FF
COLORS = (0xE8202A, 0xFF8C1A, 0xFFD020, 0x3CC23C, 0x3A7AFF, 0x9A40E0, 0xFF5AC8, 0x20C8C0)
HEART_COLORS = (0xFF2050, 0xFF5AC8)
MAX_BALLOONS = 6
BW = 22                 # balloon picture size
BH = 45
BODY_H = int(BH * 0.6)  # the round part (without the string)
MARGIN = 4              # you can miss by a few pixels and it still pops


def _shade(c):
    return ((c >> 16) * 6 // 10) << 16 | (((c >> 8) & 255) * 6 // 10) << 8 | (c & 255) * 6 // 10


def run():
    root = displayio.Group()
    root.append(hw.solid(hw.W, hw.H, SKY))
    cloud = art.cloud_art()
    for cx, cy in ((10, 30), (100, 8), (180, 50)):
        root.append(art.sprite(cloud, cx, cy))

    sheet, tw, th = art.sheet(art.balloon_arts(BW, BH))
    balloons = []
    for _ in range(MAX_BALLOONS):
        pal = displayio.Palette(5)
        pal.make_transparent(0)
        pal[3] = 0xFFFFFF
        pal[4] = 0x606060
        tg = art.tile_sprite(sheet, tw, th, pal=pal)
        tg.hidden = True
        root.append(tg)
        # sprite, state (0 off, 1 flying, 2 popping), x, y, speed, wobble phase, timer, heart?
        balloons.append([tg, 0, 0.0, 0.0, 0.0, 0.0, 0.0, False])

    cross = art.sprite(art.from_text(art.CROSSHAIR))
    root.append(cross)
    score_lbl = hw.text("0", 4, 2, 0x203060, 2)
    root.append(score_lbl)
    hw.show(root)

    cx = hw.W / 2
    cy = hw.H / 2
    score = 0
    spawn = 0.2
    t = 0.0
    while hw.frame():
        dt = hw.dt
        t += dt
        pad = hw.pad
        cx = max(0, min(hw.W - 1, cx + pad.x * 170 * dt))
        cy = max(0, min(hw.H - 1, cy + pad.y * 170 * dt))
        cross.x = int(cx) - 5
        cross.y = int(cy) - 5
        shoot = pad.tap(hw.A | hw.B | hw.X | hw.Y)

        spawn -= dt
        if spawn <= 0:
            spawn = random.uniform(0.5, 1.3)
            for b in balloons:
                if b[1] == 0:
                    heart = random.random() < 0.12
                    col = random.choice(HEART_COLORS if heart else COLORS)
                    pal = b[0].pixel_shader
                    pal[1] = col
                    pal[2] = _shade(col)
                    b[0][0] = 1 if heart else 0
                    b[1] = 1
                    b[2] = random.uniform(5, hw.W - BW - 5)
                    b[3] = float(hw.H)
                    b[4] = random.uniform(14, 30)
                    b[5] = random.uniform(0, 6.28)
                    b[7] = heart
                    b[0].hidden = False
                    break

        for b in balloons:
            tg = b[0]
            if b[1] == 1:
                b[3] -= b[4] * dt
                tg.x = int(b[2] + math.sin(t * 1.5 + b[5]) * 4)
                tg.y = int(b[3])
                if b[3] < -BH:
                    b[1] = 0
                    tg.hidden = True
                elif (shoot and tg.x - MARGIN <= cx < tg.x + BW + MARGIN and
                      tg.y - MARGIN <= cy < tg.y + BODY_H + MARGIN):
                    b[1] = 2
                    b[6] = 0.25
                    tg[0] = 2
                    score += 3 if b[7] else 1
                    score_lbl.text = str(score)
                    shoot = False     # one pop per press
            elif b[1] == 2:
                b[6] -= dt
                if b[6] <= 0:
                    b[1] = 0
                    tg.hidden = True
