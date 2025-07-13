import asyncio
import json
import re
from typing import List, Dict, Optional, Union
import aiohttp
from openai import AsyncOpenAI
from loguru import logger
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
        if "BUILD_SETTLEMENT" in action_type:
            return f"Build settlement at node {action.get('node', 'Unknown')}"
        elif "BUILD_ROAD" in action_type:
            return f"Build road on edge {action.get('edge', 'Unknown')}"
        elif "BUILD_CITY" in action_type:
            return f"Upgrade settlement to city at node {action.get('node', 'Unknown')}"
        elif "BUY_DEVELOPMENT_CARD" in action_type:
            return "Buy development card"
        elif "PLAY_KNIGHT" in action_type or "PLAY_KNIGHT_CARD" in action_type:
            return "Play knight card"
        elif "MOVE_ROBBER" in action_type:
            hex_coord = action.get('hex_coordinate', 'Unknown')
            steal_from = action.get('steal_from', '')
            if steal_from:
                return f"Move robber to hex {hex_coord} and steal from {steal_from}"
            return f"Move robber to hex {hex_coord}"
        elif "TRADE" in action_type or "MARITIME_TRADE" in action_type:
            return f"Trade resources"
        elif "END_TURN" in action_type:
            return "End turn"
        elif "ROLL" in action_type:
            return "Roll dice"
        elif "DISCARD" in action_type:
            return "Discard cards"
        else:
            # Fallback for unknown action types
            return f"{action_type}"

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
            
            # Resources
            player_state["resources"] = {
                "wood": state.player_state[f"P{i}_WOOD_IN_HAND"],
                "brick": state.player_state[f"P{i}_BRICK_IN_HAND"],
                "sheep": state.player_state[f"P{i}_SHEEP_IN_HAND"],
                "wheat": state.player_state[f"P{i}_WHEAT_IN_HAND"],
                "ore": state.player_state[f"P{i}_ORE_IN_HAND"]
            }
            
            # Development cards
            player_state["dev_cards_count"] = state.player_state[f"P{i}_DEVELOPMENT_CARDS_IN_HAND"]
            player_state["knights_played"] = state.player_state[f"P{i}_KNIGHTS_PLAYED"]
            
            # Buildings
            player_state["settlements"] = len(state.buildings_by_color[color]["SETTLEMENT"])
            player_state["cities"] = len(state.buildings_by_color[color]["CITY"])
            player_state["roads"] = len(state.roads_by_color[color])
            
            # Victory points and special cards
            player_state["victory_points"] = state.player_state[f"P{i}_VICTORY_POINTS"]
            player_state["has_longest_road"] = state.player_state[f"P{i}_HAS_LONGEST_ROAD"]
            player_state["has_largest_army"] = state.player_state[f"P{i}_HAS_LARGEST_ARMY"]
            
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
            "current_player": self.color.value,
            "players": players,
            "board": board_info,
            "dice_rolled": getattr(state, "last_dice_roll", None)
        }
    
    def _get_hex_info(self, state):
        """Get information about hex tiles"""
        hex_info = []
        # Catanatron uses a coordinate system for hexes
        # This is a simplified representation - you might need to adjust based on actual API
        for coord, tile in state.board.map.land_tiles.items():
            hex_data = {
                "coordinate": str(coord),
                "resource": tile.resource.value if tile.resource else "desert",
                "number": tile.number if hasattr(tile, 'number') else None
            }
            hex_info.append(hex_data)
        return hex_info
    
    def _get_robber_location(self, state):
        """Get current robber location"""
        # Return the coordinate of the hex with the robber
        return str(state.board.robber_coordinate)
    
    def _get_port_info(self, state):
        """Get information about ports"""
        ports = []
        for edge, port_type in state.board.map.port_edges.items():
            ports.append({
                "edge": str(edge),
                "type": port_type.value if hasattr(port_type, 'value') else str(port_type)
            })
        return ports
    
    def _get_settlement_info(self, state):
        """Get all settlements on the board"""
        settlements = []
        for color, buildings in state.buildings_by_color.items():
            for node_id in buildings.get("SETTLEMENT", []):
                settlements.append({
                    "node": node_id,
                    "owner": color.value
                })
        return settlements
    
    def _get_city_info(self, state):
        """Get all cities on the board"""
        cities = []
        for color, buildings in state.buildings_by_color.items():
            for node_id in buildings.get("CITY", []):
                cities.append({
                    "node": node_id,
                    "owner": color.value
                })
        return cities
    
    def _get_road_info(self, state):
        """Get all roads on the board"""
        roads = []
        for color, road_edges in state.roads_by_color.items():
            for edge in road_edges:
                roads.append({
                    "edge": str(edge),
                    "owner": color.value
                })
        return roads
    
    def _convert_actions(self, playable_actions):
        """Convert Catanatron actions to our format"""
        converted = []
        for action in playable_actions:
            # Catanatron actions are typically tuples (ActionType, *args)
            if isinstance(action, tuple) and len(action) > 0:
                action_type = action[0]
                action_data = {
                    "type": action_type.value if hasattr(action_type, 'value') else str(action_type),
                    "raw": str(action)
                }
                
                # Add specific parameters based on action type
                if len(action) > 1:
                    if "BUILD_SETTLEMENT" in str(action_type):
                        action_data["node"] = action[1]
                    elif "BUILD_ROAD" in str(action_type):
                        action_data["edge"] = str(action[1])
                    elif "BUILD_CITY" in str(action_type):
                        action_data["node"] = action[1]
                    elif "MOVE_ROBBER" in str(action_type):
                        action_data["hex_coordinate"] = str(action[1])
                        if len(action) > 2:
                            action_data["steal_from"] = action[2].value if hasattr(action[2], 'value') else str(action[2])
                
                converted.append(action_data)
            else:
                converted.append({"type": str(action), "raw": str(action)})
        
        return converted