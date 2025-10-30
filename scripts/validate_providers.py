#!/usr/bin/env python3
"""
TQ GenAI Chat - Provider API Validation Script

This script validates all configured AI provider API keys and generates sample responses.
Run this script to verify that all providers are working correctly.

Usage:
    python scripts/validate_providers.py [--verbose] [--provider PROVIDER_NAME] [--save] [--template]
"""

import asyncio
import os
import sys
import json
import time
import argparse
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

# Add backend to Python path
script_dir = Path(__file__).parent
project_root = script_dir.parent
backend_dir = project_root / "backend"
sys.path.insert(0, str(backend_dir))

# Import LiteLLM which is what the application actually uses
try:
    import litellm
    from dotenv import load_dotenv
except ImportError as e:
    print(f"❌ Error importing required modules: {e}")
    print("Make sure you have litellm and python-dotenv installed")
    sys.exit(1)

# Load environment variables
load_dotenv(project_root / ".env")


class ProviderValidator:
    """Validates API keys and generates sample responses for all providers"""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.results = {}
        self.test_message = "Hello! Please respond with a brief greeting and tell me what AI model you are."

    def log(self, message: str, level: str = "INFO"):
        """Log messages with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        if self.verbose or level in ["ERROR", "WARNING"]:
            print(f"[{timestamp}] {level}: {message}")

    def get_provider_config(self, provider_name: str) -> Dict[str, Any]:
        """Get configuration for a specific provider using LiteLLM format"""
        configs = {
            "openai": {
                "api_key": os.getenv("OPENAI_API_KEY"),
                "model": "gpt-3.5-turbo",
                "litellm_model": "gpt-3.5-turbo"
            },
            "anthropic": {
                "api_key": os.getenv("ANTHROPIC_API_KEY"),
                "model": "claude-3-haiku-20240307",
                "litellm_model": "anthropic/claude-3-haiku-20240307"
            },
            "groq": {
                "api_key": os.getenv("GROQ_API_KEY"),
                "model": "llama3-70b-8192",
                "litellm_model": "groq/llama3-70b-8192"
            },
            "mistral": {
                "api_key": os.getenv("MISTRAL_API_KEY"),
                "model": "mistral-tiny",
                "litellm_model": "mistral/mistral-tiny"
            },
            "gemini": {
                "api_key": os.getenv("GEMINI_API_KEY"),
                "model": "gemini-pro",
                "litellm_model": "gemini/gemini-pro"
            },
            "cohere": {
                "api_key": os.getenv("COHERE_API_KEY"),
                "model": "command-r",
                "litellm_model": "cohere/command-r"
            },
            "xai": {
                "api_key": os.getenv("XAI_API_KEY"),
                "model": "grok-beta",
                "litellm_model": "xai/grok-beta"
            },
            "deepseek": {
                "api_key": os.getenv("DEEPSEEK_API_KEY"),
                "model": "deepseek-chat",
                "litellm_model": "deepseek/deepseek-chat"
            },
            "alibaba": {
                "api_key": os.getenv("ALIBABA_API_KEY"),
                "model": "gemma3",
                "litellm_model": "ollama/gemma3"  # Using ollama for alibaba with available model
            },
            "openrouter": {
                "api_key": os.getenv("OPENROUTER_API_KEY"),
                "model": "meta-llama/llama-3.2-3b-instruct:free",
                "litellm_model": "openrouter/meta-llama/llama-3.2-3b-instruct:free"
            },
            "huggingface": {
                "api_key": os.getenv("HF_PHRM_ACCESS_TOKEN"),
                "model": "microsoft/DialoGPT-medium",
                "litellm_model": "huggingface/microsoft/DialoGPT-medium"
            },
            "moonshot": {
                "api_key": os.getenv("MOONSHOT_API_KEY"),
                "model": "moonshot-v1-8k",
                "litellm_model": "openai/moonshot-v1-8k"  # moonshot uses openai-compatible API
            },
            "perplexity": {
                "api_key": os.getenv("PERPLEXITY_API_KEY"),
                "model": "sonar-pro",
                "litellm_model": "perplexity/sonar-pro"
            }
        }
        return configs.get(provider_name, {})

    async def validate_provider(self, provider_name: str) -> Dict[str, Any]:
        """Validate a single provider's API key and generate sample response using LiteLLM"""
        self.log(f"🔍 Validating {provider_name} provider...")

        config = self.get_provider_config(provider_name)
        if not config:
            error_msg = f"No configuration found for provider: {provider_name}"
            self.log(error_msg, "ERROR")
            return {
                "provider": provider_name,
                "status": "error",
                "error": error_msg,
                "api_key_valid": False,
                "response_time": 0,
                "sample_response": None
            }

        api_key = config.get("api_key")
        if not api_key or api_key.strip() in ["", "your-api-key-here", "sk-placeholder", "YOUR_API_KEY_HERE"]:
            error_msg = f"Missing or invalid API key for {provider_name}"
            self.log(error_msg, "WARNING")
            return {
                "provider": provider_name,
                "status": "no_api_key",
                "error": error_msg,
                "api_key_valid": False,
                "response_time": 0,
                "sample_response": None,
                "setup_url": self.get_setup_url(provider_name)
            }

        # Set environment variable for LiteLLM
        original_env = {}
        env_var_map = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "groq": "GROQ_API_KEY",
            "mistral": "MISTRAL_API_KEY",
            "gemini": "GEMINI_API_KEY",
            "cohere": "COHERE_API_KEY",
            "xai": "XAI_API_KEY",
            "deepseek": "DEEPSEEK_API_KEY",
            "openrouter": "OPENROUTER_API_KEY",
            "huggingface": "HUGGINGFACE_API_KEY",
            "moonshot": "OPENAI_API_KEY",  # Moonshot uses OpenAI-compatible API
            "perplexity": "PERPLEXITY_API_KEY"
        }

        env_key = env_var_map.get(provider_name, f"{provider_name.upper()}_API_KEY")
        if env_key in os.environ:
            original_env[env_key] = os.environ[env_key]
        os.environ[env_key] = api_key

        # Test the provider using LiteLLM
        start_time = time.time()
        try:
            self.log(f"Testing with model: {config['litellm_model']}")

            response = await litellm.acompletion(
                model=config["litellm_model"],
                messages=[{"role": "user", "content": self.test_message}],
                temperature=0.7,
                max_tokens=100,
                timeout=30
            )

            response_time = time.time() - start_time

            # Extract response content
            content = response.choices[0].message.content if response.choices else ""
            model_used = response.model if hasattr(response, 'model') else config.get("model")
            usage = response.usage if hasattr(response, 'usage') else None

            self.log(f"✅ {provider_name}: API key valid, response time: {response_time:.2f}s")

            return {
                "provider": provider_name,
                "status": "success",
                "api_key_valid": True,
                "response_time": response_time,
                "sample_response": content,
                "model": model_used,
                "tokens_used": usage.total_tokens if usage else 0,
                "error": None
            }

        except Exception as e:
            response_time = time.time() - start_time
            error_msg = str(e)
            self.log(f"❌ {provider_name}: {error_msg}", "ERROR")

            return {
                "provider": provider_name,
                "status": "error",
                "api_key_valid": False,
                "response_time": response_time,
                "sample_response": None,
                "error": error_msg,
                "setup_url": self.get_setup_url(provider_name)
            }
        finally:
            # Restore original environment
            for key, value in original_env.items():
                if value is not None:
                    os.environ[key] = value
                else:
                    os.environ.pop(key, None)

    def get_setup_url(self, provider_name: str) -> str:
        """Get setup URL for provider API key"""
        setup_urls = {
            "openai": "https://platform.openai.com/api-keys",
            "anthropic": "https://console.anthropic.com/",
            "groq": "https://console.groq.com/keys",
            "mistral": "https://console.mistral.ai/api-keys/",
            "gemini": "https://makersuite.google.com/app/apikey",
            "cohere": "https://dashboard.cohere.com/api-keys",
            "xai": "https://console.x.ai/",
            "deepseek": "https://platform.deepseek.com/",
            "alibaba": "https://dashscope.aliyun.com/api",
            "openrouter": "https://openrouter.ai/keys",
            "huggingface": "https://huggingface.co/settings/tokens",
            "moonshot": "https://platform.moonshot.cn/console/api-keys",
            "perplexity": "https://www.perplexity.ai/settings/api"
        }
        return setup_urls.get(provider_name, "#")

    async def validate_all_providers(self, specific_provider: Optional[str] = None) -> Dict[str, Any]:
        """Validate all providers or a specific one"""
        providers = [
            "openai", "anthropic", "groq", "mistral", "gemini", "cohere",
            "xai", "deepseek", "alibaba", "openrouter", "huggingface",
            "moonshot", "perplexity"
        ]

        if specific_provider:
            if specific_provider not in providers:
                print(f"❌ Unknown provider: {specific_provider}")
                print(f"Available providers: {', '.join(providers)}")
                sys.exit(1)
            providers = [specific_provider]

        print(f"🚀 Starting API validation for {len(providers)} provider(s)...")
        print("=" * 60)

        # Run validations in parallel for efficiency
        tasks = [self.validate_provider(provider) for provider in providers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        validation_results = {}
        for i, result in enumerate(results):
            provider_name = providers[i]
            if isinstance(result, Exception):
                validation_results[provider_name] = {
                    "provider": provider_name,
                    "status": "error",
                    "error": str(result),
                    "api_key_valid": False,
                    "response_time": 0,
                    "sample_response": None
                }
            else:
                validation_results[provider_name] = result

        return validation_results

    def print_summary(self, results: Dict[str, Any]):
        """Print validation summary"""
        print("\n" + "=" * 60)
        print("📊 VALIDATION SUMMARY")
        print("=" * 60)

        successful = []
        failed = []
        no_key = []

        for provider, result in results.items():
            status = result["status"]
            if status == "success":
                successful.append(provider)
                response_time = result["response_time"]
                sample = result["sample_response"][:100] + "..." if len(result["sample_response"]) > 100 else result["sample_response"]
                print(f"✅ {provider.upper()}: Working ({response_time:.2f}s)")
                if self.verbose:
                    print(f"   Sample: {sample}")
            elif status == "no_api_key":
                no_key.append(provider)
                print(f"⚠️  {provider.upper()}: No API key configured")
                if "setup_url" in result:
                    print(f"   Setup: {result['setup_url']}")
            else:
                failed.append(provider)
                error = result["error"]
                response_time = result["response_time"]
                print(f"❌ {provider.upper()}: Failed ({response_time:.2f}s)")
                print(f"   Error: {error}")
                if "setup_url" in result:
                    print(f"   Setup: {result['setup_url']}")

        print(f"\n📈 Statistics:")
        print(f"   ✅ Working: {len(successful)}")
        print(f"   ❌ Failed: {len(failed)}")
        print(f"   ⚠️  No API Key: {len(no_key)}")
        print(f"   📊 Success Rate: {len(successful)}/{len(results)} ({len(successful)/len(results)*100:.1f}%)")

        if successful:
            print(f"\n🏆 Working Providers: {', '.join(successful)}")

        if failed or no_key:
            need_setup = failed + no_key
            print(f"\n🔧 Need Setup: {', '.join(need_setup)}")

    def save_results(self, results: Dict[str, Any]):
        """Save validation results to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"scripts/provider_validation_{timestamp}.json"

        report = {
            "timestamp": datetime.now().isoformat(),
            "total_providers": len(results),
            "successful_providers": len([r for r in results.values() if r["status"] == "success"]),
            "failed_providers": len([r for r in results.values() if r["status"] == "error"]),
            "no_key_providers": len([r for r in results.values() if r["status"] == "no_api_key"]),
            "results": results
        }

        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"\n💾 Detailed results saved to: {output_file}")

    def generate_env_template(self, results: Dict[str, Any]):
        """Generate .env template with missing keys highlighted"""
        template_lines = [
            "# TQ GenAI Chat - Environment Configuration",
            "# Generated by provider validation script",
            "# Fill in the missing API keys below",
            ""
        ]

        for provider, result in results.items():
            env_var = f"{provider.upper()}_API_KEY"
            if result["status"] == "success":
                template_lines.append(f"{env_var}=\"[VALIDATED_WORKING]\"")
            elif result["status"] == "no_api_key":
                template_lines.append(f"# {env_var}=\"YOUR_API_KEY_HERE\"  # ⚠️  NEEDED")
            else:
                template_lines.append(f"# {env_var}=\"YOUR_API_KEY_HERE\"  # ❌ NEEDS FIX")

        template_lines.extend([
            "",
            "# Application Configuration",
            "FLASK_ENV=development",
            "SECRET_KEY=0473dfc4a250c727e0ddfc2589b8b15b2dfa5298b01bd0ef76fe77cec8ebd995",
            "DEBUG=True",
            "LOG_LEVEL=DEBUG",
            "CACHE_ENABLED=True",
            "REDIS_URL=redis://localhost:6379/0",
            "",
            "BASIC_AUTH_USERNAME=emeeran",
            "BASIC_AUTH_PASSWORD=3u0qL1lizU19WE",
            ""
        ])

        with open("scripts/.env.template", 'w') as f:
            f.write('\n'.join(template_lines))

        print("📝 Environment template generated: scripts/.env.template")


async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Validate AI provider API keys")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--provider", "-p", help="Validate specific provider only")
    parser.add_argument("--save", "-s", action="store_true", help="Save results to file")
    parser.add_argument("--template", "-t", action="store_true", help="Generate .env template")

    args = parser.parse_args()

    validator = ProviderValidator(verbose=args.verbose)

    try:
        results = await validator.validate_all_providers(args.provider)
        validator.print_summary(results)

        if args.save:
            validator.save_results(results)

        if args.template:
            validator.generate_env_template(results)

        # Exit with error code if any providers failed
        failed_count = len([r for r in results.values() if r["status"] in ["error", "no_api_key"]])
        if failed_count > 0:
            print(f"\n⚠️  {failed_count} provider(s) need attention. See details above.")
            sys.exit(1)
        else:
            print(f"\n🎉 All providers are working correctly!")
            sys.exit(0)

    except KeyboardInterrupt:
        print("\n\n⏹️  Validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())