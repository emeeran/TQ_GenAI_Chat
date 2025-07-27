Qwen API reference
Updated at: 2025-07-25 15:22
Product
Community
This topic describes the input and output parameters of the Qwen API.

For more information about the models, how to select, and how to use them, see Text generation.
You can call the Qwen API by using the OpenAI-compatible method or the DashScope method.

OpenAI
Public cloud
base_url for SDK: https://dashscope-intl.aliyuncs.com/compatible-mode/v1

endpoint for HTTP: POST https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions

You must first obtain an API key and configure the API key as an environment variable. If using the OpenAI SDK, you must also install the OpenAI SDK.
Request body
Text inputStreaming outputImage inputVideo inputTool callingAsynchronous callingText extraction
This is an example for single-round conversation. You can also try multi-round conversation.
PythonJavaNode.jsGoC# (HTTP)PHP (HTTP)curl
 
import os
from openai import OpenAI

client = OpenAI(
    # If environment variables are not configured, replace the following line with: api_key="sk-xxx",
    api_key=os.getenv("DASHSCOPE_API_KEY"), 
    base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
)
completion = client.chat.completions.create(
    model="qwen-plus", # This example uses qwen-plus. You can change the model name as needed. Model list: https://www.alibabacloud.com/help/en/model-studio/getting-started/models
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Who are you?"}],
    )
    
print(completion.model_dump_json())
model string (Required)

The model name.

Supported models: Qwen LLMs (commercial and open-source), Qwen VL, and Qwen Coder.

For specific model names and pricing, see Models and pricing.

messages array (Required)

A list of messages of the conversation so far.

Message types

System Message object (Optional)

The the purpose or role of the model. If you set a system message, place it at the beginning of the messages list.

Properties

User Message object (Required)

Messages sent by the user to the model.

Properties

Assistant Message object (Optional)

The messages sent by the model in response to user messages.

Properties

Tool Message object (Optional)

The output information from the tool.

Properties

stream boolean (Optional) Defaults to false

Specifies whether to use streaming output. Valid values:

false: The model delivers the complete response at a time.

true: The model returns output in chunks as content is generated. You need to obtain each part in real time to get the full response.

Commerical Qwen3 (Thinking mode), open source Qwen3, QwQ, and QVQ only support steaming output.
stream_options object (Optional)

When streaming output is enabled, you can set this parameter to {"include_usage": true} to display the number of tokens used in the last line of the output.

If set to false, the number of tokens used will not be displayed.
This parameter takes effect only when stream is true.

modalities array (Optional) Defaults to ["text"]

The modality of the output data. Supported only by Qwen-Omni. Valid values:

["text","audio"]

["text"]

audio object (Optional)

The voice and format of the output audio. Supported only by Qwen-Omni. modalities must include "audio".

Properties

temperature float (Optional)

Controls the diversity of the generated text.

A higher temperature results in more diversified text, while a lower temperature results in more predictable text.

Value values: [0, 2)

Because both temperature and top_p controls text diversity, we recommend that you specify only one of them, see Temperature and top_p.

Do not change the temperature of QVQ.
top_p float (Optional)

The probability threshold for nucleus sampling, which controls the diversity of the generated text.

A higher top_p results in more diversified text, while a lower top_p results in more predictable text.

Value values: (0,1.0]

Because both temperature and top_p controls text diversity, we recommend that you specify only one of them, see Temperature and top_p.

Do not change the top_p of QVQ.
top_k integer (Optional)

The size of the candidate set for sampling. For example, when the value is 50, only the top 50 tokens with the highest scores are included in the candidate set for random sampling.

A higher top_k results in more diversified text, while a lower top_k results in more predictable text.

If top_k is set to None or a value greater than 100, top_k is disabled and only top_p takes effect.

The value must be greater than or equal to 0.

Default value

In Python SDK, put top_k in the extra_body object, as: extra_body={"top_k":xxx}.
Do not change the top_k of QVQ.
presence_penalty float (Optional)

Controls the repetition of the generated text.

Valid values: [-2.0, 2.0].

A positive value decreases repetition, while a negative value decreases repetition.

Scenarios:

A higher presence_penalty is ideal for scenarios demanding diversity, enjoyment, or creativity, such as creative writing or brainstorming.

A lower presence_penalty is ideal for scenarios demanding consistency and terminology, such as technical documentation or other formal writing.

Default values for presence_penalty

How it works

Example

