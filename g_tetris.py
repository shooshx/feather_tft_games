# Tetris - played with the device turned on its side (the screen's right edge at the bottom).
#   stick left/right = move      stick down = drop faster
#   A or stick up    = turn      B = turn the other way      X = drop all the way
import random
import displayio
import hw
import art

TURN = 270          # if the picture is upside down on your device, use 90
PAD_TURNED = True   # the gamepad is turned together with the screen
COLS = 10
ROWS = 20
CELL = 10
BOARD_X = 2
BOARD_Y = 36
GHOST = 8           # tile number of the "landing preview"
FLASH = 9           # tile number for clearing lines

COLORS = (0x00D8E0, 0xFFD020, 0xB040E0, 0x40D040, 0xF03030, 0x3060FF, 0xFF8C1A)

# piece shapes as (x, y) cells, in the 4 rotations
SHAPES = (
    ((0, 1), (1, 1), (2, 1), (3, 1)),   # I
    ((0, 0), (1, 0), (0, 1), (1, 1)),   # O
    ((1, 0), (0, 1), (1, 1), (2, 1)),   # T
    ((1, 0), (2, 0), (0, 1), (1, 1)),   # S
    ((0, 0), (1, 0), (1, 1), (2, 1)),   # Z
    ((0, 0), (0, 1), (1, 1), (2, 1)),   # J
    ((2, 0), (0, 1), (1, 1), (2, 1)),   # L
)


def _rotations(cells, size):
    out = [cells]
    for _ in range(3):
        cells = tuple((size - 1 - y, x) for x, y in cells)
        out.append(cells)
    return out


PIECES = [_rotations(s, 4 if i == 0 else (2 if i == 1 else 3)) for i, s in enumerate(SHAPES)]


