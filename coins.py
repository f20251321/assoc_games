import random
import time
import math
import sys
import threading

#ANSI colours
R  = "\033[91m"
Y  = "\033[93m"
G  = "\033[92m"
B  = "\033[94m"
M  = "\033[95m"
C  = "\033[96m"
W  = "\033[97m"
DIM= "\033[2m"
BO = "\033[1m"
RS = "\033[0m"

BOX_COLORS = [C, M, Y]
BOX_NAMES  = ["Box 1", "Box 2", "Box 3"]

COIN_COLOR = {10: DIM+W, 20: W, 50: Y+BO}
COIN_LABEL = {10: "( 10)", 20: "(20 )", 50: "{50}"}

TIME_LIMIT   = 300
MAX_SWITCHES = 4

#Integral bank
# Stored as namedtuples. integrand is a plain ASCII string,
# lower/upper are limit strings, hint walks through the solution, answer is float, tol is acceptable absolute error.
# print_integral() renders them in a box.

from collections import namedtuple
Integral = namedtuple("Integral", ["integrand", "lower", "upper", "hint", "answer", "tol"])

INTEGRALS = [
    # Polynomial & exponential
    Integral("x^2 * e^x", "0", "1",
        "IBP twice: antiderivative = e^x*(x^2-2x+2)+C\n"
        "  => e*(1) - 1*(2) = e - 2",
        math.e - 2, 0.01),
    Integral("x * e^x", "0", "1",
        "IBP: u=x, dv=e^x dx => e^x*(x-1)+C\n"
        "  => 0 - (-1) = 1",
        1.0, 0.01),
    Integral("x^3 * e^x", "0", "1",
        "IBP repeatedly; antiderivative = e^x*(x^3-3x^2+6x-6)+C\n"
        "  => e*(-2) - 1*(-6) = -2e + 6",
        6 - 2*math.e, 0.01),
    Integral("e^(-x)", "0", "inf",
        "Antiderivative = -e^(-x)+C\n"
        "  => 0 - (-1) = 1",
        1.0, 0.01),
    Integral("x * e^(-x)", "0", "inf",
        "Gamma(2) = 1! = 1",
        1.0, 0.01),
    Integral("x^2 * e^(-x)", "0", "inf",
        "Gamma(3) = 2! = 2",
        2.0, 0.01),
    Integral("e^(-x^2)", "0", "inf",
        "Half the Gaussian integral.\n"
        "  Full integral from -inf to inf = sqrt(pi)\n"
        "  => sqrt(pi) / 2",
        math.sqrt(math.pi) / 2, 0.01),
    Integral("x * e^(-x^2)", "0", "1",
        "Sub u = -x^2, du = -2x dx\n"
        "  => -(1/2)*e^(-x^2) from 0 to 1 = (1 - 1/e) / 2",
        (1 - math.exp(-1)) / 2, 0.01),
    Integral("e^(2x)", "0", "1",
        "Antiderivative = e^(2x)/2+C => (e^2 - 1)/2",
        (math.e**2 - 1) / 2, 0.01),
    Integral("x^2", "0", "3",
        "Antiderivative = x^3/3+C => 9",
        9.0, 0.01),
    Integral("x^4 - 2*x^2 + 1", "-1", "1",
        "Equals (x^2-1)^2, symmetric; 2*int_0^1 gives 2*(1/5-2/3+1) = 16/15",
        16/15, 0.01),
    Integral("x^2 * ln(x)", "0", "1",
        "IBP: u=ln(x), dv=x^2 dx\n"
        "  => x^3/3*ln(x) - x^3/9 from 0 to 1 = -1/9",
        -1/9, 0.01),
    # Logarithmic
    Integral("ln(x)", "1", "e",
        "Antiderivative = x*ln(x)-x+C\n"
        "  => (e-e)-(0-1) = 1",
        1.0, 0.01),
    Integral("-ln(x)", "0", "1",
        "IBP: antiderivative = -x*ln(x)+x+C\n"
        "  => (0+1) - lim_{x->0}(-x*ln(x)+x) = 1",
        1.0, 0.01),
    Integral("x * ln(x)", "0", "1",
        "IBP: u=ln(x), dv=x dx\n"
        "  => x^2/2*ln(x) - x^2/4 from 0 to 1 = -1/4",
        -0.25, 0.01),
    Integral("x^3 * ln(x)", "1", "2",
        "IBP: u=ln(x), dv=x^3 dx\n"
        "  => x^4/4*ln(x) - x^4/16 from 1 to 2\n"
        "  => (4*ln2-1)-(-1/16) = 4*ln(2) - 15/16",
        4*math.log(2) - 15/16, 0.01),
    Integral("ln(x)^2", "0", "1",
        "Sub u=-ln(x); becomes Gamma(3) = 2",
        2.0, 0.01),
    Integral("ln(1 + x)", "0", "1",
        "IBP: u=ln(1+x), dv=dx\n"
        "  => (x+1)*ln(1+x)-x from 0 to 1 = 2*ln(2)-1",
        2*math.log(2) - 1, 0.01),
    # Trigonometric
    Integral("sin^2(x)", "0", "pi/2",
        "Use sin^2(x)=(1-cos(2x))/2\n"
        "  => x/2 - sin(2x)/4 from 0 to pi/2 = pi/4",
        math.pi/4, 0.01),
    Integral("cos^2(x)", "0", "pi/2",
        "Use cos^2(x)=(1+cos(2x))/2\n"
        "  => x/2 + sin(2x)/4 from 0 to pi/2 = pi/4",
        math.pi/4, 0.01),
    Integral("cos^3(x)", "0", "pi/2",
        "Write as cos(x)*(1-sin^2(x)); sub u=sin(x)\n"
        "  => u - u^3/3 from 0 to 1 = 2/3",
        2/3, 0.01),
    Integral("sin(x) * cos(x)", "0", "pi/2",
        "sin(x)*cos(x)=sin(2x)/2\n"
        "  => -cos(2x)/4 from 0 to pi/2 = 1/2",
        0.5, 0.01),
    Integral("x * sin(x)", "0", "pi",
        "IBP: u=x, dv=sin(x)dx\n"
        "  => -x*cos(x)+sin(x) from 0 to pi = pi",
        math.pi, 0.01),
    Integral("x * cos(x)", "0", "pi/2",
        "IBP: u=x, dv=cos(x)dx\n"
        "  => x*sin(x)+cos(x) from 0 to pi/2 = pi/2 - 1",
        math.pi/2 - 1, 0.01),
    Integral("sin^3(x)", "0", "pi",
        "sin^3(x)=sin(x)*(1-cos^2(x)); sub u=cos(x)\n"
        "  => [-cos(x)+cos^3(x)/3] from 0 to pi = 4/3",
        4/3, 0.01),
    Integral("tan(x)", "0", "pi/4",
        "Antiderivative = -ln|cos(x)|+C\n"
        "  => -ln(cos(pi/4)) = ln(sqrt(2)) = ln(2)/2",
        math.log(2)/2, 0.01),
    Integral("sin(x) / x   [approx]", "0", "pi",
        "Sine integral Si(pi). No closed form.\n"
        "  Numerically approx 1.8519",
        1.8519, 0.005),
    Integral("cos(x) / (1 + sin(x))", "0", "pi/2",
        "Sub u=1+sin(x) => ln(1+sin(x)) from 0 to pi/2 = ln(2)",
        math.log(2), 0.01),
    Integral("1 / (1 + cos(x))", "0", "pi/2",
        "1+cos(x)=2*cos^2(x/2) => sec^2(x/2)/2\n"
        "  => tan(x/2) from 0 to pi/2 = 1",
        1.0, 0.01),
    Integral("x^2 * sin(x)", "0", "pi",
        "IBP twice: antiderivative = -x^2*cos(x)+2x*sin(x)+2*cos(x)+C\n"
        "  => (pi^2+0-2)-(0+0+2) = pi^2 - 4",
        math.pi**2 - 4, 0.01),
    Integral("e^x * sin(x)", "0", "pi",
        "IBP twice; antiderivative = e^x*(sin(x)-cos(x))/2+C\n"
        "  => e^pi*(0+1)/2 - 1*(0-1)/2 = (e^pi+1)/2",
        (math.exp(math.pi)+1)/2, 0.1),
    Integral("e^x * cos(x)", "0", "pi/2",
        "IBP twice; antiderivative = e^x*(cos(x)+sin(x))/2+C\n"
        "  => e^(pi/2)*(0+1)/2 - (1+0)/2 = (e^(pi/2)-1)/2",
        (math.exp(math.pi/2)-1)/2, 0.01),
    Integral("ln(sin(x))", "0", "pi/2",
        "Famous result: -pi*ln(2)/2",
        -math.pi*math.log(2)/2, 0.01),
    # Rational & algebraic
    Integral("1 / (1 + x^2)", "0", "1",
        "Antiderivative = arctan(x)+C\n"
        "  => arctan(1)-0 = pi/4",
        math.pi/4, 0.01),
    Integral("x / (1 + x^2)", "0", "1",
        "Sub u=1+x^2 => (1/2)*ln(1+x^2) from 0 to 1 = ln(2)/2",
        math.log(2)/2, 0.01),
    Integral("x^2 / (x^3 + 1)", "0", "1",
        "Sub u=x^3+1 => (1/3)*ln(x^3+1) from 0 to 1 = ln(2)/3",
        math.log(2)/3, 0.01),
    Integral("1 / sqrt(1 - x^2)", "0", "1",
        "Antiderivative = arcsin(x)+C\n"
        "  => arcsin(1)-0 = pi/2",
        math.pi/2, 0.01),
    Integral("sqrt(1 - x^2)", "0", "1",
        "Area of quarter unit circle => pi/4",
        math.pi/4, 0.01),
    Integral("1 / sqrt(x)", "1", "4",
        "Antiderivative = 2*sqrt(x)+C => 4-2 = 2",
        2.0, 0.01),
    Integral("1 / (x^2 - 1)   [x>1]", "2", "3",
        "Partial fractions: (1/2)*(1/(x-1)-1/(x+1))\n"
        "  => (1/2)*ln|(x-1)/(x+1)| from 2 to 3 = ln(3/2)/2",
        math.log(3/2)/2, 0.01),
    Integral("x / (x^2 + 4)", "0", "2",
        "Sub u=x^2+4 => (1/2)*ln(x^2+4) from 0 to 2\n"
        "  => (ln8-ln4)/2 = ln(2)/2",
        math.log(2)/2, 0.01),
    Integral("1 / (x*(1 + ln(x)))", "1", "e",
        "Sub u=ln(x) => 1/(1+u) from 0 to 1 = ln(2)",
        math.log(2), 0.01),
    Integral("e^x / (1 + e^x)", "0", "1",
        "Sub u=1+e^x => ln(1+e^x) from 0 to 1\n"
        "  => ln(1+e)-ln(2)",
        math.log(1+math.e)-math.log(2), 0.01),
    Integral("x / (1 + x)^2", "0", "1",
        "Write as 1/(1+x) - 1/(1+x)^2\n"
        "  => ln(1+x)+1/(1+x) from 0 to 1 = ln(2)-1/2",
        math.log(2)-0.5, 0.01),
    Integral("arctan(x)", "0", "1",
        "IBP: u=arctan(x), dv=dx\n"
        "  => x*arctan(x)-(1/2)*ln(1+x^2) from 0 to 1\n"
        "  => pi/4 - ln(2)/2",
        math.pi/4-math.log(2)/2, 0.01),
    Integral("arcsin(x)", "0", "1/2",
        "IBP: u=arcsin(x), dv=dx\n"
        "  => x*arcsin(x)+sqrt(1-x^2) from 0 to 1/2\n"
        "  => pi/12 + sqrt(3)/2 - 1",
        math.pi/12+math.sqrt(3)/2-1, 0.01),
    Integral("x^(1/3)", "0", "8",
        "Antiderivative = (3/4)*x^(4/3)+C\n"
        "  => (3/4)*16 = 12",
        12.0, 0.01),
    Integral("1 / (1 + sqrt(x))", "0", "1",
        "Sub u=sqrt(x), dx=2u du\n"
        "  => 2*(u-ln(1+u)) from 0 to 1 = 2-2*ln(2)",
        2-2*math.log(2), 0.01),
    Integral("x^2 / (1 + x^4)", "0", "inf",
        "Contour integration result: pi/(2*sqrt(2))",
        math.pi/(2*math.sqrt(2)), 0.01),
    # Hyperbolic
    Integral("sinh(x)", "0", "1",
        "Antiderivative = cosh(x)+C\n"
        "  => cosh(1) - 1",
        math.cosh(1)-1, 0.01),
    Integral("cosh(x)", "0", "ln(2)",
        "Antiderivative = sinh(x)+C\n"
        "  => sinh(ln2) = (2-1/2)/2 = 3/4",
        3/4, 0.01),
    Integral("tanh(x)", "0", "1",
        "Antiderivative = ln(cosh(x))+C => ln(cosh(1))",
        math.log(math.cosh(1)), 0.01),
    Integral("1 / cosh^2(x)", "0", "1",
        "sech^2(x); antiderivative = tanh(x)+C => tanh(1)",
        math.tanh(1), 0.01),
    # Famous
    Integral("sqrt(x) * e^(-x)", "0", "inf",
        "Gamma(3/2) = (1/2)! = sqrt(pi)/2",
        math.sqrt(math.pi)/2, 0.01),
    Integral("ln(x + 1/x) / (1 + x^2)", "0", "inf",
        "Symmetry under x->1/x makes this exactly 0",
        0.0, 0.01),
]


