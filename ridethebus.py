import random
import csv
import os
import sys
import time

#Cards
SUITS      = ["♠ Spades", "♥ Hearts", "♦ Diamonds", "♣ Clubs"]
RED_SUITS  = {"♥ Hearts", "♦ Diamonds"}
BLACK_SUITS= {"♠ Spades", "♣ Clubs"}
RANKS      = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
RANK_VALUE = {r: i+1 for i, r in enumerate(RANKS)}   # A=1 … K=13

CSV_FILE = "leaderboard.csv"

#ANSI colours
RED  = "\033[91m"
GRN  = "\033[92m"
YLW  = "\033[93m"
BLU  = "\033[94m"
MGN  = "\033[95m"
CYN  = "\033[96m"
WHT  = "\033[97m"
DIM  = "\033[2m"
BLD  = "\033[1m"
RST  = "\033[0m"

def col(text, color): return f"{color}{text}{RST}"

def draw_card(rank, suit):
    color = RED if suit in RED_SUITS else WHT
    return col(f"[{rank} {suit}]", color)

def banner():
    print(col("""🚌  R I D E  T H E  B U S  🚌""", YLW))

def slow_print(text, delay=0.03):
    for ch in text:
        print(ch, end='', flush=True)
        time.sleep(delay)
    print()

def deal_sound():
    print(col("  [ shuffling… ]", DIM))
    time.sleep(0.4)

#CSV helpers
def load_balance(name):
    if not os.path.exists(CSV_FILE):
        return None
    with open(CSV_FILE, newline='') as f:
        for row in csv.DictReader(f):
            if row["name"].strip().lower() == name.strip().lower():
                return int(row["balance"])
    return None

def save_balance(name, balance):
    rows = []
    found = False
    if os.path.exists(CSV_FILE):
        with open(CSV_FILE, newline='') as f:
            rows = list(csv.DictReader(f))
        for row in rows:
            if row["name"].strip().lower() == name.strip().lower():
                row["balance"] = balance
                found = True
    if not found:
        rows.append({"name": name, "balance": balance})
    with open(CSV_FILE, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["name", "balance"])
        writer.writeheader()
        writer.writerows(rows)

