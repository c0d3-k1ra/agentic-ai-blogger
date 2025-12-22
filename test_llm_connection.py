"""Test script for LLM client integration.

This script demonstrates the use of the generate_text function from the
LLM client module, testing both default and custom model configurations.
"""

import asyncio

from src.integrations.llm_client import generate_text


async def main():
    """Test the LLM client with different configurations."""
    try:
        # Simple test
        result = await generate_text("Write a one-sentence haiku about Python programming")
        print("✓ Success!")
        print(f"Generated text: {result}")

        # Test with custom model
        result2 = await generate_text(
            "Say hello in one sentence",
            model="gemini-2.5-flash"  # Optional: test different model
        )
        print(f"\nWith custom model: {result2}")

    except Exception as e:
        print(f"✗ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
