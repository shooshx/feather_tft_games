# Fruit Catch - move the basket with the joystick, catch the fruit, avoid the bombs!
import random
import displayio
import hw
import art

SKY = 0x1C2A4A        # dark evening sky so the bright fruit stands out
GRASS = 0x2E7A2A
MAX_FALLING = 5
LIVES = 3
BOMB = 9            # tile number of the bomb in the sheet


def run():
    root = displayio.Group()
    bg = displayio.Bitmap(hw.W, hw.H, 4)
    pal = displayio.Palette(4)
    pal[0] = SKY
    pal[1] = GRASS
    pal[2] = 0x3E9A38
    pal[3] = 0x50608A     # faint stars
    import bitmaptools
    bitmaptools.fill_region(bg, 0, hw.H - 8, hw.W, hw.H, 1)
    bitmaptools.fill_region(bg, 0, hw.H - 8, hw.W, hw.H - 7, 2)
    for _ in range(30):
        bg[random.randint(0, hw.W - 1), random.randint(0, hw.H - 12)] = 3
    root.append(displayio.TileGrid(bg, pixel_shader=pal))

    # dim clouds: a copy of the palette with darker white and gray
    cloud_pal = displayio.Palette(len(art.COLORS))
    for i, (_, c) in enumerate(art.COLORS):
        cloud_pal[i] = c
    cloud_pal.make_transparent(0)
    cloud_pal[art.WH] = 0x34446A
    cloud_pal[art.S] = 0x2C3A5C
    for cx in (30, 150):
        root.append(art.sprite(art.cloud_art(), cx, random.randint(14, 34), cloud_pal))

    sheet, tw, th = art.sheet(art.fruit_arts() + [art.bomb_art()])
    falling = []
    for _ in range(MAX_FALLING):
        tg = art.tile_sprite(sheet, tw, th)
        tg.hidden = True
        root.append(tg)
        falling.append([tg, False, 0.0, 0.0])   # sprite, active, y, speed

    basket = art.sprite(art.basket_art())
    basket.y = hw.H - 8 - 11
    root.append(basket)

    hearts = []
    heart_art = art.from_text(art.HEART)
    for i in range(LIVES):
        h = art.sprite(heart_art, hw.W - 12 * (i + 1), 3)
        hearts.append(h)
        root.append(h)

    score_lbl = hw.text("0", 4, 2, 0xFFFFFF, 2)
    root.append(score_lbl)
    plus = hw.text("+1", 0, 0, 0xFFFFFF, 1, (0.5, 1))
    plus.hidden = True
    root.append(plus)
    msg = hw.banner("")
    msg.hidden = True
    root.append(msg)

    hw.show(root)

    def reset():
        st["score"] = 0
        st["lives"] = LIVES
        st["bx"] = (hw.W - 28) / 2
        st["spawn"] = 0.5
        st["hurt"] = 0.0
        st["over"] = False
        st["plus_t"] = 0.0
        for f in falling:
            f[1] = False
            f[0].hidden = True
        for h in hearts:
            h.hidden = False
        score_lbl.text = "0"
        msg.hidden = True

    st = {}
    reset()

    while hw.frame():
        dt = hw.dt
        pad = hw.pad
        if st["over"]:
            if pad.tap(hw.A | hw.START):
                reset()
            continue

        score = st["score"]
        # move the basket
        st["bx"] += pad.x * 170 * dt
        st["bx"] = max(0, min(hw.W - 28, st["bx"]))
        bx = int(st["bx"])
        basket.x = bx

        # blink after touching a bomb
        if st["hurt"] > 0:
            st["hurt"] -= dt
            basket.hidden = st["hurt"] > 0 and int(st["hurt"] * 10) % 2 == 0
        if st["plus_t"] > 0:
            st["plus_t"] -= dt
            plus.y -= 1
            if st["plus_t"] <= 0:
                plus.hidden = True

        # new things to catch
        st["spawn"] -= dt
        if st["spawn"] <= 0:
            st["spawn"] = max(0.45, 1.5 - score * 0.03) * random.uniform(0.7, 1.3)
            for f in falling:
                if not f[1]:
                    f[1] = True
                    bomb = score >= 3 and random.random() < 0.18
                    f[0][0] = BOMB if bomb else random.randint(0, BOMB - 1)
                    f[0].x = random.randint(2, hw.W - 18)
                    f[2] = -16.0
                    f[3] = min(110, 32 + score * 1.5) * random.uniform(0.85, 1.2)
                    f[0].hidden = False
                    break

        # fall and catch
        for f in falling:
            if not f[1]:
                continue
            f[2] += f[3] * dt
            tg = f[0]
            tg.y = int(f[2])
            bottom = tg.y + 14
            cx = tg.x + 8
            if basket.y <= bottom <= basket.y + 8 and bx - 2 <= cx <= bx + 30:
                f[1] = False
                tg.hidden = True
                if tg[0] == BOMB:
                    if st["hurt"] <= 0:
                        st["lives"] -= 1
                        hearts[st["lives"]].hidden = True
                        st["hurt"] = 1.2
                        if st["lives"] == 0:
                            st["over"] = True
                            basket.hidden = False
                            msg.text = "Score: %d\nA = again" % st["score"]
                            msg.hidden = False
                else:
                    st["score"] += 1
                    score_lbl.text = str(st["score"])
                    plus.anchored_position = (cx, basket.y)
                    plus.hidden = False
                    st["plus_t"] = 0.4
            elif tg.y > hw.H:
                f[1] = False
                tg.hidden = True
