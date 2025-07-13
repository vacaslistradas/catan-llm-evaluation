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
            prompt_parts.append(f"Robber Location: {game_state['board'].get('robber_hex', 'Unknown')}")
            # Add more board details as needed
        
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
        
        if action_type == "BUILD_SETTLEMENT":
            return f"Build settlement at {action.get('location', 'Unknown')}"
        elif action_type == "BUILD_ROAD":
            return f"Build road from {action.get('from', 'Unknown')} to {action.get('to', 'Unknown')}"
        elif action_type == "BUILD_CITY":
            return f"Upgrade settlement to city at {action.get('location', 'Unknown')}"
        elif action_type == "BUY_DEVELOPMENT_CARD":
            return "Buy development card"
        elif action_type == "PLAY_KNIGHT":
            return f"Play knight card, move robber to {action.get('robber_location', 'Unknown')}"
        elif action_type == "TRADE":
            return f"Trade {action.get('give', {})} for {action.get('receive', {})}"
        elif action_type == "END_TURN":
            return "End turn"
        else:
            return f"{action_type}: {json.dumps(action)}"

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
        # This will need to be implemented based on Catanatron's actual API
        # For now, return a placeholder
        return {
            "turn": game.state.num_turns,
            "current_player": self.color.value,
            "players": {},  # To be implemented
            "board": {}     # To be implemented
        }
    
    def _convert_actions(self, playable_actions):
        """Convert Catanatron actions to our format"""
        # This will need to be implemented based on Catanatron's actual API
        return [{"type": str(action), "raw": action} for action in playable_actions]