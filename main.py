#!/usr/bin/env python3

import asyncio
import argparse
import sys
from pathlib import Path
from typing import List, Optional
import threading
from loguru import logger
from rich.console import Console
from rich.prompt import Prompt, Confirm

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.config import Config
from src.evaluation import CatanLLMEvaluator
from src.web_server import run_server
from src.elo_system import EloRatingSystem

console = Console()

def print_banner():
    """Print a nice banner"""
    banner = """
    ╔═══════════════════════════════════════════════╗
    ║       🎲 CATAN LLM EVALUATION SYSTEM 🎲       ║
    ║                                               ║
    ║   Evaluating Language Models Through          ║
    ║        Strategic Board Game Play              ║
    ╚═══════════════════════════════════════════════╝
    """
    console.print(banner, style="bold cyan")

def get_models_from_user() -> List[str]:
    """Interactive prompt to get model list from user"""
    console.print("\n[bold yellow]Enter the models you want to evaluate:[/bold yellow]")
    console.print("Format: provider/model-name (e.g., openai/gpt-3.5-turbo)")
    console.print("Press Enter with empty input when done.\n")
    
    models = []
    while True:
        model = Prompt.ask(f"Model {len(models) + 1}", default="")
        if not model:
            break
        models.append(model)
        console.print(f"✓ Added: {model}", style="green")
    
    if not models:
        console.print("\n[yellow]No models entered. Using default models:[/yellow]")
        models = Config.DEFAULT_MODELS
        for model in models:
            console.print(f"  • {model}")
    
    return models

async def run_evaluation(models: List[str], games_per_matchup: int, run_server_thread: bool):
    """Run the evaluation"""
    evaluator = CatanLLMEvaluator(models)
    
    # Start web server in background thread if requested
    if run_server_thread:
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        console.print(f"\n[green]Web dashboard started at http://localhost:{Config.APP_PORT}[/green]")
        await asyncio.sleep(2)  # Give server time to start
    
    # Run tournament
    console.print(f"\n[bold cyan]Starting tournament with {len(models)} models[/bold cyan]")
    console.print(f"Games per matchup: {games_per_matchup}")
    
    results = await evaluator.run_tournament(games_per_matchup)
    
    # Final analysis
    console.print("\n[bold green]Tournament Complete! 🎉[/bold green]")
    analysis = evaluator.analyze_results()
    
    # Print final rankings
    console.print("\n[bold]Final Rankings:[/bold]")
    for i, (model, rating) in enumerate(analysis["leaderboard"], 1):
        perf = analysis["model_performance"][model]
        console.print(
            f"{i}. {model.split('/')[-1]} - "
            f"Elo: {rating:.1f}, "
            f"Games: {perf['games_played']}, "
            f"Win Rate: {perf['win_rate']:.1%}"
        )

def main():
    parser = argparse.ArgumentParser(
        description="Catan LLM Evaluation - Test language models through strategic gameplay"
    )
    
    parser.add_argument(
        "--models",
        nargs="+",
        help="List of models to evaluate (e.g., openai/gpt-3.5-turbo anthropic/claude-3-haiku)"
    )
    
    parser.add_argument(
        "--games",
        type=int,
        default=1,
        help="Number of games per matchup (default: 1)"
    )
    
    parser.add_argument(
        "--no-web",
        action="store_true",
        help="Disable web dashboard"
    )
    
    parser.add_argument(
        "--reset-ratings",
        action="store_true",
        help="Reset all Elo ratings before starting"
    )
    
    parser.add_argument(
        "--show-stats",
        action="store_true",
        help="Show current statistics and exit"
    )
    
    args = parser.parse_args()
    
    print_banner()
    
    # Show stats and exit if requested
    if args.show_stats:
        elo_system = EloRatingSystem()
        stats = elo_system.get_statistics()
        
        console.print("\n[bold]Current Statistics:[/bold]")
        console.print(f"Total games played: {stats['total_games']}")
        console.print(f"Models evaluated: {stats['models']}")
        
        if stats['leaderboard']:
            console.print("\n[bold]Leaderboard:[/bold]")
            for i, (model, rating) in enumerate(stats['leaderboard'], 1):
                console.print(f"{i}. {model}: {rating:.1f}")
        else:
            console.print("\nNo games played yet.")
        
        return
    
    # Reset ratings if requested
    if args.reset_ratings:
        if Confirm.ask("[red]Are you sure you want to reset all ratings?[/red]"):
            elo_system = EloRatingSystem()
            elo_system.reset_ratings()
            console.print("[green]Ratings reset successfully![/green]")
        else:
            console.print("[yellow]Reset cancelled.[/yellow]")
            return
    
    # Get models
    if args.models:
        models = args.models
    else:
        models = get_models_from_user()
    
    if len(models) < 2:
        console.print("[red]Error: At least 2 models are required for evaluation.[/red]")
        return
    
    # Confirm settings
    console.print("\n[bold]Evaluation Settings:[/bold]")
    console.print(f"Models: {', '.join(models)}")
    console.print(f"Games per matchup: {args.games}")
    console.print(f"Web dashboard: {'Disabled' if args.no_web else 'Enabled'}")
    
    if not Confirm.ask("\n[cyan]Start evaluation?[/cyan]"):
        console.print("[yellow]Evaluation cancelled.[/yellow]")
        return
    
    # Run evaluation
    try:
        asyncio.run(run_evaluation(models, args.games, not args.no_web))
    except KeyboardInterrupt:
        console.print("\n[yellow]Evaluation interrupted by user.[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error during evaluation: {e}[/red]")
        logger.exception("Evaluation error")

if __name__ == "__main__":
    main()