def print_integral(integral):
    ig    = integral.integrand
    lo    = integral.lower
    hi    = integral.upper
    body  = f" | {ig}  dx"
    inner = max(len(body) + 2, len(hi) + 6, len(lo) + 6)
    def row(s): return "|" + s + " " * (inner - len(s)) + "|"
    border = "+" + "-" * inner + "+"
    lines = [
        border,
        row(f"  {hi}"),
        row("  /"),
        row(body),
        row("  \\"),
        row(f"  {lo}"),
        border,
    ]
    for line in lines:
        print(f"  {BO}{line}{RS}")
    print()


#Helpers
def cls():
    print("\033[2J\033[H", end="")

def hr(char="-", n=52):
    print(DIM + char * n + RS)

def fmt_time(s):
    return f"{s//60}:{s%60:02d}"

def multiplier(score, math_bonus):
    if score < 250:   base = 0.8
    elif score < 300: base = 1.2
    elif score < 350: base = 1.4
    elif score < 370: base = 1.8
    else:             base = 2.5
    return round(base + math_bonus, 1)

def mult_label(score):
    tiers = [(370,"2.5x",G),(350,"1.8x",Y),(300,"1.4x",M),(250,"1.2x",C),(0,"0.8x",R)]
    for threshold, label, col in tiers:
        if score >= threshold:
            return col + label + RS

