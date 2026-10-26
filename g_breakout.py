# Breakout - move the paddle with the joystick, press A to launch the ball.
# Break all the bricks!  Some bricks drop a surprise - catch it with the paddle:
#   green  <->   wider paddle             red  >-<   short blinking paddle (oops!)
#   yellow | |   guns: A fires 2 bullets  blue  3    three balls
#   purple 10    ten balls!               orange     fire ball - smashes through bricks
import math
import random
import displayio
import hw
import art

LIVES = 3
COLS = 10
ROWS = 5
BRICK_W = hw.W // COLS        # 24
BRICK_H = 8
BRICKS_TOP = 14
PADDLE_Y = hw.H - 9
PADDLE_H = 4
WIDTHS = (20, 36, 56)         # short, normal, wide
PAD_TILE_W = 56
PAD_TILE_H = 7                # paddle + room for the little guns on top
BALL = 4
MAX_BALLS = 12
MAX_DROPS = 4
MAX_BULLETS = 6
START_SPEED = 85.0
DROP_CHANCE = 0.2

WIDE, SHORT, GUN, SPLIT3, SPLIT10, FIRE = range(6)
TIME = {WIDE: 15.0, SHORT: 6.0, GUN: 12.0, FIRE: 8.0}

ROW_COLORS = ((art.R, art.r), (art.O, art.o), (art.Y, art.y), (art.G, art.g), (art.BL, art.bl))

DROP_ART = (
    (".GGGGGGGGGGGG.",
     "GGGGGGGGGGGGGG",
     "GGWGGGGGGGGWGG",
     "GWWWWWWWWWWWWG",
     "GGWGGGGGGGGWGG",
     "GGGGGGGGGGGGGG",
     ".GGGGGGGGGGGG."),
    (".RRRRRRRRRRRR.",
     "RRRRRRRRRRRRRR",
     "RRWRRRRRRRRWRR",
     "RRRWWWRRWWWRRR",
     "RRWRRRRRRRRWRR",
     "RRRRRRRRRRRRRR",
     ".RRRRRRRRRRRR."),
    (".YYYYYYYYYYYY.",
     "YYYKYYYYYYKYYY",
     "YYYKYYYYYYKYYY",
     "YYKKKYYYYKKKYY",
     "YYKKKYYYYKKKYY",
     "YYYYYYYYYYYYYY",
     ".YYYYYYYYYYYY."),
    (".BBBBBBBBBBBB.",
     "BBBBBWWWBBBBBB",
     "BBBBBBBWBBBBBB",
     "BBBBBBWWBBBBBB",
     "BBBBBBBWBBBBBB",
     "BBBBBWWWBBBBBB",
     ".BBBBBBBBBBBB."),
    (".VVVVVVVVVVVV.",
     "VVVVWVVWWWVVVV",
     "VVVWWVVWVWVVVV",
     "VVVVWVVWVWVVVV",
     "VVVVWVVWVWVVVV",
     "VVVWWWVWWWVVVV",
     ".VVVVVVVVVVVV."),
    (".OOOOOOOOOOOO.",
     "OOOOOOOYOOOOOO",
     "OOOOOOYYOOOOOO",
     "OOOOOYYYYOOOOO",
     "OOOOOYWWYOOOOO",
     "OOOOOOYYOOOOOO",
     ".OOOOOOOOOOOO."),
)


def _brick_tiles():
    tiles = [art.Art(BRICK_W, BRICK_H)]          # tile 0 = no brick
    for body, shade in ROW_COLORS:
        a = art.Art(BRICK_W, BRICK_H)
        a.rect(1, 1, BRICK_W - 2, BRICK_H - 2, body)
        a.rect(1, BRICK_H - 2, BRICK_W - 2, BRICK_H - 2, shade)
        a.rect(BRICK_W - 2, 1, BRICK_W - 2, BRICK_H - 2, shade)
        a.rect(2, 1, BRICK_W - 4, 1, art.WH)
        tiles.append(a)
    return tiles


