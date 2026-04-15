import pygame
import sys
import random
import os

# ==========================================
# --- 1. CONFIGURATION (GAME MASTER) ---
# ==========================================
CONFIG = {
    "GRID_SIZE": 11,
    "MOVES": 12,
    "SHIP_SIZES": [3, 2, 2, 4], 
    
    # Timers (in seconds)
    "BOMBING_TIME": 300,   # 5 Minutes
    "GUESSING_TIME": 120,  # 2 Minutes
    
    # Point Values (Scaled so an optimal 5.0x run yields ~1500 points)
    "POINTS": {
        "base": 430,
        "hit": 45,
        "sink": 150,
        "miss_all": 0,             
        "ship_replication": 260,
        "layout_replication": 860,
        "first_try": 130,
        "perfect_sink": 110
    }
}

# ==========================================
# --- 2. INITIALIZATION & CONSTANTS ---
# ==========================================
pygame.init()

# Launch in Fullscreen
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
WIDTH, HEIGHT = screen.get_size()
pygame.display.set_caption("Is this Hormuz?")
clock = pygame.time.Clock()

# --- VIBRANT COLOR PALETTE ---
BG_COLOR = (15, 25, 45)          
TEXT_COLOR = (240, 245, 255)     
SUBTEXT_COLOR = (150, 170, 200)  

GRID_BG = (25, 45, 75)           
GRID_OUTLINE = (50, 90, 140)     
HOVER_COLOR = (45, 80, 120)      

HIT_COLOR = (255, 60, 80)        
MISS_BG = (20, 35, 60)           
SHIP_ACTUAL = (40, 220, 120)     
SHIP_GUESS = (160, 60, 220)      

BTN_BLUE = (0, 120, 215)
BTN_GREEN = (34, 177, 76)
BTN_ORANGE = (255, 128, 0)
BTN_DARK = (60, 70, 90)

# Distance Colors (Heatmap style)
def get_dist_color(dist):
    if dist == 1: return (255, 150, 50)   
    elif dist == 2: return (255, 215, 0)  
    elif dist == 3: return (150, 255, 100)
    else: return (0, 255, 255)            

# Dynamic Scaling Based on Screen Resolution
font_large = pygame.font.SysFont(None, int(HEIGHT * 0.06))
font_med = pygame.font.SysFont(None, int(HEIGHT * 0.04))
font_small = pygame.font.SysFont(None, int(HEIGHT * 0.025))