def input_prompt(prompt):
    try:
        return input(prompt)
    except (EOFError, KeyboardInterrupt):
        print()
        return ""


# Setup
def generate_game():
    while True:
        a = random.randint(3, 9)
        b = random.randint(3, 15 - a - 3)  # leave at least 3 for c
        c = 15 - a - b
        if 3 <= c <= 9:
            break
    sizes = [a, b, c]
    random.shuffle(sizes)  # randomise which box gets which size

    coins = [10]*5 + [20]*5 + [50]*5
    random.shuffle(coins)

    boxes = []
    ptr = 0
    for size in sizes:
        boxes.append(coins[ptr:ptr+size])
        ptr += size

    math_idx = random.randint(0, 14)
    integral = random.choice(INTEGRALS)

    return boxes, sizes, math_idx, integral

def build_clues(sizes):
    clues = []
    for b in range(3):
        others = [sizes[i] for i in range(3) if i != b]
        o1, o2 = others
        diff = abs(o1 - o2)
        kind = random.randint(0, 3)
        if kind == 0:
            truth = min(o1, o2) <= 4
            stmt  = "At least one other box had <= 4 coins at the start."
            val   = str(truth)
        elif kind == 1:
            truth = max(o1, o2) >= 6
            stmt  = "Some other box had >= 6 coins at the start."
            val   = str(truth)
        elif kind == 2:
            stmt  = "Difference in coin counts of the other two boxes at start:"
            val   = str(diff)
        else:
            stmt  = f"Box {[i+1 for i in range(3) if i != b][0]} had more coins than Box {[i+1 for i in range(3) if i != b][1]} at start."
            val   = str(o1 > o2)
        clues.append({"stmt": stmt, "val": val})
    return clues


