# Snake - steer with the joystick, eat the red apples, don't bite yourself!
import random
import displayio
import hw
import art

CELL = 10
START_LEN = 3
COLS = hw.W // CELL           # 24
ROWS = (hw.H - 15) // CELL    # 12
TOP = hw.H - ROWS * CELL      # 15 pixels for the score at the top
WRAP = True                   # True: go through walls.  False: walls end the game
SHADES = 12                   # body colors from yellow to orange

# tile numbers in the tile sheet
EMPTY_A = 0
EMPTY_B = 1
APPLE = 2
HEAD = 3                      # 3..6 = head looking right, down, left, up
BODY = 7                      # 7..7+SHADES-1

DIRS = ((1, 0), (0, 1), (-1, 0), (0, -1))   # right, down, left, up


def _mix(c1, c2, t):
    out = 0
    for sh in (16, 8, 0):
        a = (c1 >> sh) & 255
        b = (c2 >> sh) & 255
        out |= int(a + (b - a) * t) << sh
    return out


def _tiles():
    """Build the tile sheet and its palette."""
    pal_colors = [0x1E5A1E, 0x23621F, 0xE8202A, 0x8C0A14, 0xFF9A9A, 0x16702A, 0x7A4A1A,
                  0x101010, 0xFFFFFF]
    # palette indices
    BG_A, BG_B, RED, DRED, PINK, LEAF, STEM, BLACK, WHITE = range(9)
    first_shade = len(pal_colors)
    for i in range(SHADES):
        pal_colors.append(_mix(0xFFE020, 0xFF6A00, i / (SHADES - 1)))
    pal = displayio.Palette(len(pal_colors))
    for i, c in enumerate(pal_colors):
        pal[i] = c

    n_tiles = BODY + SHADES
    bmp = displayio.Bitmap(CELL * n_tiles, CELL, len(pal_colors))

    def put(n, a):
        for yy in range(CELL):
            for xx in range(CELL):
                bmp[n * CELL + xx, yy] = a.p[yy * CELL + xx]

    # background tiles (checkerboard)
    a = art.Art(CELL, CELL)
    for i in range(len(a.p)):
        a.p[i] = BG_A
    put(EMPTY_A, a)
    for i in range(len(a.p)):
        a.p[i] = BG_B
    put(EMPTY_B, a)

    # apple: red and round
    a = art.Art(CELL, CELL)
    for i in range(len(a.p)):
        a.p[i] = BG_A
    a.ball(CELL / 2, CELL / 2 + 0.6, CELL / 2 - 0.6, RED, DRED, PINK)
    a.px(CELL // 2, 0, STEM)
    a.px(CELL // 2, 1, STEM)
    a.px(CELL // 2 + 1, 0, LEAF)
    a.px(CELL // 2 + 2, 0, LEAF)
    put(APPLE, a)

    # rounded body square
    def body(color):
        b = art.Art(CELL, CELL)
        for yy in range(CELL):
            for xx in range(CELL):
                corner = (xx in (0, CELL - 1)) and (yy in (0, CELL - 1))
                b.p[yy * CELL + xx] = BG_A if corner else color
        return b

    for i in range(SHADES):
        put(BODY + i, body(first_shade + i))

    # heads: eyes on the side we are going
    lo = CELL // 4
    hi = CELL - 1 - CELL // 4
    eyes = {0: ((hi, lo), (hi, hi)), 1: ((lo, hi), (hi, hi)),
            2: ((lo, lo), (lo, hi)), 3: ((lo, lo), (hi, lo))}
    for dno in range(4):
        h = body(first_shade)
        for ex, ey in eyes[dno]:
            h.rect(ex - 1, ey - 1, ex, ey, WHITE)
            h.px(ex, ey, BLACK)
        put(HEAD + dno, h)
    # the corners of body tiles use BG_A - fine on both checker colors
    return bmp, pal


def run():
    root = displayio.Group()
    root.append(hw.solid(hw.W, TOP, 0x103010))
    bmp, pal = _tiles()
    grid = displayio.TileGrid(bmp, pixel_shader=pal, width=COLS, height=ROWS,
                              tile_width=CELL, tile_height=CELL, y=TOP)
    root.append(grid)
    score_lbl = hw.text("Score 0", 4, 1, 0xFFE020)
    root.append(score_lbl)
    best_lbl = hw.text("Best 0", hw.W - 4, 1, 0xC0C0C0, 1, (1, 0))
    root.append(best_lbl)
    msg = hw.banner("")
    msg.hidden = True
    root.append(msg)
    hw.show(root)

    best = 0

    def empty(x, y):
        return EMPTY_A if (x + y) % 2 == 0 else EMPTY_B

    while True:
        # ------------------------------------------------ new game
        for yy in range(ROWS):
            for xx in range(COLS):
                grid[xx, yy] = empty(xx, yy)
        snake = [(START_LEN + 2 - i, ROWS - 3) for i in range(START_LEN)]   # head first
        occupied = set(snake)
        direction = 0
        queue = []
        score = 0
        step_time = 0.0
        speed = 6.0          # steps per second
        score_lbl.text = "Score 0"
        msg.text = "Push the stick\nto start!"
        msg.hidden = False

        def place_apple():
            while True:
                ax = random.randint(0, COLS - 1)
                ay = random.randint(0, ROWS - 1)
                if (ax, ay) not in occupied:
                    grid[ax, ay] = APPLE
                    return (ax, ay)

        def draw_snake():
            n = len(snake)
            for i, (sx, sy) in enumerate(snake):
                if i == 0:
                    grid[sx, sy] = HEAD + direction
                else:
                    grid[sx, sy] = BODY + (i * (SHADES - 1)) // (n - 1)

        apple = place_apple()
        draw_snake()
        started = False
        alive = True

        while alive:
            if not hw.frame():
                return
            pad = hw.pad
            # read the joystick as one of 4 directions
            want = None
            if abs(pad.x) > 0.5 or abs(pad.y) > 0.5:
                if abs(pad.x) > abs(pad.y):
                    want = 0 if pad.x > 0 else 2
                else:
                    want = 1 if pad.y > 0 else 3
            if want is not None:
                if not started and want != 2:
                    started = True
                    msg.hidden = True
                last = queue[-1] if queue else direction
                if want != last and want != (last + 2) % 4 and len(queue) < 2:
                    queue.append(want)
            if not started:
                continue

            step_time += hw.dt
            if step_time < 1 / speed:
                continue
            step_time -= 1 / speed
            if queue:
                direction = queue.pop(0)

            hx, hy = snake[0]
            dx, dy = DIRS[direction]
            nx = hx + dx
            ny = hy + dy
            if WRAP:
                nx %= COLS
                ny %= ROWS
            elif not (0 <= nx < COLS and 0 <= ny < ROWS):
                alive = False
                break

            eat = (nx, ny) == apple
            if not eat:
                tail = snake.pop()
                occupied.discard(tail)
                grid[tail[0], tail[1]] = empty(tail[0], tail[1])
            if (nx, ny) in occupied:
                alive = False
                break
            snake.insert(0, (nx, ny))
            occupied.add((nx, ny))
            if eat:
                score += 1
                score_lbl.text = "Score %d" % score
                speed = min(14.0, 6.0 + score * 0.25)
                apple = place_apple()
            draw_snake()

        # ------------------------------------------------ game over
        best = max(best, score)
        best_lbl.text = "Best %d" % best
        msg.text = "Score: %d\nA = again" % score
        msg.hidden = False
        while True:
            if not hw.frame():
                return
            if hw.pad.tap(hw.A | hw.START):
                break
