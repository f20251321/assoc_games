
import curses
import random
import time
import sys
import copy

# ── Color pair IDs ──────────────────────────────────────────────────────────
C_GOLD   = 1
C_RED    = 2
C_GREEN  = 3
C_DIM    = 4
C_WHITE  = 5
C_TITLE  = 6
C_BOX    = 7
C_CYAN   = 8
C_MAGENTA= 9
C_YELLOW = 10
C_BLUE   = 11
C_P1_BG  = 12
C_P2_BG  = 13

# Chip colors: value → color pair
CHIP_COLORS = {1: C_WHITE, 5: C_RED, 10: C_BLUE, 25: C_GREEN}
CHIP_SYMBOLS = {1: "○", 5: "●", 10: "◆", 25: "★"}

def init_colors():
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(C_GOLD,    curses.COLOR_YELLOW,  -1)
    curses.init_pair(C_RED,     curses.COLOR_RED,     -1)
    curses.init_pair(C_GREEN,   curses.COLOR_GREEN,   -1)
    curses.init_pair(C_DIM,     8,                    -1)
    curses.init_pair(C_WHITE,   curses.COLOR_WHITE,   -1)
    curses.init_pair(C_TITLE,   curses.COLOR_YELLOW,  -1)
    curses.init_pair(C_BOX,     curses.COLOR_CYAN,    -1)
    curses.init_pair(C_CYAN,    curses.COLOR_CYAN,    -1)
    curses.init_pair(C_MAGENTA, curses.COLOR_MAGENTA, -1)
    curses.init_pair(C_YELLOW,  curses.COLOR_YELLOW,  -1)
    curses.init_pair(C_BLUE,    curses.COLOR_BLUE,    -1)
    curses.init_pair(C_P1_BG,   curses.COLOR_BLACK,   curses.COLOR_CYAN)
    curses.init_pair(C_P2_BG,   curses.COLOR_BLACK,   curses.COLOR_MAGENTA)


# ── Drawing helpers ─────────────────────────────────────────────────────────
def safe_addstr(win, y, x, text, attr=0):
    h, w = win.getmaxyx()
    if y < 0 or y >= h or x >= w:
        return
    if x < 0:
        text = text[-x:]
        x = 0
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

def hline(win, y, x, w, char='─', color=C_DIM):
    attr = curses.color_pair(color)
    for i in range(w):
        safe_addstr(win, y, x + i, char, attr)

def flush_input(win):
    win.nodelay(True)
    while win.getch() != -1:
        pass
    win.nodelay(False)


# ── Random partition helper ─────────────────────────────────────────────────
def random_partition(n, k, min_val=1):
    if min_val * k > n:
        return None
    parts = [min_val] * k
    remaining = n - min_val * k
    for _ in range(remaining):
        idx = random.randint(0, k - 1)
        parts[idx] += 1
    random.shuffle(parts)
    return parts


# ── Nim Game Logic ──────────────────────────────────────────────────────────
class Nim:
    def __init__(self):
        self.num_piles = random.randint(4, 6)
        k = self.num_piles

        # Fixed totals for chip denominations
        total_fives = 20
        total_ones = 20
        total_tens = 6

        # Adjust for pile count > 4
        for _ in range(4, k):
            total_fives -= 4
            total_ones -= 5

        # Each pile gets exactly 1x25 and at least 1x10
        # Distribute tens: each pile gets at least 1, rest distributed randomly
        dtens = random_partition(total_tens, k, 1)
        dfives = random_partition(total_fives, k, 1)
        dones = random_partition(total_ones, k, 1)

        # Build initial counts (each pile = dones[i] + dfives[i] + dtens[i] + 1 for the 25)
        counts = [dones[i] + dfives[i] + dtens[i] + 1 for i in range(k)]

        # Ensure XOR of counts is non-zero by adjusting ones between piles
        # We move one chip from one pile to another (keeping totals the same)
        max_attempts = 100
        attempt = 0
        while attempt < max_attempts:
            xorsum = 0
            for c in counts:
                xorsum ^= c
            if xorsum != 0:
                break
            # XOR is 0 — move 1 one-chip from a pile with >2 ones to another
            # This changes two pile counts by ±1, which changes XOR
            donors = [i for i in range(k) if dones[i] > 2]
            if donors:
                src = random.choice(donors)
                dst = random.choice([i for i in range(k) if i != src])
                dones[src] -= 1
                dones[dst] += 1
                counts[src] -= 1
                counts[dst] += 1
            else:
                # Fallback: just add 1 extra one-chip to a random pile
                idx = random.randint(0, k - 1)
                dones[idx] += 1
                counts[idx] += 1
            attempt += 1

        # Build the actual stacks
        self.stacks = []
        for i in range(k):
            pile = [1]*dones[i] + [5]*dfives[i] + [10]*dtens[i] + [25]*1
            pile.sort(reverse=True)  # 25 at bottom, then 10s, 5s, 1s on top
            self.stacks.append(pile)
        self.counts = [len(s) for s in self.stacks]

    def remove(self, index, value):
        if value > self.counts[index] or value < 0:
            raise IndexError("Invalid removal")
        score = 0
        for _ in range(value):
            score += self.stacks[index].pop()
            self.counts[index] -= 1
        return score

    def check(self):
        xorsum = 0
        for c in self.counts:
            xorsum ^= c
        return xorsum != 0

    def is_over(self):
        return all(c == 0 for c in self.counts)

    def ai_move(self):
        """Optimal 9/11 AI. Returns (pile_index, num_to_remove)."""
        xorsum = 0
        for c in self.counts:
            xorsum ^= c
        if xorsum != 0:
            for i, c in enumerate(self.counts):
                target = c ^ xorsum
                if target < c:
                    return i, c - target
        non_empty = [i for i, c in enumerate(self.counts) if c > 0]
        pile = random.choice(non_empty)
        return pile, 1

    def ai_move_random(self):
        """Random AI. Picks a random pile and removes a random number of chips."""
        non_empty = [i for i, c in enumerate(self.counts) if c > 0]
        pile = random.choice(non_empty)
        num = random.randint(1, self.counts[pile])
        return pile, num


