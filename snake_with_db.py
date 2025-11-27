import pygame
import time
import random
import psycopg2

DB_CONFIG = {
    "dbname": "snake_db",        
    "user": "postgres",         
    "password": "3657", 
    "host": "localhost",
    "port": 5432
}

# Connect to database
conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor()

# Create tables if they do not exist (ONLY if not exist, data is not deleted)
cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username VARCHAR(50) UNIQUE NOT NULL
    );
""")

cur.execute("""
    CREATE TABLE IF NOT EXISTS user_score (
        user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
        level   INTEGER NOT NULL DEFAULT 1,
        score   INTEGER NOT NULL DEFAULT 0,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
""")

conn.commit()

# Ask for username BEFORE starting pygame
username = input("Enter your username: ").strip()

# Get or create user
cur.execute("SELECT id FROM users WHERE username = %s;", (username,))
row = cur.fetchone()

if row:
    user_id = row[0]
else:
    cur.execute("INSERT INTO users (username) VALUES (%s) RETURNING id;", (username,))
    user_id = cur.fetchone()[0]
    conn.commit()

# Get saved level and score if exist
cur.execute("SELECT level, score FROM user_score WHERE user_id = %s;", (user_id,))
row = cur.fetchone()

if row:
    level = row[0]
    score = row[1]
else:
    level = 1
    score = 0

print(f"Welcome, {username}! Your current level: {level}, score: {score}")

cur.close()
conn.close()

# We will reuse user_id, level, score below
current_user_id = user_id

# =======================
# GAME CONFIG
# =======================

BASE_SPEED = 15
SPEED_INCREMENT = 3
FRUITS_PER_LEVEL = 3   # how many fruits to eat to level up
FRUIT_LIFETIME = 10.0  # seconds

window_x = 720
window_y = 480

black = pygame.Color(0, 0, 0)
white = pygame.Color(255, 255, 255)
red = pygame.Color(255, 0, 0)
green = pygame.Color(0, 255, 0)
blue = pygame.Color(0, 0, 255)
yellow = pygame.Color(255, 255, 0)
purple = pygame.Color(255, 0, 255)
wall_color = pygame.Color(128, 128, 128)  # walls color (different from snake & fruits)

FOOD_TYPES = [
    {"value": 50, "color": red, "weight": 50},
    {"value": 100, "color": yellow, "weight": 30},
    {"value": 200, "color": blue, "weight": 15},
    {"value": 500, "color": purple, "weight": 5},
]


def get_random_food_type():
    total_weight = sum(food["weight"] for food in FOOD_TYPES)
    rand = random.randint(1, total_weight)

    cumulative_weight = 0
    for food_type in FOOD_TYPES:
        cumulative_weight += food_type["weight"]
        if rand <= cumulative_weight:
            return food_type

    return FOOD_TYPES[0]


def get_walls_for_level(level_value, snake_body):
    """
    Generate random wall blocks based on level.
    Walls are 10x10 squares like fruit, random positions, not touching snake.
    """
    walls_list = []

    # how many wall blocks you want per level
    # level 1 -> 5 walls, level 2 -> 10 walls, level 3 -> 15, etc. (capped)
    num_walls = min(40, 5 + (level_value - 1) * 5)

    attempts = 0
    max_attempts = num_walls * 20  # just to avoid infinite loop if map is crowded

    while len(walls_list) < num_walls and attempts < max_attempts:
        attempts += 1
        x = random.randrange(1, (window_x // 10) - 1) * 10
        y = random.randrange(1, (window_y // 10) - 1) * 10
        cell = [x, y]

        # avoid snake starting area & duplicates
        if cell in snake_body:
            continue
        if cell in walls_list:
            continue

        walls_list.append(cell)

    return walls_list


def spawn_fruit(snake_body, walls_list):
    while True:
        x = random.randrange(1, (window_x // 10) - 1) * 10
        y = random.randrange(1, (window_y // 10) - 1) * 10
        if [x, y] not in snake_body and [x, y] not in walls_list:
            food_type = get_random_food_type()
            spawn_time = time.time()
            return [x, y], food_type, spawn_time


def show_score_and_level(game_window, score_value, level_value):
    score_font = pygame.font.SysFont('impact', 20)
    score_surface = score_font.render('Score : ' + str(score_value), True, white)
    score_rect = score_surface.get_rect()
    score_rect.topleft = (10, 10)
    game_window.blit(score_surface, score_rect)

    level_surface = score_font.render('Level : ' + str(level_value), True, white)
    level_rect = level_surface.get_rect()
    level_rect.topright = (window_x - 10, 10)
    game_window.blit(level_surface, level_rect)


def show_paused(game_window):
    font = pygame.font.SysFont('impact', 32)
    text_surface = font.render('PAUSED - Press SPACE to continue', True, yellow)
    text_rect = text_surface.get_rect(center=(window_x // 2, window_y // 2))
    game_window.blit(text_surface, text_rect)


def save_progress_to_db(user_id_value, level_value, score_value):
    """Inline-style DB save (called from pause and game_over)."""
    conn_local = psycopg2.connect(**DB_CONFIG)
    cur_local = conn_local.cursor()
    cur_local.execute("""
        INSERT INTO user_score (user_id, level, score, updated_at)
        VALUES (%s, %s, %s, NOW())
        ON CONFLICT (user_id)
        DO UPDATE SET
            level = EXCLUDED.level,
            score = EXCLUDED.score,
            updated_at = EXCLUDED.updated_at;
    """, (user_id_value, level_value, score_value))
    conn_local.commit()
    cur_local.close()
    conn_local.close()


def game_over(game_window, final_score, final_level):
    """Show game over text, save progress, and quit."""
    save_progress_to_db(current_user_id, final_level, final_score)

    my_font = pygame.font.SysFont('impact', 50)
    game_over_surface = my_font.render('Your Score is : ' + str(final_score), True, red)
    game_over_rect = game_over_surface.get_rect()
    game_over_rect.midtop = (window_x / 2, window_y / 4)
    game_window.blit(game_over_surface, game_over_rect)
    pygame.display.flip()
    time.sleep(2)
    print(f"Good luck next time! Your current level: {final_level}, score: {final_score}")
    pygame.quit()
    quit()


# =======================
# GAME INITIALIZATION
# =======================

pygame.init()
pygame.display.set_caption('amanbol snake')
game_window = pygame.display.set_mode((window_x, window_y))
fps = pygame.time.Clock()

# Starting snake state
snake_position = [100, 50]
snake_body = [
    [100, 50],
    [90, 50],
    [80, 50],
    [70, 50]
]

# Use loaded level and score from DB
fruits_eaten_this_level = 0
speed = BASE_SPEED + (level - 1) * SPEED_INCREMENT
walls = get_walls_for_level(level, snake_body)

# Fruit initial spawn
fruit_position, fruit_type, fruit_spawn_time = spawn_fruit(snake_body, walls)
fruit_spawn = True

direction = 'RIGHT'
change_to = direction
paused = False

# =======================
# MAIN GAME LOOP
# =======================

while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            # Save on direct window close
            save_progress_to_db(current_user_id, level, score)
            pygame.quit()
            quit()

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                change_to = 'UP'
            elif event.key == pygame.K_DOWN:
                change_to = 'DOWN'
            elif event.key == pygame.K_LEFT:
                change_to = 'LEFT'
            elif event.key == pygame.K_RIGHT:
                change_to = 'RIGHT'
            elif event.key == pygame.K_SPACE:
                paused = not paused
                if paused:
                    # Save when pausing
                    save_progress_to_db(current_user_id, level, score)

    if paused:
        game_window.fill(black)

        # Draw snake
        for pos in snake_body:
            pygame.draw.rect(game_window, green, pygame.Rect(pos[0], pos[1], 10, 10))

        # Draw fruit
        pygame.draw.rect(
            game_window,
            fruit_type["color"],
            pygame.Rect(fruit_position[0], fruit_position[1], 10, 10)
        )

        # Draw walls (same block size as fruit)
        for wall in walls:
            pygame.draw.rect(game_window, wall_color, pygame.Rect(wall[0], wall[1], 10, 10))

        # HUD
        show_score_and_level(game_window, score, level)
        show_paused(game_window)

        pygame.display.update()
        fps.tick(5)
        continue  # skip movement logic

    # Direction update
    if change_to == 'UP' and direction != 'DOWN':
        direction = 'UP'
    if change_to == 'DOWN' and direction != 'UP':
        direction = 'DOWN'
    if change_to == 'LEFT' and direction != 'RIGHT':
        direction = 'LEFT'
    if change_to == 'RIGHT' and direction != 'LEFT':
        direction = 'RIGHT'

    # Movement
    if direction == 'UP':
        snake_position[1] -= 10
    if direction == 'DOWN':
        snake_position[1] += 10
    if direction == 'LEFT':
        snake_position[0] -= 10
    if direction == 'RIGHT':
        snake_position[0] += 10

    snake_body.insert(0, list(snake_position))

    current_time = time.time()
    time_elapsed = current_time - fruit_spawn_time
    fruit_expired = time_elapsed >= FRUIT_LIFETIME

    # Fruit eaten
    if snake_position[0] == fruit_position[0] and snake_position[1] == fruit_position[1]:
        score += fruit_type["value"]
        fruit_spawn = False
        fruits_eaten_this_level += 1

        # Level up
        if fruits_eaten_this_level >= FRUITS_PER_LEVEL:
            level += 1
            fruits_eaten_this_level = 0
            speed = BASE_SPEED + (level - 1) * SPEED_INCREMENT
            walls = get_walls_for_level(level, snake_body)

    elif fruit_expired:
        fruit_spawn = False
        snake_body.pop()
    else:
        # Normal move, no growth
        snake_body.pop()

    # Respawn fruit if needed
    if not fruit_spawn:
        fruit_position, fruit_type, fruit_spawn_time = spawn_fruit(snake_body, walls)
    fruit_spawn = True

    # Draw background
    game_window.fill(black)

    # Draw snake
    for pos in snake_body:
        pygame.draw.rect(game_window, green, pygame.Rect(pos[0], pos[1], 10, 10))

    # Draw fruit
    if not fruit_expired:
        pygame.draw.rect(
            game_window,
            fruit_type["color"],
            pygame.Rect(fruit_position[0], fruit_position[1], 10, 10)
        )

    # Draw walls (10x10 blocks, random positions)
    for wall in walls:
        pygame.draw.rect(game_window, wall_color, pygame.Rect(wall[0], wall[1], 10, 10))

    # Collision with window borders
    if snake_position[0] < 10 or snake_position[0] > window_x - 20:
        game_over(game_window, score, level)
    if snake_position[1] < 10 or snake_position[1] > window_y - 20:
        game_over(game_window, score, level)

    # Collision with itself
    for block in snake_body[1:]:
        if snake_position[0] == block[0] and snake_position[1] == block[1]:
            game_over(game_window, score, level)

    # Collision with walls
    if snake_position in walls:
        game_over(game_window, score, level)

    # HUD
    show_score_and_level(game_window, score, level)

    pygame.display.update()
    fps.tick(speed)