def _tiles(cell=CELL):
    pal = displayio.Palette(3 + len(COLORS) * 3)
    pal[0] = 0x0C0C1C       # empty
    pal[1] = 0x1A1A30       # grid dot
    pal[2] = 0xFFFFFF
    for i, c in enumerate(COLORS):
        r, g, b = c >> 16, (c >> 8) & 255, c & 255
        pal[3 + i * 3] = c
        pal[4 + i * 3] = (min(255, r + 90) << 16) | (min(255, g + 90) << 8) | min(255, b + 90)
        pal[5 + i * 3] = ((r * 5 // 10) << 16) | ((g * 5 // 10) << 8) | (b * 5 // 10)
    n = 10
    bmp = displayio.Bitmap(cell * n, cell, len(pal))

    def put(t, fn):
        for yy in range(cell):
            for xx in range(cell):
                bmp[t * cell + xx, yy] = fn(xx, yy)

    put(0, lambda x, y: 1 if x == 0 and y == 0 else 0)
    for i in range(len(COLORS)):
        base = 3 + i * 3

        def block(x, y, base=base):
            if x == 0 or y == 0:
                return base + 1
            if x == cell - 1 or y == cell - 1:
                return base + 2
            return base
        put(1 + i, block)
    put(GHOST, lambda x, y: 2 if (x in (0, cell - 1) or y in (0, cell - 1)) and (x + y) % 2 == 0 else 0)
    put(FLASH, lambda x, y: 2)
    return bmp, pal


def run():
    hw.rotate(TURN, PAD_TURNED)
    sw = hw.display.width       # 135
    sh = hw.display.height      # 240
    root = displayio.Group()
    root.append(hw.solid(sw, sh, 0x000008))
    frame = hw.solid(COLS * CELL + 2, ROWS * CELL + 2, 0x505080)
    frame.x = BOARD_X - 1
    frame.y = BOARD_Y - 1
    root.append(frame)

    bmp, pal = _tiles()
    grid = displayio.TileGrid(bmp, pixel_shader=pal, width=COLS, height=ROWS,
                              tile_width=CELL, tile_height=CELL, x=BOARD_X, y=BOARD_Y)
    root.append(grid)

    side_x = BOARD_X + COLS * CELL + 4
    root.append(hw.text("NEXT", side_x, BOARD_Y, 0x9090C0))
    small, spal = _tiles(6)
    nxt = displayio.TileGrid(small, pixel_shader=spal, width=4, height=2,
                             tile_width=6, tile_height=6)
    nxt.x = side_x + 1
    nxt.y = BOARD_Y + 16
    root.append(nxt)

    root.append(hw.text("SCORE", 4, 2, 0x9090C0))
    score_lbl = hw.text("0", 4, 14, 0xFFFFFF, 1)
    root.append(score_lbl)
    root.append(hw.text("LINES", 60, 2, 0x9090C0))
    lines_lbl = hw.text("0", 60, 14, 0xFFFFFF)
    root.append(lines_lbl)
    root.append(hw.text("LVL", 104, 2, 0x9090C0))
    level_lbl = hw.text("1", 104, 14, 0xFFFFFF)
    root.append(level_lbl)

    msg = hw.text("", sw // 2, sh // 2, 0xFFFFFF, 2, (0.5, 0.5), 0x202040)
    root.append(msg)
    hw.show(root)

    try:
        _play(grid, nxt, score_lbl, lines_lbl, level_lbl, msg)
    finally:
        hw.rotate(0)


def _play(grid, nxt, score_lbl, lines_lbl, level_lbl, msg):
    while True:
        board = [[0] * COLS for _ in range(ROWS)]
        for yy in range(ROWS):
            for xx in range(COLS):
                grid[xx, yy] = 0
        bag = []

        def take():
            if not bag:
                bag.extend(range(7))
                for i in range(6, 0, -1):     # shuffle
                    j = random.randint(0, i)
                    bag[i], bag[j] = bag[j], bag[i]
            return bag.pop()

        def fits(kind, rot, px, py):
            for cx, cy in PIECES[kind][rot]:
                x = px + cx
                y = py + cy
                if x < 0 or x >= COLS or y >= ROWS:
                    return False
                if y >= 0 and board[y][x]:
                    return False
            return True

        def draw(kind, rot, px, py, tile):
            for cx, cy in PIECES[kind][rot]:
                x = px + cx
                y = py + cy
                if 0 <= y < ROWS:
                    grid[x, y] = tile

        def erase(kind, rot, px, py):
            for cx, cy in PIECES[kind][rot]:
                x = px + cx
                y = py + cy
                if 0 <= y < ROWS:
                    grid[x, y] = board[y][x]

        def landing(kind, rot, px, py):
            while fits(kind, rot, px, py + 1):
                py += 1
            return py

        def show_next(kind):
            for i in range(8):
                nxt[i] = 0
            for cx, cy in PIECES[kind][0]:
                nxt[cx, cy] = kind + 1

        score = 0
        lines = 0
        level = 1
        score_lbl.text = "0"
        lines_lbl.text = "0"
        level_lbl.text = "1"
        kind = take()
        nxt_kind = take()
        show_next(nxt_kind)
        rot = 0
        px = 3
        py = -1
        ghost_y = landing(kind, rot, px, py)
        fall = 0.0
        move_wait = 0.0
        last_dir = 0
        first = True
        up_ready = True
        msg.hidden = True
        over = False

        while not over:
            if not hw.frame():
                return
            dt = hw.dt
            pad = hw.pad
            nx, nrot, ny = px, rot, py
            moved = False

            # left / right with auto repeat
            d = 0
            if pad.x < -0.5:
                d = -1
            elif pad.x > 0.5:
                d = 1
            if d != last_dir:
                move_wait = 0.0
                last_dir = d
                first = True
            if d:
                move_wait -= dt
                if move_wait <= 0:
                    nx += d
                    move_wait = 0.2 if first else 0.07   # wait longer before repeating
                    first = False
            # turning
            turn = 0
            if pad.tap(hw.A) or (pad.y < -0.6 and up_ready):
                turn = 1
            if pad.tap(hw.B):
                turn = -1
            up_ready = pad.y > -0.3
            if turn:
                cand = (rot + turn) % 4
                for kick in (0, -1, 1, -2, 2):
                    if fits(kind, cand, nx + kick, ny):
                        nrot = cand
                        nx += kick
                        break
            if (nx, nrot) != (px, rot) and fits(kind, nrot, nx, ny):
                moved = True
            else:
                nx, nrot = px, rot

            # falling
            speed = max(0.08, 0.8 - (level - 1) * 0.07)
            if pad.y > 0.5:
                speed = min(speed, 0.04)
            hard = pad.tap(hw.X)
            fall += dt
            lock = False
            if hard:
                ny = landing(kind, nrot, nx, ny)
                score += 2
                lock = True
            elif fall >= speed:
                fall = 0.0
                if fits(kind, nrot, nx, ny + 1):
                    ny += 1
                else:
                    lock = True

            if moved or ny != py or lock:
                erase(kind, rot, px, ghost_y)
                erase(kind, rot, px, py)
                px, rot, py = nx, nrot, ny
                ghost_y = landing(kind, rot, px, py)
                if not lock:
                    draw(kind, rot, px, ghost_y, GHOST)
                draw(kind, rot, px, py, kind + 1)

            if not lock:
                continue

            # ---- the piece lands
            for cx, cy in PIECES[kind][rot]:
                if py + cy < 0:
                    over = True
                else:
                    board[py + cy][px + cx] = kind + 1
            full = [y for y in range(ROWS) if all(board[y])]
            if full:
                for y in full:
                    for x in range(COLS):
                        grid[x, y] = FLASH
                for _ in range(5):
                    if not hw.frame():
                        return
                for y in full:
                    del board[y]
                    board.insert(0, [0] * COLS)
                for yy in range(ROWS):
                    for xx in range(COLS):
                        grid[xx, yy] = board[yy][xx]
                lines += len(full)
                score += (0, 100, 300, 500, 800)[len(full)] * level
                level = lines // 10 + 1
                lines_lbl.text = str(lines)
                level_lbl.text = str(level)
            score_lbl.text = str(score)

            kind = nxt_kind
            nxt_kind = take()
            show_next(nxt_kind)
            rot = 0
            px = 3
            py = -1
            fall = 0.0
            if not fits(kind, rot, px, py) or over:
                over = True
            else:
                ghost_y = landing(kind, rot, px, py)
                draw(kind, rot, px, ghost_y, GHOST)
                draw(kind, rot, px, py, kind + 1)

        msg.text = "Game over\n%d\nA = again" % score
        msg.hidden = False
        while True:
            if not hw.frame():
                return
            if hw.pad.tap(hw.A | hw.START):
                break