# ── Draw the title ──────────────────────────────────────────────────────────
def draw_title(win):
    lines = [
        "  █████╗        ██╗ ██╗",
        " ██╔══██╗      ███║███║",
        " ╚██████║█████╗╚██║╚██║",
        "  ╚═══██║╚════╝ ██║ ██║",
        "  █████╔╝       ██║ ██║",
        "  ╚════╝        ╚═╝ ╚═╝",
        "",
        "    G A M E   O F   C H I P S",
    ]
    start_y = 2
    for i, line in enumerate(lines):
        attr = curses.color_pair(C_GOLD) | curses.A_BOLD
        if i == len(lines) - 1:
            attr = curses.color_pair(C_WHITE) | curses.A_BOLD
        cprint(win, start_y + i, line, attr)
    return start_y + len(lines)


# ── Draw a single pile ──────────────────────────────────────────────────────
def draw_pile(win, y, x, pile_idx, stack, count, sel_pile=False, highlight_top=0):
    pile_width = 8
    label = f"Pile {pile_idx + 1}"
    label_attr = curses.color_pair(C_CYAN) | curses.A_BOLD if sel_pile else curses.color_pair(C_WHITE)
    safe_addstr(win, y + 1, x + (pile_width - len(label)) // 2, label, label_attr)

    count_str = f"({count})"
    safe_addstr(win, y + 2, x + (pile_width - len(count_str)) // 2, count_str, curses.color_pair(C_DIM))

    safe_addstr(win, y, x, "━" * pile_width, curses.color_pair(C_DIM))

    if count == 0:
        safe_addstr(win, y - 1, x + 1, "empty", curses.color_pair(C_DIM))
        return

    for i in range(count):
        chip_val = stack[i]
        color = CHIP_COLORS.get(chip_val, C_WHITE)
        symbol = CHIP_SYMBOLS.get(chip_val, "?")
        chip_y = y - 1 - i

        if chip_y < 1:
            safe_addstr(win, 1, x + 1, f"▲+{count - i}", curses.color_pair(C_GOLD))
            break

        is_highlighted = (i >= count - highlight_top) and highlight_top > 0
        if is_highlighted:
            attr = curses.color_pair(C_RED) | curses.A_BOLD | curses.A_REVERSE
        else:
            attr = curses.color_pair(color) | curses.A_BOLD

        chip_str = f"[{symbol}{chip_val:>2} ]"
        safe_addstr(win, chip_y, x, chip_str, attr)


# ═══════════════════════════════════════════════════════════════════════════
#                              S C R E E N S
# ═══════════════════════════════════════════════════════════════════════════

# ── Screen: Menu + Rules ────────────────────────────────────────────────────
def screen_menu(win):
    win.clear()
    h, w = win.getmaxyx()
    draw_title(win)

    rules_y = 11
    rules = [
        "              HOW TO PLAY                ",
        "",
        " 9/11 is a strategy game played with piles of chips.",
        " Players take turns removing chips from a single pile.",
        " You can remove any number of chips from one pile.",
        " The player who takes the LAST chip WINS!",
        "",
        " Chips have different values (score points!):",
    ]
    for i, line in enumerate(rules):
        if i == 0:
            attr = curses.color_pair(C_GOLD) | curses.A_BOLD
        else:
            attr = curses.color_pair(C_WHITE)
        cprint(win, rules_y + i, line, attr)

    # Colored chip legend
    ly = rules_y + 8
    lx = center_x(win, "   O  1pt         *  5pt         ")
    safe_addstr(win, ly, lx + 3, "○  1pt", curses.color_pair(C_WHITE) | curses.A_BOLD)
    safe_addstr(win, ly, lx + 17, "●  5pt", curses.color_pair(C_RED) | curses.A_BOLD)
    safe_addstr(win, ly + 1, lx + 3, "◆ 10pt", curses.color_pair(C_BLUE) | curses.A_BOLD)
    safe_addstr(win, ly + 1, lx + 17, "★ 25pt", curses.color_pair(C_GREEN) | curses.A_BOLD)

    more = [
        "",
        " You always take from the TOP of a pile.",
        " Chip values don't affect strategy — only counts matter.",
        " But they DO affect your final score!",
    ]
    for i, line in enumerate(more):
        cprint(win, ly + 3 + i, line, curses.color_pair(C_WHITE))

    cprint(win, ly + 8, "✦  ✦  ✦", curses.color_pair(C_GOLD))
    cprint(win, ly + 10, "Press any key to continue...", curses.color_pair(C_DIM))
    win.refresh()
    win.getch()


# ── Screen: Mode Selection ──────────────────────────────────────────────────
def screen_mode_select(win):
    selected = 0
    modes = [
        ("1v1  —  Two Players", "Two humans, one keyboard. Take turns!"),
        ("vs AI  —  Challenge the Machine", "Play against an optimal 9/11 AI."),
        ("vs AI (Easy)  —  Random Bot", "Play against a random-move AI. Good for practice!"),
    ]

    while True:
        win.clear()
        h, w = win.getmaxyx()

        cprint(win, 3, "╔═══════════════════════════════════╗", curses.color_pair(C_GOLD) | curses.A_BOLD)
        cprint(win, 4, "║       S E L E C T   M O D E       ║", curses.color_pair(C_GOLD) | curses.A_BOLD)
        cprint(win, 5, "╚═══════════════════════════════════╝", curses.color_pair(C_GOLD) | curses.A_BOLD)

        for i, (title, desc) in enumerate(modes):
            y = 9 + i * 4
            if i == selected:
                marker = "▸ "
                title_attr = curses.color_pair(C_CYAN) | curses.A_BOLD | curses.A_REVERSE
                desc_attr = curses.color_pair(C_WHITE)
            else:
                marker = "  "
                title_attr = curses.color_pair(C_DIM)
                desc_attr = curses.color_pair(C_DIM)

            cprint(win, y, f"{marker}{title}", title_attr)
            cprint(win, y + 1, desc, desc_attr)

        cprint(win, 22, "↑ ↓ : Select    ENTER: Confirm    Q: Quit", curses.color_pair(C_DIM))
        win.refresh()

        key = win.getch()
        if key == curses.KEY_UP:
            selected = (selected - 1) % len(modes)
        elif key == curses.KEY_DOWN:
            selected = (selected + 1) % len(modes)
        elif key in (ord('\n'), ord(' ')):
            return ["1v1", "ai", "ai_easy"][selected]
        elif key in (ord('q'), ord('Q'), 27):
            return None


# ── Screen: Name Input ──────────────────────────────────────────────────────
def screen_names(win, mode):
    win.clear()
    h, w = win.getmaxyx()

    cprint(win, 3, "╔═══════════════════════════════╗", curses.color_pair(C_GOLD) | curses.A_BOLD)
    cprint(win, 4, "║     E N T E R   N A M E S     ║", curses.color_pair(C_GOLD) | curses.A_BOLD)
    cprint(win, 5, "╚═══════════════════════════════╝", curses.color_pair(C_GOLD) | curses.A_BOLD)

    curses.echo()
    curses.curs_set(1)

    prompt1 = "Player 1 name: "
    px = center_x(win, prompt1 + "               ")
    safe_addstr(win, 9, px, prompt1, curses.color_pair(C_CYAN) | curses.A_BOLD)
    win.refresh()
    try:
        name1 = win.getstr(9, px + len(prompt1), 15).decode().strip()
    except Exception:
        name1 = ""
    if not name1:
        name1 = "Player 1"

    if mode == "1v1":
        prompt2 = "Player 2 name: "
        safe_addstr(win, 11, px, prompt2, curses.color_pair(C_MAGENTA) | curses.A_BOLD)
        win.refresh()
        try:
            name2 = win.getstr(11, px + len(prompt2), 15).decode().strip()
        except Exception:
            name2 = ""
        if not name2:
            name2 = "Player 2"
    else:
        name2 = "AI" if mode == "ai" else "EasyBot"

    curses.noecho()
    curses.curs_set(0)

    # ── Who goes first toggle (AI modes only) ──
    ai_first = False
    if mode in ("ai", "ai_easy"):
        selected = 0  # 0 = player first, 1 = AI first
        options = [
            (f"{name1} goes first", "You get the opening move."),
            (f"{name2} goes first", "The AI makes the first move."),
        ]
        while True:
            win.clear()
            cprint(win, 3, "╔═══════════════════════════════════╗", curses.color_pair(C_GOLD) | curses.A_BOLD)
            cprint(win, 4, "║     W H O   G O E S   F I R S T   ║", curses.color_pair(C_GOLD) | curses.A_BOLD)
            cprint(win, 5, "╚═══════════════════════════════════╝", curses.color_pair(C_GOLD) | curses.A_BOLD)

            cprint(win, 7, f"{name1}  vs  {name2}", curses.color_pair(C_WHITE) | curses.A_BOLD)

            for i, (title, desc) in enumerate(options):
                y = 10 + i * 4
                if i == selected:
                    marker = "▸ "
                    title_attr = curses.color_pair(C_CYAN) | curses.A_BOLD | curses.A_REVERSE
                    desc_attr = curses.color_pair(C_WHITE)
                else:
                    marker = "  "
                    title_attr = curses.color_pair(C_DIM)
                    desc_attr = curses.color_pair(C_DIM)
                cprint(win, y, f"{marker}{title}", title_attr)
                cprint(win, y + 1, desc, desc_attr)

            cprint(win, 20, "↑ ↓ : Toggle    ENTER: Confirm", curses.color_pair(C_DIM))
            win.refresh()

            key = win.getch()
            if key == curses.KEY_UP or key == curses.KEY_DOWN:
                selected = 1 - selected
            elif key in (ord('\n'), ord(' ')):
                ai_first = (selected == 1)
                break

    # Show matchup confirmation
    win.clear()
    cprint(win, 7, f"{name1}  vs  {name2}", curses.color_pair(C_GOLD) | curses.A_BOLD)
    if mode in ("ai", "ai_easy"):
        first = name2 if ai_first else name1
        cprint(win, 9, f"{first} goes first!", curses.color_pair(C_WHITE))
    cprint(win, 12, "Press any key to start!", curses.color_pair(C_DIM))
    win.refresh()
    win.getch()

    return name1, name2, ai_first


# ── Screen: Main Game ───────────────────────────────────────────────────────
def screen_game(win, name1, name2, mode, ai_first=False):
    nim = Nim()
    scores = {0: 0, 1: 0}
    names = {0: name1, 1: name2}
    name_colors = {0: C_CYAN, 1: C_MAGENTA}
    current_player = 1 if ai_first else 0
    sel_pile = 0
    sel_count = 1
    message = ""
    msg_color = C_DIM

    # Move history: (move_num, player_idx, pile, chips_removed, pts_gained, p1_total, p2_total, xor_before, xor_after)
    move_history = []
    move_num = 0
    last_mover = 0  # track who actually made the last move

    # Undo stack: snapshots of game state before each move
    # Each entry: dict with stacks, counts, scores, current_player, move_num, last_mover, move_history
    undo_stack = []

    while True:
        win.clear()
        h, w = win.getmaxyx()

        is_ai_turn = (mode in ("ai", "ai_easy") and current_player == 1)

        # ── Header ──
        cur_name = names[current_player]
        cur_color = name_colors[current_player]
        turn_label = f"{cur_name}'s TURN" if not is_ai_turn else f"{cur_name} THINKING..."
        cprint(win, 1, f"  9 / 1 1  —  {turn_label}  ",
               curses.color_pair(cur_color) | curses.A_BOLD)

        score_str = f"  {name1}: {scores[0]} pts    {name2}: {scores[1]} pts  "
        cprint(win, 2, score_str, curses.color_pair(C_GOLD) | curses.A_BOLD)
        hline(win, 3, 2, w - 4, '─', C_DIM)

        # ── Draw piles ──
        pile_width = 10
        total_w = nim.num_piles * pile_width
        start_x = max(2, (w - total_w) // 2)
        max_chips = max(nim.counts) if max(nim.counts) > 0 else 1
        pile_area_height = min(max_chips + 2, h - 14)
        pile_bottom_y = 4 + pile_area_height

        non_empty = [i for i, c in enumerate(nim.counts) if c > 0]
        if non_empty and sel_pile not in non_empty:
            sel_pile = non_empty[0]
        if non_empty:
            sel_count = max(1, min(sel_count, nim.counts[sel_pile]))

        for i in range(nim.num_piles):
            px = start_x + i * pile_width
            show_sel = (i == sel_pile) and not is_ai_turn
            hl = sel_count if show_sel else 0
            draw_pile(win, pile_bottom_y, px, i, nim.stacks[i], nim.counts[i],
                      sel_pile=show_sel, highlight_top=hl)

        # ── Selection info ──
        info_y = pile_bottom_y + 4
        hline(win, info_y - 1, 2, w - 4, '─', C_DIM)

        if non_empty and not is_ai_turn:
            sel_info = f"  Pile {sel_pile + 1}  |  Remove: {sel_count} chip{'s' if sel_count != 1 else ''}  "
            if nim.counts[sel_pile] >= sel_count:
                top_chips = nim.stacks[sel_pile][nim.counts[sel_pile] - sel_count:]
                chip_val = sum(top_chips)
                sel_info += f"(worth {chip_val} pts)"
            cprint(win, info_y, sel_info, curses.color_pair(cur_color) | curses.A_BOLD)

        if message:
            cprint(win, info_y + 1, message, curses.color_pair(msg_color) | curses.A_BOLD)

        ctrl_y = info_y + 3
        if not is_ai_turn:
            undo_hint = "  U: Undo" if undo_stack else ""
            cprint(win, ctrl_y,
                   f"← → : Pile  ↑ ↓ : Count  ENTER: Confirm  Q: Quit{undo_hint}",
                   curses.color_pair(C_DIM))
        else:
            cprint(win, ctrl_y, f"  {name2} is thinking...  ", curses.color_pair(C_MAGENTA))

        win.refresh()

        if nim.is_over():
            break

        # ── AI turn ──
        if is_ai_turn:
            time.sleep(0.8)
            flush_input(win)
            if not nim.is_over():
                # Save snapshot before AI move (so undo rolls back AI + preceding human move)
                undo_stack.append({
                    'stacks': copy.deepcopy(nim.stacks),
                    'counts': list(nim.counts),
                    'scores': dict(scores),
                    'current_player': 1,
                    'move_num': move_num,
                    'last_mover': last_mover,
                    'move_history': list(move_history),
                })

                xor_before = 0
                for c in nim.counts:
                    xor_before ^= c

                if mode == "ai_easy":
                    ai_pile, ai_num = nim.ai_move_random()
                else:
                    ai_pile, ai_num = nim.ai_move()
                gained = nim.remove(ai_pile, ai_num)
                scores[1] += gained
                xor_after = 0
                for c in nim.counts:
                    xor_after ^= c
                move_num += 1
                move_history.append((move_num, 1, ai_pile + 1, ai_num, gained,
                                     scores[0], scores[1], xor_before, xor_after))
                message = (f"{name2} took {ai_num} chip{'s' if ai_num != 1 else ''} "
                           f"from Pile {ai_pile + 1} (+{gained} pts)")
                msg_color = C_MAGENTA
                last_mover = 1
                current_player = 0
                sel_count = 1
            continue

        # ── Human input ──
        win.nodelay(False)
        key = win.getch()

        if key == curses.KEY_LEFT:
            if non_empty:
                idx = non_empty.index(sel_pile) if sel_pile in non_empty else 0
                sel_pile = non_empty[(idx - 1) % len(non_empty)]
                sel_count = max(1, min(sel_count, nim.counts[sel_pile]))
                message = ""
        elif key == curses.KEY_RIGHT:
            if non_empty:
                idx = non_empty.index(sel_pile) if sel_pile in non_empty else 0
                sel_pile = non_empty[(idx + 1) % len(non_empty)]
                sel_count = max(1, min(sel_count, nim.counts[sel_pile]))
                message = ""
        elif key == curses.KEY_DOWN:
            if non_empty and nim.counts[sel_pile] > sel_count:
                sel_count += 1
                message = ""
        elif key == curses.KEY_UP:
            if sel_count > 1:
                sel_count -= 1
                message = ""
        elif key in (ord('\n'), ord(' ')):
            if non_empty and sel_count <= nim.counts[sel_pile]:
                # Save snapshot for undo
                undo_stack.append({
                    'stacks': copy.deepcopy(nim.stacks),
                    'counts': list(nim.counts),
                    'scores': dict(scores),
                    'current_player': current_player,
                    'move_num': move_num,
                    'last_mover': last_mover,
                    'move_history': list(move_history),
                })

                xor_before = 0
                for c in nim.counts:
                    xor_before ^= c

                gained = nim.remove(sel_pile, sel_count)
                scores[current_player] += gained
                xor_after = 0
                for c in nim.counts:
                    xor_after ^= c
                move_num += 1
                move_history.append((move_num, current_player, sel_pile + 1, sel_count,
                                     gained, scores[0], scores[1], xor_before, xor_after))
                message = (f"{names[current_player]} took {sel_count} "
                           f"chip{'s' if sel_count != 1 else ''} from Pile {sel_pile + 1} "
                           f"(+{gained} pts)")
                msg_color = name_colors[current_player]
                last_mover = current_player

                if nim.is_over():
                    continue

                current_player = 1 - current_player
                sel_count = 1
            else:
                message = "Invalid move!"
                msg_color = C_RED
        elif key in (ord('u'), ord('U')):
            if undo_stack:
                snap = undo_stack.pop()
                nim.stacks = snap['stacks']
                nim.counts = snap['counts']
                scores = snap['scores']
                current_player = snap['current_player']
                move_num = snap['move_num']
                last_mover = snap['last_mover']
                move_history = snap['move_history']
                sel_count = 1
                message = "↩ Move undone!"
                msg_color = C_YELLOW
            else:
                message = "Nothing to undo."
                msg_color = C_DIM
        elif key in (ord('q'), ord('Q')):
            return scores[0], scores[1], name1, name2, None, move_history

    winner = last_mover
    return scores[0], scores[1], name1, name2, winner, move_history


# ── Screen: Game Review ─────────────────────────────────────────────────────
def screen_review(win, name1, name2, p1_score, p2_score, winner, move_history):
    if not move_history:
        return

    name_colors = {0: C_CYAN, 1: C_MAGENTA}

    # Build winnability timeline: +1 = P1 winning, -1 = P2 winning
    # XOR != 0 means the player about to move is in a winning position.
    initial_xor = move_history[0][7]
    winnability = []

    # Before any move: P1 is about to move
    winnability.append(+1 if initial_xor != 0 else -1)

    for entry in move_history:
        move_n, player, pile, chips, pts, p1t, p2t, xor_b, xor_a = entry
        next_player = 1 - player
        if xor_a != 0:
            # Next player to move is winning
            winnability.append(+1 if next_player == 0 else -1)
        else:
            # xor_a == 0 → next player to move is LOSING
            winnability.append(+1 if next_player == 1 else -1)

    scroll_offset = 0

    while True:
        win.clear()
        h, w = win.getmaxyx()

        # ── Title ──
        cprint(win, 1, "╔═══════════════════════════════════════╗", curses.color_pair(C_GOLD) | curses.A_BOLD)
        cprint(win, 2, "║         G A M E   R E V I E W        ║", curses.color_pair(C_GOLD) | curses.A_BOLD)
        cprint(win, 3, "╚═══════════════════════════════════════╝", curses.color_pair(C_GOLD) | curses.A_BOLD)

        # ── Horizontal line graph (chess.com style) ──
        # X axis = moves (columns), Y axis = winnability (rows)
        graph_half = 3    # rows above/below center line
        graph_top = 6
        graph_center_y = graph_top + graph_half
        graph_bottom = graph_top + graph_half * 2

        graph_left = 2
        graph_right = w - 2
        graph_width = graph_right - graph_left

        if graph_width < 10:
            graph_width = 10
            graph_right = graph_left + graph_width

        # Player labels OUTSIDE the graph area
        safe_addstr(win, graph_top - 1, graph_left, f"▲ {name1} winning",
                    curses.color_pair(C_CYAN) | curses.A_BOLD)
        safe_addstr(win, graph_bottom + 1, graph_left, f"▼ {name2} winning",
                    curses.color_pair(C_MAGENTA) | curses.A_BOLD)

        # Draw center line (the zero line)
        for col in range(graph_left, graph_right):
            safe_addstr(win, graph_center_y, col, "─", curses.color_pair(C_DIM))

        # Sample winnability to fit graph width
        n_points = len(winnability)
        if n_points <= graph_width:
            col_values = []
            for i in range(n_points):
                col = graph_left + int(i * (graph_width - 1) / max(1, n_points - 1))
                col_values.append((col, winnability[i]))
        else:
            col_values = []
            for col_idx in range(graph_width):
                data_idx = int(col_idx * (n_points - 1) / max(1, graph_width - 1))
                col_values.append((graph_left + col_idx, winnability[data_idx]))

        # Draw thick filled bars: solid █ at edge, ░ fill between edge and center
        for col, val in col_values:
            if val > 0:
                # P1 winning — fill upward from center
                top_row = graph_center_y - graph_half
                # Solid cap at the top edge
                safe_addstr(win, top_row, col, "█", curses.color_pair(C_CYAN))
                # Shaded fill between cap and center
                for row in range(top_row + 1, graph_center_y):
                    safe_addstr(win, row, col, "░", curses.color_pair(C_CYAN))
            elif val < 0:
                # P2 winning — fill downward from center
                bottom_row = graph_center_y + graph_half
                # Shaded fill between center and cap
                for row in range(graph_center_y + 1, bottom_row):
                    safe_addstr(win, row, col, "░", curses.color_pair(C_MAGENTA))
                # Solid cap at the bottom edge
                safe_addstr(win, bottom_row, col, "█", curses.color_pair(C_MAGENTA))

        # Move markers with blunder/perfect dots along the bottom edge
        marker_y = graph_bottom + 2
        # Draw axis
        for col in range(graph_left, graph_right):
            safe_addstr(win, marker_y, col, "─", curses.color_pair(C_DIM))

        # Place move number ticks
        for i, entry in enumerate(move_history):
            move_n, player, pile, chips, pts, p1t, p2t, xor_b, xor_a = entry
            # Map move index to column (i+1 because winnability[0] is "Start")
            data_idx = i + 1
            if n_points <= graph_width:
                col = graph_left + int(data_idx * (graph_width - 1) / max(1, n_points - 1))
            else:
                col = graph_left + int(data_idx * (graph_width - 1) / max(1, n_points - 1))

            if col >= graph_right:
                col = graph_right - 1

            # Show blunder/perfect markers
            if xor_b != 0:
                if xor_a == 0:
                    # Perfect move
                    safe_addstr(win, marker_y, col, "●", curses.color_pair(C_GREEN) | curses.A_BOLD)
                else:
                    # Blunder
                    safe_addstr(win, marker_y, col, "●", curses.color_pair(C_RED) | curses.A_BOLD)

        # Legend under graph
        legend_y = marker_y + 1
        legend_str = "  ● Perfect   ● Blunder"
        lx = center_x(win, legend_str + "        ")
        safe_addstr(win, legend_y, lx, "  ●", curses.color_pair(C_GREEN) | curses.A_BOLD)
        safe_addstr(win, legend_y, lx + 3, " Perfect   ", curses.color_pair(C_WHITE))
        safe_addstr(win, legend_y, lx + 14, "●", curses.color_pair(C_RED) | curses.A_BOLD)
        safe_addstr(win, legend_y, lx + 15, " Blunder", curses.color_pair(C_WHITE))

        # Move number labels
        safe_addstr(win, legend_y + 1, graph_left, "Start", curses.color_pair(C_DIM))
        end_label = f"Move {len(move_history)}"
        safe_addstr(win, legend_y + 1, graph_right - len(end_label), end_label, curses.color_pair(C_DIM))

        # ── Move log: only Perfect moves and Blunders ──
        log_start_y = legend_y + 3
        hline(win, log_start_y - 1, 2, w - 4, '─', C_DIM)
        cprint(win, log_start_y, "── Key Moves (↑↓ to scroll) ──", curses.color_pair(C_WHITE) | curses.A_BOLD)
        log_start_y += 1

        key_moves = []
        for idx, entry in enumerate(move_history):
            move_n, player, pile, chips, pts, p1t, p2t, xor_b, xor_a = entry
            if xor_b != 0:
                if xor_a == 0:
                    key_moves.append((entry, "✓ Perfect", C_GREEN))
                else:
                    key_moves.append((entry, "✗ Blunder!", C_RED))

        if move_history and (not key_moves or key_moves[-1][0] != move_history[-1]):
            last = move_history[-1]
            key_moves.append((last, "⚑ Final move", C_GOLD))

        header = f" {'#':>3}  {'Player':<12} {'Pile':>4} {'Took':>4} {'Pts':>5}  {'Verdict'}"
        safe_addstr(win, log_start_y, 2, header, curses.color_pair(C_GOLD) | curses.A_BOLD)
        hline(win, log_start_y + 1, 2, w - 4, '─', C_DIM)
        log_start_y += 2

        visible_rows = h - log_start_y - 2
        if visible_rows < 1:
            visible_rows = 1
        max_scroll = max(0, len(key_moves) - visible_rows)
        scroll_offset = max(0, min(scroll_offset, max_scroll))

        for i in range(visible_rows):
            idx = scroll_offset + i
            if idx >= len(key_moves):
                break

            entry, verdict, vcol = key_moves[idx]
            move_n, player, pile, chips, pts, p1t, p2t, xor_b, xor_a = entry
            pname = name1 if player == 0 else name2
            pcol = name_colors[player]

            ry = log_start_y + i
            safe_addstr(win, ry, 2, f" {move_n:>3}", curses.color_pair(C_DIM))
            safe_addstr(win, ry, 7, f"{pname:<12}", curses.color_pair(pcol) | curses.A_BOLD)
            safe_addstr(win, ry, 19, f"{pile:>4}", curses.color_pair(C_WHITE))
            safe_addstr(win, ry, 24, f"{chips:>4}", curses.color_pair(C_WHITE))
            safe_addstr(win, ry, 29, f"{pts:>5}", curses.color_pair(C_GOLD))
            safe_addstr(win, ry, 36, verdict, curses.color_pair(vcol) | curses.A_BOLD)

        # ── Footer ──
        footer_y = h - 1
        if len(key_moves) > visible_rows:
            scroll_hint = f"↑↓ Scroll ({scroll_offset + 1}-{min(scroll_offset + visible_rows, len(key_moves))}/{len(key_moves)})  "
        else:
            scroll_hint = ""
        cprint(win, footer_y, f"{scroll_hint}Press Q to go back", curses.color_pair(C_DIM))

        win.refresh()

        key = win.getch()
        if key == curses.KEY_UP:
            scroll_offset = max(0, scroll_offset - 1)
        elif key == curses.KEY_DOWN:
            scroll_offset = min(max_scroll, scroll_offset + 1)
        elif key in (ord('q'), ord('Q'), ord('\n'), 27):
            return


# ── Screen: Game Over ───────────────────────────────────────────────────────
def screen_game_over(win, p1_score, p2_score, name1, name2, winner, move_history):
    win.clear()
    h, w = win.getmaxyx()

    cprint(win, 2, "╔═══════════════════════════╗", curses.color_pair(C_GOLD) | curses.A_BOLD)
    cprint(win, 3, "║     G A M E   O V E R     ║", curses.color_pair(C_GOLD) | curses.A_BOLD)
    cprint(win, 4, "╚═══════════════════════════╝", curses.color_pair(C_GOLD) | curses.A_BOLD)

    if winner is None:
        verdict = "Game was quit early."
        vcol = C_DIM
    elif winner == 0:
        verdict = f"★  {name1} WINS! Took the last chip!  ★"
        vcol = C_CYAN
    else:
        verdict = f"★  {name2} WINS! Took the last chip!  ★"
        vcol = C_MAGENTA

    cprint(win, 7, verdict, curses.color_pair(vcol) | curses.A_BOLD)
    hline(win, 9, 4, w - 8, '─', C_DIM)

    cprint(win, 11, f"{name1}'s Score:  {p1_score} pts", curses.color_pair(C_CYAN))
    cprint(win, 12, f"{name2}'s Score:  {p2_score} pts", curses.color_pair(C_MAGENTA))
    cprint(win, 13, "(Scores are for bragging rights — winner is who takes the last chip!)",
           curses.color_pair(C_DIM))
    hline(win, 14, 4, w - 8, '─', C_DIM)

    diff = p1_score - p2_score
    if diff > 0:
        diff_str = f"{name1} scored {diff} more points!"
        diff_col = C_CYAN
    elif diff < 0:
        diff_str = f"{name2} scored {-diff} more points!"
        diff_col = C_MAGENTA
    else:
        diff_str = "Scores are tied!"
        diff_col = C_GOLD
    cprint(win, 15, diff_str, curses.color_pair(diff_col) | curses.A_BOLD)

    # Quick stats
    if move_history:
        total_moves = len(move_history)
        p1_moves = sum(1 for m in move_history if m[1] == 0)
        p2_moves = sum(1 for m in move_history if m[1] == 1)
        p1_blunders = 0
        p2_blunders = 0
        p1_perfect = 0
        p2_perfect = 0
        for idx, entry in enumerate(move_history):
            mn, player, pile, chips, pts, p1t, p2t, xor_b, xor_a = entry
            if xor_b != 0:
                if xor_a != 0:
                    # Blunder: had winning position but didn't play optimally
                    if player == 0:
                        p1_blunders += 1
                    else:
                        p2_blunders += 1
                else:
                    # Perfect: found the optimal move
                    if player == 0:
                        p1_perfect += 1
                    else:
                        p2_perfect += 1

        cprint(win, 17, f"Total moves: {total_moves}  ({name1}: {p1_moves}, {name2}: {p2_moves})",
               curses.color_pair(C_WHITE))
        cprint(win, 18, f"Perfect:   {name1}: {p1_perfect}   {name2}: {p2_perfect}",
               curses.color_pair(C_GREEN))
        cprint(win, 19, f"Blunders:  {name1}: {p1_blunders}   {name2}: {p2_blunders}",
               curses.color_pair(C_RED))

    cprint(win, 22, "V : View game review   R : Play again   Q : Quit",
           curses.color_pair(C_DIM))
    win.refresh()

    while True:
        key = win.getch()
        if key in (ord('v'), ord('V')):
            screen_review(win, name1, name2, p1_score, p2_score, winner, move_history)
            return screen_game_over(win, p1_score, p2_score, name1, name2, winner, move_history)
        if key in (ord('r'), ord('R')):
            return True
        if key in (ord('q'), ord('Q'), 27):
            return False


# ── Main loop ───────────────────────────────────────────────────────────────
def main(stdscr):
    curses.curs_set(0)
    curses.noecho()
    stdscr.keypad(True)
    init_colors()

    while True:
        screen_menu(stdscr)
        mode = screen_mode_select(stdscr)
        if mode is None:
            break

        name1, name2, ai_first = screen_names(stdscr, mode)
        p1_score, p2_score, n1, n2, winner, history = screen_game(stdscr, name1, name2, mode, ai_first)
        play_again = screen_game_over(stdscr, p1_score, p2_score, n1, n2, winner, history)
        if not play_again:
            break


if __name__ == '__main__':
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        print("\nThanks for playing 9/11!")
        sys.exit(0)