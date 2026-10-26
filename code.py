# code.py - the game menu.
#   D0 = up, D1 = down, D2 = start the game   (the joystick + A / START work too)
#   Inside a game, any of D0 / D1 / D2 comes back here.
import gc
import sys
import traceback
import displayio
import terminalio
from adafruit_display_text import label

import hw
import art

TITLE = "GAMES"

GAMES = (
    # name,          module,       icon color for the row highlight
    ("Fruit Catch", "g_fruit", 0xE8202A),
    ("Balloon Pop", "g_balloon", 0xFF5AC8),
    ("Paint", "g_paint", 0x3A7AFF),
    ("Snake", "g_snake", 0xFFB000),
    ("Dino Run", "g_dino", 0x3CC23C),
    ("Space", "g_space", 0x9A40E0),
    ("Breakout", "g_breakout", 0x20B0C0),
    ("Tetris", "g_tetris", 0x00D8E0),
)

ROW_H = 22
TOP = 24
VISIBLE = 5


def make_icons():
    """One 16x16-ish picture per game."""
    icons = []
    fruit = art.fruit_arts()[0]
    icons.append(art.sprite(fruit))
    bal = art.balloon_arts(11, 20, art.PK, art.r, art.WH, art.S)[0]
    icons.append(art.sprite(bal))
    icons.append(art.sprite(art.from_text(art.ICON_PAINT)))
    icons.append(art.sprite(art.from_text(art.ICON_SNAKE)))
    icons.append(art.sprite(art.dino_arts()[0]))
    icons.append(art.sprite(art.from_text(art.SHIP)))
    icons.append(art.sprite(art.from_text(art.ICON_BREAKOUT)))
    icons.append(art.sprite(art.from_text(art.ICON_TETRIS)))
    return icons