# Display
def show_header(score, switches_left, time_left, math_bonus):
    cls()
    print(f"\n  {R+BO}COINS, CLUES & CHAOS{RS}\n")
    hr()
    mult = multiplier(score, math_bonus)
    ml   = mult_label(score)
    tl   = f"{G if time_left>120 else Y if time_left>60 else R}{fmt_time(time_left)}{RS}"
    print(f"  Score: {Y+BO}{score:>4}{RS}  "
          f"Multiplier: {ml}  "
          f"Final~{Y}{int(score*mult)}{RS}  "
          f"Switches left: {B}{switches_left}{RS}  "
          f"Time: {tl}")
    hr()

def show_boxes(boxes, current_box):
    print()
    for i in range(3):
        col   = BOX_COLORS[i]
        arrow = f"{G}<< CURRENT{RS}" if current_box == i else ""
        print(f"  {col+BO}{BOX_NAMES[i]}{RS}  {arrow}")
    print()

def show_drawn(drawn):
    if not drawn:
        return
    line = "  Drawn: "
    for v in drawn[-20:]:
        line += COIN_COLOR[v] + COIN_LABEL[v] + RS + " "
    print(line)
    total = sum(drawn)
    print(f"  Total: {Y+BO}{total}{RS}\n")


#Math challenge
def do_math(integral):
    print(f"\n  {Y+BO}MATH COIN!{RS}  You must solve an integral before drawing again.\n")
    hr()
    print_integral(integral)

    while True:
        show_hint = input_prompt("  Show hint? (y/n): ").strip().lower()
        if show_hint == "y":
            print(f"\n  {DIM}{integral.hint}{RS}\n")
        ans_str = input_prompt("  Your answer: ").strip()
        try:
            ans = float(ans_str)
            break
        except ValueError:
            print(f"  {R}Enter a number.{RS}")

    correct = abs(ans - integral.answer) <= integral.tol
    if correct:
        print(f"\n  {G+BO}Correct! +0.2x bonus{RS}  (answer = {integral.answer:.4f})\n")
    else:
        print(f"\n  {R+BO}Wrong.  -0.1x penalty{RS}  (correct answer = {integral.answer:.4f})\n")
    input_prompt("  Press Enter to continue...")
    return 0.2 if correct else -0.1


