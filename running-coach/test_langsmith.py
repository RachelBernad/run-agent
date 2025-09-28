#!/usr/bin/env python3
"""Test script to verify LangSmith tracing is working."""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_langsmith_config():
    """Test LangSmith configuration."""
    print("Testing LangSmith Configuration...")
    
    # Check environment variables
    tracing_v2 = os.getenv("LANGCHAIN_TRACING_V2")
    project = os.getenv("LANGCHAIN_PROJECT")
    api_key = os.getenv("LANGCHAIN_API_KEY")
    
    print(f"LANGCHAIN_TRACING_V2: {tracing_v2}")
    print(f"LANGCHAIN_PROJECT: {project}")
    print(f"LANGCHAIN_API_KEY: {'***' + api_key[-4:] if api_key and len(api_key) > 4 else 'NOT SET'}")
    
    if not api_key or api_key == "your_langsmith_api_key_here":
        print("❌ ERROR: LANGCHAIN_API_KEY is not set or is placeholder")
        print("Please set your actual LangSmith API key in the .env file")
        return False
    
    if tracing_v2 != "true":
        print("❌ ERROR: LANGCHAIN_TRACING_V2 is not set to 'true'")
        return False
    
    print("✅ LangSmith configuration looks good!")
    return True

def test_langsmith_client():
    """Test LangSmith client connection."""
    try:
        from langsmith import Client
        
        api_key = os.getenv("LANGCHAIN_API_KEY")
        if not api_key or api_key == "your_langsmith_api_key_here":
            print("❌ Cannot test client - API key not set")
            return False
        
        client = Client(api_key=api_key)
        
        # Try to get projects to test connection
        projects = list(client.list_projects())
        print(f"✅ LangSmith client connected successfully! Found {len(projects)} projects.")
        
        return True
        
    except Exception as e:
        print(f"❌ LangSmith client test failed: {e}")
        return False

def test_langchain_tracing():
    """Test LangChain tracing setup."""
    try:
        from langchain.schema import HumanMessage
        from langchain_ollama import ChatOllama
        from langchain.callbacks import LangChainTracer
        
        print("Testing LangChain tracing...")
        
        # Create a simple LLM call with tracing
        llm = ChatOllama(model="llama2")  # Use a simple model for testing
        tracer = LangChainTracer()
        
        messages = [HumanMessage(content="Hello, how are you?")]
        response = llm.invoke(messages, config={"callbacks": [tracer]})
        
        print(f"✅ LangChain tracing test successful! Response: {response.content[:50]}...")
        return True
        
    except Exception as e:
        print(f"❌ LangChain tracing test failed: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("LangSmith Tracing Test")
    print("=" * 50)
    
    config_ok = test_langsmith_config()
    if not config_ok:
        print("\n❌ Configuration test failed. Please fix the .env file.")
        sys.exit(1)
    
    client_ok = test_langsmith_client()
    if not client_ok:
        print("\n❌ Client test failed. Please check your API key.")
        sys.exit(1)
    
    tracing_ok = test_langchain_tracing()
    if not tracing_ok:
        print("\n❌ Tracing test failed. Please check your setup.")
        sys.exit(1)
    
    print("\n" + "=" * 50)
    print("✅ All tests passed! LangSmith tracing should be working.")
    print("=" * 50)
