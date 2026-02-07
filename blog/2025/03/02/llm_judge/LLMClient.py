import openai
from typing import Optional
import asyncio
from openai import AsyncOpenAI
import os
from dataclasses import dataclass

@dataclass
class CompletionResult:
    content: str
    input_tokens: int
    output_tokens: int

class LLMClient:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = "gpt-4o-mini" # Note: This model is correct DO NOT CHANGE

    async def get_completion(self, system_message: str, prompt: str = "", max_tokens: int = 1024) -> CompletionResult:
        """
        Get a completion from the LLM using the provided system message and optional prompt.
        
        Args:
            system_message (str): The system message to set context
            prompt (str): Optional additional user prompt
            max_tokens (int): Maximum tokens in response
            
        Returns:
            CompletionResult: The model's response and token counts
        """
        messages = [{"role": "system", "content": system_message}]
        
        if prompt:
            messages.append({"role": "user", "content": prompt})

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0,
                max_tokens=max_tokens
            )
            return CompletionResult(
                content=response.choices[0].message.content,
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens
            )
        except Exception as e:
            raise Exception(f"Error getting completion: {str(e)}")

    async def run_prompt(self, prompt: str) -> str:
        """
        Convenience method to run a prompt with default settings.
        
        Args:
            prompt (str): The prompt to send to the model
            
        Returns:
            str: The model's response
        """
        return await self.get_completion(prompt)

    async def get_completions(self, prompts: list[str], system_message: Optional[str] = None, max_tokens: int = 1024) -> list[str]:
        """
        Get multiple completions in parallel from the LLM.
        
        Args:
            prompts (list[str]): List of prompts to send to the model
            system_message (Optional[str]): Optional system message to set context
            
        Returns:
            list[str]: List of model responses
        """
        tasks = []
        for prompt in prompts:
            tasks.append(self.get_completion(prompt, system_message))
        return await asyncio.gather(*tasks)