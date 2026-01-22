from trio import current_time
import pygame
import math
import random
from typing import List, Tuple

# Initialize Pygame
pygame.init()

# Constants
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
YELLOW = (255, 255, 0)

# Game settings
INITIAL_ASTEROID_SPAWN_RATE = 3000  # milliseconds
MIN_ASTEROID_SPAWN_RATE = 1000  # Lower minimum allows more asteroids
ASTEROID_SPEED_MULTIPLIER = 1.0
ASTEROID_SPEED_INCREASE = 0.04  # per second (increased for faster difficulty ramp)
MAX_ASTEROID_SPEED = 4.0
MAX_ASTEROID_SIZE = 40
SHIP_BULLET_SPEED = 10

SHOOT_COOLDOWN = 300  # milliseconds between shots

BOSS_SHIP_SPAWN_RATE = 10000  # milliseconds
BOSS_SHIP_HEALTH = 5
BOSS_SHOOT_COOLDOWN = 450  # milliseconds between shots
BOSS_BULLET_SPEED = 3

class Spaceship:
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
        self.speed = 5
        self.size = 15
        # Spaceship always points up
        self.angle = 0  # Angle in degrees (0 = pointing up)
    
    ''' 
    def move_up(self):
        self.y -= self.speed
        self.y = self.y % SCREEN_HEIGHT
    
    def move_down(self):
        self.y += self.speed
        self.y = self.y % SCREEN_HEIGHT
    '''
    
    def move_left(self):
        self.x -= self.speed
        self.x = self.x % SCREEN_WIDTH
    
    def move_right(self):
        self.x += self.speed
        self.x = self.x % SCREEN_WIDTH
    
    def get_vertices(self) -> List[Tuple[float, float]]:
        """Get the three vertices of the triangle spaceship (always pointing up)"""
        # Nose point (front/up)
        nose_x = self.x
        nose_y = self.y - self.size
        # Left point (back left)
        left_x = self.x - self.size * math.sin(math.pi / 3)
        left_y = self.y + self.size * math.cos(math.pi / 3)
        # Right point (back right)
        right_x = self.x + self.size * math.sin(math.pi / 3)
        right_y = self.y + self.size * math.cos(math.pi / 3)
        
        return [(nose_x, nose_y), (left_x, left_y), (right_x, right_y)]
    
    def get_collision_radius(self) -> float:
        return self.size * 0.8


class BossShip:
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
        self.health = BOSS_SHIP_HEALTH
        self.shooting_cooldown = BOSS_SHOOT_COOLDOWN
        self.size = 50
        
        self.vy = 2
        self.vertices = self._generate_vertices()
        self.last_shot_time = 0
    
    def _generate_vertices(self) -> List[Tuple[float, float]]:
        """Generate symmetric spaceship vertices (relative to center, pointing up)"""
        size = self.size
        vertices = []
        
        # Nose point (top center)
        vertices.append((0, -size))
        vertices.append((-size * 0.3, -size * 0.6))
        vertices.append((-size * 0.8, -size * 0.3))
        vertices.append((-size * 0.9, size * 0.2))
        vertices.append((-size * 0.5, size * 0.5))
        vertices.append((-size * 0.3, size * 0.8))
        vertices.append((0, size))
        vertices.append((size * 0.3, size * 0.8))
        vertices.append((size * 0.5, size * 0.5))
        vertices.append((size * 0.9, size * 0.2))
        vertices.append((size * 0.8, -size * 0.3))
        vertices.append((size * 0.3, -size * 0.6))
        
        return vertices
    
    def update(self, current_time: int, game_bullets: List["Bullet"]):
        if self.y < SCREEN_HEIGHT//4:
            self.y += self.vy
        else:
            if current_time - self.last_shot_time >= self.shooting_cooldown:
                self._shoot(game_bullets)
                self.last_shot_time = current_time

    def _shoot(self, game_bullets: List["Bullet"]):
        bullet = Bullet(self.x, self.y, random.randint(-45,45), self)
        game_bullets.append(bullet)

    def draw(self, screen):
        # Convert relative vertices (centered at 0,0) to absolute screen positions
        absolute_vertices = []
        for vx, vy in self.vertices:
            absolute_vertices.append((int(self.x + vx), int(self.y + vy)))

        # Draw the boss ship body
        if len(absolute_vertices) > 2:
            pygame.draw.polygon(screen, RED, absolute_vertices, 0)     # filled
            pygame.draw.polygon(screen, WHITE, absolute_vertices, 2)   # outline

        # Draw a health bar above the ship
        max_health = BOSS_SHIP_HEALTH
        health_ratio = max(0.0, min(1.0, self.health / max_health))

        bar_width = self.size * 2
        bar_height = 10
        bar_x = int(self.x - bar_width / 2)
        bar_y = int(self.y - self.size - 25)

        # background (missing health)
        pygame.draw.rect(screen, RED, (bar_x, bar_y, bar_width, bar_height))
        # foreground (current health)
        pygame.draw.rect(screen, GREEN, (bar_x, bar_y, int(bar_width * health_ratio), bar_height))
        # border
        pygame.draw.rect(screen, WHITE, (bar_x, bar_y, bar_width, bar_height), 2)

    def get_collision_radius(self) -> float:
        return self.size