def _paddle_tiles():
    """All paddle looks: tile = (width * 2 + gun) * 2 + red."""
    tiles = []
    for w in WIDTHS:
        for gun in (0, 1):
            for red in (0, 1):
                a = art.Art(PAD_TILE_W, PAD_TILE_H)
                x0 = (PAD_TILE_W - w) // 2
                x1 = x0 + w - 1
                top = PAD_TILE_H - PADDLE_H
                body, shade, hi = (art.R, art.r, art.P) if red else (art.S, art.s, art.WH)
                a.rect(x0 + 1, top, x1 - 1, top + PADDLE_H - 1, body)
                a.rect(x0, top + 1, x1, top + PADDLE_H - 2, body)
                a.rect(x0 + 1, top + PADDLE_H - 1, x1 - 1, top + PADDLE_H - 1, shade)
                a.rect(x0 + 2, top, x1 - 2, top, hi)
                if gun:
                    for gx in (x0 + 1, x1 - 2):
                        a.rect(gx, 0, gx + 1, top - 1, art.d)
                        a.rect(gx, 0, gx + 1, 0, art.Y)
                tiles.append(a)
    return tiles


def run():
    root = displayio.Group()
    root.append(hw.solid(hw.W, hw.H, 0x0A0A24))
    top_line = hw.solid(hw.W, 1, 0x404070)
    top_line.y = 11
    root.append(top_line)

    bsheet, tw, th = art.sheet(_brick_tiles())
    grid = displayio.TileGrid(bsheet, pixel_shader=art.palette(), width=COLS, height=ROWS,
                              tile_width=tw, tile_height=th, y=BRICKS_TOP)
    root.append(grid)

    paddle = art.sprite(_paddle_tiles(), 0, PADDLE_Y - (PAD_TILE_H - PADDLE_H))
    root.append(paddle)

    dsheet, dw, dh = art.sheet([art.from_text(d) for d in DROP_ART])
    drops = []
    for _ in range(MAX_DROPS):
        tg = art.tile_sprite(dsheet, dw, dh)
        tg.hidden = True
        root.append(tg)
        drops.append([tg, False, 0.0, 0])       # sprite, active, y, kind

    bul_sheet, bw, bh = art.sheet([art.from_text(("Y", "Y", "W", "W"))])
    bullets = []
    for _ in range(MAX_BULLETS):
        tg = art.tile_sprite(bul_sheet, bw, bh)
        tg.hidden = True
        root.append(tg)
        bullets.append([tg, False, 0.0])

    ball_sheet, bsw, bsh = art.sheet([art.from_text((".WW.", "WWWS", "WWSS", ".SS.")),
                                      art.from_text((".YO.", "YWYO", "OYOR", ".OR."))])
    balls = []
    for _ in range(MAX_BALLS):
        tg = art.tile_sprite(ball_sheet, bsw, bsh)
        tg.hidden = True
        root.append(tg)
        balls.append([tg, False, 0.0, 0.0, 0.0, 0.0])   # sprite, active, x, y, vx, vy

    hearts = []
    heart = art.from_text(art.HEART)
    for i in range(LIVES):
        h = art.sprite(heart, hw.W - 12 * (i + 1), 2)
        root.append(h)
        hearts.append(h)
    score_lbl = hw.text("0", 4, 0, 0xFFFFFF)
    root.append(score_lbl)
    level_lbl = hw.text("", hw.W // 2, 0, 0x8080C0, 1, (0.5, 0))
    root.append(level_lbl)
    msg = hw.banner("")
    root.append(msg)
    hw.show(root)

    def fill_bricks():
        for r in range(ROWS):
            for c in range(COLS):
                grid[c, r] = r + 1
        return ROWS * COLS

    def brick_at(x, y, size=BALL):
        """Return (col, row) of a brick touching the box at x,y or None."""
        r0 = (int(y) - BRICKS_TOP) // BRICK_H
        r1 = (int(y) + size - 1 - BRICKS_TOP) // BRICK_H
        c0 = int(x) // BRICK_W
        c1 = (int(x) + size - 1) // BRICK_W
        for r in (r0, r1):
            if 0 <= r < ROWS:
                for c in (c0, c1):
                    if 0 <= c < COLS and grid[c, r]:
                        return c, r
        return None

    st = {}

    def break_brick(c, r):
        grid[c, r] = 0
        st["bricks"] -= 1
        st["score"] += ROWS - r
        score_lbl.text = str(st["score"])
        if random.random() < DROP_CHANCE:
            for dr in drops:
                if not dr[1]:
                    dr[1] = True
                    dr[2] = float(BRICKS_TOP + r * BRICK_H)
                    dr[3] = random.randint(0, len(DROP_ART) - 1)
                    dr[0][0] = dr[3]
                    dr[0].x = c * BRICK_W + (BRICK_W - dw) // 2
                    dr[0].y = int(dr[2])
                    dr[0].hidden = False
                    break

    def clear_extras():
        for dr in drops:
            dr[1] = False
            dr[0].hidden = True
        for b in bullets:
            b[1] = False
            b[0].hidden = True
        for b in balls:
            b[1] = False
            b[0].hidden = True
        st["timers"] = {WIDE: 0.0, SHORT: 0.0, GUN: 0.0, FIRE: 0.0}

    def new_ball():
        b = balls[0]
        b[1] = True
        b[0].hidden = False
        st["stuck"] = True

    def split(n):
        live = [b for b in balls if b[1]]
        if not live:
            return
        src = live[0]
        free = [b for b in balls if not b[1]]
        speed = st["speed"]
        for i in range(n - 1):
            if not free:
                break
            b = free.pop()
            ang = -1.1 + 2.2 * i / max(1, n - 2)
            b[1] = True
            b[2], b[3] = src[2], src[3]
            b[4] = speed * math.sin(ang)
            b[5] = -speed * math.cos(ang)
            b[0][0] = src[0][0]
            b[0].hidden = False

    def paddle_width():
        t = st["timers"]
        if t[SHORT] > 0:
            return 0
        if t[WIDE] > 0:
            return 2
        return 1

    while True:
        # ---------------------------------------------------- new game
        st["bricks"] = fill_bricks()
        st["score"] = 0
        st["speed"] = START_SPEED
        lives = LIVES
        for h in hearts:
            h.hidden = False
        level = 1
        score_lbl.text = "0"
        level_lbl.text = "Level 1"
        px = (hw.W - WIDTHS[1]) / 2
        clear_extras()
        new_ball()
        gun_cool = 0.0
        blink = 0.0
        msg.text = "A = launch"
        msg.hidden = False
        game_over = False

        while not game_over:
            if not hw.frame():
                return
            dt = hw.dt
            pad = hw.pad
            timers = st["timers"]
            for k in timers:
                if timers[k] > 0:
                    timers[k] -= dt

            # ---------- paddle
            wi = paddle_width()
            pw = WIDTHS[wi]
            px = max(0, min(hw.W - pw, px + pad.x * 190 * dt))
            gun = timers[GUN] > 0
            blink += dt
            red = timers[SHORT] > 0 and int(blink * 8) % 2 == 0
            paddle[0] = (wi * 2 + (1 if gun else 0)) * 2 + (1 if red else 0)
            paddle.x = int(px) - (PAD_TILE_W - pw) // 2
            fire = timers[FIRE] > 0
            ball_tile = 1 if fire else 0

            # ---------- guns
            gun_cool -= dt
            if gun and not st["stuck"] and pad.tap(hw.A) and gun_cool <= 0:
                gun_cool = 0.25
                for gx in (px + 1, px + pw - 2):
                    for b in bullets:
                        if not b[1]:
                            b[1] = True
                            b[2] = float(PADDLE_Y - 6)
                            b[0].x = int(gx)
                            b[0].y = int(b[2])
                            b[0].hidden = False
                            break
            for b in bullets:
                if not b[1]:
                    continue
                b[2] -= 170 * dt
                b[0].y = int(b[2])
                hit = brick_at(b[0].x, b[2], 2)
                if hit:
                    break_brick(*hit)
                if hit or b[2] < 12:
                    b[1] = False
                    b[0].hidden = True

            # ---------- surprises falling down
            for dr in drops:
                if not dr[1]:
                    continue
                dr[2] += 40 * dt
                dr[0].y = int(dr[2])
                if dr[0].y + dh >= PADDLE_Y and dr[0].y <= PADDLE_Y + PADDLE_H and \
                        px - dw < dr[0].x < px + pw:
                    kind = dr[3]
                    if kind == WIDE:
                        timers[WIDE] = TIME[WIDE]
                        timers[SHORT] = 0.0
                    elif kind == SHORT:
                        timers[SHORT] = TIME[SHORT]
                        timers[WIDE] = 0.0
                    elif kind == SPLIT3:
                        split(3)
                    elif kind == SPLIT10:
                        split(10)
                    else:
                        timers[kind] = TIME[kind]
                    dr[1] = False
                    dr[0].hidden = True
                elif dr[2] > hw.H:
                    dr[1] = False
                    dr[0].hidden = True

            # ---------- balls
            if st["stuck"]:
                b = balls[0]
                b[2] = px + pw / 2 - BALL / 2
                b[3] = PADDLE_Y - BALL
                b[0].x = int(b[2])
                b[0].y = int(b[3])
                b[0][0] = ball_tile
                if pad.tap(hw.A | hw.B | hw.START):
                    st["stuck"] = False
                    msg.hidden = True
                    ang = random.uniform(-0.5, 0.5)
                    b[4] = st["speed"] * math.sin(ang)
                    b[5] = -st["speed"] * math.cos(ang)
                continue

            speed = st["speed"]
            alive = 0
            for b in balls:
                if not b[1]:
                    continue
                bx, by, vx, vy = b[2], b[3], b[4], b[5]
                steps = int(max(abs(vx), abs(vy)) * dt / 2) + 1
                h = dt / steps
                for _ in range(steps):
                    bx += vx * h
                    if bx < 0:
                        bx = 0.0
                        vx = abs(vx)
                    elif bx > hw.W - BALL:
                        bx = float(hw.W - BALL)
                        vx = -abs(vx)
                    hit = brick_at(bx, by)
                    if hit:
                        if not fire:
                            bx -= vx * h
                            vx = -vx
                    else:
                        by += vy * h
                        if by < 12:
                            by = 12.0
                            vy = abs(vy)
                        hit = brick_at(bx, by)
                        if hit and not fire:
                            by -= vy * h
                            vy = -vy
                    if hit:
                        break_brick(*hit)
                        if st["bricks"] == 0:
                            break
                    if (vy > 0 and PADDLE_Y - BALL <= by <= PADDLE_Y and
                            px - BALL < bx < px + pw):
                        off = (bx + BALL / 2 - (px + pw / 2)) / (pw / 2)
                        off = max(-1.0, min(1.0, off))
                        ang = off * 1.05           # up to ~60 degrees
                        if -0.15 < ang < 0.15:     # never perfectly straight up
                            ang = 0.15 if ang >= 0 else -0.15
                        vx = speed * math.sin(ang)
                        vy = -speed * math.cos(ang)
                        by = PADDLE_Y - BALL - 0.01
                b[2], b[3], b[4], b[5] = bx, by, vx, vy
                if by > hw.H:
                    b[1] = False
                    b[0].hidden = True
                    continue
                alive += 1
                b[0].x = int(bx)
                b[0].y = int(by)
                b[0][0] = ball_tile
                if st["bricks"] == 0:
                    break

            if st["bricks"] == 0:
                # next level: faster ball
                level += 1
                level_lbl.text = "Level %d" % level
                st["speed"] = START_SPEED * (1 + 0.12 * (level - 1))
                st["bricks"] = fill_bricks()
                clear_extras()
                new_ball()
                msg.text = "Level %d!\nA = launch" % level
                msg.hidden = False
            elif alive == 0:
                lives -= 1
                hearts[lives].hidden = True
                clear_extras()
                if lives == 0:
                    game_over = True
                else:
                    new_ball()
                    msg.text = "A = launch"
                    msg.hidden = False

        # ---------------------------------------------------- game over
        msg.text = "Score: %d\nA = again" % st["score"]
        msg.hidden = False
        while True:
            if not hw.frame():
                return
            if hw.pad.tap(hw.A | hw.START):
                break
