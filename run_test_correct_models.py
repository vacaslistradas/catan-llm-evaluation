#!/usr/bin/env python3

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.config import Config
from src.evaluation import CatanLLMEvaluator

async def main():
    # Use correct OpenRouter model names
    models = ["openai/gpt-4o", "openai/gpt-4o-mini"]
    
    print("Starting Catan LLM Evaluation Test")
    print(f"Models: {', '.join(models)}")
    print(f"Web dashboard at: http://localhost:{Config.APP_PORT}")
    print("-" * 50)
    
    # Create evaluator
    evaluator = CatanLLMEvaluator(models)
    
    # Run a single game between the two models
    print("\nRunning test game...")
    result = await evaluator.run_game(models[0], models[1])
    
    print("\nGame completed!")
    print(f"Winner: {result.get('winner', 'None')}")
    print(f"Total turns: {result.get('total_turns', 0)}")
    print(f"Game ID: {result.get('game_id')}")
    
    # Show current standings
    print("\nCurrent Standings:")
    evaluator._display_standings()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()