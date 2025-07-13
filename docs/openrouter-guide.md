# OpenRouter API Complete Guide

## Table of Contents
1. [Introduction](#introduction)
2. [Getting Started](#getting-started)
3. [Authentication](#authentication)
4. [Basic Usage](#basic-usage)
5. [Advanced Features](#advanced-features)
6. [Python Implementation Examples](#python-implementation-examples)
7. [Best Practices](#best-practices)
8. [Pricing and Models](#pricing-and-models)
9. [Troubleshooting](#troubleshooting)

## Introduction

### What is OpenRouter?

OpenRouter is a unified API gateway that provides access to multiple AI language models through a single interface. It acts as a middleware layer between your application and various LLM providers, offering:

- **Unified Interface**: Access models from OpenAI, Anthropic, Google, Meta, and others through one API
- **OpenAI Compatibility**: Drop-in replacement for OpenAI API
- **Provider Routing**: Automatic fallback between providers for resilience
- **Cost Optimization**: Choose models based on performance and price

### Key Benefits

1. **No Vendor Lock-in**: Switch between models without code changes
2. **Simplified Integration**: One API key for all providers
3. **Reliability**: Automatic provider failover
4. **Transparency**: Clear pricing and usage tracking

## Getting Started

### Step 1: Create an Account

1. Visit [OpenRouter.ai](https://openrouter.ai)
2. Sign up for an account
3. Add credits on the Credits page

### Step 2: Get Your API Key

1. Navigate to the API Keys section
2. Create a new API key
3. Store it securely (never commit to version control)

### Step 3: Base Configuration

- **Base URL**: `https://openrouter.ai/api/v1`
- **Main Endpoint**: `/chat/completions`
- **Models Endpoint**: `/models`

## Authentication

### Bearer Token Authentication

All API requests require Bearer token authentication:

```python
headers = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "Content-Type": "application/json"
}
```

### Optional Headers

```python
headers = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "Content-Type": "application/json",
    "HTTP-Referer": "https://your-app.com",  # For rankings
    "X-Title": "Your App Name"               # For identification
}
```

## Basic Usage

### Using OpenAI SDK (Recommended)

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key="your-api-key-here"
)

response = client.chat.completions.create(
    model="anthropic/claude-3-haiku",
    messages=[
        {"role": "system", "content": "You are a helpful assistant"},
        {"role": "user", "content": "Hello, how are you?"}
    ]
)

print(response.choices[0].message.content)
```

### Using Requests Library

```python
import requests
import json

url = "https://openrouter.ai/api/v1/chat/completions"
headers = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "Content-Type": "application/json"
}

data = {
    "model": "meta-llama/llama-3.1-8b-instruct",
    "messages": [
        {"role": "user", "content": "Explain quantum computing"}
    ],
    "temperature": 0.7,
    "max_tokens": 150
}

response = requests.post(url, headers=headers, json=data)
print(response.json())
```

## Advanced Features

### 1. Streaming Responses

Enable real-time token streaming with Server-Sent Events (SSE):

```python
import requests
import json

def stream_response(prompt):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "openai/gpt-3.5-turbo",
        "messages": [{"role": "user", "content": prompt}],
        "stream": True
    }
    
    response = requests.post(url, headers=headers, json=data, stream=True)
    
    for line in response.iter_lines():
        if line:
            line = line.decode('utf-8')
            if line.startswith('data: '):
                if line.strip() == 'data: [DONE]':
                    break
                try:
                    json_data = json.loads(line[6:])
                    if 'choices' in json_data:
                        content = json_data['choices'][0].get('delta', {}).get('content', '')
                        print(content, end='', flush=True)
                except json.JSONDecodeError:
                    pass
```

### 2. Provider Routing

Control which providers to use and in what order:

```python
data = {
    "model": "mistralai/mixtral-8x7b-instruct",
    "messages": [{"role": "user", "content": "Hello"}],
    "provider": {
        "order": ["together", "deepinfra"],  # Prioritize providers
        "require_parameters": True,          # Require specific params
        "data_collection": "deny"            # Privacy setting
    }
}
```

### 3. Partial Response Completion

Guide model responses by including an assistant message:

```python
messages = [
    {"role": "user", "content": "List three benefits of exercise"},
    {"role": "assistant", "content": "Here are three benefits of exercise:\n1."}
]
```

### 4. Response Format Control

For supported models, enforce structured output:

```python
data = {
    "model": "openai/gpt-4",
    "messages": [{"role": "user", "content": "List 3 colors"}],
    "response_format": {"type": "json_object"}
}
```

### 5. Cost Tracking

Retrieve generation stats after completion:

```python
# After making a request, use the returned ID
generation_id = response.json()["id"]

# Query generation stats
stats_url = f"https://openrouter.ai/api/v1/generation/{generation_id}"
stats_response = requests.get(stats_url, headers=headers)
print(stats_response.json())  # Contains token counts and costs
```

## Python Implementation Examples

### Complete Example with Error Handling

```python
import os
import requests
import json
from typing import List, Dict, Optional

class OpenRouterClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("API key required")
        
        self.base_url = "https://openrouter.ai/api/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "anthropic/claude-3-haiku",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False
    ) -> Dict:
        """Send chat completion request"""
        url = f"{self.base_url}/chat/completions"
        
        data = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": stream
        }
        
        if max_tokens:
            data["max_tokens"] = max_tokens
        
        try:
            response = requests.post(url, headers=self.headers, json=data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            return None
    
    def list_models(self) -> List[Dict]:
        """Get available models"""
        url = f"{self.base_url}/models"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()["data"]
        except requests.exceptions.RequestException as e:
            print(f"Failed to fetch models: {e}")
            return []

# Usage example
if __name__ == "__main__":
    client = OpenRouterClient()
    
    # Simple chat
    response = client.chat_completion(
        messages=[{"role": "user", "content": "Hello!"}],
        model="meta-llama/llama-3.1-8b-instruct"
    )
    
    if response:
        print(response["choices"][0]["message"]["content"])
```

### Async Implementation with aiohttp

```python
import asyncio
import aiohttp
import os
from typing import List, Dict

class AsyncOpenRouterClient:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
        self.base_url = "https://openrouter.ai/api/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "openai/gpt-3.5-turbo"
    ) -> Dict:
        url = f"{self.base_url}/chat/completions"
        data = {
            "model": model,
            "messages": messages
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=self.headers, json=data) as response:
                return await response.json()

# Usage
async def main():
    client = AsyncOpenRouterClient()
    response = await client.chat_completion(
        messages=[{"role": "user", "content": "What is async programming?"}]
    )
    print(response["choices"][0]["message"]["content"])

asyncio.run(main())
```

## Best Practices

### 1. Environment Variables

```python
# .env file
OPENROUTER_API_KEY=your-key-here

# Python code
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.environ.get("OPENROUTER_API_KEY")
```

### 2. Rate Limiting

Implement exponential backoff for rate limits:

```python
import time
from typing import Callable

def retry_with_backoff(func: Callable, max_retries: int = 3):
    for attempt in range(max_retries):
        try:
            return func()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:  # Rate limited
                wait_time = 2 ** attempt
                print(f"Rate limited. Waiting {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise
    raise Exception("Max retries exceeded")
```

### 3. Session Management

Use sessions for multiple requests:

```python
class OpenRouterSession:
    def __init__(self, api_key: str):
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        })
    
    def __enter__(self):
        return self.session
    
    def __exit__(self, *args):
        self.session.close()

# Usage
with OpenRouterSession(api_key) as session:
    response = session.post(url, json=data)
```

## Pricing and Models

### Pricing Structure

- **Pay-per-use**: Credits deducted based on token usage
- **Different rates**: Input and output tokens priced separately
- **Model variety**: Prices vary significantly between models

### Free Tier Limits

- With 10+ credits purchased: 1000 requests/day for free models
- Otherwise: 50 requests/day for free models

### Popular Models (Examples)

```python
# Budget-friendly options
budget_models = [
    "meta-llama/llama-3.1-8b-instruct",
    "mistralai/mistral-7b-instruct"
]

# High-performance options
premium_models = [
    "anthropic/claude-3-opus",
    "openai/gpt-4",
    "google/gemini-pro"
]

# Balanced options
balanced_models = [
    "anthropic/claude-3-haiku",
    "openai/gpt-3.5-turbo"
]
```

### Cost Optimization

```python
# Use provider routing to optimize costs
data = {
    "model": "openai/gpt-3.5-turbo",
    "messages": messages,
    "provider": {
        "order": [":floor"],  # Use cheapest provider
        "allow_fallbacks": True
    }
}
```

## Troubleshooting

### Common Issues and Solutions

#### 1. Authentication Errors
```python
# Issue: 401 Unauthorized
# Solution: Check API key
if response.status_code == 401:
    print("Invalid API key. Check your credentials.")
```

#### 2. Model Not Found
```python
# Issue: Model not available
# Solution: Check available models
models = client.list_models()
model_ids = [m["id"] for m in models]
if desired_model not in model_ids:
    print(f"Model {desired_model} not available")
```

#### 3. Rate Limiting
```python
# Issue: 429 Too Many Requests
# Solution: Implement backoff strategy
if response.status_code == 429:
    retry_after = int(response.headers.get("Retry-After", 60))
    time.sleep(retry_after)
```

#### 4. Timeout Issues
```python
# Solution: Increase timeout
response = requests.post(
    url,
    headers=headers,
    json=data,
    timeout=120  # 2 minutes
)
```

### Debug Mode

Enable verbose logging:

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def make_request(url, data):
    logger.debug(f"Request URL: {url}")
    logger.debug(f"Request data: {json.dumps(data, indent=2)}")
    
    response = requests.post(url, headers=headers, json=data)
    
    logger.debug(f"Response status: {response.status_code}")
    logger.debug(f"Response: {response.text[:200]}...")
    
    return response
```

## Conclusion

OpenRouter provides a powerful, flexible way to access multiple LLM providers through a unified interface. Key takeaways:

1. **Easy Integration**: Compatible with OpenAI SDK
2. **Provider Flexibility**: Switch models without code changes
3. **Cost Effective**: Pay only for what you use
4. **Reliable**: Automatic failover between providers
5. **Feature Rich**: Streaming, routing, format control

For the latest updates and detailed API documentation, visit the [OpenRouter Documentation](https://openrouter.ai/docs).