from flask import Flask, render_template, jsonify, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import json
from pathlib import Path
from datetime import datetime
from loguru import logger

from .config import Config
from .elo_system import EloRatingSystem

app = Flask(__name__, 
    static_folder='../web/static',
    template_folder='../web/templates'
)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Global state
elo_system = EloRatingSystem()
active_games = {}

@app.route('/')
def index():
    """Serve the main visualization page"""
    return render_template('index.html')

@app.route('/api/leaderboard')
def get_leaderboard():
    """Get current leaderboard data"""
    stats = elo_system.get_statistics()
    return jsonify({
        "leaderboard": [
            {
                "rank": i + 1,
                "model": model,
                "rating": rating,
                "stats": stats["model_stats"].get(model, {})
            }
            for i, (model, rating) in enumerate(stats["leaderboard"])
        ],
        "total_games": stats["total_games"],
        "last_updated": datetime.now().isoformat()
    })

@app.route('/api/games')
def get_games():
    """Get list of game logs"""
    game_logs_dir = Config.BASE_DIR / "game_logs"
    games = []
    
    if game_logs_dir.exists():
        for game_file in sorted(game_logs_dir.glob("*.json"), reverse=True)[:50]:
            try:
                with open(game_file, 'r') as f:
                    game_data = json.load(f)
                    games.append({
                        "game_id": game_data.get("game_id"),
                        "players": game_data.get("players"),
                        "winner": game_data.get("winner_model"),
                        "total_turns": game_data.get("total_turns"),
                        "start_time": game_data.get("start_time"),
                        "end_time": game_data.get("end_time")
                    })
            except Exception as e:
                logger.error(f"Error loading game {game_file}: {e}")
    
    return jsonify(games)

@app.route('/api/game/<game_id>')
def get_game_details(game_id):
    """Get detailed game log"""
    game_file = Config.BASE_DIR / "game_logs" / f"{game_id}.json"
    
    if game_file.exists():
        with open(game_file, 'r') as f:
            return jsonify(json.load(f))
    else:
        return jsonify({"error": "Game not found"}), 404

@app.route('/api/active-games')
def get_active_games():
    """Get currently running games"""
    return jsonify([
        {
            "game_id": game_id,
            "players": game_info["players"],
            "current_turn": game_info["current_turn"],
            "started": game_info["started"]
        }
        for game_id, game_info in active_games.items()
    ])

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info(f"Client connected: {request.sid}")
    emit('connected', {"message": "Connected to Catan LLM Evaluation server"})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info(f"Client disconnected: {request.sid}")

def broadcast_game_update(game_id: str, update_type: str, data: dict):
    """Broadcast game updates to all connected clients"""
    socketio.emit('game_update', {
        "game_id": game_id,
        "type": update_type,
        "data": data,
        "timestamp": datetime.now().isoformat()
    })

def broadcast_leaderboard_update():
    """Broadcast leaderboard updates"""
    stats = elo_system.get_statistics()
    socketio.emit('leaderboard_update', {
        "leaderboard": stats["leaderboard"],
        "timestamp": datetime.now().isoformat()
    })

# Game lifecycle notifications
def notify_game_start(game_id: str, players: dict):
    """Notify clients when a game starts"""
    active_games[game_id] = {
        "players": players,
        "current_turn": 0,
        "started": datetime.now().isoformat()
    }
    broadcast_game_update(game_id, "game_start", {
        "players": players
    })

def notify_game_action(game_id: str, action: dict):
    """Notify clients of game actions"""
    if game_id in active_games:
        active_games[game_id]["current_turn"] = action.get("turn", 0)
    
    broadcast_game_update(game_id, "action", action)

def notify_game_end(game_id: str, winner: str, stats: dict):
    """Notify clients when a game ends"""
    if game_id in active_games:
        del active_games[game_id]
    
    broadcast_game_update(game_id, "game_end", {
        "winner": winner,
        "stats": stats
    })
    
    # Update leaderboard
    broadcast_leaderboard_update()

def run_server():
    """Run the web server"""
    logger.info(f"Starting web server on {Config.APP_HOST}:{Config.APP_PORT}")
    socketio.run(app, host=Config.APP_HOST, port=Config.APP_PORT, debug=Config.APP_DEBUG)