When using qwen-vl-plus-2025-01-25 for text extraction, set presence_penalty to 1.5.
Do not change the presence_penalty of QVQ.
response_format object (Optional) Defaults to {"type": "text"}

The format of the response.

Valid values: {"type": "text"} or {"type": "json_object"}.

When set to {"type": "json_object"}, the output will be standard JSON strings. For usage instructions, see Structured output.

If you specify {"type": "json_object"}, you must also prompt the model to output in the JSON format in System Message or User Message. For example, "Please output in the JSON format."
Supported models

max_tokens integer (Optional)

The maximum number of tokens to return in this request.

The value of max_tokens does not influence the generation process of the model. If the model generates more tokens than max_tokens the excessive content will be truncated.
The default and maximum values correspond to the maximum output length of each model.

This parameter is useful in scenarios that require a limited word count, such as summaries, keywords, controlling costs, or improving response time.

For qwen-vl-ocr, the max_tokens parameter (maximum output length) defaults to 4096. To increase this parameter value (4097 to 8192), send an email to modelstudio@service.aliyun.com with the following information: Alibaba Cloud account ID, image type (such as document images, e-commerce images, contracts, etc.), model name, estimated QPS and total daily requests, and the percentage of required output length exceeding 4096.
For QwQ, QVQ, and Qwen3 in thinking mode, max_tokens limits the length of response, but not the length of deep thinking.
n integer (Optional) Defaults to 1

The number of responses to generate.

Valid values: 1 to 4.

For scenarios that require multiple responses (such as creative writing and advertising copy), you can set a larger value for n.

Currently, only Qwen Plus and Qwen3 (non-thinking) is supported. The value is fixed at 1 when the tools parameter is specified.
Setting a larger value for n will not increase the input tokens, but will increase the output tokens.
enable_thinking boolean (Optional)

Specifies whether to use the thinking mode. Applicable for Qwen3 models.

Defaults to False for commercial Qwen3 models. Defaults to True for open-source Qwen3 models.

For Python SDK, use extra_body={"enable_thinking": xxx} instead.
thinking_budget integer (Optional)

The maximum reasoning length, effective only when enable_thinking is set to true. Applicable for Qwen3 models. For details, see Limit thinking length.

For Python SDK, use extra_body={"thinking_budget": xxx} instead.
seed integer (Optional)

This parameter makes the text generation process more predictable.

If you specify the same seed every time you call a model, while keeping other parameters unchanged, the model will attempt to return the same response as much as possible.

Value values: 0 to 231-1.

logprobs <i>boolean</i> (Optional)

Specifies whether to return the log probabilities of output tokens. Valid values:

true

false

Snapshot models of qwen-plus, qwen-turbo series (not the stable models) and open-source Qwen3 models support this parameter.
top_logprobs <i>integer</i> (Optional)

Specifies the number of most probable candidate tokens at each generation step.

Value range: [0,5]

Takes effect only when logprobs is true.

stop string or array (Optional)

If you specify this parameter, the model stops generating content when it is about to include the specified string or token_id.

You can set stop to sensitive words to control model response.

When stop is an array, it cannot contain both token_id and string at the same time. For example, you cannot specify ["hello",104307].
tools array (Optional)

Specifies an array of tools that the model can call. tools can include one or more tool objects. The model selects one or more (If parallel_tool_calls is true) appropriate tools to use during each function calling process.

Currently, Qwen VL does not support tools.
Properties

tool_choice string or object (Optional) Defaults to "auto"

If you want the model to adopt a predetermined tool selection policy for a certain type of query, such (such as forcing the use of a specific tool or no tool usage), you can specify tool_choice. Valid values:

"auto"

The model selects the tool on its own.

"none"

If you want no tool is used whatever the query is, set tool_choice to "none".

{"type": "function", "function": {"name": "the_function_to_call"}}

If you want to force the use of a specific tool, set tool_choice to {"type": "function", "function": {"name": "the_function_to_call"}}.

parallel_tool_calls boolean (Optional) Defaults to false

Specify whether to enable parallel tool calling.

translation_options object (Optional)

The translation parameters when using Qwen-MT.

Properties

For Python SDK, configure through extra_body: extra_body={"translation_options": xxx}.
chat completion object (non-stream)
 
