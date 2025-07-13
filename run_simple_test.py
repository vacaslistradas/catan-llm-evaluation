#!/usr/bin/env python3

from catanatron import Game, Color
from catanatron.models.player import RandomPlayer
import json

print("Testing basic Catanatron game...")

# Create 4 random players
players = [
    RandomPlayer(Color.RED),
    RandomPlayer(Color.BLUE),
    RandomPlayer(Color.WHITE),
    RandomPlayer(Color.ORANGE)
]

# Create and play game
game = Game(players)
print(f"Initial state - Turn: {game.state.num_turns}")

# Play a few turns
for i in range(10):
    if game.winning_color() is not None:
        break
    
    playable_actions = game.state.playable_actions
    if playable_actions:
        action = playable_actions[0]
        game.execute(action)
        print(f"Turn {game.state.num_turns}: Executed {action}")

winner = game.winning_color()
print(f"\nGame winner: {winner}")

# Test state access
print("\nTesting state access:")
print(f"Number of turns: {game.state.num_turns}")
print(f"Current player index: {game.state.current_player_index}")
print(f"Colors: {game.state.colors}")

# Check available attributes
print("\nState attributes:")
state_attrs = [attr for attr in dir(game.state) if not attr.startswith('_')]
print(json.dumps(state_attrs, indent=2))