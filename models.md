

## Provider - openai

- 

- | Alias                          | Points to                                 |
  | :----------------------------- | :---------------------------------------- |
  | `gpt-4o`                       | `gpt-4o-2024-08-06`                       |
  | `chatgpt-4o-latest`            | Latest used in ChatGPT                    |
  | `gpt-4o-mini`                  | `gpt-4o-mini-2024-07-18`                  |
  | `o1`                           | `o1-2024-12-17`                           |
  | `o1-mini`                      | `o1-mini-2024-09-12`                      |
  | `o3-mini`                      | `o3-mini-2025-01-31`                      |
  | `o1-preview`                   | `o1-preview-2024-09-12`                   |
  | `gpt-4o-realtime-preview`      | `gpt-4o-realtime-preview-2024-12-17`      |
  | `gpt-4o-mini-realtime-preview` | `gpt-4o-mini-realtime-preview-2024-12-17` |
  | `gpt-4o-audio-preview`         | `gpt-4o-audio-preview-2024-12-17`         |



```python
from openai import OpenAI
client = OpenAI()

completion = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {
            "role": "user",
            "content": "Write a haiku about recursion in programming."
        }
    ]
)

print(completion.choices[0].message)
```

------



## Groq

| MODEL ID                   | DEVELOPER   | CONTEXT WINDOW (TOKENS) | MAX COMPLETION TOKENS | MAX FILE SIZE | MODEL CARD LINK                                              |
| :------------------------- | :---------- | :---------------------- | :-------------------- | :------------ | :----------------------------------------------------------- |
| distil-whisper-large-v3-en | HuggingFace | -                       | -                     | 25 MB         | [Card](https://huggingface.co/distil-whisper/distil-large-v3) |
| gemma2-9b-it               | Google      | 8,192                   | -                     | -             | [Card](https://huggingface.co/google/gemma-2-9b-it)          |
| llama-3.3-70b-versatile    | Meta        | 128K                    | 32,768                | -             | [Card](https://github.com/meta-llama/llama-models/blob/main/models/llama3_3/MODEL_CARD.md) |
| llama-3.1-8b-instant       | Meta        | 128K                    | 8,192                 | -             | [Card](https://github.com/meta-llama/llama-models/blob/main/models/llama3_1/MODEL_CARD.md) |
| llama-guard-3-8b           | Meta        | 8,192                   | -                     | -             | [Card](https://console.groq.com/docs/model/llama-guard-3-8b) |
| llama3-70b-8192            | Meta        | 8,192                   | -                     | -             | [Card](https://huggingface.co/meta-llama/Meta-Llama-3-70B-Instruct) |
| llama3-8b-8192             | Meta        | 8,192                   | -                     | -             | [Card](https://huggingface.co/meta-llama/Meta-Llama-3-8B-Instruct) |
| mixtral-8x7b-32768         | Mistral     | 32,768                  | -                     | -             | [Card](https://huggingface.co/mistralai/Mixtral-8x7B-Instruct-v0.1) |
| whisper-large-v3           | OpenAI      | -                       | -                     | 25 MB         | [Card](https://huggingface.co/openai/whisper-large-v3)       |
| whisper-large-v3-turbo     | OpenAI      | -                       | -                     | 25 MB         | [Card](https://huggingface.co/openai/whisper-large-v3-turbo) |

### [Preview Models](https://console.groq.com/docs/models#preview-models)

**Note:** Preview models are intended for evaluation purposes only and should not be used in production environments as they may be discontinued at short notice.

| MODEL ID                              | DEVELOPER     | CONTEXT WINDOW (TOKENS) | MAX COMPLETION TOKENS | MAX FILE SIZE | MODEL CARD LINK                                              |
| :------------------------------------ | :------------ | :---------------------- | :-------------------- | :------------ | :----------------------------------------------------------- |
| qwen-2.5-coder-32b                    | Alibaba Cloud | 128K                    | -                     | -             | [Card](https://huggingface.co/Qwen/Qwen2.5-Coder-32B-Instruct) |
| qwen-2.5-32b                          | Alibaba Cloud | 128K                    | -                     | -             | [Card](https://huggingface.co/Qwen/Qwen2.5-32B-Instruct)     |
| deepseek-r1-distill-qwen-32b          | DeepSeek      | 128K                    | 16,384                | -             | [Card](https://huggingface.co/deepseek-ai/DeepSeek-R1-Distill-Qwen-32B) |
| deepseek-r1-distill-llama-70b-specdec | DeepSeek      | 128K                    | 16,384                | -             | [Card](https://console.groq.com/docs/model/deepseek-r1-distill-llama-70b) |
| deepseek-r1-distill-llama-70b         | DeepSeek      | 128K                    | -                     | -             | [Card](https://console.groq.com/docs/model/deepseek-r1-distill-llama-70b) |
| llama-3.3-70b-specdec                 | Meta          | 8,192                   | -                     | -             | [Card](https://github.com/meta-llama/llama-models/blob/main/models/llama3_3/MODEL_CARD.md) |
| llama-3.2-1b-preview                  | Meta          | 128K                    | 8,192                 | -             | [Card](https://huggingface.co/meta-llama/Llama-3.2-1B)       |
| llama-3.2-3b-preview                  | Meta          | 128K                    | 8,192                 | -             | [Card](https://huggingface.co/meta-llama/Llama-3.2-3B)       |
| llama-3.2-11b-vision-preview          | Meta          | 128K                    | 8,192                 | -             | [Card](https://huggingface.co/meta-llama/Llama-3.2-11B-Vision) |
| llama-3.2-90b-vision-preview          | Meta          | 128K                    | 8,192                 | -             | [Card](https://huggingface.co/meta-llama/Llama-3.2-90B-Vision-Instruct) |



```python
import os

from groq import Groq

client = Groq(
    api_key=os.environ.get("GROQ_API_KEY"),
)

chat_completion = client.chat.completions.create(
    messages=[
        {
            "role": "user",
            "content": "Explain the importance of fast language models",
        }
    ],
    model="llama-3.3-70b-versatile",
)

print(chat_completion.choices[0].message.content)
```



------



## Anthropic

| Model             | Anthropic API                                             | AWS Bedrock                                 | GCP Vertex AI                   |
| ----------------- | --------------------------------------------------------- | ------------------------------------------- | ------------------------------- |
| Claude 3.5 Sonnet | `claude-3-5-sonnet-20241022` (`claude-3-5-sonnet-latest`) | `anthropic.claude-3-5-sonnet-20241022-v2:0` | `claude-3-5-sonnet-v2@20241022` |
| Claude 3.5 Haiku  | `claude-3-5-haiku-20241022` (`claude-3-5-haiku-latest`)   | `anthropic.claude-3-5-haiku-20241022-v1:0`  | `claude-3-5-haiku@20241022`     |

| Model           | Anthropic API                                     | AWS Bedrock                               | GCP Vertex AI              |
| --------------- | ------------------------------------------------- | ----------------------------------------- | -------------------------- |
| Claude 3 Opus   | `claude-3-opus-20240229` (`claude-3-opus-latest`) | `anthropic.claude-3-opus-20240229-v1:0`   | `claude-3-opus@20240229`   |
| Claude 3 Sonnet | `claude-3-sonnet-20240229`                        | `anthropic.claude-3-sonnet-20240229-v1:0` | `claude-3-sonnet@20240229` |
| Claude 3 Haiku  | `claude-3-haiku-20240307`                         | `anthropic.claude-3-haiku-20240307-v1:0`  | `claude-3-haiku@20240307`  |

```python
import anthropic

client = anthropic.Anthropic(
    # defaults to os.environ.get("ANTHROPIC_API_KEY")
    api_key="my_api_key",
)
message = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    messages=[
        {"role": "user", "content": "Hello, Claude"}
    ]
)
print(message.content)

```

------



## Mistral

| Model              |                     Weight availability                      | Available via API |                         Description                          | Max Tokens |        API Endpoints        | Version |
| ------------------ | :----------------------------------------------------------: | :---------------: | :----------------------------------------------------------: | :--------: | :-------------------------: | :-----: |
| Codestral          |                                                              |         ✔️         | Our cutting-edge language model for coding with the second version released January 2025, Codestral specializes in low-latency, high-frequency tasks such as fill-in-the-middle (FIM), code correction and test generation. Learn more on our [blog post](https://mistral.ai/news/codestral-2501/) |    256k    |     `codestral-latest`      |  25.01  |
| Mistral Large      | ✔️ [Mistral Research License](https://mistral.ai/licenses/MRL-0.1.md) |         ✔️         | Our top-tier reasoning model for high-complexity tasks with the lastest version released November 2024. Learn more on our [blog post](https://mistral.ai/news/pixtral-large/) |    131k    |   `mistral-large-latest`    |  24.11  |
| Pixtral Large      | ✔️ [Mistral Research License](https://mistral.ai/licenses/MRL-0.1.md) |         ✔️         | Our frontier-class multimodal model released November 2024. Learn more on our [blog post](https://mistral.ai/news/pixtral-large/) |    131k    |   `pixtral-large-latest`    |  24.11  |
| Mistral Saba       |                                                              |         ✔️         | A powerfull and efficient model for languages from the Middle East and South Asia. Learn more on our [blog post](https://mistral.ai/news/mistral-saba/) |    32k     |    `mistral-saba-latest`    |  25.02  |
| Ministral 3B       |                                                              |         ✔️         | World’s best edge model. Learn more on our [blog post](https://mistral.ai/news/ministraux/) |    131k    |    `ministral-3b-latest`    |  24.10  |
| Ministral 8B       | ✔️ [Mistral Research License](https://mistral.ai/licenses/MRL-0.1.md) |         ✔️         | Powerful edge model with extremely high performance/price ratio. Learn more on our [blog post](https://mistral.ai/news/ministraux/) |    131k    |    `ministral-8b-latest`    |  24.10  |
| Mistral Embed      |                                                              |         ✔️         | Our state-of-the-art semantic for extracting representation of text extracts |     8k     |       `mistral-embed`       |  23.12  |
| Mistral Moderation |                                                              |         ✔️         | Our moderation service that enables our users to detect harmful text content |     8k     | `mistral-moderation-latest` |  24.11  |

- 

| Model         | Weight availability | Available via API |                         Description                          | Max Tokens |     API Endpoints      | Version |
| ------------- | :-----------------: | :---------------: | :----------------------------------------------------------: | :--------: | :--------------------: | :-----: |
| Mistral Small |      ✔️ Apache2      |         ✔️         | A new leader in the small models category with the lastest version v3 released January 2025. Learn more on our [blog post](https://mistral.ai/news/mistral-small-3/) |    32k     | `mistral-small-latest` |  25.01  |
| Pixtral       |      ✔️ Apache2      |         ✔️         | A 12B model with image understanding capabilities in addition to text. Learn more on our [blog post](https://mistral.ai/news/pixtral-12b/) |    131k    |   `pixtral-12b-2409`   |  24.09  |

- **Research models**

| Model           | Weight availability | Available via API |                         Description                          | Max Tokens |     API Endpoints      | Version |
| --------------- | :-----------------: | :---------------: | :----------------------------------------------------------: | :--------: | :--------------------: | :-----: |
| Mistral Nemo    |      ✔️ Apache2      |         ✔️         | Our best multilingual open source model released July 2024. Learn more on our [blog post](https://mistral.ai/news/mistral-nemo/) |    131k    |  `open-mistral-nemo`   |  24.07  |
| Codestral Mamba |      ✔️ Apache2      |         ✔️         | Our first mamba 2 open source model released July 2024. Learn more on our [blog post](https://mistral.ai/news/codestral-mamba/) |    256k    | `open-codestral-mamba` |  v0.1   |
| Mathstral       |      ✔️ Apache2      |                   | Our first math open source model released July 2024. Learn more on our [blog post](https://mistral.ai/news/mathstral/) |    32k     |           NA           |  v0.1   |

Mistral AI API are versions with specific release dates. To prevent any disruptions due to model updates and breaking changes, it is recommended to use the dated versions of the Mistral AI API. Additionally, be prepared for the deprecation of certain endpoints in the coming months.

Here are the details of the available versions:

- `mistral-large-latest`: currently points to `mistral-large-2411`.
- `pixtral-large-latest`: currently points to `pixtral-large-2411`.
- `mistral-moderation-latest`: currently points to `mistral-moderation-2411`.
- `ministral-3b-latest`: currently points to `ministral-3b-2410`.
- `ministral-8b-latest`: currently points to `ministral-8b-2410`.
- `open-mistral-nemo`: currently points to `open-mistral-nemo-2407`.
- `mistral-small-latest`: currently points to `mistral-small-2501`.
- `mistral-saba-latest`: currently points to `mistral-saba-2502`.
- `codestral-latest`: currently points to `codestral-2501`.

## 

| Model               |                     Weight availability                      | Available via API |                         Description                          | Max Tokens |     API Endpoints     | Version | Legacy date | Deprecation on date | Retirement date |   Alternative model    |
| ------------------- | :----------------------------------------------------------: | :---------------: | :----------------------------------------------------------: | :--------: | :-------------------: | :-----: | :---------: | :-----------------: | :-------------: | :--------------------: |
| Mistral 7B          |                          ✔️ Apache2                           |         ✔️         | Our first dense model released September 2023. Learn more on our [blog post](https://mistral.ai/news/announcing-mistral-7b/) |    32k     |   `open-mistral-7b`   |  v0.3   | 2024/11/25  |     2024/11/30      |   2025/03/30    | `ministral-8b-latest`  |
| Mixtral 8x7B        |                          ✔️ Apache2                           |         ✔️         | Our first sparse mixture-of-experts released December 2023. Learn more on our [blog post](https://mistral.ai/news/mixtral-of-experts/) |    32k     |  `open-mixtral-8x7b`  |  v0.1   | 2024/11/25  |     2024/11/30      |   2025/03/30    | `mistral-small-latest` |
| Mixtral 8x22B       |                          ✔️ Apache2                           |         ✔️         | Our best open source model to date released April 2024. Learn more on our [blog post](https://mistral.ai/news/mixtral-8x22b/) |    64k     | `open-mixtral-8x22b`  |  v0.1   | 2024/11/25  |     2024/11/30      |   2025/03/30    | `mistral-small-latest` |
| Mistral Medium      |                                                              |         ✔️         | Ideal for intermediate tasks that require moderate reasoning |    32k     | `mistral-medium-2312` |  23.12  | 2024/11/25  |     2024/11/30      |   2025/03/30    | `mistral-small-latest` |
| Mistral Small 24.02 |                                                              |         ✔️         | Our latest enterprise-grade small model with the first version released Feb. 2024 |    32k     | `mistral-small-2402`  |  24.09  | 2024/11/25  |     2024/11/30      |   2025/03/30    | `mistral-small-latest` |
| Mistral Large 24.02 |                                                              |         ✔️         | Our top-tier reasoning model for high-complexity tasks with the the first version released Feb. 2024. Learn more on our [blog post](https://mistral.ai/news/mistral-large/) |    32k     | `mistral-large-2402`  |  24.02  | 2024/11/25  |     2024/11/30      |   2025/03/30    | `mistral-large-latest` |
| Mistral Large 24.07 | ✔️ [Mistral Research License](https://mistral.ai/licenses/MRL-0.1.md) |         ✔️         | Our top-tier reasoning model for high-complexity tasks with the the second version released July 2024. Learn more on our [blog post](https://mistral.ai/news/mistral-large-2407/) |    131k    | `mistral-large-2407`  |  24.02  | 2024/11/25  |     2024/11/30      |   2025/03/30    | `mistral-large-latest` |
| Codestral           | ✔️ [Mistral Non-Production License](https://mistral.ai/licenses/MNPL-0.1.md) |         ✔️         | Our cutting-edge language model for coding with the first version released [May 2024](https://mistral.ai/news/codestral/) |    32k     |   `codestral-2405`    |  24.05  | 2024/12/02  |     2024/12/02      |   2025/03/30    |   `codestral-latest`   |

- - **Latest models**

  | Model         | Weight availability | Available via API |                         Description                          | Max Tokens |     API Endpoints      | Version |
  | ------------- | :-----------------: | :---------------: | :----------------------------------------------------------: | :--------: | :--------------------: | :-----: |
  | Mistral Small |      ✔️ Apache2      |         ✔️         | A new leader in the small models category with the lastest version v3 released January 2025. Learn more on our [blog post](https://mistral.ai/news/mistral-small-3/) |    32k     | `mistral-small-latest` |  25.01  |
  | Pixtral       |      ✔️ Apache2      |         ✔️         | A 12B model with image understanding capabilities in addition to text. Learn more on our [blog post](https://mistral.ai/news/pixtral-12b/) |    131k    |   `pixtral-12b-2409`   |  24.09  |

  - **Research models**

  | Model           | Weight availability | Available via API |                         Description                          | Max Tokens |     API Endpoints      | Version |
  | --------------- | :-----------------: | :---------------: | :----------------------------------------------------------: | :--------: | :--------------------: | :-----: |
  | Mistral Nemo    |      ✔️ Apache2      |         ✔️         | Our best multilingual open source model released July 2024. Learn more on our [blog post](https://mistral.ai/news/mistral-nemo/) |    131k    |  `open-mistral-nemo`   |  24.07  |
  | Codestral Mamba |      ✔️ Apache2      |         ✔️         | Our first mamba 2 open source model released July 2024. Learn more on our [blog post](https://mistral.ai/news/codestral-mamba/) |    256k    | `open-codestral-mamba` |  v0.1   |
  | Mathstral       |      ✔️ Apache2      |                   | Our first math open source model released July 2024. Learn more on our [blog post](https://mistral.ai/news/mathstral/) |    32k     |           NA           |  v0.1   |



Mistral AI API are versions with specific release dates. To prevent any disruptions due to model updates and breaking changes, it is recommended to use the dated versions of the Mistral AI API. Additionally, be prepared for the deprecation of certain endpoints in the coming months.

Here are the details of the available versions:

- `mistral-large-latest`: currently points to `mistral-large-2411`.
- `pixtral-large-latest`: currently points to `pixtral-large-2411`.
- `mistral-moderation-latest`: currently points to `mistral-moderation-2411`.
- `ministral-3b-latest`: currently points to `ministral-3b-2410`.
- `ministral-8b-latest`: currently points to `ministral-8b-2410`.
- `open-mistral-nemo`: currently points to `open-mistral-nemo-2407`.
- `mistral-small-latest`: currently points to `mistral-small-2501`.
- `mistral-saba-latest`: currently points to `mistral-saba-2502`.
- `codestral-latest`: currently points to `codestral-2501`.



------



## X AI

| Model                                                   | Input | Output | Context | PricePer Million Tokens                              |
| :------------------------------------------------------ | :---- | :----- | :------ | :--------------------------------------------------- |
| grok-2-vision-1212- grok-2-vision- grok-2-vision-latest |       |        | 32768   | Text Input$2.00Image Input$2.00Text Completion$10.00 |
| grok-2-1212- grok-2- grok-2-latest                      |       |        | 131072  | Text Input$2.00Text Completion$10.00                 |
| grok-vision-beta                                        |       |        | 8192    | Text Input$5.00Image Input$5.00Text Completion$15.00 |
| grok-beta                                               |       |        | 131072  | Text Input$5.00Text Completion$15.00                 |
|                                                         |       |        |         |                                                      |

```python
# In your terminal, first run:
# pip install openai

import os
from openai import OpenAI

XAI_API_KEY = os.getenv("XAI_API_KEY")
client = OpenAI(
    api_key=XAI_API_KEY,
    base_url="https://api.x.ai/v1",
)

completion = client.chat.completions.create(
    model="grok-2-latest",
    messages=[
        {
            "role": "system",
            "content": "You are Grok, a chatbot inspired by the Hitchhikers Guide to the Galaxy."
        },
        {
            "role": "user",
            "content": "What is the meaning of life, the universe, and everything?"
        },
    ],
)

print(completion.choices[0].message.content)
```

------

## deepseek

| MODEL(1)          | CONTEXT LENGTH | MAX COT TOKENS(2) | MAX OUTPUT TOKENS(3) | 1M TOKENS INPUT PRICE (CACHE HIT) (4) | 1M TOKENS INPUT PRICE (CACHE MISS) | 1M TOKENS OUTPUT PRICE |
| ----------------- | -------------- | ----------------- | -------------------- | ------------------------------------- | ---------------------------------- | ---------------------- |
| deepseek-chat     | 64K            | -                 | 8K                   | $0.07                                 | $0.27                              | $1.10                  |
| deepseek-reasoner | 64K            | 32K               | 8K                   | $0.14                                 | $0.55                              |                        |

```python
# Please install OpenAI SDK first: `pip3 install openai`

from openai import OpenAI

client = OpenAI(api_key="<DeepSeek API Key>", base_url="https://api.deepseek.com")

response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {"role": "system", "content": "You are a helpful assistant"},
        {"role": "user", "content": "Hello"},
    ],
    stream=False
)

print(response.choices[0].message.content)
```