{
    "choices": [
        {
            "message": {
                "role": "assistant",
                "content": "I am a large language model developed by Alibaba Cloud, my name is Qwen."
            },
            "finish_reason": "stop",
            "index": 0,
            "logprobs": null
        }
    ],
    "object": "chat.completion",
    "usage": {
        "prompt_tokens": 3019,
        "completion_tokens": 104,
        "total_tokens": 3123,
        "prompt_tokens_details": {
            "cached_tokens": 2048
        }
    },
    "created": 1735120033,
    "system_fingerprint": null,
    "model": "qwen-plus",
    "id": "chatcmpl-6ada9ed2-7f33-9de2-8bb0-78bd4035025a"
}
id string

The ID for this call.

choices array

An array of content generated by the model. This may contain one or more choices objects.

Properties

created integer

The timestamp when this chat completion was created.

model string

The name of the model used for this chat completion.

object string

Fixed as chat.completion.

service_tier string

Fixed as null.

system_fingerprint string

Fixed as null.

usage object

The token consumption of this chat completion.

Properties

chat completion chunk object (stream)
 
{"id":"chatcmpl-e30f5ae7-3063-93c4-90fe-beb5f900bd57","choices":[{"delta":{"content":"","function_call":null,"refusal":null,"role":"assistant","tool_calls":null},"finish_reason":null,"index":0,"logprobs":null}],"created":1735113344,"model":"qwen-plus","object":"chat.completion.chunk","service_tier":null,"system_fingerprint":null,"usage":null}
{"id":"chatcmpl-e30f5ae7-3063-93c4-90fe-beb5f900bd57","choices":[{"delta":{"content":"I am","function_call":null,"refusal":null,"role":null,"tool_calls":null},"finish_reason":null,"index":0,"logprobs":null}],"created":1735113344,"model":"qwen-plus","object":"chat.completion.chunk","service_tier":null,"system_fingerprint":null,"usage":null}
{"id":"chatcmpl-e30f5ae7-3063-93c4-90fe-beb5f900bd57","choices":[{"delta":{"content":"a large","function_call":null,"refusal":null,"role":null,"tool_calls":null},"finish_reason":null,"index":0,"logprobs":null}],"created":1735113344,"model":"qwen-plus","object":"chat.completion.chunk","service_tier":null,"system_fingerprint":null,"usage":null}
{"id":"chatcmpl-e30f5ae7-3063-93c4-90fe-beb5f900bd57","choices":[{"delta":{"content":"language","function_call":null,"refusal":null,"role":null,"tool_calls":null},"finish_reason":null,"index":0,"logprobs":null}],"created":1735113344,"model":"qwen-plus","object":"chat.completion.chunk","service_tier":null,"system_fingerprint":null,"usage":null}
{"id":"chatcmpl-e30f5ae7-3063-93c4-90fe-beb5f900bd57","choices":[{"delta":{"content":"model from","function_call":null,"refusal":null,"role":null,"tool_calls":null},"finish_reason":null,"index":0,"logprobs":null}],"created":1735113344,"model":"qwen-plus","object":"chat.completion.chunk","service_tier":null,"system_fingerprint":null,"usage":null}
{"id":"chatcmpl-e30f5ae7-3063-93c4-90fe-beb5f900bd57","choices":[{"delta":{"content":"Alibaba Cloud. I","function_call":null,"refusal":null,"role":null,"tool_calls":null},"finish_reason":null,"index":0,"logprobs":null}],"created":1735113344,"model":"qwen-plus","object":"chat.completion.chunk","service_tier":null,"system_fingerprint":null,"usage":null}
{"id":"chatcmpl-e30f5ae7-3063-93c4-90fe-beb5f900bd57","choices":[{"delta":{"content":"am called","function_call":null,"refusal":null,"role":null,"tool_calls":null},"finish_reason":null,"index":0,"logprobs":null}],"created":1735113344,"model":"qwen-plus","object":"chat.completion.chunk","service_tier":null,"system_fingerprint":null,"usage":null}
{"id":"chatcmpl-e30f5ae7-3063-93c4-90fe-beb5f900bd57","choices":[{"delta":{"content":"Qwen.","function_call":null,"refusal":null,"role":null,"tool_calls":null},"finish_reason":null,"index":0,"logprobs":null}],"created":1735113344,"model":"qwen-plus","object":"chat.completion.chunk","service_tier":null,"system_fingerprint":null,"usage":null}
{"id":"chatcmpl-e30f5ae7-3063-93c4-90fe-beb5f900bd57","choices":[{"delta":{"content":"","function_call":null,"refusal":null,"role":null,"tool_calls":null},"finish_reason":"stop","index":0,"logprobs":null}],"created":1735113344,"model":"qwen-plus","object":"chat.completion.chunk","service_tier":null,"system_fingerprint":null,"usage":null}
{"id":"chatcmpl-e30f5ae7-3063-93c4-90fe-beb5f900bd57","choices":[],"created":1735113344,"model":"qwen-plus","object":"chat.completion.chunk","service_tier":null,"system_fingerprint":null,"usage":{"completion_tokens":17,"prompt_tokens":22,"total_tokens":39,"completion_tokens_details":null,"prompt_tokens_details":{"audio_tokens":null,"cached_tokens":0}}}
id string