#Clue reveal
def show_clue(clue, box_idx):
    print(f"\n  {M+BO}CLUE COIN -- {BOX_NAMES[box_idx]}{RS}\n")
    hr()
    print(f"  {clue['stmt']}")
    print(f"\n  Answer: {Y+BO}{clue['val']}{RS}\n")
    input_prompt("  Press Enter to continue...")


#Timer
class Timer:
    def __init__(self, limit):
        self.limit     = limit
        self.elapsed   = 0
        self.running   = False
        self._thread   = None
        self._stop_evt = threading.Event()

    def start(self):
        self.running = True
        self._stop_evt.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        while not self._stop_evt.is_set():
            time.sleep(1)
            self.elapsed += 1
            if self.elapsed >= self.limit:
                self.running = False
                return

    def pause(self):
        self._stop_evt.set()
        if self._thread:
            self._thread.join()

    def resume(self):
        self._stop_evt.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    @property
    def left(self):
        return max(0, self.limit - self.elapsed)

    @property
    def expired(self):
        return self.elapsed >= self.limit


# Main menu
def main_menu():
    cls()
    print(f"""
  {R+BO}+---------------------------------------+
  |     COINS, CLUES & CHAOS              |
  +---------------------------------------+{RS}

  {BO}Rules:{RS}
  * 15 coins (5x each of 10, 20, 50 pts) in 3 boxes
  * Each box has at least 3 coins
  * Draw one coin at a time; choose to stay or switch
  * Up to {B}4 switches{RS} allowed
  * {R}Game ends{RS} when you try to draw from an empty box
  * {Y}5-minute timer{RS} starts on your first draw

  {BO}Multipliers:{RS}
    {R}< 250   -> 0.8x{RS}
    {C}250-299 -> 1.2x{RS}
    {M}300-349 -> 1.4x{RS}
    {Y}350-369 -> 1.8x{RS}
    {G}>= 370  -> 2.5x{RS}

  {BO}Special coins:{RS}
    {M}Clue coin{RS}  -- first draw from each box reveals info about the other boxes
    {Y}Math coin{RS}  -- solve an integral for +0.2x, or lose 0.1x if wrong
""")
    input_prompt("  Press Enter to start...")


