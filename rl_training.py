import os
from stable_baselines3 import PPO
from stable_baselines3.common.env_util import make_vec_env
from rl_env import AsteroidEnv

def main():
    # Create the environment
    env = make_vec_env(lambda: AsteroidEnv(render_mode=None), n_envs=8)
    print("Environment created.")
    # Initialize the model
    model = PPO("MlpPolicy", env, verbose=1, learning_rate=1e-4, tensorboard_log="./ppo_asteroid_tensorboard/")
    print("Model initialized.")
    # Train the model
    timesteps = 3_000_000  # Adjust based on your needs
    model.learn(total_timesteps=timesteps)
    print("Model training completed.")
    # Save the model
    model_dir = "models/ppo_asteroid"
    os.makedirs(model_dir, exist_ok=True)
    model.save(f"{model_dir}/ppo_asteroid")
    print(f"Model saved to {model_dir}/ppo_asteroid.")

    # Close the environment
    env.close()

if __name__ == "__main__":
    main()