The request ID. Each chunk has the same id.

choices array

An array of chat completion choices. Can contain one or more choices objects. If include_usage is set to true, the last chunk will be empty.

Properties

created integer

The timestamp when this chat completion was created. Each chunk has the same timestamp.

model string

The name of the model used for this chat completion.

object string

Fixed as chat.completion.chunk.

service_tier string

Fixed as null.

system_fingerprintstring

Fixed as null.

usage object

The token consumption of this chat completion. It is only displayed in the last chunk when include_usage is true.

Properties

DashScope
Public cloud
endpoint for HTTP:

For Qwen LLMs: POST https://dashscope-intl.aliyuncs.com/api/v1/services/aigc/text-generation/generation

For Qwen VL model: POST https://dashscope-intl.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation

base_url for SDK:

Python:

dashscope.base_http_api_url = 'https://dashscope-intl.aliyuncs.com/api/v1'

Java:

Method 1:

 
import com.alibaba.dashscope.protocol.Protocol;
Generation gen = new Generation(Protocol.HTTP.getValue(), "https://dashscope-intl.aliyuncs.com/api/v1");
Method 2:

 
import com.alibaba.dashscope.utils.Constants;
Constants.baseHttpApiUrl="https://dashscope-intl.aliyuncs.com/api/v1";
You must first obtain an API key and configure the API key as an environment variable. If using the DashScope SDK, you must also install the DashScope SDK.
Request body
Text inputStreaming outputImage inputVideo inputTool callingAsynchronous callingText extraction
This is an example for single-round conversation. You can also try multi-round conversation.
PythonJavaPHP (HTTP)Node.js (HTTP)C# (HTTP)Go (HTTP)curl
 
import os
import dashscope

dashscope.base_http_api_url = 'https://dashscope-intl.aliyuncs.com/api/v1'
messages = [
    {'role': 'system', 'content': 'You are a helpful assistant.'},
    {'role': 'user', 'content': 'Who are you?'}
    ]
response = dashscope.Generation.call(
    # If environment variable is not configured, replace the line below with: api_key="sk-xxx",
    api_key=os.getenv('DASHSCOPE_API_KEY'),
    model="qwen-plus", # This example uses qwen-plus. You can change the model name as needed. Model list: https://www.alibabacloud.com/help/en/model-studio/getting-started/models
    messages=messages,
    result_format='message'
    )
print(response)
model string (Required)

The model name.

Supported models: Qwen LLMs (commercial and open-source), Qwen Coder, and Qwen VL models.

For specific model names and pricing, see Models and pricing.

messages array (Required)

A list of messages of the conversation so far.

For HTTP, put messages in the input object.
Message types

temperature float (Optional)

Controls the diversity of the generated text.

A higher temperature results in more diversified text, while a lower temperature results in more predictable text.

Value values: [0, 2)

For HTTP, put temperature in the parameters object.
Do not change the temperature of QVQ.
top_p float (Optional)

The probability threshold for nucleus sampling, which controls the diversity of the generated text.

A higher top_p results in more diversified text, while a lower top_p results in more predictable text.

Value range: (0,1.0].

Default value

In Java SDK, this is topP. For HTTP, put top_p in the parameters object.
Do not change the top_p of QVQ.
top_k integer (Optional)

The size of the candidate set for sampling. For example, when the value is 50, only the top 50 tokens with the highest scores are included in the candidate set for random sampling.

A higher top_k results in more diversified text, while a lower top_k results in more predictable text.

If top_k is set to None or a value greater than 100, top_k is disabled and only top_p takes effect.

The value must be greater than or equal to 0.

Default value

In Java SDK, this is topK. For HTTP, put top_k in the parameters object.
Do not change the top_k of QVQ.
enable_thinking boolean (Optional)

Specifies whether to use the reasoning mode. Applicable for Qwen3 models.

Defaults to False for commercial Qwen3 models. Defaults to True for open-source Qwen3 models.

For Java, this is enableThinking. For HTTP, put enable_thinking in parameters.
thinking_budget integer (Optional)