class Asteroid:
    def __init__(self, x: float, y: float, size: int, speed_multiplier: float = 1.0):
        self.x = x
        self.y = y
        self.size = size
        # Random velocity - can come from any angle, but always moving downward (vy < 0)
        base_speed = random.uniform(1, 2) * speed_multiplier
        # Horizontal velocity can be any direction
        self.vx = random.uniform(-base_speed, base_speed)
        # Vertical velocity must be negative (downward)
        self.vy = random.uniform(0.5, base_speed)  # Always positive value
        self.vy = self.vy  
        # Create simple polygon shape (irregular polygon for asteroid look)
        self.vertices = self._generate_vertices()
    
    def _generate_vertices(self) -> List[Tuple[float, float]]:
        """Generate irregular polygon vertices for asteroid shape (relative to center)"""
        num_points = 8
        vertices = []
        for i in range(num_points):
            angle = (2 * math.pi * i) / num_points
            # Add some randomness to make it look irregular
            radius = self.size + random.uniform(-self.size * 0.3, self.size * 0.3)
            vertices.append((radius, angle))  # Store as (radius, angle) for relative positioning
        return vertices
    
    def update(self):
        self.x += self.vx
        self.y += self.vy
    
    def is_off_screen(self) -> bool:
        """Check if asteroid is completely off screen"""
        margin = self.size + 10  # Add margin to ensure it's fully off screen before removing
        return (self.x < -margin or self.x > SCREEN_WIDTH + margin or 
                self.y < -margin or self.y > SCREEN_HEIGHT + margin)
    
    def draw(self, screen):
        # Calculate absolute vertex positions
        absolute_vertices = []
        for radius, angle in self.vertices:
            x = self.x + radius * math.cos(angle)
            y = self.y + radius * math.sin(angle)
            absolute_vertices.append((int(x), int(y)))
        # Draw filled polygon for asteroid shape
        if len(absolute_vertices) > 2:
            pygame.draw.polygon(screen, WHITE, absolute_vertices, 0)  # 0 = filled
    
    def get_collision_radius(self) -> float:
        return self.size

class Bullet:
    def __init__(self, x: float, y: float, angle: float, origin: Spaceship | BossShip):
        self.x = x
        self.y = y
        self.angle = angle
        self.active = True
        self.origin = origin
        self.size = 3 if isinstance(self.origin, Spaceship) else 6
        self.speed = SHIP_BULLET_SPEED if isinstance(self.origin, Spaceship) else BOSS_BULLET_SPEED

    def update(self):
        angle_rad = math.radians(self.angle)
        self.x += self.speed * math.sin(angle_rad)
        if isinstance(self.origin, Spaceship):
            self.y -= self.speed * math.cos(angle_rad)
        elif isinstance(self.origin, BossShip):
            self.y += self.speed * math.cos(angle_rad)
        
        # Deactivate if off screen
        if self.x < 0 or self.x > SCREEN_WIDTH or self.y < 0 or self.y > SCREEN_HEIGHT:
            self.active = False
    
    def draw(self, screen):
        if self.active:
            if isinstance(self.origin, Spaceship):
                pygame.draw.circle(screen, YELLOW, (int(self.x), int(self.y)), self.size)
            elif isinstance(self.origin, BossShip):
                pygame.draw.circle(screen, RED, (int(self.x), int(self.y)), self.size)
    
    def get_collision_radius(self) -> float:
        return self.size

def check_collision(obj1, obj2) -> bool:
    """Check collision between two circular objects"""
    distance = math.sqrt((obj1.x - obj2.x)**2 + (obj1.y - obj2.y)**2)
    return distance < (obj1.get_collision_radius() + obj2.get_collision_radius())


