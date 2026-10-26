# Space - fly the ship with the joystick, hold A to shoot the space rocks.
# The flying saucer is worth 5 points.
import math
import random
import displayio
import hw
import art

LIVES = 3
MAX_ROCKS = 6
MAX_SHOTS = 6
STAR_LAYERS = (   # count, speed (px/s), dim color, bright color, width
    (16, 8, 0x343434, 0x4C4C4C, 1),
    (12, 20, 0x505050, 0x6C6C6C, 1),
    (7, 45, 0x707070, 0x8C8C8C, 2),
)
BIG = (0, 1, 2)        # tiles
CRACKED = 3            # BIG tile + 3 = the same rock with cracks (after the first hit)
SMALL = (6, 7)
BOOM = 8               # 8..11


def run():
    root = displayio.Group()
    root.append(hw.solid(hw.W, hw.H, 0x02020C))

    # ------------------------------------------------- stars
    stars = []
    for count, speed, dim, bright, w in STAR_LAYERS:
        bmp = displayio.Bitmap(w * 2, 1, 3)
        for i in range(w):
            bmp[i, 0] = 1
            bmp[w + i, 0] = 2
        pal = displayio.Palette(3)
        pal.make_transparent(0)
        pal[1] = dim
        pal[2] = bright
        for _ in range(count):
            tg = displayio.TileGrid(bmp, pixel_shader=pal, tile_width=w, tile_height=1,
                                    x=random.randint(0, hw.W - 1), y=random.randint(0, hw.H - 1))
            root.append(tg)
            stars.append([tg, float(tg.x), speed])

    # ------------------------------------------------- sprites
    big_rocks = art.rock_arts(3, 3, 8)
    sheet, tw, th = art.sheet(big_rocks + art.cracked(big_rocks) + art.rock_arts(5, 2, 4.5) +
                              art.boom_arts())
    hw.reseed()
    rocks = []
    for _ in range(MAX_ROCKS):
        tg = art.tile_sprite(sheet, tw, th)
        tg.hidden = True
        root.append(tg)
        # sprite, state (0 off, 1 flying, 2 exploding), x, y, vx, vy, hp, timer, big?
        rocks.append([tg, 0, 0.0, 0.0, 0.0, 0.0, 0, 0.0, False])

    ufo = art.sprite(art.from_text(art.UFO))
    ufo.hidden = True
    root.append(ufo)

    shot_art = art.from_text(("OYYYYW", "OYYYYW"))
    shot_sheet, sw, sh = art.sheet([shot_art])
    shots = []
    for _ in range(MAX_SHOTS):
        tg = art.tile_sprite(shot_sheet, sw, sh)
        tg.hidden = True
        root.append(tg)
        shots.append([tg, False, 0.0])

    flame = art.sprite([art.from_text(f) for f in art.FLAMES])
    root.append(flame)
    ship = art.sprite(art.from_text(art.SHIP))
    root.append(ship)

    hearts = []
    heart = art.from_text(art.HEART)
    for i in range(LIVES):
        h = art.sprite(heart, hw.W - 12 * (i + 1), 3)
        root.append(h)
        hearts.append(h)
    score_lbl = hw.text("0", 4, 2, 0xC0C0FF, 1)
    root.append(score_lbl)
    msg = hw.banner("")
    msg.hidden = True
    root.append(msg)
    hw.show(root)

    def boom(r):
        r[1] = 2
        r[7] = 0.0
        r[0][0] = BOOM

    while True:
        # ------------------------------------------------- new game
        for r in rocks:
            r[1] = 0
            r[0].hidden = True
        for s in shots:
            s[1] = False
            s[0].hidden = True
        for h in hearts:
            h.hidden = False
        ufo.hidden = True
        ufo_on = False
        ufo_x = 0.0
        ufo_t = 0.0
        ufo_wait = 12.0
        sx = 20.0
        sy = hw.H / 2
        lives = LIVES
        score = 0
        score_lbl.text = "0"
        cooldown = 0.0
        spawn = 1.0
        hurt = 0.0
        t = 0.0
        over = False
        msg.hidden = True
        ship.hidden = False
        flame.hidden = False

        while True:
            if not hw.frame():
                return
            dt = hw.dt
            t += dt
            pad = hw.pad

            # ---------- stars (always moving, even after game over)
            for st in stars:
                st[1] -= st[2] * dt
                if st[1] < 0:
                    st[1] += hw.W
                    st[0].y = random.randint(0, hw.H - 1)
                nx = int(st[1])
                if nx != st[0].x:
                    st[0].x = nx
            # twinkle a few stars
            tw_star = stars[random.randint(0, len(stars) - 1)][0]
            tw_star[0] = 1 - tw_star[0]

            if over:
                if pad.tap(hw.A | hw.START):
                    break
                continue

            # ---------- ship
            sx = max(2, min(90, sx + pad.x * 110 * dt))
            sy = max(14, min(hw.H - 12, sy + pad.y * 110 * dt))
            ship.x = int(sx)
            ship.y = int(sy)
            flame.x = ship.x - 6
            flame.y = ship.y + 3
            flame[0] = int(t * 15) % 2
            if hurt > 0:
                hurt -= dt
                vis = hurt <= 0 or int(hurt * 10) % 2 == 0
                ship.hidden = not vis
                flame.hidden = not vis

            # ---------- shooting
            cooldown -= dt
            if pad.held(hw.A | hw.B) and cooldown <= 0:
                for s in shots:
                    if not s[1]:
                        s[1] = True
                        s[2] = sx + 14
                        s[0].y = ship.y + 4
                        s[0].hidden = False
                        cooldown = 0.2
                        break
            for s in shots:
                if s[1]:
                    s[2] += 220 * dt
                    if s[2] > hw.W:
                        s[1] = False
                        s[0].hidden = True
                    else:
                        s[0].x = int(s[2])

            # ---------- rocks
            spawn -= dt
            if spawn <= 0:
                spawn = max(0.5, 1.6 - t * 0.01) * random.uniform(0.6, 1.4)
                for r in rocks:
                    if r[1] == 0:
                        big = random.random() < 0.45
                        r[8] = big
                        r[6] = 2 if big else 1
                        r[0][0] = random.choice(BIG if big else SMALL)
                        r[1] = 1
                        r[2] = float(hw.W)
                        r[3] = random.uniform(12, hw.H - 18)
                        r[4] = -random.uniform(35, 60 + min(60, t))
                        r[5] = random.uniform(-10, 10)
                        r[0].hidden = False
                        break

            ship_box = (sx + 2, sy + 2, 12, 7)
            for r in rocks:
                tg = r[0]
                if r[1] == 2:          # exploding
                    r[7] += dt
                    f = int(r[7] / 0.08)
                    if f > 3:
                        r[1] = 0
                        tg.hidden = True
                    else:
                        tg[0] = BOOM + f
                    continue
                if r[1] != 1:
                    continue
                r[2] += r[4] * dt
                r[3] += r[5] * dt
                if r[3] < 10 or r[3] > hw.H - 18:
                    r[5] = -r[5]
                tg.x = int(r[2])
                tg.y = int(r[3])
                if r[2] < -18:
                    r[1] = 0
                    tg.hidden = True
                    continue
                rad = 7 if r[8] else 4
                cx = r[2] + 9
                cy = r[3] + 9
                # hit by a shot?
                for s in shots:
                    if s[1] and abs(s[2] + 3 - cx) < rad + 3 and abs(s[0].y + 1 - cy) < rad + 1:
                        s[1] = False
                        s[0].hidden = True
                        r[6] -= 1
                        if r[6] <= 0:
                            score += 2 if r[8] else 1
                            score_lbl.text = str(score)
                            boom(r)
                        else:
                            # hit but not broken yet: show cracks and knock it back
                            if tg[0] < CRACKED:
                                tg[0] += CRACKED
                            r[2] += 6
                            r[4] *= 0.8
                        break
                # hit the ship?
                if r[1] == 1 and hurt <= 0:
                    bx, by, bw, bh = ship_box
                    if (cx + rad > bx and cx - rad < bx + bw and
                            cy + rad > by and cy - rad < by + bh):
                        boom(r)
                        lives -= 1
                        hearts[lives].hidden = True
                        hurt = 2.0
                        if lives == 0:
                            over = True
                            ship.hidden = True
                            flame.hidden = True
                            msg.text = "Score: %d\nA = again" % score
                            msg.hidden = False

            # ---------- flying saucer
            if not ufo_on:
                ufo_wait -= dt
                if ufo_wait <= 0:
                    ufo_on = True
                    ufo_x = float(hw.W)
                    ufo_t = 0.0
                    ufo.hidden = False
            else:
                ufo_t += dt
                ufo_x -= 45 * dt
                ufo.x = int(ufo_x)
                ufo.y = int(hw.H / 2 - 4 + math.sin(ufo_t * 2.5) * 40)
                done = ufo_x < -16
                for s in shots:
                    if s[1] and ufo.x - 4 < s[2] < ufo.x + 16 and ufo.y - 1 < s[0].y < ufo.y + 7:
                        s[1] = False
                        s[0].hidden = True
                        score += 5
                        score_lbl.text = str(score)
                        # show an explosion using a free rock slot
                        for r in rocks:
                            if r[1] == 0:
                                r[0].x = ufo.x - 1
                                r[0].y = ufo.y - 5
                                r[0].hidden = False
                                boom(r)
                                break
                        done = True
                        break
                if done:
                    ufo_on = False
                    ufo.hidden = True
                    ufo_wait = random.uniform(10, 20)
