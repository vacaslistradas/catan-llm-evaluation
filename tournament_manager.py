#!/usr/bin/env python3
"""Resumable tournament manager - runs in chunks and saves progress"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import time

sys.path.insert(0, str(Path(__file__).parent))

from src.evaluation import CatanLLMEvaluator
from src.web_server import run_server
import threading

class ResumableTournament:
    """Tournament that can be stopped and resumed"""
    
    def __init__(self, models: List[str], games_per_matchup: int = 1):
        self.models = models
        self.games_per_matchup = games_per_matchup
        self.progress_file = Path("tournament_progress.json")
        self.completed_matchups = []
        self.pending_matchups = []
        self.current_session_results = []
        
        # Load previous progress if it exists
        self.load_progress()
        
    def load_progress(self):
        """Load tournament progress from file"""
        if self.progress_file.exists():
            with open(self.progress_file, 'r') as f:
                data = json.load(f)
                self.completed_matchups = data.get("completed_matchups", [])
                print(f"📂 Loaded progress: {len(self.completed_matchups)} matchups completed")
        else:
            print("🆕 Starting fresh tournament")
            
    def save_progress(self):
        """Save current tournament progress"""
        data = {
            "models": self.models,
            "games_per_matchup": self.games_per_matchup,
            "completed_matchups": self.completed_matchups,
            "last_updated": datetime.now().isoformat(),
            "total_games_completed": len(self.completed_matchups),
            "session_results": self.current_session_results
        }
        with open(self.progress_file, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"💾 Progress saved: {len(self.completed_matchups)} games completed")
    
    def generate_all_matchups(self) -> List[Tuple[str, str]]:
        """Generate all possible matchups"""
        matchups = []
        for i, model1 in enumerate(self.models):
            for j, model2 in enumerate(self.models):
                if i != j:  # Don't play against self
                    for game_num in range(self.games_per_matchup):
                        matchups.append((model1, model2, game_num))
        return matchups
    
    def get_pending_matchups(self) -> List[Tuple[str, str, int]]:
        """Get list of matchups that haven't been played yet"""
        all_matchups = self.generate_all_matchups()
        pending = []
        
        for matchup in all_matchups:
            # Check if this exact matchup has been completed
            matchup_id = f"{matchup[0]}_vs_{matchup[1]}_game{matchup[2]}"
            if not any(m.get("matchup_id") == matchup_id for m in self.completed_matchups):
                pending.append(matchup)
                
        return pending
    
    def run_chunk(self, chunk_size: int = 5):
        """Run a chunk of games"""
        pending = self.get_pending_matchups()
        
        if not pending:
            print("✅ Tournament complete! All matchups have been played.")
            return False
            
        print(f"\n📊 Tournament Progress:")
        print(f"Completed: {len(self.completed_matchups)} games")
        print(f"Remaining: {len(pending)} games")
        print(f"Running next {min(chunk_size, len(pending))} games...\n")
        
        # Initialize evaluator
        evaluator = CatanLLMEvaluator(models=self.models)
        
        # Run chunk of games
        games_in_chunk = pending[:chunk_size]
        
        for i, (model1, model2, game_num) in enumerate(games_in_chunk):
            print(f"\n🎮 Game {i+1}/{len(games_in_chunk)} in this chunk")
            print(f"📍 Overall progress: {len(self.completed_matchups) + i + 1}/{len(self.generate_all_matchups())}")
            
            try:
                # Run the game
                result = evaluator.run_game(model1, model2)
                
                # Record the result
                matchup_result = {
                    "matchup_id": f"{model1}_vs_{model2}_game{game_num}",
                    "model1": model1,
                    "model2": model2,
                    "game_num": game_num,
                    "winner": result.get("winner"),
                    "loser": result.get("loser"),
                    "total_turns": result.get("total_turns"),
                    "game_id": result.get("game_id"),
                    "timestamp": datetime.now().isoformat()
                }
                
                self.completed_matchups.append(matchup_result)
                self.current_session_results.append(matchup_result)
                
                # Save progress after each game
                self.save_progress()
                
                # Small delay between games
                time.sleep(2)
                
            except Exception as e:
                print(f"❌ Error in game {model1} vs {model2}: {e}")
                # Continue with next game
                
        return True  # More games remaining
    
    def print_current_standings(self):
        """Print current tournament standings based on completed games"""
        # Count wins for each model
        wins = {}
        games_played = {}
        
        for matchup in self.completed_matchups:
            winner = matchup.get("winner")
            model1 = matchup.get("model1")
            model2 = matchup.get("model2")
            
            # Initialize counters
            for model in [model1, model2]:
                if model not in wins:
                    wins[model] = 0
                    games_played[model] = 0
                    
            # Count the game
            if model1 and model2:
                games_played[model1] += 1
                games_played[model2] += 1
                
            # Count the win
            if winner:
                wins[winner] = wins.get(winner, 0) + 1
                
        print("\n🏆 Current Standings:")
        print("-" * 60)
        print(f"{'Model':<35} {'Games':>8} {'Wins':>8} {'Win Rate':>8}")
        print("-" * 60)
        
        # Sort by win rate
        standings = []
        for model in self.models:
            if model in games_played and games_played[model] > 0:
                win_rate = wins.get(model, 0) / games_played[model]
                standings.append((model, games_played[model], wins.get(model, 0), win_rate))
            else:
                standings.append((model, 0, 0, 0.0))
                
        standings.sort(key=lambda x: x[3], reverse=True)
        
        for model, games, win_count, win_rate in standings:
            model_short = model.split("/")[-1][:30]
            print(f"{model_short:<35} {games:>8} {win_count:>8} {win_rate:>7.1%}")

