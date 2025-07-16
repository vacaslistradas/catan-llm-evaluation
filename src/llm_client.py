import json
import re
from typing import List, Dict, Optional, Union
from openai import OpenAI
from loguru import logger
from catanatron.models.enums import SETTLEMENT, CITY
from .config import Config
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

console = Console()

class LLMClient:
    """Unified client for interacting with LLMs through OpenRouter"""
    
    def __init__(self, model: str, api_key: Optional[str] = None):
        self.model = model
        self.api_key = api_key or Config.OPENROUTER_API_KEY
        
        # Initialize synchronous OpenAI client
        self.client = OpenAI(
            base_url=Config.OPENROUTER_BASE_URL,
            api_key=self.api_key
        )
        
        logger.info(f"Initialized LLM client for model: {model}")
    
    def get_move(
        self,
        game_state: Dict,
        legal_actions: List[Dict],
        game_history: Optional[List[Dict]] = None
    ) -> Dict:
        """Get the next move from the LLM given the game state"""
        
        # Create system prompt
        system_prompt = """You are an expert Settlers of Catan player. You will be given the current game state and a list of legal actions.
        
Your task is to choose the best action from the legal actions list. Consider:
1. Resource optimization and diversification
2. Strategic positioning on the board
3. Blocking opponents
4. Victory point progression
5. Trade opportunities

You MUST respond with ONLY a valid JSON object in this exact format:
{"action_index": 0, "reasoning": "Brief explanation"}

Where:
- action_index: An integer from 0 to (number of legal actions - 1)
- reasoning: A brief string explaining your choice

Do not include any text before or after the JSON object. The response must be valid JSON that can be parsed."""
        
        # Format game state for LLM
        user_prompt = self._format_game_state(game_state, legal_actions, game_history)
        
        # Color based on model name
        color = "cyan" if "o4-mini" in self.model else "magenta"
        
        # Log the input
        console.print(Panel(
            f"[bold {color}]🤖 {self.model} - INPUT[/bold {color}]\n\n" + 
            user_prompt[:500] + ("..." if len(user_prompt) > 500 else ""),
            border_style=color
        ))
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7
                # No max_tokens limit - let models use as many as they need
                # No response_format - we'll parse JSON manually
            )
            
            # Parse response
            content = response.choices[0].message.content.strip()
            
            # Log the output
            console.print(Panel(
                f"[bold {color}]🤖 {self.model} - OUTPUT[/bold {color}]\n\n{content}",
                border_style=color
            ))
            
            # Try to extract JSON from the response
            # Sometimes models add extra text despite instructions
            try:
                # First try direct parsing
                decision = json.loads(content)
            except json.JSONDecodeError:
                # Try to find JSON object in the response
                import re
                # Look for JSON that might be embedded in text, handle nested braces
                json_candidates = re.findall(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', content)
                
                decision = None
                for candidate in json_candidates:
                    if '"action_index"' in candidate:
                        try:
                            decision = json.loads(candidate)
                            break
                        except json.JSONDecodeError:
                            continue
                
                if not decision:
                    # Try to find action_index mentioned in text
                    # Look for patterns like "action index 0", "choose action 0", "index: 0", etc.
                    action_match = re.search(r'(?:action\s*(?:index)?|index|choose\s*action|choose)\s*[:=]?\s*(\d+)', content, re.IGNORECASE)
                    if action_match:
                        action_index = int(action_match.group(1))
                        # Extract reasoning if possible
                        reasoning_match = re.search(r'"reasoning"\s*:\s*"([^"]+)"', content)
                        reasoning = reasoning_match.group(1) if reasoning_match else "Extracted from text response"
                        decision = {"action_index": action_index, "reasoning": reasoning}
                    else:
                        # Last resort - find the first number
                        number_match = re.search(r'\b(\d+)\b', content)
                        if number_match:
                            action_index = int(number_match.group(1))
                            decision = {"action_index": action_index, "reasoning": "Extracted first number from response"}
                        else:
                            decision = {"action_index": 0, "reasoning": "Could not parse response - defaulting to first action"}
            
            # Validate action index
            action_index = decision.get("action_index", 0)
            if not isinstance(action_index, int) or not 0 <= action_index < len(legal_actions):
                logger.warning(f"Invalid action index {action_index}, defaulting to 0")
                action_index = 0
            
            # Log the chosen action
            chosen_action = legal_actions[action_index]
            console.print(f"[bold {color}]➡️  {self.model} chose: {self._format_action(chosen_action)}[/bold {color}]\n")
            
            return {
                "action": chosen_action,
                "action_index": action_index,
                "reasoning": decision.get("reasoning", "No reasoning provided"),
                "model": self.model,
                "raw_response": content  # Keep for debugging
            }
            
        except Exception as e:
            logger.error(f"Error getting move from {self.model}: {e}")
            # Return first legal action as fallback
            return {
                "action": legal_actions[0],
                "action_index": 0,
                "reasoning": f"Error occurred, defaulting to first legal action: {e}",
                "model": self.model
            }
    
    def _format_game_state(
        self,
        game_state: Dict,
        legal_actions: List[Dict],
        game_history: Optional[List[Dict]] = None
    ) -> str:
        """Format game state into a prompt for the LLM"""
        
        prompt_parts = []
        
        # Add comprehensive board layout explanation
        if game_state.get('turn', 0) <= 4:  # Initial placement phase
            prompt_parts.append("=== CATAN BOARD SPATIAL GUIDE ===")
            prompt_parts.append("\nThe board has 19 hexes arranged in a honeycomb pattern:")
            prompt_parts.append("- Center hex (0) is surrounded by 6 hexes (1-6)")
            prompt_parts.append("- Outer ring has 12 hexes (7-18)")
            prompt_parts.append("- Each hex has 6 vertices (nodes) and 6 edges")
            prompt_parts.append("")
            prompt_parts.append("NODE REFERENCE:")
            prompt_parts.append("- Node 0: Center of board (touches hexes 0,5,6)")
            prompt_parts.append("- Nodes 1-5: Inner ring around center hex")
            prompt_parts.append("- Nodes 6-23: Middle ring positions")
            prompt_parts.append("- Nodes 24-53: Coastal positions")
            prompt_parts.append("")
            prompt_parts.append("PORT LOCATIONS (2:1 specialized trading):")
            prompt_parts.append("- Nodes 52-53: SHEEP port (trade 2 sheep for 1 any)")
            prompt_parts.append("- Nodes 35-36: WOOD port")  
            prompt_parts.append("- Nodes 32-33: WHEAT port")
            prompt_parts.append("- Nodes 40-44: BRICK port")
            prompt_parts.append("- Nodes 28-29: ORE port")
            prompt_parts.append("- Other coastal pairs: 3:1 ports (trade 3 of same for 1 any)")
            prompt_parts.append("")
            prompt_parts.append("ADJACENCY PATTERNS:")
            prompt_parts.append("- Adjacent nodes have consecutive numbers along edges")
            prompt_parts.append("- E.g., node 0 connects to nodes 1,5,20")
            prompt_parts.append("- E.g., node 7 connects to nodes 6,8,24")
            prompt_parts.append("")
            prompt_parts.append("")
        
        # Current game state
        prompt_parts.append("=== CURRENT GAME STATE ===")
        prompt_parts.append(f"Turn: {game_state.get('turn', 0)}")
        prompt_parts.append(f"Current Player: {game_state.get('current_player', 'Unknown')}")
        
        # Player resources and scores
        if "players" in game_state:
            prompt_parts.append("\n=== PLAYER STATUS ===")
            for player_id, player_data in game_state["players"].items():
                prompt_parts.append(f"\nPlayer {player_id}:")
                prompt_parts.append(f"  Victory Points: {player_data.get('victory_points', 0)}")
                prompt_parts.append(f"  Resources: {player_data.get('resources', {})}")
                prompt_parts.append(f"  Development Cards: {player_data.get('dev_cards_count', 0)}")
                prompt_parts.append(f"  Settlements: {player_data.get('settlements', 0)}")
                prompt_parts.append(f"  Cities: {player_data.get('cities', 0)}")
                prompt_parts.append(f"  Roads Built: {player_data.get('roads', 0)}")
                prompt_parts.append(f"  Longest Road: {player_data.get('longest_road_length', 0)}")
        
        # Board state summary
        if "board" in game_state:
            prompt_parts.append("\n=== BOARD STATE ===")
            
            # Hex tiles
            hexes = game_state["board"].get("hexes", [])
            if hexes:
                prompt_parts.append("\nResource Hexes:")
                for hex_info in hexes[:19]:  # Standard Catan has 19 hexes
                    if hex_info["resource"] != "desert":
                        prompt_parts.append(f"  {hex_info['coordinate']}: {hex_info['resource']} (number: {hex_info['number']})")
                    else:
                        prompt_parts.append(f"  {hex_info['coordinate']}: desert")
            
            prompt_parts.append(f"\nRobber Location: {game_state['board'].get('robber_location', 'Unknown')}")
            
            # Add detailed hex information for initial placement
            if game_state.get('turn', 0) <= 4 and hexes:
                prompt_parts.append("\nKey Node-Hex Relationships:")
                # Show some important nodes and what they touch
                hex_by_coord = {h['cube_coord']: h for h in hexes if 'cube_coord' in h}
                # The hardcoded approach doesn't work because of board randomization
                # Instead, provide information for all buildable nodes dynamically
                # Nodes to show in initial placement (good starting positions)
                nodes_to_show = [0, 1, 2, 3, 4, 5, 7, 8, 9, 10, 11, 12, 13, 14, 15, 
                               16, 17, 18, 19, 20, 21, 22, 23, 30, 35, 37, 40, 45, 47, 50]
                
                # For each node, find what hexes it actually touches in THIS game
                # by checking all hexes and seeing which ones are adjacent
                node_hex_mapping = {}
                for node_id in nodes_to_show:
                    adjacent_hexes = []
                    # Check each hex to see if this node is adjacent to it
                    for hex_info in hexes:
                        cube_coord = hex_info.get('cube_coord', '')
                        # Use the hardcoded adjacency patterns from find_correct_node_hex_mapping.py
                        # These define the fixed topology of the Catan board
                        node_adjacencies = {
                            0: ['(0, 0, 0)', '(0, 1, -1)', '(1, 0, -1)'],
                            1: ['(0, 0, 0)', '(1, -1, 0)', '(1, 0, -1)'],
                            2: ['(0, 0, 0)', '(1, -1, 0)', '(0, -1, 1)'],
                            3: ['(0, 0, 0)', '(0, -1, 1)', '(-1, 0, 1)'],
                            4: ['(0, 0, 0)', '(-1, 0, 1)', '(-1, 1, 0)'],
                            5: ['(0, 0, 0)', '(-1, 1, 0)', '(0, 1, -1)'],
                            6: ['(1, -1, 0)', '(1, 0, -1)', '(2, -1, -1)'],
                            7: ['(1, -1, 0)', '(2, -2, 0)', '(2, -1, -1)'],
                            8: ['(1, -1, 0)', '(2, -2, 0)', '(1, -2, 1)'],
                            9: ['(1, -1, 0)', '(0, -1, 1)', '(1, -2, 1)'],
                            10: ['(0, -1, 1)', '(1, -2, 1)', '(0, -2, 2)'],
                            11: ['(0, -1, 1)', '(0, -2, 2)', '(-1, -1, 2)'],
                            12: ['(0, -1, 1)', '(-1, 0, 1)', '(-1, -1, 2)'],
                            13: ['(-1, 0, 1)', '(-1, -1, 2)', '(-2, 0, 2)'],
                            14: ['(-1, 0, 1)', '(-2, 0, 2)', '(-2, 1, 1)'],
                            15: ['(-1, 0, 1)', '(-1, 1, 0)', '(-2, 1, 1)'],
                            16: ['(-1, 1, 0)', '(0, 1, -1)', '(-1, 2, -1)'],
                            17: ['(-1, 1, 0)', '(-2, 1, 1)', '(-2, 2, 0)'],
                            18: ['(-1, 1, 0)', '(-2, 2, 0)', '(-1, 2, -1)'],
                            19: ['(0, 1, -1)', '(0, 2, -2)', '(1, 1, -2)'],
                            20: ['(0, 1, -1)', '(1, 0, -1)', '(1, 1, -2)'],
                            21: ['(0, 1, -1)', '(-1, 2, -1)', '(0, 2, -2)'],
                            22: ['(1, 0, -1)', '(1, 1, -2)', '(2, 0, -2)'],
                            23: ['(1, 0, -1)', '(2, 0, -2)', '(2, -1, -1)'],
                            30: ['(1, -2, 1)', '(0, -2, 2)'],
                            35: ['(-1, -1, 2)', '(-2, 0, 2)'],
                            37: ['(-2, 0, 2)', '(-2, 1, 1)'],
                            40: ['(-2, 2, 0)', '(-1, 2, -1)'],
                            45: ['(0, 2, -2)', '(1, 1, -2)'],
                            47: ['(1, 1, -2)', '(2, 0, -2)'],
                            50: ['(2, 0, -2)', '(2, -1, -1)']
                        }
                        
                        if node_id in node_adjacencies and cube_coord in node_adjacencies[node_id]:
                            adjacent_hexes.append(hex_info)
                    
                    if adjacent_hexes:
                        node_hex_mapping[node_id] = adjacent_hexes
                
                # Now format the node information with actual resources
                for node_id, adjacent_hexes in sorted(node_hex_mapping.items()):
                    resources = []
                    for hex_info in adjacent_hexes:
                        if hex_info['resource'] != 'desert':
                            resources.append(f"{hex_info['resource']}-{hex_info.get('number', '?')}")
                        else:
                            resources.append("desert")
                    if resources:
                        prompt_parts.append(f"  Node {node_id}: adjacent to {', '.join(resources)}")
            
            # Current buildings
            settlements = game_state["board"].get("settlements", [])
            cities = game_state["board"].get("cities", [])
            roads = game_state["board"].get("roads", [])
            
            if settlements:
                prompt_parts.append(f"\nSettlements on board: {len(settlements)}")
                for s in settlements[:5]:  # Show first 5
                    prompt_parts.append(f"  Node {s['node']}: {s['owner']}")
                if len(settlements) > 5:
                    prompt_parts.append(f"  ... and {len(settlements) - 5} more")
            
            if cities:
                prompt_parts.append(f"\nCities on board: {len(cities)}")
                for c in cities[:3]:  # Show first 3
                    prompt_parts.append(f"  Node {c['node']}: {c['owner']}")
            
            if roads:
                prompt_parts.append(f"\nTotal roads on board: {len(roads)}")
        
        # Recent history
        if game_history and len(game_history) > 0:
            prompt_parts.append("\n=== RECENT ACTIONS ===")
            for action in game_history[-5:]:  # Last 5 actions
                prompt_parts.append(f"- {action.get('player', 'Unknown')}: {action.get('action_type', 'Unknown')}")
        
        # Legal actions
        prompt_parts.append("\n=== LEGAL ACTIONS ===")
        prompt_parts.append(f"You have {len(legal_actions)} legal actions available:")
        for i, action in enumerate(legal_actions):
            action_str = self._format_action(action)
            prompt_parts.append(f"{i}: {action_str}")
        
        prompt_parts.append("\nChoose the best action by its index number.")
        
        return "\n".join(prompt_parts)
    
    def _format_action(self, action: Dict) -> str:
        """Format a single action for display"""
        action_type = action.get("type", "Unknown")
        
        # Debug log to see what we're getting
        if action_type == "BUILD_ROAD" and "edge" not in action:
            logger.debug(f"BUILD_ROAD action missing edge key. Full action: {action}")
        
        # Handle Catanatron action types
        if action_type == "BUILD_SETTLEMENT":
            node = action.get('node', 'Unknown')
            # Add hints for key positions during initial placement
            hint = ""
            # Removed hints - models should figure out what's good themselves
            return f"Build settlement at node {node}{hint}"
        elif action_type == "BUILD_ROAD":
            edge = action.get('edge', None)
            
            # Try different keys where edge might be stored
            if not edge:
                edge = action.get('value', None) or action.get('params', None)
            
            # Fallback: try to extract from raw string if edge not found
            if not edge and 'raw' in action:
                raw = action['raw']
                # Extract edge from "Action(COLOR BUILD_ROAD (n1, n2))"
                if 'BUILD_ROAD' in raw and '(' in raw and ')' in raw:
                    try:
                        edge_part = raw.split('BUILD_ROAD')[1].strip()
                        if edge_part.startswith('(') and ')' in edge_part:
                            edge = edge_part[:edge_part.index(')')+1]
                    except:
                        pass
            
            if not edge:
                edge = 'Unknown'
                # Log what keys we have for debugging
                logger.warning(f"Could not find edge in BUILD_ROAD action. Keys: {list(action.keys())}, Action: {action}")
            
            return f"Build road on edge {edge}"
        elif action_type == "BUILD_CITY":
            return f"Upgrade settlement to city at node {action.get('node', 'Unknown')}"
        elif action_type == "BUY_DEVELOPMENT_CARD":
            return "Buy development card"
        elif action_type in ["PLAY_KNIGHT", "PLAY_KNIGHT_CARD"]:
            return "Play knight card"
        elif action_type == "MOVE_ROBBER":
            coordinate = action.get('coordinate', action.get('params', 'Unknown'))
            steal_from = action.get('steal_from', '')
            if steal_from:
                return f"Move robber to {coordinate} and steal from {steal_from}"
            else:
                return f"Move robber to {coordinate}"
        elif action_type in ["TRADE", "MARITIME_TRADE"]:
            params = action.get('params', '')
            return f"Trade resources {params}" if params else "Trade resources"
        elif action_type == "END_TURN":
            return "End turn"
        elif action_type == "ROLL":
            return "Roll dice"
        elif action_type == "DISCARD":
            return "Discard cards"
        elif action_type == "PLAY_MONOPOLY":
            return "Play monopoly card"
        elif action_type == "PLAY_YEAR_OF_PLENTY":
            return "Play year of plenty card"
        elif action_type == "PLAY_ROAD_BUILDING":
            return "Play road building card"
        else:
            # Include raw action for unknown types
            return f"{action_type} ({action.get('raw', '')})"

class LLMPlayer:
    """Wrapper to make LLMClient compatible with Catanatron's player interface"""
    
    def __init__(self, color, model: str):
        self.color = color
        self.model = model
        self.llm_client = LLMClient(model)
        self.name = f"LLM-{model.split('/')[-1]}"
    
    def get_move(self, game_state, legal_actions, game_history=None):
        """Get move with reasoning for the evaluation system"""
        # This is already in the correct format
        return self.llm_client.get_move(game_state, legal_actions, game_history)
    
    def decide(self, game, playable_actions):
        """Synchronous decide method for Catanatron compatibility"""
        # Convert Catanatron game state to our format
        game_state = self._convert_game_state(game)
        legal_actions = self._convert_actions(playable_actions)
        
        # Get move from LLM
        decision = self.llm_client.get_move(game_state, legal_actions)
        
        # Return the original Catanatron action
        return playable_actions[decision["action_index"]]
    
    def _convert_game_state(self, game):
        """Convert Catanatron game state to our format"""
        state = game.state
        
        # Debug logging to check road values
        if state.num_turns <= 5:  # Only log early game
            for i, color in enumerate(state.colors):
                roads_built = 15 - state.player_state[f"P{i}_ROADS_AVAILABLE"]
                longest_road = state.player_state[f"P{i}_LONGEST_ROAD_LENGTH"]
                logger.debug(f"Turn {state.num_turns} - {color.value}: Roads built={roads_built}, Longest road={longest_road}")
        
        # Extract player information
        players = {}
        for i, color in enumerate(state.colors):
            player_state = {}
            
            # Resources - these keys always exist
            player_state["resources"] = {
                "wood": state.player_state[f"P{i}_WOOD_IN_HAND"],
                "brick": state.player_state[f"P{i}_BRICK_IN_HAND"],
                "sheep": state.player_state[f"P{i}_SHEEP_IN_HAND"],
                "wheat": state.player_state[f"P{i}_WHEAT_IN_HAND"],
                "ore": state.player_state[f"P{i}_ORE_IN_HAND"]
            }
            
            # Development cards - full breakdown
            player_state["dev_cards"] = {
                "knight": state.player_state[f"P{i}_KNIGHT_IN_HAND"],
                "victory_point": state.player_state[f"P{i}_VICTORY_POINT_IN_HAND"],
                "road_building": state.player_state[f"P{i}_ROAD_BUILDING_IN_HAND"],
                "year_of_plenty": state.player_state[f"P{i}_YEAR_OF_PLENTY_IN_HAND"],
                "monopoly": state.player_state[f"P{i}_MONOPOLY_IN_HAND"]
            }
            player_state["dev_cards_count"] = sum(player_state["dev_cards"].values())
            
            # Played development cards
            player_state["played_knight"] = state.player_state[f"P{i}_PLAYED_KNIGHT"]
            player_state["played_road_building"] = state.player_state[f"P{i}_PLAYED_ROAD_BUILDING"]
            player_state["played_year_of_plenty"] = state.player_state[f"P{i}_PLAYED_YEAR_OF_PLENTY"]
            player_state["played_monopoly"] = state.player_state[f"P{i}_PLAYED_MONOPOLY"]
            
            # Buildings - count actual buildings on the board for this player
            player_state["settlements"] = 0
            player_state["cities"] = 0
            player_state["roads"] = 0
            
            # Count settlements and cities from buildings_by_color
            if hasattr(state, 'buildings_by_color') and color in state.buildings_by_color:
                buildings = state.buildings_by_color[color]
                player_state["settlements"] = len(buildings.get(SETTLEMENT, []))
                player_state["cities"] = len(buildings.get(CITY, []))
            
            # Count roads from board.roads
            # Note: Catanatron might store roads as both (A,B) and (B,A), so we need to deduplicate
            if hasattr(state, 'board') and hasattr(state.board, 'roads'):
                player_roads = set()
                for edge, road_color in state.board.roads.items():
                    if road_color == color:
                        # Normalize edge to avoid double counting (always use smaller node first)
                        if isinstance(edge, tuple) and len(edge) == 2:
                            normalized_edge = tuple(sorted(edge))
                            player_roads.add(normalized_edge)
                        else:
                            player_roads.add(edge)
                player_state["roads"] = len(player_roads)
            
            # Victory points and special achievements
            player_state["victory_points"] = state.player_state[f"P{i}_VICTORY_POINTS"]
            player_state["actual_victory_points"] = state.player_state[f"P{i}_ACTUAL_VICTORY_POINTS"]
            player_state["has_longest_road"] = state.player_state[f"P{i}_HAS_ROAD"]
            player_state["has_largest_army"] = state.player_state[f"P{i}_HAS_ARMY"]
            player_state["longest_road_length"] = state.player_state[f"P{i}_LONGEST_ROAD_LENGTH"]
            
            # Turn state
            player_state["has_rolled"] = state.player_state[f"P{i}_HAS_ROLLED"]
            player_state["has_played_dev_card"] = state.player_state[f"P{i}_HAS_PLAYED_DEVELOPMENT_CARD_IN_TURN"]
            
            players[color.value] = player_state
        
        # Extract board information
        board_info = {
            "hexes": self._get_hex_info(state),
            "robber_location": self._get_robber_location(state),
            "ports": self._get_port_info(state),
            "settlements": self._get_settlement_info(state),
            "cities": self._get_city_info(state),
            "roads": self._get_road_info(state)
        }
        
        return {
            "turn": state.num_turns,
            "current_player": state.colors[state.current_player_index].value,
            "current_player_index": state.current_player_index,
            "players": players,
            "board": board_info,
            "is_initial_build_phase": state.is_initial_build_phase,
            "resource_bank": state.resource_freqdeck if hasattr(state, 'resource_freqdeck') else None
        }
    
    def _get_hex_info(self, state):
        """Get information about hex tiles"""
        hex_info = []
        # Catanatron uses a coordinate system for hexes
        if hasattr(state.board, 'map') and hasattr(state.board.map, 'land_tiles'):
            for coord, tile in state.board.map.land_tiles.items():
                resource = tile.resource
                # Handle resource - it might be a string or enum
                if hasattr(resource, 'value'):
                    resource_str = resource.value
                elif resource:
                    resource_str = str(resource)
                else:
                    resource_str = "desert"
                
                hex_data = {
                    "coordinate": str(coord),
                    "resource": resource_str,
                    "number": tile.number if hasattr(tile, 'number') else None
                }
                hex_info.append(hex_data)
        return hex_info
    
    def _get_robber_location(self, state):
        """Get current robber location"""
        # Return the coordinate of the hex with the robber
        if hasattr(state.board, 'robber_coordinate'):
            return str(state.board.robber_coordinate)
        return "Unknown"
    
    def _get_port_info(self, state):
        """Get information about ports"""
        ports = []
        if hasattr(state.board, 'map') and hasattr(state.board.map, 'port_edges'):
            for edge, port_type in state.board.map.port_edges.items():
                ports.append({
                    "edge": str(edge),
                    "type": port_type.value if hasattr(port_type, 'value') else str(port_type)
                })
        return ports
    
    def _get_settlement_info(self, state):
        """Get all settlements on the board"""
        settlements = []
        if hasattr(state, 'buildings_by_color'):
            for color, buildings in state.buildings_by_color.items():
                # buildings is a defaultdict(list)
                settlement_nodes = buildings.get(SETTLEMENT, []) if hasattr(buildings, 'get') else []
                for node_id in settlement_nodes:
                    settlements.append({
                        "node": node_id,
                        "owner": color.value
                    })
        return settlements
    
    def _get_city_info(self, state):
        """Get all cities on the board"""
        cities = []
        if hasattr(state, 'buildings_by_color'):
            for color, buildings in state.buildings_by_color.items():
                # buildings is a defaultdict(list)
                city_nodes = buildings.get(CITY, []) if hasattr(buildings, 'get') else []
                for node_id in city_nodes:
                    cities.append({
                        "node": node_id,
                        "owner": color.value
                    })
        return cities
    
    def _get_road_info(self, state):
        """Get all roads on the board"""
        roads = []
        if hasattr(state, 'board') and hasattr(state.board, 'roads'):
            # Roads are stored in board.roads as {edge: color}
            for edge, color in state.board.roads.items():
                roads.append({
                    "edge": str(edge),
                    "owner": color.value
                })
        return roads
    
    def _convert_actions(self, playable_actions):
        """Convert Catanatron actions to our format"""
        converted = []
        for action in playable_actions:
            # Actions come as Action objects with string representation
            action_str = str(action)
            action_data = {"raw": action_str}
            
            # Parse the action string format: "Action(COLOR ACTION_TYPE params)"
            # Example: "Action(RED BUILD_SETTLEMENT 0)"
            if action_str.startswith("Action(") and action_str.endswith(")"):
                content = action_str[7:-1]  # Remove "Action(" and ")"
                parts = content.split(" ", 2)  # Split into at most 3 parts
                
                if len(parts) >= 2:
                    color = parts[0]
                    action_type = parts[1]
                    action_data["color"] = color
                    action_data["type"] = action_type
                    
                    # Parse parameters based on action type
                    if len(parts) > 2:
                        params = parts[2]
                        
                        if action_type == "BUILD_SETTLEMENT":
                            action_data["node"] = int(params) if params.isdigit() else params
                        elif action_type == "BUILD_ROAD":
                            # Road format: "(node1, node2)"
                            action_data["edge"] = params
                            # Debug: log what we're getting
                            logger.debug(f"BUILD_ROAD action: raw={action_str}, edge={params}")
                        elif action_type == "BUILD_CITY":
                            action_data["node"] = int(params) if params.isdigit() else params
                        elif action_type == "MOVE_ROBBER":
                            # Parse robber move parameters
                            action_data["params"] = params
                        elif action_type in ["MARITIME_TRADE", "TRADE"]:
                            action_data["params"] = params
                else:
                    action_data["type"] = content
            else:
                # Fallback for other action formats
                action_data["type"] = action_str
            
            converted.append(action_data)
        
        return converted