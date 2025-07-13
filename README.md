# Catan LLM Evaluation

A framework for evaluating Large Language Model capabilities through Settlers of Catan gameplay.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Status](https://img.shields.io/badge/status-alpha-orange.svg)

## Overview

This project uses the strategic board game Settlers of Catan to benchmark and rank LLMs. Models compete in matches where they must demonstrate:
- Strategic planning and resource management
- Negotiation and trading decisions
- Probabilistic reasoning
- Long-term goal optimization

Performance is tracked using an Elo rating system, providing quantifiable comparisons between models.

## Features

- 🎲 **Automated Gameplay** - LLMs play complete Catan games autonomously
- 📊 **Elo Rankings** - Chess-style rating system for fair model comparison
- 🌐 **Live Dashboard** - Beautiful web visualization of ongoing games and statistics
- 📝 **Detailed Logging** - Complete game histories with reasoning explanations
- 🤖 **Multi-Provider** - Support for any model available through OpenRouter
- ⚡ **High Performance** - Leverages Catanatron engine for fast game simulation
- 🏆 **Tournament Mode** - Round-robin tournaments with configurable match counts

## Screenshots

The web dashboard provides real-time visualization of:
- Model leaderboard with Elo ratings
- Active game monitoring
- Historical game analysis
- Performance statistics and charts

## Quick Start

### Prerequisites

- Python 3.8+
- OpenRouter API key ([Get one here](https://openrouter.ai))

### Installation

```bash
# Clone the repository
git clone https://github.com/vacaslistradas/catan-llm-evaluation.git
cd catan-llm-evaluation

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env and add your OpenRouter API key
```

### Running Your First Evaluation

```bash
# Interactive mode - guides you through model selection
python main.py

# Or specify models directly
python main.py --models openai/gpt-3.5-turbo anthropic/claude-3-haiku

# Run a full tournament with 3 games per matchup
python main.py --models openai/gpt-4 anthropic/claude-3-opus meta-llama/llama-3.1-70b-instruct --games 3
```

The web dashboard will automatically open at `http://localhost:5000`

## Usage Examples

### Basic Evaluation
```bash
# Evaluate two models with default settings
python main.py --models openai/gpt-3.5-turbo mistralai/mixtral-8x7b-instruct
```

### Tournament Mode
```bash
# Run a tournament with multiple games per matchup
python main.py --games 5 --models openai/gpt-4 anthropic/claude-3-opus meta-llama/llama-3.1-70b-instruct
```

### View Statistics
```bash
# Show current leaderboard and statistics
python main.py --show-stats
```

### Reset Rankings
```bash
# Reset all Elo ratings to start fresh
python main.py --reset-ratings
```

## Supported Models

Any model available on OpenRouter can be used. Popular options include:

- **OpenAI**: gpt-4, gpt-3.5-turbo
- **Anthropic**: claude-3-opus, claude-3-sonnet, claude-3-haiku
- **Meta**: llama-3.1-70b-instruct, llama-3.1-8b-instruct
- **Mistral**: mixtral-8x7b-instruct, mistral-7b-instruct
- **Google**: gemini-pro

See the full list at [OpenRouter Models](https://openrouter.ai/models)

## How It Works

1. **Game Setup**: Each evaluation match includes 2 LLM players and 2 random players
2. **Decision Making**: LLMs receive game state and legal actions, returning strategic decisions
3. **Elo Updates**: Winners gain rating points, losers lose points (K-factor: 32)
4. **Tournament Play**: Round-robin format ensures all models play each other
5. **Analysis**: Results include win rates, game lengths, and decision patterns

## Configuration

Edit `.env` for customization:

```env
# API Configuration
OPENROUTER_API_KEY=your-key-here

# Game Settings
MAX_TURNS_PER_GAME=200        # Prevent infinite games
GAME_TIMEOUT_SECONDS=300      # 5-minute timeout per game

# Web Dashboard
APP_PORT=5000                 # Web server port
APP_DEBUG=false               # Production mode

# Elo System
INITIAL_ELO=1500             # Starting rating
ELO_K_FACTOR=32              # Rating volatility
```

## Output

### Game Logs
Detailed JSON logs saved in `game_logs/` include:
- Complete move history
- LLM reasoning for each decision
- Game state at each turn
- Performance metrics

### Tournament Results
- `tournament_YYYYMMDD_HHMMSS.json` - Complete tournament data
- `elo_rankings.json` - Current ratings and match history

### Web Dashboard
Real-time visualization at `http://localhost:5000` showing:
- Live leaderboard
- Active games
- Historical results
- Performance charts

## Documentation

- [📖 Usage Guide](USAGE.md) - Detailed usage instructions
- [🎲 Catan Research](docs/catan-research.md) - Game mechanics and strategy
- [🤖 OpenRouter Guide](docs/openrouter-guide.md) - API integration details

## Development

### Project Structure
```
catan-llm-evaluation/
├── src/
│   ├── config.py          # Configuration management
│   ├── llm_client.py      # LLM integration
│   ├── evaluation.py      # Game orchestration
│   ├── elo_system.py      # Rating calculations
│   └── web_server.py      # Dashboard server
├── web/
│   ├── templates/         # HTML templates
│   └── static/           # CSS/JS assets
├── docs/                 # Documentation
├── game_logs/           # Game history
└── main.py             # CLI entry point
```

### Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Roadmap

- [ ] Multi-player games (3-4 LLMs)
- [ ] Custom game scenarios
- [ ] Advanced statistics and analytics
- [ ] Model fine-tuning integration
- [ ] Replay viewer in dashboard
- [ ] Export to standard chess notation

## Acknowledgments

- [Catanatron](https://github.com/bcollazo/catanatron) - High-performance Catan engine
- [OpenRouter](https://openrouter.ai) - Unified LLM API
- Settlers of Catan - Created by Klaus Teuber

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Citation

If you use this framework in research, please cite:

```bibtex
@software{catan-llm-evaluation,
  title = {Catan LLM Evaluation: Benchmarking Language Models through Strategic Board Game Play},
  author = {Your Name},
  year = {2024},
  url = {https://github.com/vacaslistradas/catan-llm-evaluation}
}
```

## Support

- 🐛 [Report Issues](https://github.com/vacaslistradas/catan-llm-evaluation/issues)
- 💬 [Discussions](https://github.com/vacaslistradas/catan-llm-evaluation/discussions)
- 📧 Contact: your.email@example.com