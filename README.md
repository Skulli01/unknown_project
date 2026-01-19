# Game Project with Reinforcement Learning

This project contains simple games that can be played by users, with the ability to use reinforcement learning to teach the computer to play autonomously.

## Asteroid Shooter Game

A simple 2D asteroid shooter game built with Python and Pygame.

### Features

- **Simple Graphics**: Triangle spaceship and polygon asteroids
- **Progressive Difficulty**: Game gets harder the longer you survive (asteroids spawn more frequently and move faster over time)
- **Lives System**: 3 lives before Game Over
- **Score System**: Score equals the time elapsed since the game started (in seconds)

### Installation

1. Install Python 3.7 or higher
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### How to Play

Run the game:
```bash
python asteroid_shooter.py
```

**Controls:**
- **Arrow Keys** or **WASD**: Rotate spaceship (Left/Right or A/D) and move forward (Up or W)
- **Space**: Shoot bullets
- **R**: Restart after Game Over

**Objective:**
- Survive as long as possible by shooting asteroids and avoiding collisions
- Each asteroid collision costs one life
- Large asteroids split into smaller ones when hit
- Game becomes progressively harder over time

### Future: Reinforcement Learning

The next phase will add reinforcement learning capabilities to train an AI agent to play the game autonomously.
