import gymnasium as gym
import numpy as np
import sys
import argparse
from asteroid_shooter import ( 
    BOSS_SHIP_HEALTH,
    SCREEN_WIDTH, 
    SCREEN_HEIGHT, 
    FPS, 
    SHOOT_COOLDOWN,
    MAX_ASTEROID_SPEED,
    MAX_ASTEROID_SIZE,
    BOSS_BULLET_SPEED,
    SHIP_BULLET_SPEED,
    Game,
    BossShip, 
    Spaceship)
FRAMES_PER_STEP = 1

class AsteroidEnv(gym.Env):
    """
    Gymnasium wrapper for asteroid shooter.

    Action: MultiDiscrete([3, 2])
        move_action: 0=noop, 1=left, 2=right
        fire_action: 0=no fire, 1=fire

    Observation: structured fixed-size vector (float32).
    """
    metadata = {"render_modes": ["human", None], "render_fps": FPS}

    def __init__(
        self,
        render_mode: str | None = None,
        max_steps: int = 60*FPS,
        k_asteroids: int = 5,
        k_boss_bullets: int = 5,
        delta_time: int = int(1000/FPS)
    ):
        super().__init__()
        self.render_mode = render_mode
        self.max_steps = max_steps
        self.k_asteroids = k_asteroids
        self.k_boss_bullets = k_boss_bullets
        self.delta_time = delta_time


        #RL Spaces
        self.action_space = gym.spaces.MultiDiscrete([3, 2])

        #Structured observations
        self.ship_feat = 4
        self.boss_feat = 4
        self.ast_feat = 5
        self.bul_feat = 4
        self.obs_dim = self.ship_feat + self.boss_feat + self.k_asteroids*self.ast_feat + self.k_boss_bullets*self.bul_feat

        self.observation_space = gym.spaces.Box(
            low=-1.0,
            high=1.0,
            shape=(self.obs_dim,),
            dtype=np.float32,
        )



        # --- Game instance ---
        # If your Game always opens a window, this will still work,
        # but training will be slower. Best practice: Game(render_mode=render_mode).
        try:
            self.game = Game(render_mode=render_mode)
        except TypeError:
            self.game = Game()
        
        self.step_count = 0

        # For reward shaping via deltas
        self._prev_score = 0
        self._prev_lives = 0
        self._prev_player_bullet_count = 0

    def reset(self, seed: int | None = None, options = None):
        super().reset(seed=seed)
        if seed is not None:
            # Seed numpy (and optionally python random inside your game if you use it)
            np.random.seed(seed)
        
        self.game.reset_game()
        self.step_count = 0

        self._prev_score = self.game.score
        self._prev_lives = self.game.lives
        self._prev_player_bullet_count = self._count_player_bullets()

        obs = self._get_obs()
        info = {}
        return obs, info

    def step(self, action):

        move_action, fire_action = int(action[0]), int(action[1])

        # Track before-state for reward deltas
        prev_score = self.game.score
        prev_lives = self.game.lives
        prev_player_bullets = self._count_player_bullets()

        #Advace one tick
        self.game.step(move_action, fire_action, self.delta_time)
        self.step_count += 1

        score_delta = self.game.score - prev_score
        lives_delta = self.game.lives - prev_lives
        did_shoot = self._count_player_bullets() > prev_player_bullets

        reward = 0.0
        reward += 1.0 * float(score_delta)                 # asteroid kills etc.
        reward += -20.0 * float(max(0, -lives_delta))      # losing a life is bad
        reward += 0.01

        # --- Termination / truncation ---
        terminated = bool(self.game.game_over)
        truncated = bool(self.step_count >= self.max_steps)


        if did_shoot:
            reward -= 0.01

        obs = self._get_obs()  
        info = {
            "score_delta": score_delta,
            "lives_delta": lives_delta,
            "did_shoot": did_shoot,
            "score": self.game.score,
            "lives": self.game.lives,
        }     

        if self.render_mode == "human":
            self.render()

        return obs, float(reward), terminated, truncated, info
    
    def render(self):
        self.game.draw()

    def close(self):
        # If your Game handles pygame.quit() elsewhere, you can leave this empty.
        # But it's nice to allow Gym to close cleanly.
        try:
            import pygame
            pygame.quit()
        except Exception:
            pass
    
    def _get_obs(self) -> np.ndarray:

        ship = self.game.spaceship
        sx = ship.x / SCREEN_WIDTH
        sy = ship.y / SCREEN_HEIGHT

        # can_shoot: based on cooldown (requires  game to track last_shot_time and internal clock)
        # If you use the internal clock (t_ms) from earlier refactor:

        try:
            can_shoot = 1.0 if (self.game.time - ship.last_shot_time) >= SHOOT_COOLDOWN else 0.0
        
        except Exception:
            can_shoot = 0.0

        lives_norm = float(self.game.lives) / 3.0
        ship_feats = np.array([sx, sy, can_shoot, lives_norm], dtype=np.float32)

        boss_exists = float(self.game.boss_active)

        if boss_exists:
            boss = self.game.boss_ship[0]
            boss_to_ship_dx = (boss.x - ship.x) / SCREEN_WIDTH
            boss_to_ship_dy = (boss.y - ship.y) / SCREEN_HEIGHT
            boss_health_norm = float(boss.health) / BOSS_SHIP_HEALTH
            # Better: divide by BOSS_SHIP_HEALTH if you import it.
            boss_feats = np.array([1.0, boss_to_ship_dx, boss_to_ship_dy, np.clip(boss_health_norm, 0.0, 1.0)], dtype=np.float32)
        else:
            boss_feats = np.zeros((4,), dtype=np.float32)
        
        # Asteroids: take K nearest
        ast_feats = self._asteroid_features(ship, self.k_asteroids)

        # Boss bullets: take K nearest bullets where origin is BossShip
        bul_feats = self._boss_bullet_features(ship, self.k_boss_bullets)

        obs = np.concatenate([ship_feats, boss_feats, ast_feats, bul_feats], axis=0)

        # Clamp to [-1, 1] since we promised that in observation_space
        obs = np.clip(obs, -1.0, 1.0).astype(np.float32)
        return obs
        
    def _asteroid_features(self, ship: Spaceship, k: int) -> np.ndarray:

        asteroids = self.game.asteroids

        def distance(a):
            return np.sqrt((a.x - ship.x) ** 2 + (a.y - ship.y) ** 2)
    
        asteroids.sort(key=distance)

        feats = []
        for a in asteroids[:k]:
            dx = (a.x - ship.x) / SCREEN_WIDTH
            dy = (a.y - ship.y) / SCREEN_HEIGHT
            vx = float(a.vx) / MAX_ASTEROID_SPEED
            vy = float(a.vy) / MAX_ASTEROID_SPEED
            size = float(a.size) / MAX_ASTEROID_SIZE
            feats.extend([dx, dy, vx, vy, size])

        # pad
        while len(feats) < k * self.ast_feat:
            feats.extend([0.0] * self.ast_feat)

        return np.array(feats, dtype=np.float32)
    
    def _boss_bullet_features(self, ship: Spaceship, k: int) -> np.ndarray:

        boss_bullets = [b for b in self.game.bullets if isinstance(b.origin, BossShip)]

        # sort by distance
        def d2(b):
            dx = b.x - ship.x
            dy = b.y - ship.y
            return dx * dx + dy * dy

        boss_bullets.sort(key=d2)

        feats = []
        for b in boss_bullets[:k]:
            dx = (b.x - ship.x) / SCREEN_WIDTH
            dy = (b.y - ship.y) / SCREEN_HEIGHT

            # derive velocity from angle+speed (consistent with your Bullet.update)
            ang = np.deg2rad(float(b.angle))
            vx = float(b.speed) * np.sin(ang)
            vy = float(b.speed) * np.cos(ang)  # boss bullets go downward in your update
            vx /= BOSS_BULLET_SPEED
            vy /= BOSS_BULLET_SPEED

            feats.extend([dx, dy, vx, vy])

        while len(feats) < k * self.bul_feat:
            feats.extend([0.0] * self.bul_feat)

        return np.array(feats, dtype=np.float32)

    def _count_player_bullets(self) -> int:
        return sum(1 for b in self.game.bullets if isinstance(b.origin, Spaceship))

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="gym environment for asteroid shooter")
    parser.add_argument("mode", choices=["train", "random_play", "play"])
    mode = sys.argv[1]

    args = parser.parse_args()

    mode = args.mode

    if mode == "play":
        game = Game(render_mode="human")
        game.run()

    elif mode == "random_play":
        env = AsteroidEnv(render_mode="human")
        obs, info = env.reset()

        done = False
        while True:
            # IMPORTANT: keep pygame responsive
            import pygame
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    env.close()
                    raise SystemExit

            action = env.action_space.sample()
            obs, reward, terminated, truncated, info = env.step(action)
            if terminated or truncated:
                obs, info = env.reset()