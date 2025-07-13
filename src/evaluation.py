import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from catanatron import Game, Color
from catanatron.models.player import RandomPlayer
from loguru import logger
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TimeElapsedColumn

from .config import Config
from .llm_client import LLMPlayer
from .elo_system import EloRatingSystem, TournamentScheduler

console = Console()

class CatanLLMEvaluator:
    """Main evaluation engine for testing LLMs with Catan"""
    
    def __init__(self, models: Optional[List[str]] = None):
        Config.validate()
        
        self.models = models or Config.DEFAULT_MODELS
        self.elo_system = EloRatingSystem()
        self.game_logs_dir = Config.BASE_DIR / "game_logs"
        self.game_logs_dir.mkdir(exist_ok=True)
        
        logger.info(f"Initialized evaluator with {len(self.models)} models")
    
    async def run_game(self, model1: str, model2: str) -> Dict:
        """Run a single game between two models"""
        logger.info(f"Starting game: {model1} vs {model2}")
        
        # Create players
        colors = [Color.RED, Color.BLUE]
        players = [
            LLMPlayer(colors[0], model1),
            LLMPlayer(colors[1], model2)
        ]
        
        # Add two random players for 4-player game
        players.extend([
            RandomPlayer(Color.WHITE),
            RandomPlayer(Color.ORANGE)
        ])
        
        # Create and play game
        game = Game(players)
        
        # Track game progress
        game_log = {
            "game_id": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "players": {
                "RED": model1,
                "BLUE": model2,
                "WHITE": "RandomPlayer",
                "ORANGE": "RandomPlayer"
            },
            "actions": [],
            "start_time": datetime.now().isoformat()
        }
        
        try:
            # Play the game with timeout
            winner_color = await asyncio.wait_for(
                self._play_game_async(game, game_log),
                timeout=Config.GAME_TIMEOUT_SECONDS
            )
            
            # Determine winner model
            if winner_color == Color.RED:
                winner_model = model1
                loser_model = model2
            elif winner_color == Color.BLUE:
                winner_model = model2
                loser_model = model1
            else:
                # Random player won
                winner_model = None
                loser_model = None
            
            game_log["winner"] = winner_color.value if winner_color else "None"
            game_log["winner_model"] = winner_model
            game_log["end_time"] = datetime.now().isoformat()
            game_log["total_turns"] = game.state.num_turns
            
            # Update Elo ratings if LLM won
            if winner_model and loser_model:
                self.elo_system.update_ratings(winner_model, loser_model)
            
            # Save game log
            self._save_game_log(game_log)
            
            return {
                "winner": winner_model,
                "loser": loser_model,
                "total_turns": game.state.num_turns,
                "game_id": game_log["game_id"]
            }
            
        except asyncio.TimeoutError:
            logger.error(f"Game timeout: {model1} vs {model2}")
            game_log["error"] = "Game timeout"
            game_log["end_time"] = datetime.now().isoformat()
            self._save_game_log(game_log)
            return {
                "winner": None,
                "loser": None,
                "error": "timeout",
                "game_id": game_log["game_id"]
            }
        except Exception as e:
            logger.error(f"Game error: {e}")
            game_log["error"] = str(e)
            game_log["end_time"] = datetime.now().isoformat()
            self._save_game_log(game_log)
            return {
                "winner": None,
                "loser": None,
                "error": str(e),
                "game_id": game_log["game_id"]
            }
    
    async def _play_game_async(self, game: Game, game_log: Dict) -> Optional[Color]:
        """Play a game asynchronously to support LLM calls"""
        while not game.state.is_game_over():
            if game.state.num_turns > Config.MAX_TURNS_PER_GAME:
                logger.warning("Game exceeded maximum turns")
                break
            
            # Get current player
            current_player = game.state.current_player()
            current_color = game.state.colors[current_player.value]
            
            # Get playable actions
            playable_actions = game.state.playable_actions
            
            if len(playable_actions) == 0:
                logger.error("No playable actions available")
                break
            
            # Get player's decision
            if isinstance(current_player, LLMPlayer):
                action = await current_player.decide_async(game, playable_actions)
            else:
                action = current_player.decide(game, playable_actions)
            
            # Log action
            game_log["actions"].append({
                "turn": game.state.num_turns,
                "player": current_color.value,
                "action": str(action),
                "timestamp": datetime.now().isoformat()
            })
            
            # Execute action
            game.execute(action)
        
        # Return winner
        return game.state.winning_color()
    
    def _save_game_log(self, game_log: Dict):
        """Save game log to file"""
        filename = f"{game_log['game_id']}.json"
        filepath = self.game_logs_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(game_log, f, indent=2)
        
        logger.debug(f"Saved game log to {filepath}")
    
    async def run_tournament(self, games_per_matchup: int = 1) -> Dict:
        """Run a round-robin tournament between all models"""
        console.print(f"[bold green]Starting tournament with {len(self.models)} models[/bold green]")
        console.print(f"Games per matchup: {games_per_matchup}")
        
        scheduler = TournamentScheduler(self.models)
        results = {
            "start_time": datetime.now().isoformat(),
            "models": self.models,
            "games": []
        }
        
        with Progress(
            SpinnerColumn(),
            *Progress.get_default_columns(),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            total_games = len(scheduler.matchups) * games_per_matchup
            task = progress.add_task("[cyan]Running tournament...", total=total_games)
            
            while True:
                matchup = scheduler.get_next_matchup()
                if not matchup:
                    break
                
                model1, model2 = matchup
                
                # Play multiple games for this matchup
                for game_num in range(games_per_matchup):
                    progress.update(task, advance=1)
                    console.print(f"[yellow]Game {len(results['games']) + 1}/{total_games}:[/yellow] {model1} vs {model2}")
                    
                    # Alternate who goes first
                    if game_num % 2 == 0:
                        result = await self.run_game(model1, model2)
                    else:
                        result = await self.run_game(model2, model1)
                    
                    results["games"].append(result)
                    
                    # Show current standings
                    self._display_standings()
        
        results["end_time"] = datetime.now().isoformat()
        results["final_standings"] = self.elo_system.get_leaderboard()
        
        # Save tournament results
        tournament_file = Config.BASE_DIR / f"tournament_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(tournament_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        console.print(f"\n[bold green]Tournament complete![/bold green]")
        console.print(f"Results saved to: {tournament_file}")
        
        return results
    
    def _display_standings(self):
        """Display current standings in a nice table"""
        leaderboard = self.elo_system.get_leaderboard()
        stats = self.elo_system.get_statistics()
        
        table = Table(title="Current Standings")
        table.add_column("Rank", style="cyan", no_wrap=True)
        table.add_column("Model", style="magenta")
        table.add_column("Elo Rating", style="green")
        table.add_column("Games", style="yellow")
        table.add_column("Win Rate", style="blue")
        
        for rank, (model, rating) in enumerate(leaderboard, 1):
            model_stats = stats["model_stats"].get(model, {})
            games = model_stats.get("games_played", 0)
            win_rate = model_stats.get("win_rate", 0)
            
            table.add_row(
                str(rank),
                model.split("/")[-1],  # Show just model name
                f"{rating:.1f}",
                str(games),
                f"{win_rate:.1%}"
            )
        
        console.print(table)
    
    def analyze_results(self) -> Dict:
        """Analyze tournament results and provide insights"""
        stats = self.elo_system.get_statistics()
        
        analysis = {
            "summary": {
                "total_games": stats["total_games"],
                "models_evaluated": stats["models"],
                "average_rating": stats["average_rating"]
            },
            "leaderboard": stats["leaderboard"],
            "model_performance": {}
        }
        
        # Detailed model analysis
        for model, rating in stats["leaderboard"]:
            model_stats = stats["model_stats"].get(model, {})
            
            analysis["model_performance"][model] = {
                "elo_rating": rating,
                "games_played": model_stats.get("games_played", 0),
                "wins": model_stats.get("wins", 0),
                "losses": model_stats.get("losses", 0),
                "draws": model_stats.get("draws", 0),
                "win_rate": model_stats.get("win_rate", 0)
            }
        
        # Head-to-head predictions
        analysis["matchup_predictions"] = {}
        for i, (model1, _) in enumerate(stats["leaderboard"]):
            for j, (model2, _) in enumerate(stats["leaderboard"]):
                if i < j:
                    prediction = self.elo_system.get_matchup_prediction(model1, model2)
                    analysis["matchup_predictions"][f"{model1} vs {model2}"] = prediction
        
        return analysis