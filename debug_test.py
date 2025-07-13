#!/usr/bin/env python3

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from catanatron import Game, Color
from catanatron.models.player import RandomPlayer
from src.llm_client import LLMPlayer

async def main():
    print("=== DEBUG TEST ===\n")
    
    # Create simple game with 2 random players first
    players = [
        RandomPlayer(Color.RED),
        RandomPlayer(Color.BLUE),
        RandomPlayer(Color.WHITE),
        RandomPlayer(Color.ORANGE)
    ]
    
    game = Game(players)
    print("1. Basic game created successfully")
    print(f"   Current player: {game.state.current_player()}")
    print(f"   Current color: {game.state.current_color()}")
    print(f"   Playable actions: {len(game.state.playable_actions)}")
    
    # Now test with LLM player
    print("\n2. Testing LLM player creation...")
    try:
        llm_player = LLMPlayer(Color.RED, "openai/gpt-3.5-turbo")
        print("   LLM player created successfully")
        
        print("\n3. Testing state conversion...")
        game_state = llm_player._convert_game_state(game)
        print("   State conversion successful")
        print(f"   Current player in state: {game_state['current_player']}")
        print(f"   Turn: {game_state['turn']}")
        
        print("\n4. Testing action conversion...")
        actions = game.state.playable_actions[:5]
        converted_actions = llm_player._convert_actions(actions)
        print("   Action conversion successful")
        print(f"   Sample action: {converted_actions[0] if converted_actions else 'None'}")
        
    except Exception as e:
        print(f"   ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())