class Game:
    def __init__(self, render_mode='human'):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Asteroid Shooter")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)
        
        self.reset_game()
    
    def reset_game(self):
        self.spaceship = Spaceship((SCREEN_WIDTH // 2), 9*(SCREEN_HEIGHT // 10))
        self.bullets: List[Bullet] = []
        self.asteroids: List[Asteroid] = []
        self.boss_ship: List[BossShip] = []

        self.lives = 3
        self.boss_score = 0
        self.ast_score = 0
        self.game_over = False
        self.time = 0
        self.start_time = 0
        self.last_asteroid_spawn = 0
        self.asteroid_spawn_rate = INITIAL_ASTEROID_SPAWN_RATE
        self.asteroid_speed_multiplier = ASTEROID_SPEED_MULTIPLIER
        self.last_shot_time = 0
        self.boss_ship_spawn_rate = BOSS_SHIP_SPAWN_RATE
        self.last_boss_ship_spawn = 0
        self.boss_active = False
        
        # Generate starfield background
        self.stars = [(random.randint(0, SCREEN_WIDTH), random.randint(0, SCREEN_HEIGHT)) 
                      for _ in range(100)]
        
        # Spawn initial asteroids
        for _ in range(5):
            self.spawn_asteroid()
        

    @property
    def total_score(self):
        return 50*self.boss_score + self.ast_score
    
    def spawn_boss_ship(self):
        """Spawn a boss ship from the top of the screen"""
        x = random.randint(0, SCREEN_WIDTH)
        y = -20

        boss_ship = BossShip(x, y)
        self.boss_ship.append(boss_ship)
    
    def spawn_asteroid(self):
        """Spawn an asteroid from the top of the screen"""
        # Asteroids always spawn from the top (they come from up to down)
        x = random.randint(0, SCREEN_WIDTH)
        y = -20
        
        size = random.randint(20, MAX_ASTEROID_SIZE)
        asteroid = Asteroid(x, y, size, self.asteroid_speed_multiplier)
        self.asteroids.append(asteroid)
    
    def update_difficulty(self):
        """Update game difficulty based on elapsed time"""
        elapsed_time = (self.time - self.start_time) / 1000.0  # in seconds
        
        # Increase asteroid spawn rate over time (decrease interval = more frequent spawning)
        # Use steeper curve for faster difficulty increase
        spawn_rate_reduction = 1 + (elapsed_time * elapsed_time / 450.0)  # Steeper quadratic for faster reduction
        self.asteroid_spawn_rate = max(
            MIN_ASTEROID_SPAWN_RATE,
            INITIAL_ASTEROID_SPAWN_RATE / spawn_rate_reduction
        )
        
        # Increase asteroid speed faster
        self.asteroid_speed_multiplier = min(MAX_ASTEROID_SPEED, ASTEROID_SPEED_MULTIPLIER + (elapsed_time * ASTEROID_SPEED_INCREASE))
    
    def apply_action(self, move_action: int, fire_action: int, current_time: int):
        """
+        Two-head action:
+          move_action: 0=noop, 1=left, 2=right
+          fire_action: 0=no fire, 1=fire
+        """
        #For movement
        if move_action == 1:
            self.spaceship.move_left()
        elif move_action == 2:
            self.spaceship.move_right()

        #For shooting
        if fire_action == 1:
            if current_time - self.last_shot_time >= SHOOT_COOLDOWN:
                self.shoot()
                self.last_shot_time = current_time
    
    def shoot(self):
        """Create a new bullet from the spaceship (always shoots up)"""
        bullet = Bullet(self.spaceship.x, self.spaceship.y, 0, self.spaceship)  
        self.bullets.append(bullet)
    
    def step(self, move_action: int, fire_action: int, delta_time: int = int(1000/FPS)):

        if self.game_over:
            return
        
        # Update difficulty
        self.time += delta_time
        current_time = self.time

        self.update_difficulty()
        
        # Apply action for this tick
        self.apply_action(move_action, fire_action, current_time)

        # Spawn new asteroids
        if current_time - self.last_asteroid_spawn > self.asteroid_spawn_rate:
            self.spawn_asteroid()
            self.last_asteroid_spawn = current_time
        
        # Update asteroids and remove those that go off screen
        for asteroid in self.asteroids[:]:
            asteroid.update()
            if asteroid.is_off_screen():
                self.asteroids.remove(asteroid)

        if not self.boss_active and current_time - self.last_boss_ship_spawn > self.boss_ship_spawn_rate:
            self.spawn_boss_ship()
            self.last_boss_ship_spawn = current_time
            self.boss_active = True

        # Update boss ship
        for boss_ship in self.boss_ship[:]:
            boss_ship.update(current_time, self.bullets)
        
        # Update bullets
        for bullet in self.bullets[:]:
            bullet.update()
            if not bullet.active:
                self.bullets.remove(bullet)
        
        # Check bullet-asteroid collisions
        for bullet in self.bullets[:]:
            if not isinstance(bullet.origin, Spaceship):
                continue
            for asteroid in self.asteroids[:]:
                if check_collision(bullet, asteroid):
                    self.bullets.remove(bullet)
                    self.asteroids.remove(asteroid)
                    # Increment score when asteroid is destroyed
                    self.ast_score += 1
                    # Break into smaller asteroids or remove
                    if asteroid.size > 25:
                        # Split into 2 smaller asteroids
                        for _ in range(2):
                            new_size = asteroid.size // 2
                            new_asteroid = Asteroid(
                                asteroid.x + random.randint(-10, 10),
                                asteroid.y + random.randint(-10, 10),
                                new_size,
                                self.asteroid_speed_multiplier
                            )
                            self.asteroids.append(new_asteroid)
                    break
        
        # Check bullet-boss ship collisions
        for bullet in self.bullets[:]:
            if not isinstance(bullet.origin, Spaceship):
                continue
            for boss_ship in self.boss_ship[:]:
                if check_collision(bullet, boss_ship):
                    self.bullets.remove(bullet)
                    boss_ship.health -= 1
                    if boss_ship.health <= 0:
                        self.boss_active = False
                        self.boss_ship.remove(boss_ship)
                        self.boss_score += 1
                    break

        # Check boss_bullet-spaceship collisions
        for bullet in self.bullets[:]:
            if not isinstance(bullet.origin, BossShip):
                continue
            if check_collision(bullet, self.spaceship):
                self.bullets.remove(bullet)
                self.lives -= 1
                if self.lives <= 0:
                    self.game_over = True
                break

        # Check spaceship-asteroid collisions
        for asteroid in self.asteroids[:]:
            if check_collision(self.spaceship, asteroid):
                self.lives -= 1
                if self.lives <= 0:
                    self.game_over = True
                else:
                    # Remove the asteroid but keep spaceship at current position
                    self.asteroids.remove(asteroid)
                    # Brief invincibility could be added here
                break
    
    def draw(self):
        self.screen.fill(BLACK)
        
        # Draw stars (background effect)
        for x, y in self.stars:
            pygame.draw.circle(self.screen, WHITE, (x, y), random.randint(1, 3))
        
        if not self.game_over:
            # Draw spaceship
            vertices = self.spaceship.get_vertices()
            pygame.draw.polygon(self.screen, GREEN, [(int(v[0]), int(v[1])) for v in vertices])
            
            # Draw bullets
            for bullet in self.bullets:
                bullet.draw(self.screen)
            
            # Draw asteroids
            for asteroid in self.asteroids:
                asteroid.draw(self.screen)

            for boss_ship in self.boss_ship:
                boss_ship.draw(self.screen)
        
        # Draw UI
        score_text = self.font.render(f"Score: {self.total_score}", True, WHITE)
        self.screen.blit(score_text, (10, 10))
        
        lives_text = self.font.render(f"Lives: {self.lives}", True, WHITE)
        self.screen.blit(lives_text, (10, 50))
        
        if self.game_over:
            game_over_text = self.font.render("GAME OVER", True, RED)
            text_rect = game_over_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 30))
            self.screen.blit(game_over_text, text_rect)
            
            final_score_text = self.font.render(f"Final Score: {self.total_score}", True, WHITE)
            score_rect = final_score_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 10))
            self.screen.blit(final_score_text, score_rect)
            
            restart_text = self.small_font.render("Press R to restart", True, YELLOW)
            restart_rect = restart_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 50))
            self.screen.blit(restart_text, restart_rect)
        
        pygame.display.flip()
    
    def run(self):
        running = True
        
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r and self.game_over:
                        self.reset_game()
            
            # For manual testing, we can use keyboard input
            move_action = 0
            fire_action = 0

            keys = pygame.key.get_pressed()
            left = keys[pygame.K_LEFT] or keys[pygame.K_a]
            right = keys[pygame.K_RIGHT] or keys[pygame.K_d]
            if left and not right:
                move_action = 1
            elif right and not left:
                move_action = 2
            else:
                move_action = 0

            if keys[pygame.K_SPACE]:
                fire_action = 1

            self.step(move_action, fire_action)

            self.draw()
            self.clock.tick(FPS)
        
        pygame.quit()


if __name__ == "__main__":
    game = Game()
    game.run()