# Math to perfectly bound the grid between the text and the bottom buttons
max_grid_width = int(WIDTH * 0.9)
max_grid_height = int(HEIGHT * 0.55)
CELL_SIZE = min(max_grid_width // max(1, CONFIG["GRID_SIZE"]), max_grid_height // max(1, CONFIG["GRID_SIZE"]))
GRID_OFFSET_X = (WIDTH - (CONFIG["GRID_SIZE"] * CELL_SIZE)) // 2
GRID_OFFSET_Y = int(HEIGHT * 0.22)

# States
STATE_MENU = 0
STATE_GM_SETUP = 1
STATE_REVIEW = 2
STATE_PLAY = 3
STATE_REPLICATE = 4
STATE_RESULTS = 5

# ==========================================
# --- 3. DATABASE HELPER ---
# ==========================================
def save_game_to_db(actual_ships, guessed_ships, moves, final_score):
    db_file = "games_db.txt"
    game_num = 1
    
    if os.path.exists(db_file):
        with open(db_file, "r") as f:
            lines = f.readlines()
            game_num = len([l for l in lines if l.strip()]) + 1
            
    def compress_ships(ships):
        return "-".join(["".join([f"{r}{c}" for r, c in ship]) for ship in ships])
        
    actual_str = compress_ships(actual_ships)
    guess_str = compress_ships(guessed_ships) if guessed_ships else "None"
    moves_str = "-".join([f"{r}{c}" for r, c in moves])
    
    record = f"Game:{game_num} | Actual:{actual_str} | Guess:{guess_str} | Moves:{moves_str} | Score:{final_score}\n"
    
    with open(db_file, "a") as f:
        f.write(record)
    print(f"Game saved to database! Total Games Played: {game_num}")

# ==========================================
# --- 4. GAME LOGIC HELPERS ---
# ==========================================
def get_all_ship_cells(ships):
    cells = set()
    for ship in ships:
        for r, c in ship:
            cells.add((r, c))
    return cells

def get_manhattan_dist(r, c, ships):
    cells = get_all_ship_cells(ships)
    if (r, c) in cells:
        return 0
    return min(abs(r - sr) + abs(c - sc) for sr, sc in cells)

def get_ship_footprint(r, c, length, horizontal):
    if horizontal:
        if c + length > CONFIG["GRID_SIZE"]: return None
        return set((r, c + i) for i in range(length))
    else:
        if r + length > CONFIG["GRID_SIZE"]: return None
        return set((r + i, c) for i in range(length))

def generate_random_ships():
    ships = []
    sizes = CONFIG["SHIP_SIZES"].copy()
    for size in sizes:
        placed = False
        while not placed:
            horizontal = random.choice([True, False])
            r = random.randint(0, CONFIG["GRID_SIZE"] - 1)
            c = random.randint(0, CONFIG["GRID_SIZE"] - 1)
            footprint = get_ship_footprint(r, c, size, horizontal)
            if footprint:
                overlap = False
                for existing in ships:
                    if footprint.intersection(existing):
                        overlap = True
                        break
                if not overlap:
                    ships.append(footprint)
                    placed = True
    return ships

def calculate_live_score(actual_ships, move_history):
    score = CONFIG["POINTS"]["base"]
    hits = sinks = perfect_sinks = 0
    
    for ship in actual_ships:
        ship_hits = [i for i, move in enumerate(move_history) if move in ship]
        hits += len(ship_hits)
        if len(ship_hits) == len(ship):
            sinks += 1
            if max(ship_hits) - min(ship_hits) == len(ship) - 1:
                perfect_sinks += 1

    score += (CONFIG["POINTS"]["hit"] * hits) + (CONFIG["POINTS"]["sink"] * sinks) + (CONFIG["POINTS"]["perfect_sink"] * perfect_sinks)
    
    if move_history and move_history[0] in get_all_ship_cells(actual_ships):
        score += CONFIG["POINTS"]["first_try"]
        
    return score, sinks

def calculate_score(actual_ships, guessed_ships, move_history):
    score, sinks = calculate_live_score(actual_ships, move_history)
    hits = sum(1 for m in move_history if get_manhattan_dist(m[0], m[1], actual_ships) == 0)

    correct_ships = 0
    matched_guessed = []
    for actual_ship in actual_ships:
        for g_ship in guessed_ships:
            if g_ship == actual_ship and g_ship not in matched_guessed:
                correct_ships += 1
                matched_guessed.append(g_ship)
                break
                
    score += (CONFIG["POINTS"]["ship_replication"] * correct_ships)
    if correct_ships == len(actual_ships):
        score += CONFIG["POINTS"]["layout_replication"]
        
    perfect_sinks = 0
    for ship in actual_ships:
        ship_hits = [i for i, move in enumerate(move_history) if move in ship]
        if len(ship_hits) == len(ship) and max(ship_hits) - min(ship_hits) == len(ship) - 1:
            perfect_sinks += 1

    return score, hits, sinks, perfect_sinks, correct_ships

def reset_game():
    return [], [], [], {}, CONFIG["POINTS"]["base"], 0, 0, None, CONFIG["SHIP_SIZES"].copy(), True, 0

def draw_timer(screen, time_left_ms):
    minutes = (time_left_ms // 1000) // 60
    seconds = (time_left_ms // 1000) % 60
    color = HIT_COLOR if time_left_ms <= 30000 else TEXT_COLOR  
    timer_txt = font_large.render(f"{minutes:02}:{seconds:02}", True, color)
    screen.blit(timer_txt, (WIDTH - timer_txt.get_width() - 30, int(HEIGHT * 0.05)))

def draw_score_legend(screen):
    """Draws the scoring rubric on the left side of the screen."""
    start_x = int(WIDTH * 0.03)
    start_y = int(HEIGHT * 0.3)
    
    title = font_med.render("Points Guide", True, BTN_ORANGE)
    screen.blit(title, (start_x, start_y))
    
    rules = [
        f"Base Score: {CONFIG['POINTS']['base']}",
        f"Hit: +{CONFIG['POINTS']['hit']}",
        f"Sink: +{CONFIG['POINTS']['sink']}",
        f"Perfect Sink: +{CONFIG['POINTS']['perfect_sink']}",
        f"First Try: +{CONFIG['POINTS']['first_try']}",
        f"Ship Rep: +{CONFIG['POINTS']['ship_replication']}",
        f"Layout Rep: +{CONFIG['POINTS']['layout_replication']}"
    ]
    
    y_offset = start_y + int(HEIGHT * 0.06)
    for text in rules:
        txt_surface = font_small.render(text, True, SUBTEXT_COLOR)
        screen.blit(txt_surface, (start_x, y_offset))
        y_offset += int(HEIGHT * 0.035)


# ==========================================
# --- 5. MAIN GAME LOOP ---
# ==========================================
def main():
    state = STATE_MENU
    actual_ships, guessed_ships, move_history, attacked_cells, live_score, previous_sinks, sunk_timer, score_data, setup_queue, horizontal_placement, phase_timer_start = reset_game()

    btn_w, btn_h = int(WIDTH * 0.3), int(HEIGHT * 0.08)
    y_btn = int(HEIGHT * 0.85)

    running = True
    while running:
        screen.fill(BG_COLOR)
        mouse_pos = pygame.mouse.get_pos()
        grid_r = (mouse_pos[1] - GRID_OFFSET_Y) // CELL_SIZE
        grid_c = (mouse_pos[0] - GRID_OFFSET_X) // CELL_SIZE
        in_grid = 0 <= grid_r < CONFIG["GRID_SIZE"] and 0 <= grid_c < CONFIG["GRID_SIZE"]
        current_ticks = pygame.time.get_ticks()

        # --- TIMER AUTO-TRANSITION LOGIC ---
        time_left = 0
        if state == STATE_PLAY:
            elapsed = current_ticks - phase_timer_start
            time_left = max(0, (CONFIG["BOMBING_TIME"] * 1000) - elapsed)
            if time_left == 0:
                state = STATE_REPLICATE
                setup_queue = CONFIG["SHIP_SIZES"].copy()
                horizontal_placement = True
                phase_timer_start = pygame.time.get_ticks()

        elif state == STATE_REPLICATE:
            elapsed = current_ticks - phase_timer_start
            time_left = max(0, (CONFIG["GUESSING_TIME"] * 1000) - elapsed)
            if time_left == 0:
                score_data = calculate_score(actual_ships, guessed_ships, move_history)
                save_game_to_db(actual_ships, guessed_ships, move_history, score_data[0])
                state = STATE_RESULTS


        # --- EVENT HANDLING ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            # Universal Escape to Quit
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
                
            if state == STATE_MENU:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if WIDTH//2 - btn_w//2 <= mouse_pos[0] <= WIDTH//2 + btn_w//2:
                        if int(HEIGHT*0.4) <= mouse_pos[1] <= int(HEIGHT*0.4) + btn_h:
                            actual_ships = generate_random_ships()
                            state = STATE_REVIEW
                        elif int(HEIGHT*0.52) <= mouse_pos[1] <= int(HEIGHT*0.52) + btn_h:
                            state = STATE_GM_SETUP

            elif state == STATE_GM_SETUP:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 3:
                        horizontal_placement = not horizontal_placement
                    elif event.button == 1 and in_grid and setup_queue:
                        length = setup_queue[0]
                        footprint = get_ship_footprint(grid_r, grid_c, length, horizontal_placement)
                        if footprint and not any(footprint.intersection(s) for s in actual_ships):
                            actual_ships.append(footprint)
                            setup_queue.pop(0)
                            if not setup_queue:
                                state = STATE_REVIEW

            elif state == STATE_REVIEW:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if WIDTH//2 - btn_w - 20 <= mouse_pos[0] <= WIDTH//2 - 20 and y_btn <= mouse_pos[1] <= y_btn + btn_h:
                        actual_ships = generate_random_ships()
                    elif WIDTH//2 + 20 <= mouse_pos[0] <= WIDTH//2 + btn_w + 20 and y_btn <= mouse_pos[1] <= y_btn + btn_h:
                        state = STATE_PLAY
                        phase_timer_start = pygame.time.get_ticks() 

            elif state == STATE_PLAY:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if len(move_history) < CONFIG["MOVES"]:
                        if in_grid and (grid_r, grid_c) not in attacked_cells:
                            move_history.append((grid_r, grid_c))
                            dist = get_manhattan_dist(grid_r, grid_c, actual_ships)
                            attacked_cells[(grid_r, grid_c)] = "HIT" if dist == 0 else dist
                            
                            live_score, current_sinks = calculate_live_score(actual_ships, move_history)
                            if current_sinks > previous_sinks:
                                sunk_timer = 60
                                previous_sinks = current_sinks
                    else:
                        if WIDTH//2 - btn_w//2 <= mouse_pos[0] <= WIDTH//2 + btn_w//2 and y_btn <= mouse_pos[1] <= y_btn + btn_h:
                            state = STATE_REPLICATE
                            setup_queue = CONFIG["SHIP_SIZES"].copy()
                            horizontal_placement = True
                            phase_timer_start = pygame.time.get_ticks() 

            elif state == STATE_REPLICATE:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_u and len(guessed_ships) > 0:
                    last_ship = guessed_ships.pop()
                    setup_queue.insert(0, len(last_ship))
                
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 3:
                        horizontal_placement = not horizontal_placement
                    elif event.button == 1:
                        if not setup_queue and WIDTH//2 - btn_w//2 <= mouse_pos[0] <= WIDTH//2 + btn_w//2 and y_btn <= mouse_pos[1] <= y_btn + btn_h:
                            score_data = calculate_score(actual_ships, guessed_ships, move_history)
                            save_game_to_db(actual_ships, guessed_ships, move_history, score_data[0])
                            state = STATE_RESULTS
                            
                        elif in_grid and setup_queue:
                            length = setup_queue[0]
                            footprint = get_ship_footprint(grid_r, grid_c, length, horizontal_placement)
                            if footprint and not any(footprint.intersection(s) for s in guessed_ships):
                                guessed_ships.append(footprint)
                                setup_queue.pop(0)

            elif state == STATE_RESULTS:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if WIDTH//2 - btn_w//2 <= mouse_pos[0] <= WIDTH//2 + btn_w//2 and y_btn <= mouse_pos[1] <= y_btn + btn_h:
                        state = STATE_MENU
                        actual_ships, guessed_ships, move_history, attacked_cells, live_score, previous_sinks, sunk_timer, score_data, setup_queue, horizontal_placement, phase_timer_start = reset_game()


        # --- DRAWING LOGIC ---
        esc_txt = font_small.render("Press ESC to Quit", True, SUBTEXT_COLOR)
        screen.blit(esc_txt, (20, 20))
        
        if state == STATE_MENU:
            title = font_large.render("IS THIS HORMUZ?", True, TEXT_COLOR)
            screen.blit(title, (WIDTH//2 - title.get_width()//2, int(HEIGHT*0.2)))
            
            y_pos_1 = int(HEIGHT*0.4)
            pygame.draw.rect(screen, BTN_BLUE, (WIDTH//2 - btn_w//2, y_pos_1, btn_w, btn_h), border_radius=10)
            btn1 = font_med.render("Play (Random Ships)", True, TEXT_COLOR)
            screen.blit(btn1, (WIDTH//2 - btn1.get_width()//2, y_pos_1 + (btn_h - btn1.get_height())//2))
            
            y_pos_2 = int(HEIGHT*0.52)
            pygame.draw.rect(screen, BTN_DARK, (WIDTH//2 - btn_w//2, y_pos_2, btn_w, btn_h), border_radius=10)
            btn2 = font_med.render("Game Master Setup", True, TEXT_COLOR)
            screen.blit(btn2, (WIDTH//2 - btn2.get_width()//2, y_pos_2 + (btn_h - btn2.get_height())//2))

        elif state == STATE_GM_SETUP:
            txt = font_med.render("GAME MASTER: Place Ships", True, TEXT_COLOR)
            screen.blit(txt, (WIDTH//2 - txt.get_width()//2, int(HEIGHT*0.05)))
            txt2 = font_small.render("Left Click = Place | Right Click = Rotate", True, SUBTEXT_COLOR)
            screen.blit(txt2, (WIDTH//2 - txt2.get_width()//2, int(HEIGHT*0.1)))
            
            if setup_queue:
                info = font_med.render(f"Placing Size: {setup_queue[0]}", True, BTN_ORANGE)
                screen.blit(info, (WIDTH//2 - info.get_width()//2, int(HEIGHT*0.15)))

            for r in range(CONFIG["GRID_SIZE"]):
                for c in range(CONFIG["GRID_SIZE"]):
                    rect = (GRID_OFFSET_X + c*CELL_SIZE, GRID_OFFSET_Y + r*CELL_SIZE, CELL_SIZE, CELL_SIZE)
                    pygame.draw.rect(screen, GRID_BG, rect)
                    pygame.draw.rect(screen, GRID_OUTLINE, rect, 1)

            for ship in actual_ships:
                for r, c in ship:
                    rect = (GRID_OFFSET_X + c*CELL_SIZE, GRID_OFFSET_Y + r*CELL_SIZE, CELL_SIZE, CELL_SIZE)
                    pygame.draw.rect(screen, SHIP_ACTUAL, rect)
                    pygame.draw.rect(screen, GRID_OUTLINE, rect, 1)

            if in_grid and setup_queue:
                footprint = get_ship_footprint(grid_r, grid_c, setup_queue[0], horizontal_placement)
                if footprint:
                    color = HIT_COLOR if any(footprint.intersection(s) for s in actual_ships) else SHIP_GUESS
                    for r, c in footprint:
                        rect = (GRID_OFFSET_X + c*CELL_SIZE, GRID_OFFSET_Y + r*CELL_SIZE, CELL_SIZE, CELL_SIZE)
                        pygame.draw.rect(screen, color, rect, 3)

        elif state == STATE_REVIEW:
            txt = font_med.render("GAME MASTER REVIEW PHASE", True, BTN_BLUE)
            screen.blit(txt, (WIDTH//2 - txt.get_width()//2, int(HEIGHT*0.05)))
            txt2 = font_small.render("Ensure the player is looking away before continuing!", True, SUBTEXT_COLOR)
            screen.blit(txt2, (WIDTH//2 - txt2.get_width()//2, int(HEIGHT*0.1)))

            for r in range(CONFIG["GRID_SIZE"]):
                for c in range(CONFIG["GRID_SIZE"]):
                    rect = (GRID_OFFSET_X + c*CELL_SIZE, GRID_OFFSET_Y + r*CELL_SIZE, CELL_SIZE, CELL_SIZE)
                    pygame.draw.rect(screen, GRID_BG, rect)
                    pygame.draw.rect(screen, GRID_OUTLINE, rect, 1)

            for ship in actual_ships:
                for r, c in ship:
                    rect = (GRID_OFFSET_X + c*CELL_SIZE, GRID_OFFSET_Y + r*CELL_SIZE, CELL_SIZE, CELL_SIZE)
                    pygame.draw.rect(screen, SHIP_ACTUAL, rect)
                    pygame.draw.rect(screen, GRID_OUTLINE, rect, 1)

            pygame.draw.rect(screen, BTN_ORANGE, (WIDTH//2 - btn_w - 20, y_btn, btn_w, btn_h), border_radius=10)
            btn_regen = font_med.render("Regenerate", True, TEXT_COLOR)
            screen.blit(btn_regen, (WIDTH//2 - btn_w//2 - 20 - btn_regen.get_width()//2, y_btn + (btn_h - btn_regen.get_height())//2))

            pygame.draw.rect(screen, BTN_GREEN, (WIDTH//2 + 20, y_btn, btn_w, btn_h), border_radius=10)
            btn_start = font_med.render("Start Game", True, TEXT_COLOR)
            screen.blit(btn_start, (WIDTH//2 + 20 + btn_w//2 - btn_start.get_width()//2, y_btn + (btn_h - btn_start.get_height())//2))

        elif state == STATE_PLAY:
            draw_timer(screen, time_left)
            draw_score_legend(screen)
            
            mult_txt = font_large.render(f"Score: {live_score}", True, TEXT_COLOR)
            screen.blit(mult_txt, (WIDTH//2 - mult_txt.get_width()//2, int(HEIGHT*0.05)))
            
            moves_left = CONFIG["MOVES"] - len(move_history)
            
            if moves_left > 0:
                txt = font_med.render(f"Moves Left: {moves_left}", True, HIT_COLOR if moves_left < 3 else TEXT_COLOR)
                screen.blit(txt, (WIDTH//2 - txt.get_width()//2, int(HEIGHT*0.12)))
            else:
                txt = font_med.render("Out of Moves! Analyze your intel.", True, BTN_ORANGE)
                screen.blit(txt, (WIDTH//2 - txt.get_width()//2, int(HEIGHT*0.12)))
                
                pygame.draw.rect(screen, BTN_GREEN, (WIDTH//2 - btn_w//2, y_btn, btn_w, btn_h), border_radius=10)
                btn_txt = font_med.render("Proceed to Guessing", True, TEXT_COLOR)
                screen.blit(btn_txt, (WIDTH//2 - btn_txt.get_width()//2, y_btn + (btn_h - btn_txt.get_height())//2))

            if sunk_timer > 0:
                sunk_txt = font_large.render("SHIP SUNK!", True, SHIP_ACTUAL)
                screen.blit(sunk_txt, (WIDTH//2 - sunk_txt.get_width()//2, int(HEIGHT*0.18)))
                sunk_timer -= 1

            for r in range(CONFIG["GRID_SIZE"]):
                for c in range(CONFIG["GRID_SIZE"]):
                    rect = (GRID_OFFSET_X + c*CELL_SIZE, GRID_OFFSET_Y + r*CELL_SIZE, CELL_SIZE, CELL_SIZE)
                    
                    if (r, c) in attacked_cells:
                        val = attacked_cells[(r, c)]
                        if val == "HIT":
                            pygame.draw.rect(screen, HIT_COLOR, rect)
                            txt_c = font_med.render("X", True, TEXT_COLOR)
                        else:
                            pygame.draw.rect(screen, MISS_BG, rect)
                            dist_color = get_dist_color(val)
                            txt_c = font_med.render(str(val), True, dist_color)
                        screen.blit(txt_c, (rect[0] + CELL_SIZE//2 - txt_c.get_width()//2, rect[1] + CELL_SIZE//2 - txt_c.get_height()//2))
                    else:
                        is_hovering = in_grid and grid_r == r and grid_c == c and moves_left > 0
                        pygame.draw.rect(screen, HOVER_COLOR if is_hovering else GRID_BG, rect)
                    pygame.draw.rect(screen, GRID_OUTLINE, rect, 1)

        elif state == STATE_REPLICATE:
            draw_timer(screen, time_left)
            draw_score_legend(screen)
            
            mult_txt = font_large.render(f"Locked Score: {live_score}", True, TEXT_COLOR)
            screen.blit(mult_txt, (WIDTH//2 - mult_txt.get_width()//2, int(HEIGHT*0.05)))

            txt = font_med.render("Guess Ship Layout", True, TEXT_COLOR)
            screen.blit(txt, (WIDTH//2 - txt.get_width()//2, int(HEIGHT*0.12)))
            txt2 = font_small.render("Right Click = Rotate | Press 'U' to Undo | Hits in red", True, SUBTEXT_COLOR)
            screen.blit(txt2, (WIDTH//2 - txt2.get_width()//2, int(HEIGHT*0.16)))

            if setup_queue:
                info = font_med.render(f"Placing Size: {setup_queue[0]}", True, BTN_ORANGE)
                screen.blit(info, (WIDTH//2 - info.get_width()//2, int(HEIGHT*0.2)))
            else:
                pygame.draw.rect(screen, BTN_GREEN, (WIDTH//2 - btn_w//2, y_btn, btn_w, btn_h), border_radius=10)
                btn_txt = font_med.render("Submit Guess", True, TEXT_COLOR)
                screen.blit(btn_txt, (WIDTH//2 - btn_txt.get_width()//2, y_btn + (btn_h - btn_txt.get_height())//2))

            for r in range(CONFIG["GRID_SIZE"]):
                for c in range(CONFIG["GRID_SIZE"]):
                    rect = (GRID_OFFSET_X + c*CELL_SIZE, GRID_OFFSET_Y + r*CELL_SIZE, CELL_SIZE, CELL_SIZE)
                    pygame.draw.rect(screen, GRID_BG, rect)

            for ship in guessed_ships:
                for r, c in ship:
                    rect = (GRID_OFFSET_X + c*CELL_SIZE, GRID_OFFSET_Y + r*CELL_SIZE, CELL_SIZE, CELL_SIZE)
                    pygame.draw.rect(screen, SHIP_GUESS, rect)
            
            if in_grid and setup_queue:
                footprint = get_ship_footprint(grid_r, grid_c, setup_queue[0], horizontal_placement)
                if footprint:
                    color = HIT_COLOR if any(footprint.intersection(s) for s in guessed_ships) else SHIP_GUESS
                    for r, c in footprint:
                        rect = (GRID_OFFSET_X + c*CELL_SIZE, GRID_OFFSET_Y + r*CELL_SIZE, CELL_SIZE, CELL_SIZE)
                        pygame.draw.rect(screen, color, rect, 3)

            for r in range(CONFIG["GRID_SIZE"]):
                for c in range(CONFIG["GRID_SIZE"]):
                    rect = (GRID_OFFSET_X + c*CELL_SIZE, GRID_OFFSET_Y + r*CELL_SIZE, CELL_SIZE, CELL_SIZE)
                    
                    if (r, c) in attacked_cells:
                        val = attacked_cells[(r, c)]
                        is_covered = any((r,c) in s for s in guessed_ships)
                        
                        if val == "HIT":
                            pygame.draw.rect(screen, HIT_COLOR, rect, max(1, CELL_SIZE//15)) 
                            txt_c = font_med.render("X", True, TEXT_COLOR if is_covered else HIT_COLOR)
                        else:
                            dist_color = TEXT_COLOR if is_covered else get_dist_color(val)
                            txt_c = font_med.render(str(val), True, dist_color)
                        screen.blit(txt_c, (rect[0] + CELL_SIZE//2 - txt_c.get_width()//2, rect[1] + CELL_SIZE//2 - txt_c.get_height()//2))
                    
                    pygame.draw.rect(screen, GRID_OUTLINE, rect, 1)

        elif state == STATE_RESULTS:
            final_score, hits, sinks, perfect_sinks, correct_ships = score_data
            
            title = font_large.render(f"FINAL SCORE: {final_score}", True, TEXT_COLOR)
            screen.blit(title, (WIDTH//2 - title.get_width()//2, int(HEIGHT*0.03)))
            
            title2 = font_med.render(f"SCORE x 5.0: {int(final_score * 5.0)}", True, BTN_ORANGE)
            screen.blit(title2, (WIDTH//2 - title2.get_width()//2, int(HEIGHT*0.08)))
            
            stats = [
                f"Base Score: {CONFIG['POINTS']['base']}",
                f"Hits: {hits} (+{hits * CONFIG['POINTS']['hit']})",
                f"Sinks: {sinks} (+{sinks * CONFIG['POINTS']['sink']})",
                f"Perfect Sinks: {perfect_sinks} (+{perfect_sinks * CONFIG['POINTS']['perfect_sink']})",
                f"Correct Ships: {correct_ships} (+{correct_ships * CONFIG['POINTS']['ship_replication']})"
            ]
            if move_history and move_history[0] in get_all_ship_cells(actual_ships):
                stats.append(f"First Try Bonus: Yes (+{CONFIG['POINTS']['first_try']})")
            if correct_ships == len(actual_ships):
                stats.append(f"Layout Bonus: Yes (+{CONFIG['POINTS']['layout_replication']})")

            for i, text in enumerate(stats):
                txt = font_med.render(text, True, SUBTEXT_COLOR)
                screen.blit(txt, (int(WIDTH*0.1), int(HEIGHT*0.16) + i*int(HEIGHT*0.04)))

            available_width = int(WIDTH * 0.4)
            available_height = int(HEIGHT * 0.35) 
            mini_size = min(
                available_width // max(1, CONFIG["GRID_SIZE"]),
                available_height // max(1, CONFIG["GRID_SIZE"]),
                CELL_SIZE
            )

            y_start = int(HEIGHT * 0.45)
            total_board_w = CONFIG["GRID_SIZE"] * mini_size
            spacing = int(WIDTH * 0.1)
            x_offset_actual = (WIDTH - (total_board_w * 2 + spacing)) // 2
            x_offset_guess = x_offset_actual + total_board_w + spacing
            
            lbl1 = font_med.render("Actual Board", True, TEXT_COLOR)
            screen.blit(lbl1, (x_offset_actual + total_board_w//2 - lbl1.get_width()//2, y_start - int(HEIGHT*0.05)))
            for r in range(CONFIG["GRID_SIZE"]):
                for c in range(CONFIG["GRID_SIZE"]):
                    rect = (x_offset_actual + c*mini_size, y_start + r*mini_size, mini_size, mini_size)
                    pygame.draw.rect(screen, GRID_BG, rect)
                    pygame.draw.rect(screen, GRID_OUTLINE, rect, 1)
                    if any((r,c) in s for s in actual_ships):
                        pygame.draw.rect(screen, SHIP_ACTUAL, rect)
                        pygame.draw.rect(screen, TEXT_COLOR, rect, 1)
                    if (r,c) in attacked_cells:
                        pygame.draw.circle(screen, HIT_COLOR if attacked_cells[(r,c)] == "HIT" else TEXT_COLOR, (rect[0]+mini_size//2, rect[1]+mini_size//2), max(2, mini_size//6))

            lbl2 = font_med.render("Your Guess", True, TEXT_COLOR)
            screen.blit(lbl2, (x_offset_guess + total_board_w//2 - lbl2.get_width()//2, y_start - int(HEIGHT*0.05)))
            for r in range(CONFIG["GRID_SIZE"]):
                for c in range(CONFIG["GRID_SIZE"]):
                    rect = (x_offset_guess + c*mini_size, y_start + r*mini_size, mini_size, mini_size)
                    pygame.draw.rect(screen, GRID_BG, rect)
                    pygame.draw.rect(screen, GRID_OUTLINE, rect, 1)
                    if any((r,c) in s for s in guessed_ships):
                        pygame.draw.rect(screen, SHIP_GUESS, rect)
                        pygame.draw.rect(screen, TEXT_COLOR, rect, 1)
                        
            pygame.draw.rect(screen, BTN_BLUE, (WIDTH//2 - btn_w//2, y_btn, btn_w, btn_h), border_radius=10)
            btn_txt = font_med.render("Main Menu", True, TEXT_COLOR)
            screen.blit(btn_txt, (WIDTH//2 - btn_txt.get_width()//2, y_btn + (btn_h - btn_txt.get_height())//2))

        pygame.display.flip()
        clock.tick(30)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()