# Settlers of Catan Research Guide

## Table of Contents
1. [Game Overview](#game-overview)
2. [Game Rules and Mechanics](#game-rules-and-mechanics)
3. [Victory Conditions](#victory-conditions)
4. [Strategy Elements](#strategy-elements)
5. [Best Python Libraries](#best-python-libraries)
6. [Recommended Library: Catanatron](#recommended-library-catanatron)

## Game Overview

Settlers of Catan (now simply called "Catan") is a multiplayer board game designed by Klaus Teuber. It's a resource management and trading game where players:
- Take on roles of settlers on the island of Catan
- Build settlements, cities, and roads
- Trade resources with other players
- Race to be the first to reach 10 victory points

### Player Count
- Standard game: 3-4 players
- With expansion: up to 6 players
- Community variants exist for 2 players

### Game Duration
- Typical game: 60-120 minutes
- Varies based on player count and experience

## Game Rules and Mechanics

### Board Setup
1. **Hexagonal Board**: 19 terrain hexes arranged randomly
2. **Terrain Types**: 
   - Forest (produces wood)
   - Hills (produces brick)
   - Fields (produces wheat/grain)
   - Mountains (produces ore)
   - Pastures (produces sheep/wool)
   - Desert (produces nothing)
3. **Number Tokens**: Placed on non-desert tiles (2-12, no 7)
4. **Sea Frame**: 6 pieces forming the board edge

### Turn Structure

Each turn consists of three phases:

#### 1. Resource Production Phase
- Roll two dice
- All players with settlements/cities on hexes with the rolled number receive resources
- Settlements produce 1 resource card
- Cities produce 2 resource cards
- Rolling 7 activates the robber:
  - Players with 8+ cards must discard half
  - Active player moves robber to block a hex
  - Active player steals a card from an adjacent player

#### 2. Trading Phase
- **Domestic Trade**: Negotiate trades with other players
- **Maritime Trade**: Trade with the bank
  - 4:1 - Four of any identical resource for one of any other
  - 3:1 port - Three of any identical resource for one of any other
  - 2:1 port - Two of a specific resource for one of any other

#### 3. Building Phase
Build structures using resources:
- **Road** (1 brick + 1 wood): Connects intersections
- **Settlement** (1 brick + 1 wood + 1 wheat + 1 sheep): Worth 1 VP
- **City** (2 wheat + 3 ore): Upgrades settlement, worth 2 VP
- **Development Card** (1 wheat + 1 sheep + 1 ore): Special abilities

### Development Cards
- **Knight**: Move the robber and steal a resource
- **Progress Cards**: Various special actions
- **Victory Point Cards**: Hidden VPs

## Victory Conditions

First player to reach **10 Victory Points** wins:

### Victory Point Sources
1. **Settlements**: 1 VP each
2. **Cities**: 2 VP each
3. **Longest Road**: 2 VP (5+ continuous roads)
4. **Largest Army**: 2 VP (3+ played knight cards)
5. **Victory Point Cards**: 1 VP each

## Strategy Elements

### Key Strategic Considerations
1. **Initial Placement**: Critical for resource access
2. **Resource Probability**: Tiles with 6 and 8 are most productive
3. **Resource Diversity**: Access to all five resources is valuable
4. **Port Access**: Reduces dependency on other players
5. **Blocking**: Strategic road and settlement placement
6. **Trading**: Negotiation skills are crucial

### Common Strategies
- **Ore-Wheat Strategy**: Focus on cities and development cards
- **Wood-Brick Strategy**: Expand quickly with roads and settlements
- **Balanced Strategy**: Maintain access to all resources
- **Port Strategy**: Leverage maritime trade advantages

## Best Python Libraries

### 1. **Catanatron** ⭐ (Recommended)
- **GitHub**: https://github.com/bcollazo/catanatron
- **Features**:
  - High-performance game engine (thousands of games per minute)
  - Strong AI players including MCTS and Alpha-Beta search
  - OpenAI Gym integration
  - Web UI support
  - Actively maintained
  - pip-installable: `pip install catanatron`

### 2. **PyCatan**
- **GitHub**: https://github.com/josefwaller/PyCatan
- **Features**:
  - Simple, clean API
  - Good for beginners
  - MIT licensed
  - Basic game mechanics implementation

### 3. **Catan-AI**
- **GitHub**: https://github.com/kvombatkere/Catan-AI
- **Features**:
  - Reinforcement Learning integration
  - MCTS implementation
  - pygame GUI
  - Graph-based board representation

### 4. **settlers4py**
- **GitHub**: https://github.com/dr3amt3am/settlers4py
- **Features**:
  - Simple terminal implementation
  - Basic 4-player support
  - Good for learning

## Recommended Library: Catanatron

### Why Catanatron?

1. **Performance**: Optimized for running thousands of games quickly
2. **AI Quality**: Includes state-of-the-art AI implementations
3. **Documentation**: Comprehensive docs at https://catanatron.readthedocs.io/
4. **Active Development**: Regular updates and improvements
5. **Extensibility**: Easy to add custom players and strategies

### Quick Start Example

```python
from catanatron import Game, RandomPlayer, Color
from catanatron.players import AlphaBetaPlayer

# Create players
players = [
    AlphaBetaPlayer(Color.RED),     # Strong AI
    RandomPlayer(Color.BLUE),        # Random moves
    RandomPlayer(Color.WHITE),       # Random moves
    RandomPlayer(Color.ORANGE),      # Random moves
]

# Create and play game
game = Game(players)
winner = game.play()
print(f"Winner: {winner}")

# Access game state
print(f"Final scores: {game.state.player_state}")
```

### Key Features for LLM Evaluation

1. **State Representation**: Clean game state access for LLM input
2. **Action Space**: Well-defined action space for LLM output
3. **Gym Integration**: Compatible with standard RL interfaces
4. **Logging**: Comprehensive game logging capabilities
5. **Visualization**: Web UI for game replay and analysis

### Installation

```bash
# Basic installation
pip install catanatron

# With Gym support
pip install catanatron_gym

# Development installation
git clone https://github.com/bcollazo/catanatron.git
cd catanatron
pip install -e .
```

## Conclusion

Catanatron stands out as the best choice for implementing a Catan-based LLM evaluation framework due to its:
- High performance for running many games
- Clean API for integration
- Strong existing AI players for benchmarking
- Active maintenance and community

The combination of strategic depth in Catan and Catanatron's robust implementation makes it ideal for evaluating LLM decision-making capabilities.