# End screen
def end_screen(reason, drawn, score, math_bonus):
    cls()
    mult  = multiplier(score, math_bonus)
    final = int(score * mult)
    base  = round(mult - math_bonus, 1)

    print(f"\n  {Y+BO}--- GAME OVER ---{RS}\n")
    print(f"  {reason}\n")
    hr()
    print(f"  Coins drawn : {len(drawn)}")
    print(f"  10pt coins  : {drawn.count(10)}")
    print(f"  20pt coins  : {drawn.count(20)}")
    print(f"  50pt coins  : {drawn.count(50)}")
    hr()
    print(f"  Raw score   : {Y}{score}{RS}")
    print(f"  Base mult   : {base}x")
    if math_bonus != 0:
        col = G if math_bonus > 0 else R
        print(f"  Math bonus  : {col}{'+' if math_bonus>0 else ''}{math_bonus}x{RS}")
    print(f"  Total mult  : {Y+BO}{mult}x{RS}")
    hr()
    print(f"\n  {G+BO}FINAL SCORE: {final}{RS}\n")


#Game loop
def play():
    main_menu()

    boxes, sizes, math_global_idx, integral = generate_game()
    clues = build_clues(sizes)

    first_draw     = [True, True, True]
    global_drawn   = 0
    math_triggered = False

    drawn       = []
    score       = 0
    math_bonus  = 0.0
    current_box = None
    switches    = 0

    timer = Timer(TIME_LIMIT)

    while True:
        if timer.expired and timer.elapsed > 0:
            end_screen("Time's up!", drawn, score, math_bonus)
            break

        time_left     = timer.left
        switches_left = MAX_SWITCHES - switches

        show_header(score, switches_left, time_left, math_bonus)
        show_boxes(boxes, current_box)
        show_drawn(drawn)

        options = {}
        print(f"  {BO}Actions:{RS}")

        if current_box is not None:
            options["d"] = ("draw", current_box)
            print(f"  {G}[d]{RS} Draw from {BOX_COLORS[current_box]}{BOX_NAMES[current_box]}{RS}")

        for i in range(3):
            if i != current_box:
                key = str(i + 1)
                if current_box is None:
                    options[key] = ("start", i)
                    print(f"  {C}[{key}]{RS} Start at {BOX_COLORS[i]}{BOX_NAMES[i]}{RS}")
                elif switches_left > 0:
                    options[key] = ("switch", i)
                    print(f"  {B}[{key}]{RS} Switch to {BOX_COLORS[i]}{BOX_NAMES[i]}{RS} ")
                else:
                    print(f"  {DIM}[{key}] {BOX_NAMES[i]} -- no switches left{RS}")

        options["q"] = ("quit", None)
        print(f"  {R}[q]{RS} Quit\n")

        choice = input_prompt("  > ").strip().lower()

        if choice == "q":
            end_screen("You quit early.", drawn, score, math_bonus)
            break

        if choice not in options:
            continue

        action, target_box = options[choice]

        if action == "switch":
            switches    += 1
            current_box  = target_box

        if action in ("start", "switch", "draw"):
            if action == "start":
                current_box = target_box

            box = boxes[current_box]

            if not timer.running and timer.elapsed == 0:
                timer.start()

            # Empty box = game over (player finds out by trying)
            if len(box) == 0:
                end_screen(
                    f"You tried to draw from {BOX_NAMES[current_box]}, it was empty. Game over!",
                    drawn, score, math_bonus
                )
                break

            coin = box.pop()
            drawn.append(coin)
            score += coin
            global_drawn += 1

            print(f"\n  Drew: {COIN_COLOR[coin]+BO}{COIN_LABEL[coin]}{RS}  "
                  f"{DIM}(+{coin} pts){RS}")

            if first_draw[current_box]:
                first_draw[current_box] = False
                time.sleep(0.4)
                show_clue(clues[current_box], current_box)

            elif not math_triggered and global_drawn - 1 == math_global_idx:
                math_triggered = True
                bonus = do_math(integral)
                math_bonus = round(math_bonus + bonus, 1)

            else:
                time.sleep(0.3)

    print()
    again = input_prompt("  Play again? (y/n): ").strip().lower()
    if again == "y":
        play()


if __name__ == "__main__":
    try:
        play()
    except KeyboardInterrupt:
        print(f"\n\n  {DIM}Thanks for playing.{RS}\n")
        sys.exit(0)
