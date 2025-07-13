# Catan LLM Evaluation - Usage Guide

## Quick Start

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up Environment**
   ```bash
   cp .env.example .env
   # Edit .env and add your OpenRouter API key
   ```

3. **Run Evaluation**
   ```bash
   python main.py
   ```

## Command Line Options

### Basic Usage

```bash
# Interactive mode - prompts for models
python main.py

# Specify models directly
python main.py --models openai/gpt-3.5-turbo anthropic/claude-3-haiku meta-llama/llama-3.1-8b-instruct

# Run multiple games per matchup
python main.py --games 3

# Disable web dashboard
python main.py --no-web
```

### Advanced Options

```bash
# Show current statistics
python main.py --show-stats

# Reset all Elo ratings
python main.py --reset-ratings

# Full example
python main.py --models openai/gpt-4 anthropic/claude-3-opus --games 5
```

## Web Dashboard

The web dashboard runs automatically at `http://localhost:5000` and provides:

- **Real-time Leaderboard**: Live Elo ratings and statistics
- **Active Games**: Monitor ongoing matches
- **Game History**: Review past games and actions
- **Rating Chart**: Visual representation of model rankings

## Model Selection

### Supported Models

You can use any model available on OpenRouter. Popular options include:

**OpenAI Models:**
- `openai/gpt-4`
- `openai/gpt-3.5-turbo`
- `openai/gpt-4-turbo`

**Anthropic Models:**
- `anthropic/claude-3-opus`
- `anthropic/claude-3-sonnet`
- `anthropic/claude-3-haiku`

**Open Source Models:**
- `meta-llama/llama-3.1-70b-instruct`
- `meta-llama/llama-3.1-8b-instruct`
- `mistralai/mixtral-8x7b-instruct`
- `mistralai/mistral-7b-instruct`

### Model Format

Always use the format: `provider/model-name`

## Understanding Results

### Elo Ratings

- Models start at 1500 Elo
- Winning increases rating, losing decreases it
- Rating changes depend on opponent strength
- K-factor of 32 (configurable)

### Game Logs

Game logs are saved in `game_logs/` directory with:
- Complete action history
- Player decisions and reasoning
- Final game state
- Performance metrics

### Tournament Results

After a tournament, you'll find:
- `tournament_YYYYMMDD_HHMMSS.json` - Full tournament data
- `elo_rankings.json` - Current ratings and history

## Configuration

Edit `.env` file for customization:

```env
# API Configuration
OPENROUTER_API_KEY=your-key-here

# Game Settings
DEFAULT_NUM_GAMES=10
MAX_TURNS_PER_GAME=200
GAME_TIMEOUT_SECONDS=300

# Web Server
APP_HOST=0.0.0.0
APP_PORT=5000
APP_DEBUG=false

# Elo System
INITIAL_ELO=1500
ELO_K_FACTOR=32
```

## Troubleshooting

### Common Issues

1. **API Key Error**
   - Ensure `OPENROUTER_API_KEY` is set in `.env`
   - Check API key validity on OpenRouter dashboard

2. **Game Timeouts**
   - Increase `GAME_TIMEOUT_SECONDS` for slower models
   - Check network connectivity

3. **Web Dashboard Not Loading**
   - Ensure port 5000 is not in use
   - Check firewall settings
   - Try accessing via `http://127.0.0.1:5000`

### Debug Mode

Enable debug logging:
```bash
LOG_LEVEL=DEBUG python main.py
```

## Tips for Best Results

1. **Model Selection**
   - Mix different model sizes and providers
   - Include both fast and powerful models
   - Consider cost vs performance tradeoffs

2. **Tournament Size**
   - Start with 2-3 games per matchup
   - Increase for more statistical significance
   - Balance between accuracy and time/cost

3. **Monitoring**
   - Keep web dashboard open during evaluation
   - Watch for consistent timeout patterns
   - Monitor game turn counts for efficiency

## Data Analysis

### Export Results

```python
# Export leaderboard to CSV
import pandas as pd
from src.elo_system import EloRatingSystem

elo = EloRatingSystem()
df = pd.DataFrame(elo.get_leaderboard(), columns=['Model', 'Rating'])
df.to_csv('leaderboard.csv', index=False)
```

### Custom Analysis

Game logs are JSON files that can be analyzed with any tool:

```python
import json
from pathlib import Path

# Load all game logs
game_logs = []
for log_file in Path('game_logs').glob('*.json'):
    with open(log_file) as f:
        game_logs.append(json.load(f))

# Analyze average game length by model
# ... custom analysis code ...
```

## Contributing

Found a bug or want to add a feature? 
- Check existing issues on GitHub
- Submit pull requests with tests
- Follow the existing code style

## Support

For issues and questions:
- GitHub Issues: https://github.com/vacaslistradas/catan-llm-evaluation/issues
- Documentation: See `/docs` folder