The maximum reasoning length, effective when enable_thinking is set to true. Applicable for all Qwen3 models. For details, see Limit thinking length.

repetition_penalty float (Optional)

Controls the repetition of the generated text.

A higher value above 1.0 reduces repetition.

The value must be greater than 0.

In Java SDK, this is repetitionPenalty. For HTTP, put repetition_penalty in the parameters object.
When extracting text using qwen-vl-plus_latest, or qwen-vl-plus_2025-01-25, set repetition_penalty to 1.0.
For Qwen-OCR, the default value of repetition_penalty is 1.05. This parameter significantly affects model performance. Do not modify it.
Do not change the repetition_penalty of QVQ.
presence_penalty float (Optional)

Controls the repetition of the generated text.

Valid values: [-2.0, 2.0].

A positive value decreases repetition, while a negative value decreases repetition.

Scenarios:

A higher presence_penalty is ideal for scenarios demanding diversity, enjoyment, or creativity, such as creative writing or brainstorming.

A lower presence_penalty is ideal for scenarios demanding consistency and terminology, such as technical documentation or other formal writing.

Default values for presence_penalty

How it works

Example

When using qwen-vl-plus-2025-01-25 for text extraction, set presence_penalty to 1.5.
Do not change the presence_penalty of QVQ.
Java SDK does not support this parameter. For HTTP, put presence_penalty in the parameters object.
vl_high_resolution_images boolean (Optional) defaults to false

Specifies whether to increase the default token limit for input images. The default token limit is 1,280. When this parameter is set to true, it is increased to 16,384. Supported by Qwen-VL and QVQ models.

In Java SDK, this is vlHighResolutionImages. The Java SDK version must be at least 2.20.8. For HTTP, place vl_high_resolution_images in the parameters object.
vl_enable_image_hw_output boolean (Optional) defaults to false

Specifies whether to return the dimensions of the scaled image. The model scales the input image. When this parameter is set to true, the height and width of the scaled image are returned. When streaming output is enabled, this information is returned in the last block. Qwen-VL models support this parameter.

In Java SDK, this is vlEnableImageHwOutput. The Java SDK version must be at least 2.20.8. For HTTP, place vl_enable_image_hw_output in the parameters object.
ocr_options object (Optional)

Built-in tasks when using Qwen-OCR.

Properties

This parameter requires DashScope Python SDK version 1.22.2 or later, or Java SDK version 2.18.4 or later.
For HTTP, place ocr_options in the parameters object.
max_tokens integer (Optional)

The maximum number of tokens to return in this request.

The value of max_tokens does not influence the generation process of the model. If the model generates more tokens than max_tokens the excessive content will be truncated.
The default and maximum values correspond to the maximum output length of each model.

This parameter is useful in scenarios that require a limited word count, such as summaries, keywords, controlling costs, or improving response time.

For qwen-vl-ocr, the max_tokens parameter (maximum output length) defaults to 4096. To increase this parameter value (4097 to 8192), send an email to modelstudio@service.aliyun.com with the following information: Alibaba Cloud account ID, image type (such as document images, e-commerce images, contracts, etc.), model name, estimated QPS and total daily requests, and the percentage of required output length exceeding 4096.
For QwQ, QVQ, and Qwen3 in thinking mode, max_tokens limits the length of response, but not the length of deep thinking.
In Java SDK, this is maxTokens (For Qwen-VL/Qwen-OCR or if Java SDK version 2.18.4 or later, this can also be maxLength). For HTTP, put max_tokens in the parameters object.
seed integer (Optional)

This parameter makes the text generation process more predictable.

If you specify the same seed every time you call a model, while keeping other parameters unchanged, the model will attempt to return the same response as much as possible.

Value values: 0 to 231-1.

For HTTP, put seed in the parameters object.
stream boolean (Optional) Defaults to false

Specifies whether to use streaming output. Valid values:

false: The model delivers the complete response at a time.

true: The model returns output in chunks as content is generated.

Only the Python SDK supports this parameter. For the Java SDK, use streamCall. For HTTP, set X-DashScope-SSE to enable in the request header.
Commerical Qwen3 (thinking mode), open source Qwen3, QwQ, and QVQ only supports steaming output.
incremental_output boolean (Optional) Defaults to false (For open source Qwen3, QwQ and QVQ, true)

Specifies whether to enable incremental output in the streaming output mode. Valid values:

false: Each output includes the entire sequence generated so far.

 
I
I like
I like apple
I like apple.
true: Each output excludes previous content. You need to obtain each part in real time to get the full response.

 
I
like
apple
.
In Java SDK, this is incrementalOutput. For HTTP, put incremental_output in the parameters object.
QwQ and Qwen3 in reasoning mode only support true. Because the default value for commercial Qwen3 is false, you need to manually set it to true in thinking mode.
Open source Qwen3 does not support false.
response_format object (Optional) Defaults to {"type": "text"}

The format of the response.

Valid values: {"type": "text"} or {"type": "json_object"}.

When set to {"type": "json_object"}, the output will be standard JSON strings. For usage instructions, see Structured output.

If you specify {"type": "json_object"}, you must also prompt the model to output in the JSON format in System Message or User Message. For example, "Please output in the JSON format."
In Java SDK, this is responseFormat. For HTTP, put response_format in the parameters object.
Supported models

result_format string (Optional) Defaults to "text" (For QwQ and open source Qwen3, "message")

The format of the result. Valid values: text and message.

We recommend that you use "message", which facilitates multi-round conversations.

The default value for all models will be message in the future.
In Java SDK, this is resultFormat. For HTTP, put result_format in the parameters object.
For Qwen-VL, QVQ, or Qwen-OCR, text is not effective.
In reasoning mode, the Qwen3 model only support message. Because the default value for commercial Qwen3 is text, you will need to change it to message.
If you are using the Java SDK to call open source Qwen3 and passed text, it will still return in message format.
logprobs boolean (Optional)

Specifies whether to return the logarithmic probabilities of output tokens. Valid values:

true

false

Snapshot models of qwen-plus, qwen-turbo series (not the stable models) and open-source Qwen3 models support this parameter.
top_logprobs integer (Optional)

Specifies the number of most probable candidate tokens to return at each generation step.

Valid values: [0,5]

Takes effect only when logprobs is true.

stop string or array (Optional)

If you specify this parameter, the model stops generating content when it is about to include the specified string or token_id.

You can set stop to sensitive words to control model response.

When stop is an array, it cannot contain both token_id and string at the same time. For example, you cannot specify ["hello",104307].
tools array (Optional)

Specifies an array of tools that the model can call.tools can include one or more tool objects. The model selects one or more (If paralell_tool_calls is true) appropriate tools to use during each function calling process.

If you specify this parameter, you must also set result_format to "message".

In the function calling process, you need to specify tools when initiating function calling and when submitting the results of a tool function to the model.

Currently, Qwen VL does not support tools.
Properties

For HTTP, put tools in the parameters JSON object.
tool_choice string or object (Optional)

Controls the tool selection when using tools. Valid values:

"none": Do not call tools. If tools is left empty, "none" is the default value.

"auto": The model decides whether to call a tool. If tools is not empty, "auto" is the default value.

Use an object structure to specify a tool for the model to call. For example, tool_choice={"type": "function", "function": {"name": "user_function"}}.

type Fixed as "function".

function

name: the tool to be called, such as "get_current_time".

In Java SDK, this is toolChoice. For HTTP, put tool_choice in the parameters object.
parallel_tool_calls boolean (Optional) Defaults to false

Specify whether to enable parallel tool calling.

translation_options object (Optional)

The translation parameters when using Qwen-MT.

Properties

In Java SDK, this is translationOptions. For HTTP, put translation_options into the parameters object.
chat completion object (same for stream and non-stream)
 
{
  "status_code": 200,
  "request_id": "902fee3b-f7f0-9a8c-96a1-6b4ea25af114",
  "code": "",
  "message": "",
  "output": {
    "text": null,
    "finish_reason": null,
    "choices": [
      {
        "finish_reason": "stop",
        "message": {
          "role": "assistant",
          "content": "I am Qwen, a large language model developed by Alibaba Cloud."
        }
      }
    ]
  },
  "usage": {
    "input_tokens": 22,
    "output_tokens": 17,
    "total_tokens": 39
  }
}
status_code string

The status code of this request. The status code 200 indicates that the request is successful. Other status codes indicate that the request failed.

The Java SDK does not return this parameter. Instead, an exception is thrown with status_code and message.
request_id string

The ID of this call.

In Java SDK, this is requestId.
code string

The error code. Empty when the call is successful.

Only Python SDK returns this parameter.
output object

Call result information.

Properties

usage map

The token consumption of this chat completion.

Properties

Error codes
If the model call failed and returned an error message, see Error messages for troubleshooting.

Feedback
