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
from rich.panel import Panel

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
    
    def run_game(self, model1: str, model2: str) -> Dict:
        """Run a single game between two models"""
        logger.info(f"Starting game: {model1} vs {model2}")
        
        # Show game setup
        console.print(Panel(
            f"[bold yellow]Starting 1v1 Game[/bold yellow]\n\n" +
            f"🔴 Player 1 (RED): [cyan]{model1}[/cyan]\n" +
            f"🔵 Player 2 (BLUE): [magenta]{model2}[/magenta]",
            title="Game Setup",
            border_style="yellow"
        ))
        
        # Create players - just 2 for 1v1
        colors = [Color.RED, Color.BLUE]
        players = [
            LLMPlayer(colors[0], model1),
            LLMPlayer(colors[1], model2)
        ]
        
        # Create and play game
        game = Game(players)
        
        # Track game progress
        game_log = {
            "game_id": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "players": {
                "RED": model1,
                "BLUE": model2
            },
            "actions": [],
            "start_time": datetime.now().isoformat()
        }
        
        try:
            # Play the game
            winner_color = self._play_game_sync(game, game_log)
            
            # Determine winner model
            if winner_color == Color.RED:
                winner_model = model1
                loser_model = model2
            elif winner_color == Color.BLUE:
                winner_model = model2
                loser_model = model1
            else:
                # No winner (draw/timeout)
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
            
            # Notify web server of game end
            self._notify_web_server("game_end", game_log["game_id"], {
                "winner": winner_model or "Draw",
                "total_turns": game.state.num_turns,
                "final_state": self._get_simplified_game_state(game)
            })
            
            # Display results
            if winner_model:
                winner_color = "cyan" if winner_model == model1 else "magenta"
                console.print(Panel(
                    f"[bold {winner_color}]🏆 Winner: {winner_model}[/bold {winner_color}]\n\n" +
                    f"Total turns: {game.state.num_turns}\n" +
                    f"Game ID: {game_log['game_id']}",
                    title="Game Results",
                    border_style="green"
                ))
            else:
                console.print(Panel(
                    f"[bold yellow]Draw - No winner[/bold yellow]\n\n" +
                    f"Total turns: {game.state.num_turns}\n" +
                    f"Game ID: {game_log['game_id']}",
                    title="Game Results",
                    border_style="yellow"
                ))
            
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
            
            console.print(Panel(
                f"[bold red]Game Timeout[/bold red]\n\n" +
                f"Models: {model1} vs {model2}\n" +
                f"Game ID: {game_log['game_id']}",
                title="Game Error",
                border_style="red"
            ))
            
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
            
            console.print(Panel(
                f"[bold red]Game Error[/bold red]\n\n" +
                f"Error: {str(e)}\n" +
                f"Game ID: {game_log['game_id']}",
                title="Game Error",
                border_style="red"
            ))
            
            return {
                "winner": None,
                "loser": None,
                "error": str(e),
                "game_id": game_log["game_id"]
            }
    
    def _play_game_sync(self, game: Game, game_log: Dict) -> Optional[Color]:
        """Play a game synchronously"""
        
        # Send game start notification to web server with initial board state
        initial_state = self._get_simplified_game_state(game)
        self._notify_web_server("game_start", game_log["game_id"], {
            "players": game_log["players"],
            "board": initial_state["board"]
        })
        
        # Check if game has a winner
        while game.winning_color() is None:
            if game.state.num_turns > Config.MAX_TURNS_PER_GAME:
                logger.warning("Game exceeded maximum turns")
                break
            
            # Get current player
            current_player_idx = game.state.current_player_index
            current_player = game.state.players[current_player_idx]
            current_color = game.state.colors[current_player_idx]
            
            # Get playable actions
            playable_actions = game.state.playable_actions
            
            if len(playable_actions) == 0:
                logger.error("No playable actions available")
                break
            
            # If only one legal action, take it without calling the model
            reasoning = None
            if len(playable_actions) == 1:
                action = playable_actions[0]
                reasoning = "AUTO MOVE"
                color = "cyan" if current_color == Color.RED else "magenta"
                console.print(f"[dim {color}]Auto-action for {current_color.value}: {action} (only option)[/dim {color}]")
            else:
                # Get player's decision - all players use synchronous decide method
                if hasattr(current_player, 'get_move'):
                    # This is an LLM player - get full response with reasoning
                    game_state = self._get_simplified_game_state(game)
                    legal_actions = self._format_legal_actions(playable_actions)
                    decision = current_player.get_move(game_state, legal_actions, [])
                    action = decision.get('action', playable_actions[0])
                    reasoning = decision.get('reasoning', 'No reasoning provided')
                    
                    # Convert back to Catanatron action
                    for pa in playable_actions:
                        if self._actions_match(pa, action):
                            action = pa
                            break
                else:
                    # Regular player (Random, etc)
                    action = current_player.decide(game, playable_actions)
                    reasoning = "Random player - no reasoning"
            
            # Log action
            action_data = {
                "turn": game.state.num_turns,
                "player": current_color.value,
                "action": str(action),
                "reasoning": reasoning,
                "timestamp": datetime.now().isoformat()
            }
            
            # Execute action BEFORE getting the game state
            game.execute(action)
            
            # Now get the game state AFTER the action has been executed
            action_data["game_state"] = self._get_simplified_game_state(game)
            
            # Save to log and notify web server
            game_log["actions"].append(action_data)
            self._notify_web_server("action", game_log["game_id"], action_data)
            
            # Log progress every 10 turns
            if game.state.num_turns % 10 == 0:
                logger.info(f"Game progress - Turn {game.state.num_turns}")
        
        # Return winner
        return game.winning_color()
    
    def _get_simplified_game_state(self, game) -> Dict:
        """Get a simplified game state for web display"""
        state = game.state
        
        # Get player scores and resources
        players = {}
        for i, color in enumerate(state.colors):
            players[color.value] = {
                "victory_points": state.player_state[f"P{i}_VICTORY_POINTS"],
                "resources": {
                    "wood": state.player_state[f"P{i}_WOOD_IN_HAND"],
                    "brick": state.player_state[f"P{i}_BRICK_IN_HAND"],
                    "sheep": state.player_state[f"P{i}_SHEEP_IN_HAND"],
                    "wheat": state.player_state[f"P{i}_WHEAT_IN_HAND"],
                    "ore": state.player_state[f"P{i}_ORE_IN_HAND"]
                },
                "settlements": 0,
                "cities": 0,
                "roads": 0
            }
            
            # Count buildings
            if hasattr(state, 'buildings_by_color') and color in state.buildings_by_color:
                from catanatron.models.enums import SETTLEMENT, CITY
                buildings = state.buildings_by_color[color]
                players[color.value]["settlements"] = len(buildings.get(SETTLEMENT, []))
                players[color.value]["cities"] = len(buildings.get(CITY, []))
            
            # Count roads (deduplicated)
            if hasattr(state, 'board') and hasattr(state.board, 'roads'):
                player_roads = set()
                for edge, road_color in state.board.roads.items():
                    if road_color == color:
                        if isinstance(edge, tuple) and len(edge) == 2:
                            normalized_edge = tuple(sorted(edge))
                            player_roads.add(normalized_edge)
                        else:
                            player_roads.add(edge)
                players[color.value]["roads"] = len(player_roads)
        
        # Get board hex data
        board_hexes = []
        if hasattr(state.board, 'map') and hasattr(state.board.map, 'land_tiles'):
            # Mapping from Catanatron cube coordinates to offset coordinates
            cube_to_offset = {
                (-2, 0, 2): (0, 0),    # Row 0
                (-1, -1, 2): (1, 0),
                (0, -2, 2): (2, 0),
                
                (-2, 1, 1): (0, 1),    # Row 1
                (-1, 0, 1): (1, 1),
                (0, -1, 1): (2, 1),
                (1, -2, 1): (3, 1),
                
                (-2, 2, 0): (0, 2),    # Row 2 (middle)
                (-1, 1, 0): (1, 2),
                (0, 0, 0): (2, 2),
                (1, -1, 0): (3, 2),
                (2, -2, 0): (4, 2),
                
                (-1, 2, -1): (0, 3),   # Row 3
                (0, 1, -1): (1, 3),
                (1, 0, -1): (2, 3),
                (2, -1, -1): (3, 3),
                
                (0, 2, -2): (0, 4),    # Row 4
                (1, 1, -2): (1, 4),
                (2, 0, -2): (2, 4),
            }
            
            for coord, tile in state.board.map.land_tiles.items():
                # Convert cube coord to offset coord
                offset_coord = cube_to_offset.get(coord)
                if not offset_coord:
                    continue
                    
                resource = tile.resource
                # Handle resource - it might be a string or enum
                if hasattr(resource, 'value'):
                    resource_str = resource.value
                elif resource:
                    resource_str = str(resource)
                else:
                    resource_str = "desert"
                
                hex_data = {
                    "coordinate": f"({offset_coord[0]}, {offset_coord[1]})",
                    "cube_coord": str(coord),  # Keep original for robber comparison
                    "resource": resource_str.lower(),
                    "number": tile.number if hasattr(tile, 'number') and tile.number else None
                }
                board_hexes.append(hex_data)
        
        # Get robber location
        robber_coord = None
        if hasattr(state.board, 'robber_coordinate'):
            robber_coord = str(state.board.robber_coordinate)
        
        # Get buildings (settlements and cities) - use board.buildings directly
        buildings = []
        if hasattr(state.board, 'buildings'):
            from catanatron.models.enums import SETTLEMENT, CITY
            for node_id, (color, building_type) in state.board.buildings.items():
                building_type_str = "settlement" if building_type == SETTLEMENT else "city"
                buildings.append({
                    "type": building_type_str,
                    "color": color.value,
                    "node_id": node_id
                })
        
        # Get roads
        roads = []
        if hasattr(state.board, 'roads'):
            for edge, color in state.board.roads.items():
                roads.append({
                    "color": color.value,
                    "edge": [str(edge[0]), str(edge[1])] if isinstance(edge, tuple) else str(edge)
                })
        
        return {
            "turn": state.num_turns,
            "current_player": state.colors[state.current_player_index].value,
            "players": players,
            "board": {
                "hexes": board_hexes,
                "robber": robber_coord,
                "buildings": buildings,
                "roads": roads
            }
        }
    
    def _format_legal_actions(self, playable_actions):
        """Format Catanatron actions into a format the LLM can understand"""
        formatted = []
        for action in playable_actions:
            # Convert Catanatron action to dictionary format
            action_dict = {
                "type": action.action_type.name if hasattr(action, 'action_type') else str(action),
                "params": str(action)
            }
            
            # Add specific parameters based on action type
            if hasattr(action, 'node_id'):
                action_dict["node"] = action.node_id
            if hasattr(action, 'edge'):
                action_dict["edge"] = action.edge
            if hasattr(action, 'coordinate'):
                action_dict["coordinate"] = action.coordinate
                
            formatted.append(action_dict)
        return formatted
    
    def _actions_match(self, catanatron_action, llm_action_dict):
        """Check if a Catanatron action matches an LLM action dictionary"""
        if not isinstance(llm_action_dict, dict):
            return False
            
        # Compare action types
        if hasattr(catanatron_action, 'action_type'):
            if catanatron_action.action_type.name != llm_action_dict.get('type', ''):
                return False
                
        # Compare specific parameters
        if hasattr(catanatron_action, 'node_id') and 'node' in llm_action_dict:
            if catanatron_action.node_id != llm_action_dict['node']:
                return False
                
        if hasattr(catanatron_action, 'edge') and 'edge' in llm_action_dict:
            if catanatron_action.edge != llm_action_dict['edge']:
                return False
                
        return True
    
    def _notify_web_server(self, event_type: str, game_id: str, data: Dict):
        """Send notification to web server via HTTP"""
        try:
            import requests
            url = f"http://localhost:{Config.APP_PORT}/api/game-event"
            payload = {
                "game_id": game_id,
                "type": event_type,
                "data": data,
                "timestamp": datetime.now().isoformat()
            }
            requests.post(url, json=payload, timeout=0.5)
        except:
            pass  # Web server might not be running or request failed
    
    def _save_game_log(self, game_log: Dict):
        """Save game log to file"""
        filename = f"{game_log['game_id']}.json"
        filepath = self.game_logs_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(game_log, f, indent=2)
        
        logger.debug(f"Saved game log to {filepath}")
    
    def run_tournament(self, games_per_matchup: int = 1) -> Dict:
        """Run a round-robin tournament between all models"""
        console.print(f"[bold green]Starting tournament with {len(self.models)} models[/bold green]")
        console.print(f"Games per matchup: {games_per_matchup}")
        
        scheduler = TournamentScheduler(self.models)
        results = {
            "start_time": datetime.now().isoformat(),
            "models": self.models,
            "games": []
        }
        
        total_games = len(scheduler.matchups) * games_per_matchup
        console.print(f"\n[bold cyan]Running {total_games} total games...[/bold cyan]\n")
        
        while True:
            matchup = scheduler.get_next_matchup()
            if not matchup:
                break
            
            model1, model2 = matchup
            
            # Play multiple games for this matchup
            for game_num in range(games_per_matchup):
                console.print(f"\n[bold yellow]Match {len(results['games']) + 1}/{total_games}[/bold yellow]")
                
                # Alternate who goes first
                if game_num % 2 == 0:
                    result = self.run_game(model1, model2)
                else:
                    result = self.run_game(model2, model1)
                
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