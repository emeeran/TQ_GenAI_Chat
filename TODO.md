



[]  make "Provider | Model" real-time

[]  The following providers API did not generate response, fix after going thorough respective providers' web site:
    1   Openrouter
    2   Alibaba
    3   hugging Face
    4   Moonshot
    5   Perplexity
    
    URLs:
        ## OPENAI
`https://platform.openai.com/docs/overview`
## Gemini
`https://ai.google.dev/gemini-api/docs/api-key`
## Deepseek
`https://api-docs.deepseek.com/`
## Anthropic
`https://docs.anthropic.com/en/api/overview#python`
## Mistral
`https://docs.mistral.ai/getting-started/quickstart/`
## Cohere
`https://docs.cohere.com/reference/chat`
## Openrouter
`https://openrouter.ai/docs/quickstart`
## Hugging Face
`https://huggingface.co/docs/inference-providers/en/hub-api`
## X AI
`https://docs.x.ai/docs/overview`
`https://docs.x.ai/docs/tutorial`
## Gorq
`https://console.groq.com/docs/quickstart`

## Alibaba
https://www.alibabacloud.com/help/en/model-studio/use-qwen-by-calling-api

# Moonshot
https://platform.moonshot.ai/docs/api/chat#public-service-address

# Perplexity
https://docs.perplexity.ai/docs/

Alibaba Chat completions sample

import os
from openai import OpenAI

client = OpenAI(
    # If the environment variable is not configured, replace the following line with: api_key="sk-xxx",
    api_key=os.getenv("DASHSCOPE_API_KEY"), 
    base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
)
completion = client.chat.completions.create(
    model="qwen-plus", # Here qwen-plus is used as an example. You can change the model name as needed. Model list: https://www.alibabacloud.com/help/en/model-studio/getting-started/models
    messages=[
        {'role': 'system', 'content': 'You are a helpful assistant.'},
        {'role': 'user', 'content': 'Who are you?'}],
    )
    
print(completion.model_dump_json())

	```



client = OpenAI(
api_key="YOUR_API_KEY",
base_url="https://api.perplexity.ai"
)

response = client.chat.completions.create(
model="sonar-pro",
messages=[
  {"role": "system", "content": "Be precise and concise."},
  {"role": "user", "content": "How many stars are there in our galaxy?"}
],
temperature=0.2,
top_p=0.9,
max_tokens=1000,
presence_penalty=0,
frequency_penalty=0,
stream=False,
extra_body={
  "search_mode": "web",
  "search_domain_filter": ["government.gov", "nature.com", "science.org"],
  "search_recency_filter": "month"
}
)

print(response.choices[0].message.content)
print(f"Search Results: {response.search_results}")