def main():
    # 10 diverse models for the tournament
    TOURNAMENT_MODELS = [
        "openai/gpt-4o",
        "anthropic/claude-3-opus",
        "google/gemini-flash-1.5",  # Gemini Flash 1.5
        "openai/gpt-4o-mini",
        "anthropic/claude-3-haiku",
        "mistralai/mixtral-8x7b-instruct",
        "meta-llama/llama-3.1-70b-instruct",
        "meta-llama/llama-3.1-8b-instruct",
        "mistralai/mistral-7b-instruct",
        "openai/gpt-3.5-turbo-0613"  # Use specific version
    ]
    
    print("🎲 Resumable Catan LLM Tournament")
    print(f"Models: {len(TOURNAMENT_MODELS)}")
    print(f"Games per matchup: 1")
    print(f"Total games: {len(TOURNAMENT_MODELS) * (len(TOURNAMENT_MODELS) - 1)}")
    
    # Check if we want to start web server
    start_web = input("\nStart web server? (y/n): ").lower() == 'y'
    
    if start_web:
        print("\nStarting web server...")
        web_thread = threading.Thread(target=run_server, daemon=True)
        web_thread.start()
        time.sleep(2)
        print(f"Web dashboard available at: http://localhost:8888")
    
    # Create tournament manager
    tournament = ResumableTournament(TOURNAMENT_MODELS, games_per_matchup=1)
    
    # Check chunk size preference
    try:
        chunk_size = int(input("\nHow many games to run in this session? (default 5): ") or "5")
    except:
        chunk_size = 5
        
    print(f"\nWill run {chunk_size} games in this session")
    print("You can stop anytime with Ctrl+C and resume later")
    print("-" * 60)
    
    try:
        # Run the chunk
        has_more = tournament.run_chunk(chunk_size)
        
        # Show standings
        tournament.print_current_standings()
        
        if has_more:
            pending = tournament.get_pending_matchups()
            print(f"\n📋 {len(pending)} games remaining in tournament")
            print("Run this script again to continue!")
        else:
            print("\n🎉 Tournament complete!")
            
    except KeyboardInterrupt:
        print("\n\n⏸️  Tournament paused")
        tournament.save_progress()
        tournament.print_current_standings()
        pending = tournament.get_pending_matchups()
        print(f"\n📋 {len(pending)} games remaining")
        print("Run this script again to resume!")

if __name__ == "__main__":
    main()