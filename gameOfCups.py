import curses
import random
import time
import sys

# Constants
INIT_WINNING   = 1
INIT_CURSED    = 1
INIT_CUPS      = 5
MAX_ATTEMPTS   = 7
REWARDS        = [0.5, 0.4, 0.3, 0.25, 0.2, 0.15, 0.1]
CURSE_PENALTY  = -0.5

# Color pair IDs
C_GOLD   = 1
C_RED    = 2
C_GREEN  = 3
C_DIM    = 4
C_WHITE  = 5
C_TITLE  = 6
C_BOX    = 7
C_CURSE  = 8
C_WIN    = 9
C_EMPTY  = 10
C_CYAN   = 11

def init_colors():
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(C_GOLD,  curses.COLOR_YELLOW,  -1)
    curses.init_pair(C_RED,   curses.COLOR_RED,      -1)
    curses.init_pair(C_GREEN, curses.COLOR_GREEN,    -1)
    curses.init_pair(C_DIM,   8,                     -1)   # dark grey
    curses.init_pair(C_WHITE, curses.COLOR_WHITE,    -1)
    curses.init_pair(C_TITLE, curses.COLOR_YELLOW,   -1)
    curses.init_pair(C_BOX,   curses.COLOR_CYAN,     -1)
    curses.init_pair(C_CURSE, curses.COLOR_RED,      -1)
    curses.init_pair(C_WIN,   curses.COLOR_GREEN,    -1)
    curses.init_pair(C_EMPTY, curses.COLOR_WHITE,    -1)
    curses.init_pair(C_CYAN,  curses.COLOR_CYAN,     -1)


# Drawing helpers
def flush_input(win):
    win.nodelay(True)
    while win.getch() != -1:
        pass
    win.nodelay(False)

def safe_addstr(win, y, x, text, attr=0):
    h, w = win.getmaxyx()
    if y < 0 or y >= h:
        return
    if x < 0:
        text = text[-x:]
        x = 0
    if x >= w:
        return
    max_len = w - x - 1
    if max_len <= 0:
        return
    try:
        win.addstr(y, x, text[:max_len], attr)
    except curses.error:
        pass