def show_leaderboard():
    if not os.path.exists(CSV_FILE):
        return
    print(col("\n── Leaderboard ──────────────────────", CYN))
    with open(CSV_FILE, newline='') as f:
        rows = sorted(csv.DictReader(f), key=lambda r: -int(r["balance"]))
    for i, row in enumerate(rows[:5], 1):
        bar = "★" * min(int(int(row["balance"]) // 200), 10)
        print(f"  {i}. {col(row['name'], WHT):<20} {col(row['balance'], GRN)} pts  {col(bar, YLW)}")
    print(col("─────────────────────────────────────\n", CYN))

#Game helpers
def new_deck():
    deck = [(r, s) for s in SUITS for r in RANKS]
    random.shuffle(deck)
    return deck

def deal(deck):
    return deck.pop()

def get_bet(prompt, balance, min_bet=50):
    while True:
        try:
            raw = input(prompt).strip()
            if raw.lower() in ('q', 'quit', 'exit'):
                return None
            bet = int(raw)
            if bet < min_bet:
                print(col(f"  Minimum bet is {min_bet} pts.", YLW))
            elif bet > balance:
                print(col(f"  You only have {balance} pts!", YLW))
            else:
                return bet
        except ValueError:
            print(col("  Enter a whole number.", YLW))

def ask(prompt, choices):
    while True:
        ans = input(prompt).strip().lower()
        if ans in choices:
            return ans
        print(col(f"  Please enter one of: {', '.join(choices)}", YLW))

def status_line(name, balance, bet):
    print(col(f"\n  👤 {name}  |  Balance: {balance} pts  |  Riding: {bet} pts", BLU))

# Rounds
def round_one(deck, name, balance, bet):
    print(col("\n─── Round 1: Red or Black? ───────────", MGN))
    deal_sound()
    card = deal(deck)
    rank, suit = card
    guess = ask("  Your guess (red/black): ", ["red", "black"])
    is_red = suit in RED_SUITS
    correct = (guess == "red") == is_red
    print(f"  Card: {draw_card(rank, suit)}")
    if correct:
        print(col("  ✅ Correct!", GRN))
    else:
        print(col("  ❌ Wrong!", RED))
    return card, correct

def round_two(deck, prev_card, name, balance, bet):
    prev_rank, prev_suit = prev_card
    prev_val = RANK_VALUE[prev_rank]
    print(col(f"\n─── Round 2: Higher or Lower than {draw_card(prev_rank, prev_suit)}? ───", MGN))
    print(f"  (Ace = 1, King = 13)")
    deal_sound()
    card = deal(deck)
    rank, suit = card
    guess = ask("  Your guess (higher/lower): ", ["higher", "lower"])
    new_val = RANK_VALUE[rank]
    correct = (guess == "higher" and new_val > prev_val) or \
              (guess == "lower"  and new_val < prev_val)
    if new_val == prev_val:
        correct = False  # tie = loss
        print(f"  Card: {draw_card(rank, suit)}  — It's a tie! You lose.")
    else:
        print(f"  Card: {draw_card(rank, suit)}")
        print(col("  ✅ Correct!", GRN) if correct else col("  ❌ Wrong!", RED))
    return card, correct

def round_three(deck, card1, card2, name, balance, bet):
    val1 = RANK_VALUE[card1[0]]
    val2 = RANK_VALUE[card2[0]]
    lo, hi = min(val1, val2), max(val1, val2)
    print(col(f"\n─── Round 3: Inside or Outside [{card1[0]} – {card2[0]}]? ───", MGN))
    print(f"  Previous cards: {draw_card(*card1)}  {draw_card(*card2)}")
    print(f"  Range: {lo} to {hi}  (closed set — cards equal to {lo} or {hi} count as Inside)")
    if lo == hi:
        print(col("  Cards are equal — only that exact value is Inside, everything else is Outside.", DIM))
    deal_sound()
    card = deal(deck)
    rank, suit = card
    val = RANK_VALUE[rank]
    guess = ask("  Your guess (inside/outside): ", ["inside", "outside"])
    is_inside = lo <= val <= hi
    correct = (guess == "inside") == is_inside
    print(f"  Card: {draw_card(rank, suit)}")
    if val == lo or val == hi:
        print(col("  (Boundary card — counts as Inside)", DIM))
    print(col("  ✅ Correct!", GRN) if correct else col("  ❌ Wrong!", RED))
    return card, correct

def round_four(deck, name, balance, bet):
    print(col("\n─── Round 4: Guess the Suit! ────────", MGN))
    deal_sound()
    card = deal(deck)
    rank, suit = card
    print("  The suits are: ♠ Spades | ♥ Hearts | ♦ Diamonds | ♣ Clubs")
    short_map = {"s": "♠ Spades", "h": "♥ Hearts", "d": "♦ Diamonds", "c": "♣ Clubs",
                 "spades":"♠ Spades","hearts":"♥ Hearts","diamonds":"♦ Diamonds","clubs":"♣ Clubs"}
    prompt = "  Your guess (S/H/D/C or full name): "
    while True:
        raw = input(prompt).strip().lower()
        if raw in short_map:
            guess = short_map[raw]
            break
        print(col("  Enter S, H, D, or C (or full name).", YLW))

    wrong_suits = [s for s in SUITS if s != suit and s != guess]
    if not wrong_suits:
        wrong_suits = [s for s in SUITS if s != suit]
    revealed_wrong = random.choice(wrong_suits)
    print(col(f"\n  🃏 Dealer: \"{revealed_wrong} is NOT the suit.\"", YLW))

    remaining = [s for s in SUITS if s != revealed_wrong]
    print(f"  Remaining options: {', '.join(remaining)}")
    switch = ask("  Do you want to switch your guess? (yes/no): ", ["yes", "no"])
    if switch == "yes":
        other = [s for s in remaining if s != guess]
        if len(other) == 1:
            guess = other[0]
        else:
            print(f"  Switch to which? {', '.join(other)}")
            short_map2 = {s[0].lower(): s for s in other}
            short_map2.update({s.lower(): s for s in other})
            while True:
                raw = input("  Your new guess: ").strip().lower()
                if raw in short_map2:
                    guess = short_map2[raw]
                    break
                matched = [s for s in other if s.lower() == raw]
                if matched:
                    guess = matched[0]
                    break
                print(col("  Pick from the remaining options.", YLW))
        print(col(f"  Switched to: {guess}", CYN))
    else:
        print(col(f"  Sticking with: {guess}", CYN))

    correct = (guess == suit)
    print(f"  Card: {draw_card(rank, suit)}")
    print(col("  ✅ Correct! You rode the bus!", GRN) if correct else col("  ❌ Wrong!", RED))
    return correct

#Main game loop
def play_game(name, balance):
    MIN_BALANCE = 500
    MIN_BET     = 50

    print(col(f"\n  Welcome back, {name}! Balance: {balance} pts\n", GRN))

    if balance < MIN_BALANCE:
        print(col(f"  ⛔  Your balance ({balance}) is below 500. Game over.", RED))
        return balance

    # Initial bet
    print(col("─── Place your initial bet ───────────", CYN))
    print(f"  Balance: {col(balance, GRN)} pts  |  Min bet: {col(MIN_BET, YLW)} pts")
    bet = get_bet(f"  Enter bet: ", balance, MIN_BET)
    if bet is None:
        print(col("  Cashing out before starting.", YLW))
        return balance

    balance -= bet
    riding   = bet

    deck = new_deck()
    history = []

    #ROUND 1
    status_line(name, balance, riding)
    card1, win = round_one(deck, name, balance, riding)
    if not win:
        print(col(f"  Lost {riding} pts.", RED))
        save_balance(name, balance)
        return balance

    # Payout r1 = 1.25×
    winnings_r1 = int(riding * 1.25)
    history.append(card1)

    print(col(f"\n  Payout if you leave now: {winnings_r1} pts (+{winnings_r1-riding})", GRN))
    action = ask("  Continue to Round 2 or cash out? (continue/cashout): ", ["continue", "cashout"])
    if action == "cashout":
        balance += winnings_r1
        print(col(f"  Cashed out! +{winnings_r1} pts. New balance: {balance}", GRN))
        save_balance(name, balance)
        return balance

    riding = winnings_r1

    #ROUND 2
    status_line(name, balance, riding)
    card2, win = round_two(deck, card1, name, balance, riding)
    if not win:
        print(col(f"  Lost {riding} pts.", RED))
        save_balance(name, balance)
        return balance

    winnings_r2 = int(bet * 1.5)
    history.append(card2)

    print(col(f"\n  Payout if you leave now: {winnings_r2} pts", GRN))
    action = ask("  Continue to Round 3 or cash out? (continue/cashout): ", ["continue", "cashout"])
    if action == "cashout":
        balance += winnings_r2
        print(col(f"  Cashed out! +{winnings_r2} pts. New balance: {balance}", GRN))
        save_balance(name, balance)
        return balance

    riding = winnings_r2

    #ROUND 3
    status_line(name, balance, riding)
    card3, win = round_three(deck, card1, card2, name, balance, riding)
    if not win:
        print(col(f"  Lost {riding} pts.", RED))
        save_balance(name, balance)
        return balance

    winnings_r3 = int(bet * 1.75)
    history.append(card3)

    print(col(f"\n  Payout if you leave now: {winnings_r3} pts", GRN))
    action = ask("  Continue to Round 4 or cash out? (continue/cashout): ", ["continue", "cashout"])
    if action == "cashout":
        balance += winnings_r3
        print(col(f"  Cashed out! +{winnings_r3} pts. New balance: {balance}", GRN))
        save_balance(name, balance)
        return balance

    riding = winnings_r3

    #ROUND 4
    status_line(name, balance, riding)
    win = round_four(deck, name, balance, riding)
    if not win:
        print(col(f"  Lost {riding} pts.", RED))
        save_balance(name, balance)
        return balance

    final_payout = riding * 2
    balance += final_payout
    print(col(f"\n  Congratulations {name}, You rode the bus all the way! +{final_payout} pts!", GRN))
    print(col(f"  New balance: {balance} pts", GRN))
    save_balance(name, balance)
    return balance


#Entry point
def main():
    banner()
    slow_print(col("  A card game of nerve, luck, and knowing when to stop.\n", DIM), 0.02)

    name = input(col("  Enter your name: ", CYN)).strip()
    if not name:
        name = "Stranger"

    existing = load_balance(name)
    if existing is not None:
        print(col(f"\n  Welcome back, {name}! Loaded balance: {existing} pts", GRN))
        balance = existing
    else:
        balance = 1000
        save_balance(name, balance)
        print(col(f"\n  New player! Starting balance: {balance} pts", GRN))

    show_leaderboard()

    while True:
        if balance < 500:
            print(col(f"\n  ⛔  Balance dropped below 500 pts ({balance}). You're out!", RED))
            break

        print(col("\n══════════════════════════════════════════", YLW))
        action = ask(
            col("  Start a new ride, view leaderboard, or quit? (play/leaderboard/quit): ", CYN),
            ["play", "leaderboard", "quit", "p", "l", "q"]
        )
        if action in ("quit", "q"):
            print(col(f"\n  Cashing out with {balance} pts. See you on the bus, {name}!\n", YLW))
            break
        if action in ("leaderboard", "l"):
            show_leaderboard()
            continue

        balance = play_game(name, balance)
        save_balance(name, balance)

        print(col(f"\n  Current balance: {balance} pts", BLU))

    show_leaderboard()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(col("\n\n  Game interrupted. Goodbye! 🚌\n", YLW))
        sys.exit(0)
