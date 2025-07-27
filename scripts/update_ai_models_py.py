"""
Script to update ai_models.py with new model lists for a given provider.
Usage: python3 update_ai_models_py.py <provider> <models_json_file>
"""
import sys
import json
import re

AI_MODELS_PATH = "../ai_models.py"

PROVIDER_BLOCKS = {
    'openai': ('# OpenAI Models', 'OPENAI_MODELS'),
    'groq': ('# Groq Models', 'GROQ_MODELS'),
    'anthropic': ('# Anthropic Models', 'ANTHROPIC_MODELS'),
    'mistral': ('# Mistral Models', 'MISTRAL_MODELS'),
    'xai': ('# X.AI (Grok) Models', 'XAI_MODELS'),
    # Add more as needed
}

def update_model_block(provider, new_models):
    with open(AI_MODELS_PATH, 'r') as f:
        lines = f.readlines()
    block_start, dict_name = PROVIDER_BLOCKS[provider]
    start_idx = None
    end_idx = None
    for i, line in enumerate(lines):
        if block_start in line:
            start_idx = i
        if start_idx is not None and line.strip().startswith('}'):  # End of dict
            end_idx = i
            break
    if start_idx is None or end_idx is None:
        print(f"Could not find block for {provider}")
        sys.exit(1)
    # Build new dict string
    dict_str = f"{dict_name} = {{\n"
    for k, v in new_models.items():
        dict_str += f"    '{k}': {{'name': '{v['name']}'}} ,\n"
    dict_str += "}\n"
    # Replace block
    new_lines = lines[:start_idx+1] + [dict_str] + lines[end_idx+1:]
    with open(AI_MODELS_PATH, 'w') as f:
        f.writelines(new_lines)
    print(f"Updated {dict_name} in ai_models.py")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 update_ai_models_py.py <provider> <models_json_file>")
        sys.exit(1)
    provider = sys.argv[1]
    models_file = sys.argv[2]
    with open(models_file) as f:
        models = json.load(f)
    update_model_block(provider, models)