def center_x(win, text):
    _, w = win.getmaxyx()
    return max(0, (w - len(text)) // 2)

def cprint(win, y, text, attr=0):
    safe_addstr(win, y, center_x(win, text), text, attr)

def draw_box(win, y, x, h, w, color=C_BOX):
    attr = curses.color_pair(color)
    # corners
    safe_addstr(win, y,     x,     '╔', attr)
    safe_addstr(win, y,     x+w-1, '╗', attr)
    safe_addstr(win, y+h-1, x,     '╚', attr)
    safe_addstr(win, y+h-1, x+w-1, '╝', attr)
    # horizontal
    for i in range(1, w-1):
        safe_addstr(win, y,     x+i, '═', attr)
        safe_addstr(win, y+h-1, x+i, '═', attr)
    # vertical
    for i in range(1, h-1):
        safe_addstr(win, y+i, x,     '║', attr)
        safe_addstr(win, y+i, x+w-1, '║', attr)

def hline(win, y, x, w, char='─', color=C_DIM):
    attr = curses.color_pair(color)
    for i in range(w):
        safe_addstr(win, y, x+i, char, attr)

def draw_title(win):
    lines = [
        "  ██████╗  █████╗ ███╗   ███╗███████╗",
        " ██╔════╝ ██╔══██╗████╗ ████║██╔════╝",
        " ██║  ███╗███████║██╔████╔██║█████╗  ",
        " ██║   ██║██╔══██║██║╚██╔╝██║██╔══╝  ",
        " ╚██████╔╝██║  ██║██║ ╚═╝ ██║███████╗",
        "  ╚═════╝ ╚═╝  ╚═╝╚═╝     ╚═╝╚══════╝",
        "",
        "          O F   C U P S              ",
    ]
    h, w = win.getmaxyx()
    start_y = 2
    for i, line in enumerate(lines):
        attr = curses.color_pair(C_GOLD) | curses.A_BOLD
        if i == len(lines) - 1:
            attr = curses.color_pair(C_WHITE) | curses.A_BOLD
        cprint(win, start_y + i, line, attr)
    return start_y + len(lines)

def draw_cup(win, y, x, label, state='hidden', selected=False):
    """
    Draw a single cup at (y, x).
    state: 'hidden' | 'winning' | 'cursed' | 'empty'
    """
    cup_art = [
        " ___ ",
        "|   |",
        " \\ / ",
        "  |  ",
        " === ",
    ]

    if state == 'winning':
        inner = ' ★ '
        cup_color = curses.color_pair(C_WIN) | curses.A_BOLD
    elif state == 'cursed':
        inner = ' ☠ '
        cup_color = curses.color_pair(C_CURSE) | curses.A_BOLD
    elif state == 'empty':
        inner = '   '
        cup_color = curses.color_pair(C_DIM)
    else:
        inner = '   '
        cup_color = curses.color_pair(C_GOLD)
        if selected:
            cup_color = curses.color_pair(C_CYAN) | curses.A_BOLD

    art = [
        " ___ ",
        f"|{inner}|",
        " \\ / ",
        "  |  ",
        " === ",
    ]

    label_str = f"[{label}]"
    label_attr = curses.color_pair(C_CYAN) | curses.A_BOLD if selected else curses.color_pair(C_WHITE)

    for i, line in enumerate(art):
        safe_addstr(win, y + i, x, line, cup_color)
    cprint_at = x + (5 - len(label_str)) // 2
    safe_addstr(win, y + len(art), x + max(0, (5 - len(label_str)) // 2), label_str, label_attr)


# Game Logic 
def build_pool(winning, cursed, cups):
    pool = ['winning'] * winning + ['cursed'] * cursed
    n_empty = max(0, cups - len(pool))
    pool += ['empty'] * n_empty
    random.shuffle(pool)
    return pool

def pool_after_attempts(attempt_num):
    #Calculate pool state after `attempt_num` empty picks.
    w, c, cups = INIT_WINNING, INIT_CURSED, INIT_CUPS
    for i in range(attempt_num):
        if (i + 1) % 3 == 0:
            c += 1
        else:
            w += 1
        cups += 1
    return w, c, cups


# Input helpers 
def get_int(win, y, x, prompt, lo, hi, default=None):
    curses.echo()
    curses.curs_set(1)
    safe_addstr(win, y, x, prompt, curses.color_pair(C_WHITE))
    win.refresh()
    while True:
        try:
            inp = win.getstr(y, x + len(prompt), 10).decode().strip()
            if inp == '' and default is not None:
                curses.noecho()
                curses.curs_set(0)
                return default
            val = int(inp)
            if lo <= val <= hi:
                curses.noecho()
                curses.curs_set(0)
                return val
            safe_addstr(win, y+1, x, f"  Enter a number {lo}–{hi}          ", curses.color_pair(C_RED))
            win.refresh()
        except (ValueError, KeyboardInterrupt):
            safe_addstr(win, y+1, x, f"  Enter a number {lo}–{hi}          ", curses.color_pair(C_RED))
            win.refresh()

def wait_key(win, y, msg="Press any key to continue...", color=C_DIM):
    cprint(win, y, msg, curses.color_pair(color))
    win.refresh()
    win.nodelay(False)
    win.getch()

def flash_message(win, y, msg, color, duration=0.6):
    cprint(win, y, msg, curses.color_pair(color) | curses.A_BOLD)
    win.refresh()
    time.sleep(duration)


# Screens
def screen_menu(win):
    win.clear()
    h, w = win.getmaxyx()
    draw_title(win)

    rules_y = 11
    rules = [
        "                HOW TO PLAY                ",
        " • Cups hide: ★ winning balls, ☠ cursed balls, or nothing.",
        " • Empty cup → pool grows (+1★, +1 cup).",
        " • Every 3rd attempt → +1☠ added instead.",
        " • Find ★ faster = bigger multiplier (up to 0.5×).",
        " • Hit ☠ = game ends, -0.5× your bet.",
        " • 7 failed attempts = game ends, no reward.",
        " • Find the winning ball for a bonus!",
        " • Quit any time to cash out early.",
    ]
    for i, line in enumerate(rules):
        color = C_GOLD if i in (0, len(rules)-1) else C_WHITE
        cprint(win, rules_y + i, line, curses.color_pair(color))

    cprint(win, rules_y + len(rules) + 1, "✦  ✦  ✦", curses.color_pair(C_GOLD))

    start_pt_y = rules_y + len(rules) + 3
    cprint(win, start_pt_y,     "Starting points: 1000", curses.color_pair(C_GOLD) | curses.A_BOLD)
    cprint(win, start_pt_y + 1, "Default bet: 100", curses.color_pair(C_WHITE))
    cprint(win, start_pt_y + 3, "Press any key to begin...", curses.color_pair(C_DIM))
    win.refresh()
    win.getch()
    return 1000



def screen_bet(win, points):
    win.clear()
    h, w = win.getmaxyx()

    # stats bar
    bar = f"Total Points: {points} "
    cprint(win, 4, bar, curses.color_pair(C_WHITE))
    hline(win, 5, center_x(win, bar), len(bar), '─', C_DIM)

    cprint(win, 9, "Place your bet:", curses.color_pair(C_WHITE))
    cprint(win, 10, f"(1 – {points}  |  default = {min(100, points)})",
           curses.color_pair(C_DIM))
    win.refresh()

    curses.echo()
    curses.curs_set(1)
    prompt_x = center_x(win, ">>> ")
    safe_addstr(win, 12, prompt_x, ">>> ", curses.color_pair(C_GOLD) | curses.A_BOLD)
    win.refresh()

    default_bet = min(100, points)
    while True:
        try:
            inp = win.getstr(12, prompt_x + 4, 6).decode().strip()
            if inp == '':
                bet = default_bet; break
            val = int(inp)
            if 1 <= val <= points:
                bet = val; break
            safe_addstr(win, 13, prompt_x, f"Enter 1–{points}          ", curses.color_pair(C_RED))
            safe_addstr(win, 12, prompt_x + 4, "      ", 0)
            win.refresh()
        except (ValueError, KeyboardInterrupt):
            safe_addstr(win, 13, prompt_x, f"Enter 1–{points}          ", curses.color_pair(C_RED))
            safe_addstr(win, 12, prompt_x + 4, "      ", 0)
            win.refresh()

    curses.noecho()
    curses.curs_set(0)
    return bet


def screen_game(win, bet, points):
    """
    Returns the bonus earned this round.
    Also returns whether the player wants to quit the whole game.
    """
    attempt   = 0
    w_count   = INIT_WINNING
    c_count   = INIT_CURSED
    cup_count = INIT_CUPS
    pool      = build_pool(w_count, c_count, cup_count)
    selected  = 0
    revealed  = {}  # idx -> content
    quit_game = False
    round_bonus = 0.0

    while attempt < MAX_ATTEMPTS:
        # Recalculate pool state
        w_count, c_count, cup_count = pool_after_attempts(attempt)

        win.clear()
        h, w = win.getmaxyx()

        # Header 
        cprint(win, 1, f" BET: {bet} pts   POINTS: {points}",
               curses.color_pair(C_GOLD) | curses.A_BOLD)

        # attempt pips
        pips = ""
        for i in range(MAX_ATTEMPTS):
            if i < attempt:
                pips += " ● "
            elif i == attempt:
                pips += " ◉ "
            else:
                pips += " ○ "
        cprint(win, 2, f"Attempt {attempt+1}/{MAX_ATTEMPTS}:  {pips}", curses.color_pair(C_WHITE))
        hline(win, 3, 2, w-4, '─', C_DIM)

        # pool info
        n_empty = max(0, cup_count - w_count - c_count)
        pool_str = (f"  Pool →  ★ winning: {w_count}   "
                    f"☠ cursed: {c_count}   "
                    f"○ empty: {n_empty}   "
                    f"🏺 cups: {cup_count}  ")
        cprint(win, 4, pool_str, curses.color_pair(C_DIM))

        # reward hint
        reward = REWARDS[attempt]
        cprint(win, 5, f"  Find ★ now → +{reward}×  |  Hit ☠ any time → -0.5×",
               curses.color_pair(C_WHITE))
        hline(win, 6, 2, w-4, '─', C_DIM)

        # Cups
        cups_per_row = min(cup_count, 8)
        cup_w = 7
        total_cup_w = cups_per_row * cup_w
        start_x = max(2, (w - total_cup_w) // 2)
        cup_y_start = 8

        for i in range(cup_count):
            row = i // cups_per_row
            col = i % cups_per_row
            cx = start_x + col * cup_w
            cy = cup_y_start + row * 7
            if i in revealed:
                state = revealed[i]
            else:
                state = 'hidden'
            draw_cup(win, cy, cx, i+1, state, selected=(i == selected and i not in revealed))

        # Controls 
        ctrl_y = cup_y_start + ((cup_count - 1) // cups_per_row + 1) * 7 + 1
        hline(win, ctrl_y, 2, w-4, '─', C_DIM)
        ctrl_y += 1
        cprint(win, ctrl_y,
               "  ← → : Select cup   ENTER / number: Pick cup   Q: Quit game  ",
               curses.color_pair(C_DIM))


        win.refresh()

        # Input
        win.nodelay(False)
        key = win.getch()

        if key in (curses.KEY_LEFT,):
            selected = (selected - 1) % cup_count
        elif key in (curses.KEY_RIGHT,):
            selected = (selected + 1) % cup_count
        elif key in (ord('\n'), ord(' ')):
            pick = selected
            if pick in revealed:
                cprint(win, ctrl_y + 2, "  Already revealed! Pick another.",
                       curses.color_pair(C_RED))
                win.refresh(); time.sleep(0.5)
                continue
            # Reveal
            content = pool[pick]
            revealed[pick] = content

            win.clear()  # redraw with reveal
            h, w = win.getmaxyx()

            # redraw header
            cprint(win, 1, f" BET: {bet} pts   POINTS: {points}",
                   curses.color_pair(C_GOLD) | curses.A_BOLD)
            pips = "".join(" ● " if i < attempt else " ◉ " if i == attempt else " ○ "
                            for i in range(MAX_ATTEMPTS))
            cprint(win, 2, f"Attempt {attempt+1}/{MAX_ATTEMPTS}:  {pips}", curses.color_pair(C_WHITE))
            hline(win, 3, 2, w-4, '─', C_DIM)
            n_empty = max(0, cup_count - w_count - c_count)
            pool_str = (f"  Pool →  ★ winning: {w_count}   "
                        f"☠ cursed: {c_count}   "
                        f"○ empty: {n_empty}   "
                        f"🏺 cups: {cup_count}  ")
            cprint(win, 4, pool_str, curses.color_pair(C_DIM))
            cprint(win, 5, f"  Find ★ now → +{reward}×  |  Hit ☠ any time → -0.5×",
                   curses.color_pair(C_WHITE))
            hline(win, 6, 2, w-4, '─', C_DIM)
            for i in range(cup_count):
                row = i // cups_per_row; col = i % cups_per_row
                cx = start_x + col * cup_w; cy = cup_y_start + row * 7
                draw_cup(win, cy, cx, i+1, revealed.get(i, 'hidden'),
                         selected=(i == pick))
            win.refresh()
            time.sleep(0.5)
            flush_input(win)

            if content == 'winning':
                round_bonus = REWARDS[attempt]
                cprint(win, ctrl_y + 1,
                       f"  ★  WINNING BALL!  +{round_bonus}×  →  +{int(bet * round_bonus)} pts!  ★",
                       curses.color_pair(C_WIN) | curses.A_BOLD)
                win.refresh()
                time.sleep(1.2)
                flush_input(win)
                return round_bonus, False

            elif content == 'cursed':
                round_bonus = CURSE_PENALTY
                cprint(win, ctrl_y + 1,
                       f"  ☠  CURSED BALL!  -0.5×  →  -{int(bet * 0.5)} pts!  ☠",
                       curses.color_pair(C_CURSE) | curses.A_BOLD)
                win.refresh(); time.sleep(1.2)
                return round_bonus, False

            else:
                # empty cup — show result, then update pool
                cprint(win, ctrl_y + 1,
                       "  ○  Empty cup...  +1★ and +1 cup added to the pool.  ○",
                       curses.color_pair(C_DIM) | curses.A_BOLD)
                win.refresh()
                time.sleep(1.5)
                flush_input(win)
                attempt += 1
                if attempt < MAX_ATTEMPTS:
                    pool = build_pool(*pool_after_attempts(attempt))
                    revealed = {}
                    selected = 0

        # number key — instantly pick that cup
        elif ord('1') <= key <= ord('9'):
            num = key - ord('0') - 1
            if 0 <= num < cup_count and num not in revealed:
                selected = num
                key = ord('\n')          # fall through to the pick logic below
                # inline pick (mirrors the Enter branch)
                pick = selected
                content = pool[pick]
                revealed[pick] = content

                win.clear()
                h, w = win.getmaxyx()
                cprint(win, 1, f" BET: {bet} pts   POINTS: {points}",
                       curses.color_pair(C_GOLD) | curses.A_BOLD)
                pips = "".join(" ● " if i < attempt else " ◉ " if i == attempt else " ○ "
                               for i in range(MAX_ATTEMPTS))
                cprint(win, 2, f"Attempt {attempt+1}/{MAX_ATTEMPTS}:  {pips}", curses.color_pair(C_WHITE))
                hline(win, 3, 2, w-4, '─', C_DIM)
                n_empty = max(0, cup_count - w_count - c_count)
                pool_str = (f"  Pool →  ★ winning: {w_count}   "
                            f"☠ cursed: {c_count}   "
                            f"○ empty: {n_empty}   "
                            f"🏺 cups: {cup_count}  ")
                cprint(win, 4, pool_str, curses.color_pair(C_DIM))
                cprint(win, 5, f"  Find ★ now → +{reward}×  |  Hit ☠ any time → -0.5×",
                       curses.color_pair(C_WHITE))
                hline(win, 6, 2, w-4, '─', C_DIM)
                for i in range(cup_count):
                    row = i // cups_per_row; col = i % cups_per_row
                    cx = start_x + col * cup_w; cy = cup_y_start + row * 7
                    draw_cup(win, cy, cx, i+1, revealed.get(i, 'hidden'), selected=(i == pick))
                win.refresh()
                time.sleep(0.5)
                flush_input(win)

                if content == 'winning':
                    round_bonus = REWARDS[attempt]
                    cprint(win, ctrl_y + 1,
                           f"  ★  WINNING BALL!  +{round_bonus}×  →  +{int(bet * round_bonus)} pts!  ★",
                           curses.color_pair(C_WIN) | curses.A_BOLD)
                    win.refresh(); time.sleep(1.2)
                    flush_input(win)
                    return round_bonus, False
                elif content == 'cursed':
                    round_bonus = CURSE_PENALTY
                    cprint(win, ctrl_y + 1,
                           f"  ☠  CURSED BALL!  -0.5×  →  -{int(bet * 0.5)} pts!  ☠",
                           curses.color_pair(C_CURSE) | curses.A_BOLD)
                    win.refresh(); time.sleep(1.2)
                    flush_input(win)
                    return round_bonus, False
                else:
                    cprint(win, ctrl_y + 1,
                           "  ○  Empty cup...  +1★ and +1 cup added to the pool.  ○",
                           curses.color_pair(C_DIM) | curses.A_BOLD)
                    win.refresh()
                    time.sleep(1.5)
                    flush_input(win)
                    attempt += 1
                    if attempt < MAX_ATTEMPTS:
                        pool = build_pool(*pool_after_attempts(attempt))
                        revealed = {}
                        selected = 0

        elif key in (ord('q'), ord('Q')):
            quit_game = True
            return 0.0, True

    # Timed out
    cprint(win, 8, "  ⏰  7 attempts used. No reward.  ⏰",
           curses.color_pair(C_RED) | curses.A_BOLD)
    win.refresh()
    time.sleep(1.5)
    flush_input(win)
    return 0.0, False


def screen_game_over(win, start_pts, final_pts, bonus, bet):
    win.clear()
    h, w = win.getmaxyx()

    cprint(win, 2, "╔═══════════════════════╗", curses.color_pair(C_GOLD) | curses.A_BOLD)
    cprint(win, 3, "║    G A M E  O V E R   ║", curses.color_pair(C_GOLD) | curses.A_BOLD)
    cprint(win, 4, "╚═══════════════════════╝", curses.color_pair(C_GOLD) | curses.A_BOLD)

    net = final_pts - start_pts
    if net > 0:
        verdict = "You walked away richer. Well played."
        vcol    = C_WIN
    elif final_pts == 0:
        verdict = "The cups took everything. Better luck next time."
        vcol    = C_CURSE
    else:
        verdict = "A mixed fortune. The cups are fickle."
        vcol    = C_DIM

    cprint(win, 6, verdict, curses.color_pair(vcol) | curses.A_BOLD)
    hline(win, 7, 4, w - 8, '─', C_DIM)

    cprint(win, 9,  f"Started with :  {start_pts} pts",  curses.color_pair(C_WHITE))
    this_bonus = bonus
    bcol = C_WIN if this_bonus > 0 else C_CURSE if this_bonus < 0 else C_DIM
    cprint(win, 10, f"Multiplier:  {this_bonus:+.2f}×",
           curses.color_pair(bcol) | curses.A_BOLD)
    cprint(win, 11, f"Net gain/loss:  {net:+d} pts",
           curses.color_pair(C_GREEN if net >= 0 else C_RED) | curses.A_BOLD)
    cprint(win, 12, f"Final points :  {final_pts} pts",  curses.color_pair(C_GOLD) | curses.A_BOLD)


    hline(win, 15, 4, w - 8, '─', C_DIM)
    cprint(win, 17, "Press R to play again, or Q to quit.",
           curses.color_pair(C_DIM))
    win.refresh()

    while True:
        key = win.getch()
        if key in (ord('r'), ord('R')):
            return True
        if key in (ord('q'), ord('Q'), 27):
            return False


# Main loop 
def main(stdscr):
    curses.curs_set(0)
    curses.noecho()
    stdscr.keypad(True)
    init_colors()

    while True:
        # Menu
        start_pts = screen_menu(stdscr)
        points    = start_pts

        # Bet screen
        bet = screen_bet(stdscr, points)

        # Play game
        bonus, quit_early = screen_game(stdscr, bet, points)

        # Calculate final points
        clamped     = max(-1.0, bonus)
        net         = round(bet * clamped)
        final_pts   = max(0, start_pts + net)

        play_again = screen_game_over(stdscr, start_pts, final_pts, bonus, bet)
        if not play_again:
            break


if __name__ == '__main__':
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        print("\nThanks for playing Game of Cups!")
        sys.exit(0)