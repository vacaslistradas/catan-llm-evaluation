import asyncio
import json
import re
from typing import List, Dict, Optional, Union
import aiohttp
from openai import AsyncOpenAI
from loguru import logger
from catanatron.models.enums import SETTLEMENT, CITY
from .config import Config

class LLMClient:
    """Unified client for interacting with LLMs through OpenRouter"""
    
    def __init__(self, model: str, api_key: Optional[str] = None):
        self.model = model
        self.api_key = api_key or Config.OPENROUTER_API_KEY
        
        # Initialize async OpenAI client
        self.client = AsyncOpenAI(
            base_url=Config.OPENROUTER_BASE_URL,
            api_key=self.api_key
        )
        
        logger.info(f"Initialized LLM client for model: {model}")
    
    async def get_move(
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
        
        try:
            response = await self.client.chat.completions.create(
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
            
            # Try to extract JSON from the response
            # Sometimes models add extra text despite instructions
            try:
                # First try direct parsing
                decision = json.loads(content)
            except json.JSONDecodeError:
                # Try to find JSON object in the response
                import re
                json_match = re.search(r'\{[^{}]*"action_index"[^{}]*\}', content)
                if json_match:
                    try:
                        decision = json.loads(json_match.group())
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse JSON from {self.model}, using fallback")
                        decision = {"action_index": 0, "reasoning": "JSON parsing failed"}
                else:
                    # Last resort - try to find a number
                    number_match = re.search(r'\b(\d+)\b', content)
                    if number_match:
                        action_index = int(number_match.group(1))
                        decision = {"action_index": action_index, "reasoning": "Extracted number from response"}
                    else:
                        decision = {"action_index": 0, "reasoning": "Could not parse response"}
            
            # Validate action index
            action_index = decision.get("action_index", 0)
            if not isinstance(action_index, int) or not 0 <= action_index < len(legal_actions):
                logger.warning(f"Invalid action index {action_index}, defaulting to 0")
                action_index = 0
            
            return {
                "action": legal_actions[action_index],
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
                prompt_parts.append(f"  Settlements: {player_data.get('settlement_count', 0)}")
                prompt_parts.append(f"  Cities: {player_data.get('city_count', 0)}")
                prompt_parts.append(f"  Road Length: {player_data.get('road_length', 0)}")
        
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
        for i, action in enumerate(legal_actions):
            action_str = self._format_action(action)
            prompt_parts.append(f"{i}: {action_str}")
        
        prompt_parts.append("\nChoose the best action by its index number.")
        
        return "\n".join(prompt_parts)
    
    def _format_action(self, action: Dict) -> str:
        """Format a single action for display"""
        action_type = action.get("type", "Unknown")
        
        # Handle Catanatron action types
        if action_type == "BUILD_SETTLEMENT":
            return f"Build settlement at node {action.get('node', 'Unknown')}"
        elif action_type == "BUILD_ROAD":
            return f"Build road on edge {action.get('edge', 'Unknown')}"
        elif action_type == "BUILD_CITY":
            return f"Upgrade settlement to city at node {action.get('node', 'Unknown')}"
        elif action_type == "BUY_DEVELOPMENT_CARD":
            return "Buy development card"
        elif action_type in ["PLAY_KNIGHT", "PLAY_KNIGHT_CARD"]:
            return "Play knight card"
        elif action_type == "MOVE_ROBBER":
            params = action.get('params', 'Unknown')
            return f"Move robber {params}"
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
    
    async def decide_async(self, game, playable_actions):
        """Async version of decide method for LLM calls"""
        # Convert Catanatron game state to our format
        game_state = self._convert_game_state(game)
        legal_actions = self._convert_actions(playable_actions)
        
        # Get move from LLM
        decision = await self.llm_client.get_move(game_state, legal_actions)
        
        # Return the original Catanatron action
        return playable_actions[decision["action_index"]]
    
    def decide(self, game, playable_actions):
        """Synchronous wrapper for Catanatron compatibility"""
        # Run async method in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.decide_async(game, playable_actions))
        finally:
            loop.close()
    
    def _convert_game_state(self, game):
        """Convert Catanatron game state to our format"""
        state = game.state
        
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
            
            # Buildings - calculate from available pieces
            player_state["settlements"] = 5 - state.player_state[f"P{i}_SETTLEMENTS_AVAILABLE"]
            player_state["cities"] = 4 - state.player_state[f"P{i}_CITIES_AVAILABLE"]
            player_state["roads"] = 15 - state.player_state[f"P{i}_ROADS_AVAILABLE"]
            
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
                            if params.startswith("(") and params.endswith(")"):
                                action_data["edge"] = params
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