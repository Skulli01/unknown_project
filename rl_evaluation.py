from stable_baselines3 import PPO
from rl_env import AsteroidEnv
import time
import pygame

def evaluate_model(model_path: str):
    """
    Load a trained model and visualize its performance in the AsteroidEnv.

    Args:
        model_path (str): Path to the trained model zip file.
    """
    # Load the trained model
    model = PPO.load(model_path)

    # Create the environment
    env = AsteroidEnv(render_mode="human")

    # Reset the environment
    obs, info = env.reset()

    fps = env.metadata["render_fps"]
    while True:
        # Check for key press to exit
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                env.close()
                return

        # Predict the action using the trained model
        action, _ = model.predict(obs, deterministic=True)

        # Step the environment
        obs, reward, terminated, truncated, info = env.step(action)

        # Add delay to match the game's FPS
        time.sleep(1 / fps)

        # Check if the episode is over
        if terminated or truncated:
            obs, info = env.reset()

if __name__ == "__main__":
    model_path = "models/ppo_asteroid/ppo_asteroid.zip"  # Update this path if needed
    evaluate_model(model_path)

