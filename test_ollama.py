"""Simple test script to verify Ollama API connection."""
from openai import OpenAI

client = OpenAI(
    base_url="http://127.0.0.1:11434/v1",
    api_key="local-key"
)

print("Testing Ollama API connection...")
print("-" * 40)

try:
    # Test model list
    models = client.models.list()
    print(f"Available models: {[m.id for m in models.data]}")
    print()

    # Test chat completion
    print("Sending test message: 'Say hello in Chinese'")
    response = client.chat.completions.create(
        model="qwen2.5:7b-instruct",
        messages=[{"role": "user", "content": "Say hello in Chinese"}],
        temperature=0.3,
    )
    print(f"Response: {response.choices[0].message.content}")
    print()
    print("✓ Ollama API is working correctly!")

except Exception as e:
    print(f"✗ Error: {e}")
    print("\nTroubleshooting:")
    print("1. Make sure Ollama is running: ollama serve")
    print("2. Make sure model is installed: ollama pull qwen2.5:7b-instruct")
    print("3. Check if port 11434 is accessible")
