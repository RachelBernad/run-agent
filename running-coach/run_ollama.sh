#!/bin/bash

# Run Ollama with the specified model
# This script will pull the model if not already available and run it

echo "Starting Ollama with Qwen3-4B-Instruct model..."

# Pull the model if not already available
ollama pull hf.co/unsloth/Qwen3-4B-Instruct-2507-GGUF:Q4_K_M #changeable

# Run the model server
echo "Model pulled successfully. Ollama server should be running on http://localhost:11434"
echo "You can now start the running coach API."
