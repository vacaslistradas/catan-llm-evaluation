import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from loguru import logger
from .config import Config

class EloRatingSystem:
    """Elo rating system for tracking model performance"""
    
    def __init__(self, k_factor: int = Config.ELO_K_FACTOR, initial_rating: int = Config.INITIAL_ELO):
        self.k_factor = k_factor
        self.initial_rating = initial_rating
        self.ratings: Dict[str, float] = {}
        self.game_history: List[Dict] = []
        self.ratings_file = Config.BASE_DIR / "elo_rankings.json"
        self.load_ratings()
    
    def load_ratings(self):
        """Load existing ratings from file"""
        if self.ratings_file.exists():
            try:
                with open(self.ratings_file, 'r') as f:
                    data = json.load(f)
                    self.ratings = data.get("ratings", {})
                    self.game_history = data.get("history", [])
                    logger.info(f"Loaded ratings for {len(self.ratings)} models")
            except Exception as e:
                logger.error(f"Error loading ratings: {e}")
                self.ratings = {}
                self.game_history = []
        else:
            logger.info("No existing ratings found, starting fresh")
    
    def save_ratings(self):
        """Save current ratings to file"""
        try:
            data = {
                "ratings": self.ratings,
                "history": self.game_history,
                "last_updated": datetime.now().isoformat()
            }
            with open(self.ratings_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info("Ratings saved successfully")
        except Exception as e:
            logger.error(f"Error saving ratings: {e}")
    
    def get_rating(self, model: str) -> float:
        """Get current rating for a model"""
        if model not in self.ratings:
            self.ratings[model] = self.initial_rating
        return self.ratings[model]
    
    def expected_score(self, rating_a: float, rating_b: float) -> float:
        """Calculate expected score for player A against player B"""
        return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))
    
    def update_ratings(self, winner: str, loser: str, draw: bool = False):
        """Update ratings after a game"""
        winner_rating = self.get_rating(winner)
        loser_rating = self.get_rating(loser)
        
        # Calculate expected scores
        winner_expected = self.expected_score(winner_rating, loser_rating)
        loser_expected = self.expected_score(loser_rating, winner_rating)
        
        # Actual scores
        if draw:
            winner_score = 0.5
            loser_score = 0.5
        else:
            winner_score = 1.0
            loser_score = 0.0
        
        # Update ratings
        self.ratings[winner] = winner_rating + self.k_factor * (winner_score - winner_expected)
        self.ratings[loser] = loser_rating + self.k_factor * (loser_score - loser_expected)
        
        # Record game
        game_record = {
            "timestamp": datetime.now().isoformat(),
            "winner": winner,
            "loser": loser,
            "draw": draw,
            "winner_rating_before": winner_rating,
            "loser_rating_before": loser_rating,
            "winner_rating_after": self.ratings[winner],
            "loser_rating_after": self.ratings[loser]
        }
        self.game_history.append(game_record)
        
        logger.info(f"Updated ratings - {winner}: {winner_rating:.1f} -> {self.ratings[winner]:.1f}, "
                   f"{loser}: {loser_rating:.1f} -> {self.ratings[loser]:.1f}")
        
        self.save_ratings()
    
    def get_leaderboard(self) -> List[Tuple[str, float]]:
        """Get sorted leaderboard"""
        return sorted(self.ratings.items(), key=lambda x: x[1], reverse=True)
    
    def get_matchup_prediction(self, model_a: str, model_b: str) -> Dict[str, float]:
        """Get win probability prediction for a matchup"""
        rating_a = self.get_rating(model_a)
        rating_b = self.get_rating(model_b)
        
        prob_a_wins = self.expected_score(rating_a, rating_b)
        prob_b_wins = self.expected_score(rating_b, rating_a)
        
        return {
            model_a: prob_a_wins,
            model_b: prob_b_wins,
            "rating_difference": abs(rating_a - rating_b)
        }
    
    def get_statistics(self) -> Dict:
        """Get overall statistics"""
        if not self.game_history:
            return {
                "total_games": 0,
                "models": len(self.ratings),
                "average_rating": self.initial_rating
            }
        
        total_games = len(self.game_history)
        draws = sum(1 for game in self.game_history if game["draw"])
        
        # Model performance stats
        model_stats = {}
        for game in self.game_history:
            winner = game["winner"]
            loser = game["loser"]
            
            if winner not in model_stats:
                model_stats[winner] = {"wins": 0, "losses": 0, "draws": 0}
            if loser not in model_stats:
                model_stats[loser] = {"wins": 0, "losses": 0, "draws": 0}
            
            if game["draw"]:
                model_stats[winner]["draws"] += 1
                model_stats[loser]["draws"] += 1
            else:
                model_stats[winner]["wins"] += 1
                model_stats[loser]["losses"] += 1
        
        # Calculate win rates
        for model, stats in model_stats.items():
            total = stats["wins"] + stats["losses"] + stats["draws"]
            stats["win_rate"] = stats["wins"] / total if total > 0 else 0
            stats["games_played"] = total
        
        return {
            "total_games": total_games,
            "total_draws": draws,
            "models": len(self.ratings),
            "average_rating": sum(self.ratings.values()) / len(self.ratings) if self.ratings else self.initial_rating,
            "model_stats": model_stats,
            "leaderboard": self.get_leaderboard()
        }
    
    def reset_ratings(self):
        """Reset all ratings to initial value"""
        logger.warning("Resetting all ratings")
        self.ratings = {}
        self.game_history = []
        self.save_ratings()

class TournamentScheduler:
    """Schedule round-robin tournaments between models"""
    
    def __init__(self, models: List[str]):
        self.models = models
        self.matchups = self._generate_matchups()
        self.current_round = 0
    
    def _generate_matchups(self) -> List[Tuple[str, str]]:
        """Generate all possible matchups for round-robin"""
        matchups = []
        for i in range(len(self.models)):
            for j in range(i + 1, len(self.models)):
                matchups.append((self.models[i], self.models[j]))
        return matchups
    
    def get_next_matchup(self) -> Optional[Tuple[str, str]]:
        """Get the next matchup to play"""
        if self.current_round < len(self.matchups):
            matchup = self.matchups[self.current_round]
            self.current_round += 1
            return matchup
        return None
    
    def get_progress(self) -> Dict:
        """Get tournament progress"""
        return {
            "total_matchups": len(self.matchups),
            "completed": self.current_round,
            "remaining": len(self.matchups) - self.current_round,
            "progress_percentage": (self.current_round / len(self.matchups)) * 100
        }
    
    def reset(self):
        """Reset tournament progress"""
        self.current_round = 0