# Dino Run - press A (or push the stick up) to jump, pull the stick down to duck.
# Jump over cacti, rocks, poop, bouncing faces, cars... and duck under high birds and rockets.
import math
import random
import displayio
import bitmaptools
import hw
import art
import art_dino

SKY = 0xBFEFFF
SAND = 0xE8C890
GROUND_Y = 122            # where the dino's feet are
GRAVITY = 1050.0
JUMP_V = -390.0
DINO_X = 10
MAX_OBST = 3


def _ground():
    gw = hw.W + 64
    gh = hw.H - GROUND_Y
    bmp = displayio.Bitmap(gw, gh, 4)
    pal = displayio.Palette(4)
    pal[0] = SAND
    pal[1] = 0x8A6A3A
    pal[2] = 0xC8A870
    pal[3] = 0xF4DCB0
    bitmaptools.fill_region(bmp, 0, 0, gw, 1, 1)
    pebbles = [(random.randint(0, 62), random.randint(2, gh - 2), random.randint(2, 3))
               for _ in range(9)]
    for x0 in range(0, gw, 64):          # repeat every 64 pixels so we can scroll
        for px, py, c in pebbles:
            if x0 + px + 1 < gw:
                bmp[x0 + px, py] = c
                bmp[x0 + px + 1, py] = c
    return displayio.TileGrid(bmp, pixel_shader=pal, y=GROUND_Y)


def run():
    root = displayio.Group()
    root.append(hw.solid(hw.W, hw.H, SKY))
    loading = hw.banner("Loading...")
    root.append(loading)
    hw.show(root)
    hw.frame()

    cloud_art = art.cloud_art()
    clouds = []
    for i in range(3):
        c = art.sprite(cloud_art, 40 + i * 90, random.randint(8, 40))
        clouds.append([c, float(c.x)])
        root.insert(1, c)

    ground = _ground()
    root.append(ground)

    tiles, kinds = art_dino.kinds()
    hw.reseed()
    osheet, ow, oh = art.sheet(tiles)
    del tiles
    obst = []
    for _ in range(MAX_OBST):
        tg = art.tile_sprite(osheet, ow, oh)
        tg.hidden = True
        root.append(tg)
        obst.append([tg, False, 0.0, kinds[0], 0, 0.0])   # sprite, active, x, kind, base y, phase

    frames = art_dino.dino_frames()
    boxes = []
    for f in frames:
        bx, by, bw, bh = art.bbox(f)
        boxes.append((bx + 5, by + 4, bw - 10, bh - 5))    # forgiving hitbox
    dino_h = frames[0].h
    dino = art.sprite(frames, DINO_X)
    del frames
    root.append(dino)

    score_lbl = hw.text("0", hw.W - 4, 2, 0x505050, 1, (1, 0))
    root.append(score_lbl)
    best_lbl = hw.text("", hw.W - 50, 2, 0x909090, 1, (1, 0))
    root.append(best_lbl)
    root.remove(loading)
    msg = hw.banner("")
    root.append(msg)

    best = 0
    first_game = True
    while True:
        # ---------------------------------------------------- new game
        for o in obst:
            o[1] = False
            o[0].hidden = True
        y = 0.0            # height above the ground (negative = up)
        vy = 0.0
        on_ground = True
        speed = 110.0
        dist = 0.0
        next_gap = 160.0
        scroll = 0.0
        anim = 0.0
        score = 0
        dino[0] = 0
        dino.y = GROUND_Y - dino_h
        score_lbl.text = "0"
        if first_game:
            first_game = False
            msg.text = "A = jump\nstick down = duck"
            msg.hidden = False
            while True:
                if not hw.frame():
                    return
                if hw.pad.tap(hw.A | hw.B) or hw.pad.y < -0.6:
                    break
        msg.hidden = True
        crashed = False

        while not crashed:
            if not hw.frame():
                return
            dt = hw.dt
            pad = hw.pad
            jump_keys = hw.A | hw.B | hw.X | hw.Y

            # ---------------- dino
            jump = pad.tap(jump_keys) or (pad.y < -0.6 and on_ground)
            duck = pad.y > 0.5
            if jump and on_ground:
                vy = JUMP_V
                on_ground = False
            if not on_ground:
                # let go of the button early = smaller jump
                if vy < -160 and not pad.held(jump_keys) and pad.y > -0.6:
                    vy = -160
                if duck:
                    vy += GRAVITY * 1.5 * dt      # fall faster
                vy += GRAVITY * dt
                y += vy * dt
                if y >= 0:
                    y = 0.0
                    vy = 0.0
                    on_ground = True
            dino.y = GROUND_Y - dino_h + int(y)

            anim += dt * speed / 14
            step = int(anim) % 2
            if not on_ground:
                frame = 0
            elif duck:
                frame = 3 + step
            else:
                frame = 1 + step
            dino[0] = frame
            bx, by, bw, bh = boxes[frame]
            box = (DINO_X + bx, dino.y + by, bw, bh)

            # ---------------- world
            move = speed * dt
            dist += move
            speed = min(250.0, speed + 3.0 * dt)
            scroll = (scroll + move) % 64
            ground.x = -int(scroll)
            for c in clouds:
                c[1] -= move * 0.25
                if c[1] < -32:
                    c[1] = hw.W + random.randint(0, 60)
                    c[0].y = random.randint(8, 40)
                c[0].x = int(c[1])

            new_score = int(dist / 10)
            if new_score != score:
                score = new_score
                score_lbl.text = str(score)

            # ---------------- new obstacles
            next_gap -= move
            if next_gap <= 0:
                for o in obst:
                    if not o[1]:
                        choices = [k for k in kinds if k[4] <= score]
                        kind = random.choice(choices)
                        box_y, box_h = kind[5][1], kind[5][3]
                        if kind[2] == art_dino.FLY:
                            if random.random() < 0.5:
                                # high: the bottom is above a ducking dino - duck under it
                                o[4] = GROUND_Y - 17 - (box_y + box_h)
                            else:
                                # low: jump over it
                                o[4] = GROUND_Y - 3 - (box_y + box_h)
                        else:
                            o[4] = GROUND_Y - oh
                        o[0].y = o[4]
                        o[3] = kind
                        o[0][0] = kind[0]
                        o[1] = True
                        o[2] = float(hw.W)
                        o[5] = random.random() * 3
                        o[0].hidden = False
                        break
                next_gap = speed * random.uniform(0.8, 1.6) + 60

            # ---------------- move obstacles, check crash
            for o in obst:
                if not o[1]:
                    continue
                kind = o[3]
                o[2] -= move * kind[3]
                tg = o[0]
                tg.x = int(o[2])
                if kind[1] > 1:
                    tg[0] = kind[0] + int(anim / 2) % kind[1]
                if kind[2] == art_dino.HOP:
                    o[5] += dt * 5
                    tg.y = o[4] - int(abs(math.sin(o[5])) * 10)
                if o[2] < -ow:
                    o[1] = False
                    tg.hidden = True
                    continue
                kx, ky, kw, kh = kind[5]
                hx = tg.x + kx
                hy = tg.y + ky
                if (hx < box[0] + box[2] and box[0] < hx + kw and
                        hy < box[1] + box[3] and box[1] < hy + kh):
                    crashed = True

        # ---------------------------------------------------- oops
        dino[0] = 5
        best = max(best, score)
        best_lbl.text = "HI %d" % best
        msg.text = "Oops! %d\nA = again" % score
        msg.hidden = False
        t = 0.0
        while True:
            if not hw.frame():
                return
            t += hw.dt
            if t > 0.5 and hw.pad.tap(hw.A | hw.B):
                break
