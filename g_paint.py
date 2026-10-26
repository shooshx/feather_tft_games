# Paint - draw with the joystick.
#   A      = pen down / pen up (draw or just move)
#   B      = next color
#   X      = brush size
#   Y      = clear the page (hold it for half a second, so it doesn't happen by accident)
import displayio
import bitmaptools
import hw

COLORS = (0xFFFFFF, 0x101010, 0xE8202A, 0xFF8C1A, 0xFFE23A, 0x3CC23C,
          0x3A7AFF, 0x9A40E0, 0xFF5AC8, 0x7A4A1A, 0x80E8FF, 0x808080)
SIZES = (1, 3, 5, 9)          # brush diameters
BAR = 12                      # toolbar height
CW = hw.W
CH = hw.H - BAR


def _disk_rows(dia):
    """Half-widths of a round brush, one per row."""
    rad = dia / 2
    rows = []
    for i in range(dia):
        dy = i + 0.5 - rad
        hw2 = rad * rad - dy * dy
        rows.append(int((max(0, hw2)) ** 0.5 + 0.5))
    return rows


def _cursor_sheet():
    """Ring-shaped cursors (black/white dashes) for each brush size."""
    size = 13
    bmp = displayio.Bitmap(size * len(SIZES), size, 3)
    for n, dia in enumerate(SIZES):
        rad = dia / 2 + 1.2
        c = size / 2
        for yy in range(size):
            for xx in range(size):
                dx = xx + 0.5 - c
                dy = yy + 0.5 - c
                dd = (dx * dx + dy * dy) ** 0.5
                if abs(dd - rad) < 0.6:
                    bmp[n * size + xx, yy] = 1 + (xx + yy) % 2
        if dia == 1:
            for k in (1, 2):
                bmp[n * size + 6 - k - 1, 6] = 1
                bmp[n * size + 6 + k + 1, 6] = 1
                bmp[n * size + 6, 6 - k - 1] = 2
                bmp[n * size + 6, 6 + k + 1] = 2
    pal = displayio.Palette(3)
    pal.make_transparent(0)
    pal[1] = 0x000000
    pal[2] = 0xFFFFFF
    return bmp, pal, size


def run():
    root = displayio.Group()
    canvas = displayio.Bitmap(CW, CH, len(COLORS))
    cpal = displayio.Palette(len(COLORS))
    for i, c in enumerate(COLORS):
        cpal[i] = c
    root.append(displayio.TileGrid(canvas, pixel_shader=cpal, y=BAR))

    # toolbar
    root.append(hw.solid(hw.W, BAR, 0x303040))
    frame = hw.solid(10, 10, 0x000000)
    frame.x, frame.y = 2, 1
    root.append(frame)
    swatch = hw.solid(8, 8, COLORS[1])
    swatch.x, swatch.y = 3, 2
    root.append(swatch)
    size_lbl = hw.text("", 15, 0, 0xFFFFFF)
    root.append(size_lbl)
    pen_lbl = hw.text("", 42, 0, 0xFFFFFF)
    root.append(pen_lbl)
    root.append(hw.text("A:pen B:col X:size Y:clear", 74, 0, 0x9090A0))

    cbmp, cpal2, csize = _cursor_sheet()
    cursor = displayio.TileGrid(cbmp, pixel_shader=cpal2, tile_width=csize, tile_height=csize)
    root.append(cursor)

    clear_bar = hw.solid(hw.W, 3, 0xE8202A)
    clear_bar.y = BAR - 3
    clear_bar.hidden = True
    root.append(clear_bar)

    hw.show(root)

    brushes = [_disk_rows(dd) for dd in SIZES]
    color = 1
    size_i = 1
    pen = True
    x = CW / 2
    y = CH / 2
    last = None
    hold = 0.0

    def stamp(px, py):
        rows = brushes[size_i]
        dia = SIZES[size_i]
        top = py - dia // 2
        for i, half in enumerate(rows):
            yy = top + i
            if 0 <= yy < CH and half:
                bitmaptools.fill_region(canvas, max(0, px - half + 1), yy,
                                        min(CW, px + half), yy + 1, color)

    def ui():
        swatch.pixel_shader[0] = COLORS[color]
        size_lbl.text = "sz%d" % (size_i + 1)
        pen_lbl.text = "DRAW" if pen else "MOVE"
        pen_lbl.color = 0x60FF60 if pen else 0xFFB040
        cursor[0] = size_i

    canvas.fill(0)
    ui()
    while hw.frame():
        dt = hw.dt
        pad = hw.pad
        changed = False
        if pad.tap(hw.A):
            pen = not pen
            last = None
            changed = True
        if pad.tap(hw.B):
            color = (color + 1) % len(COLORS)
            changed = True
        if pad.tap(hw.X):
            size_i = (size_i + 1) % len(SIZES)
            changed = True
        if changed:
            ui()

        # hold Y (or START) to clear
        if pad.held(hw.Y | hw.START):
            hold += dt
            clear_bar.hidden = False
            w = int(hw.W * min(1, hold / 0.5))
            clear_bar.x = w - hw.W
            if hold >= 0.5:
                canvas.fill(0)
                hold = -100          # don't clear again until released
        else:
            hold = 0
            clear_bar.hidden = True

        # move: slow near the middle of the stick, fast at the edge
        sx = pad.x * abs(pad.x)
        sy = pad.y * abs(pad.y)
        x = max(0, min(CW - 1, x + sx * 110 * dt))
        y = max(0, min(CH - 1, y + sy * 110 * dt))
        ix = int(x)
        iy = int(y)
        cursor.x = ix - csize // 2
        cursor.y = iy - csize // 2 + BAR

        if pen:
            if last is None:
                stamp(ix, iy)
            elif last != (ix, iy):
                lx, ly = last
                steps = max(abs(ix - lx), abs(iy - ly))
                if SIZES[size_i] == 1:
                    bitmaptools.draw_line(canvas, lx, ly, ix, iy, color)
                else:
                    for k in range(1, steps + 1):
                        stamp(lx + (ix - lx) * k // steps, ly + (iy - ly) * k // steps)
            last = (ix, iy)