def build_menu():
    root = displayio.Group()
    bg = hw.solid(hw.W, hw.H, 0x101830)
    root.append(bg)

    # rainbow title
    colors = (0xFF4040, 0xFFA020, 0xFFE040, 0x40E040, 0x40A0FF, 0xC060FF)
    x = (hw.W - len(TITLE) * 12) // 2
    for i, ch in enumerate(TITLE):
        t = label.Label(terminalio.FONT, text=ch, color=colors[i % len(colors)], scale=2)
        t.anchor_point = (0, 0)
        t.anchored_position = (x + i * 12, 0)
        root.append(t)

    bar = hw.solid(hw.W - 8, ROW_H - 2, 0x304070)
    bar.x = 4
    root.append(bar)

    rows = displayio.Group()
    root.append(rows)
    icons = make_icons()
    for i, (name, _, _) in enumerate(GAMES):
        row = displayio.Group(y=i * ROW_H)
        ic = icons[i]
        # center the picture inside a 26x20 box
        ic.x = 8 + (26 - ic.tile_width) // 2
        ic.y = (ROW_H - ic.tile_height) // 2 - 1
        row.append(ic)
        t = label.Label(terminalio.FONT, text=name, color=0xFFFFFF, scale=2)
        t.anchor_point = (0, 0.5)
        t.anchored_position = (42, ROW_H // 2 - 1)
        row.append(t)
        rows.append(row)

    # the scroll arrows sit at the right end of the list
    up = label.Label(terminalio.FONT, text="^", color=0x8090B0)
    up.anchor_point = (1, 0)
    up.anchored_position = (hw.W - 1, TOP)
    dn = label.Label(terminalio.FONT, text="v", color=0x8090B0)
    dn.anchor_point = (1, 1)
    dn.anchored_position = (hw.W - 1, hw.H - 1)
    root.append(up)
    root.append(dn)

    # battery in the top right corner, as big as the title:
    # the percent in 2x text and a battery picture drawn 2x bigger
    icon_bmp = displayio.Bitmap(14, 8, 3)
    icon_pal = displayio.Palette(3)
    icon_pal.make_transparent(0)
    icon_pal[1] = 0xC0C0D0
    icon_pal[2] = 0x60E060
    for i in range(12):
        icon_bmp[i, 0] = icon_bmp[i, 7] = 1
    for j in range(8):
        icon_bmp[0, j] = icon_bmp[11, j] = 1
    for j in range(2, 6):
        icon_bmp[12, j] = icon_bmp[13, j] = 1
    icon_group = displayio.Group(scale=2, y=3)
    icon = displayio.TileGrid(icon_bmp, pixel_shader=icon_pal)
    icon_group.append(icon)
    # lightning bolt shown while charging, drawn over the battery picture
    bolt = art.sprite(art.from_text((
        "...KYK",
        "..KYK.",
        ".KYYYK",
        "KYYYK.",
        ".KYK..",
        "KYK...",
    )), 3, 1)
    bolt.hidden = True
    icon_group.append(bolt)
    icon_group.hidden = True
    root.append(icon_group)
    batt = hw.text("", hw.W - 1, 0, 0xC0C0D0, 2, (1, 0))
    root.append(batt)
    return root, bar, rows, up, dn, (batt, icon_group, icon, bolt)


def show_battery(batt):
    label_, icon_group, icon, bolt = batt
    p = hw.battery.percent()
    bolt.hidden = p is None or not hw.battery.charging()
    if p is None:
        icon_group.hidden = True
        label_.text = ""
        return
    if p >= 50:
        color = 0x60E060
    elif p >= 20:
        color = 0xFFC040
    else:
        color = 0xFF5050
    icon.pixel_shader[2] = color
    bmp = icon.bitmap
    fill = (p * 10 + 50) // 100           # 0..10 bars inside the battery
    for i in range(10):
        for j in range(2, 6):
            bmp[1 + i, j] = 2 if i < fill else 0
    label_.text = "%d%%" % p
    # put the picture just left of the text (the text width changes: 9% / 76% / 100%)
    icon_group.x = hw.W - 1 - label_.bounding_box[2] * 2 - 4 - 28
    icon_group.hidden = False


def run_game(module_name):
    gc.collect()
    try:
        mod = __import__(module_name)
        mod.run()
    except Exception as e:  # show the problem instead of freezing
        traceback.print_exception(e)
        err = displayio.Group()
        err.append(hw.solid(hw.W, hw.H, 0x400000))
        t = label.Label(terminalio.FONT, text="Oops! " + module_name + "\n" + str(e)[:80],
                        color=0xFFFFFF)
        t.anchor_point = (0, 0)
        t.anchored_position = (4, 4)
        err.append(t)
        hw.show(err)
        while hw.frame():
            pass
    hw.rotate(0)
    if module_name in sys.modules:
        del sys.modules[module_name]
    gc.collect()


def main():
    root, bar, rows, up, dn, batt = build_menu()
    batt_timer = 0.0
    sel = 0
    scroll = 0
    stick_ready = True
    redraw = True
    hw.show(root)
    while True:
        hw.frame()
        batt_timer -= hw.dt
        if batt_timer <= 0:          # read the battery every 5 seconds
            batt_timer = 5.0
            show_battery(batt)
        move = 0
        go = False
        for b in hw.side.pressed:
            if b == 0:
                move = -1
            elif b == 1:
                move = 1
            else:
                go = True
        p = hw.pad
        if p.y < -0.6 or p.y > 0.6:
            if stick_ready:
                move = -1 if p.y < 0 else 1
                stick_ready = False
        elif -0.3 < p.y < 0.3:
            stick_ready = True
        if p.tap(hw.A | hw.START):
            go = True

        if move:
            sel = (sel + move) % len(GAMES)
            if sel < scroll:
                scroll = sel
            elif sel >= scroll + VISIBLE:
                scroll = sel - VISIBLE + 1
        if move or redraw:
            redraw = False
            rows.y = TOP - scroll * ROW_H
            for i in range(len(GAMES)):
                rows[i].hidden = not scroll <= i < scroll + VISIBLE
            bar.y = TOP + (sel - scroll) * ROW_H
            bar.pixel_shader[0] = (GAMES[sel][2] >> 2) & 0x3F3F3F | 0x202020
            up.hidden = scroll == 0
            dn.hidden = scroll + VISIBLE >= len(GAMES)

        if go:
            run_game(GAMES[sel][1])
            hw.show(root)


main()
