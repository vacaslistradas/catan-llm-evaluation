#!/usr/bin/env python3

from catanatron import Game, Color
from catanatron.models.player import RandomPlayer
from catanatron.models.enums import RESOURCES, SETTLEMENT, CITY, Action, ActionType
import json

print("=== COMPREHENSIVE CATANATRON API TEST ===\n")

# Create 4 random players
players = [
    RandomPlayer(Color.RED),
    RandomPlayer(Color.BLUE),
    RandomPlayer(Color.WHITE),
    RandomPlayer(Color.ORANGE)
]

# Create game
game = Game(players)
state = game.state

print("1. TESTING STATE STRUCTURE:")
print(f"   - num_turns: {state.num_turns}")
print(f"   - current_player_index: {state.current_player_index}")
print(f"   - is_initial_build_phase: {state.is_initial_build_phase}")
print(f"   - colors: {state.colors}")

print("\n2. TESTING PLAYER_STATE DICTIONARY:")
print("   Available keys in player_state:")
if hasattr(state, 'player_state') and state.player_state:
    for key in sorted(state.player_state.keys()):
        print(f"      - {key}: {state.player_state[key]}")

print("\n3. TESTING BUILDINGS_BY_COLOR:")
if hasattr(state, 'buildings_by_color'):
    print(f"   Type: {type(state.buildings_by_color)}")
    for color in state.colors:
        if color in state.buildings_by_color:
            buildings = state.buildings_by_color[color]
            print(f"   {color.value}: {buildings}")

print("\n4. TESTING BOARD STRUCTURE:")
board = state.board
print(f"   Board type: {type(board)}")
print("   Board attributes:")
board_attrs = [attr for attr in dir(board) if not attr.startswith('_')]
for attr in board_attrs[:10]:  # First 10 attributes
    print(f"      - {attr}")

print("\n5. TESTING BOARD MAP:")
if hasattr(board, 'map'):
    board_map = board.map
    print(f"   Map type: {type(board_map)}")
    
    # Check for land tiles
    if hasattr(board_map, 'land_tiles'):
        print(f"   Number of land tiles: {len(board_map.land_tiles)}")
        # Show first tile
        for coord, tile in list(board_map.land_tiles.items())[:1]:
            print(f"   Sample tile at {coord}:")
            print(f"      - Type: {type(tile)}")
            if hasattr(tile, 'resource'):
                print(f"      - Resource: {tile.resource}")
            if hasattr(tile, 'number'):
                print(f"      - Number: {tile.number}")

print("\n6. PLAYING SOME TURNS:")
for i in range(20):
    if game.winning_color() is not None:
        print(f"   Game won by {game.winning_color()}")
        break
    
    actions = game.state.playable_actions
    if not actions:
        print("   No playable actions!")
        break
    
    # Show first few actions
    if i < 5:
        print(f"\n   Turn {state.num_turns} - Player {state.current_color().value}")
        print(f"   Available actions: {len(actions)}")
        for j, action in enumerate(actions[:3]):
            print(f"      {j}: {action}")
    
    # Execute random action
    action = actions[0]  # Take first action for consistency
    game.execute(action)

print("\n7. FINAL STATE CHECK:")
state = game.state
print(f"   - num_turns: {state.num_turns}")
print(f"   - is_initial_build_phase: {state.is_initial_build_phase}")

# Check player state after some gameplay
print("\n8. PLAYER STATE AFTER GAMEPLAY:")
if hasattr(state, 'player_state') and state.player_state:
    # Group by player
    for i in range(4):
        print(f"\n   Player {i} ({state.colors[i].value}):")
        player_keys = [k for k in state.player_state.keys() if k.startswith(f'P{i}_')]
        for key in sorted(player_keys):
            print(f"      {key}: {state.player_state[key]}")

print("\n9. RESOURCE AND BUILDING TRACKING:")
# Check how resources are tracked
if hasattr(state, 'resource_freqdeck'):
    print(f"   resource_freqdeck type: {type(state.resource_freqdeck)}")
    print(f"   resource_freqdeck: {state.resource_freqdeck}")

# Check development cards
if hasattr(state, 'development_listdeck'):
    print(f"   development_listdeck type: {type(state.development_listdeck)}")
    print(f"   development_listdeck length: {len(state.development_listdeck) if state.development_listdeck else 0}")

print("\n10. ACTION TYPES:")
# List all action types
action_types = [attr for attr in dir(ActionType) if not attr.startswith('_') and attr.isupper()]
print(f"   Available ActionTypes: {action_types}")

print("\n=== TEST COMPLETE ===")