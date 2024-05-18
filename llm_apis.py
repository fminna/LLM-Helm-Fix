# Copyright 2024
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

""" Query LLM using APIs to get refactored chart snippets.
"""

from openai import OpenAI
import google.generativeai as genai
from asyncio.log import logger
import boto3
import json
from botocore.exceptions import ClientError
import yaml
import os
import requests


def query_local_llm(rq2_rows: list):
    failed_to_answer = "no"
    answer_time = 0.0

    aux = rq2_rows[0].copy()
    rq2_rows.append(aux)
    aux = rq2_rows[1].copy()
    rq2_rows.append(aux)

    with open("tmp_snippets/chatgpt_ns_snippet.yaml", "r", encoding="utf-8") as file:
        chatgpt_ns = yaml.load(file, Loader=yaml.FullLoader)
    rq2_rows[0].append("chatgpt")
    rq2_rows[0].append(chatgpt_ns)

    # TODO: evaluate LLM failures to answer
    rq2_rows[0].append(failed_to_answer)

    # Measure LLM answer time
    rq2_rows[0].append(answer_time)

    with open("tmp_snippets/chatgpt_mem_snippet.yaml", "r", encoding="utf-8") as file:
        chatgpt_mem = yaml.load(file, Loader=yaml.FullLoader)
    rq2_rows[1].append("chatgpt")
    rq2_rows[1].append(chatgpt_mem)
    rq2_rows[1].append(failed_to_answer)
    rq2_rows[1].append(answer_time)

    with open("tmp_snippets/gemini_ns_snippet.yaml", "r", encoding="utf-8") as file:
        gemini_ns = yaml.load(file, Loader=yaml.FullLoader)
    rq2_rows[2].append("gemini")
    rq2_rows[2].append(gemini_ns)
    rq2_rows[2].append(failed_to_answer)
    rq2_rows[2].append(answer_time)

    with open("tmp_snippets/gemini_mem_snippet.yaml", "r", encoding="utf-8") as file:
        gemini_mem = yaml.load(file, Loader=yaml.FullLoader)
    rq2_rows[3].append("gemini")
    rq2_rows[3].append(gemini_mem)
    rq2_rows[3].append(failed_to_answer)
    rq2_rows[3].append(answer_time)

    return rq2_rows


############################################


def invoke_claude_3_with_text(prompt):
    """ Invokes Anthropic Claude 3 Sonnet to run an inference using the input
    provided in the request body.
    """

    # Initialize the Amazon Bedrock runtime client
    client = boto3.client(
        service_name="bedrock-runtime", region_name="us-west-2"
    )

    # Invoke Claude 3 with the text prompt
    model_id = "anthropic.claude-3-sonnet-20240229-v1:0"

    try:
        response = client.invoke_model(
            modelId=model_id,
            body=json.dumps(
                {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 1024,
                    "messages": [
                        {
                            "role": "user",
                            "content": [{"type": "text", "text": prompt}],
                        }
                    ],
                }
            ),
        )

        # Process and print the response
        result = json.loads(response.get("body").read())
        input_tokens = result["usage"]["input_tokens"]
        output_tokens = result["usage"]["output_tokens"]
        output_list = result.get("content", [])

        # print("Invocation details:")
        # print(f"- The input length is {input_tokens} tokens.")
        # print(f"- The output length is {output_tokens} tokens.")

        print(f"Answer: ")
        for output in output_list:
            print(output["text"])

        return result

    except ClientError as err:
        logger.error(
            "Couldn't invoke Claude 3 Sonnet. Here's why: %s: %s",
            err.response["Error"]["Code"],
            err.response["Error"]["Message"],
        )
        raise


def query_chatgpt(query: str) -> dict:
    """Query the ChatGPT model to generate fixes.
    """
    # client = OpenAI()
    # TODO
    pass


def query_gemini(query: str) -> dict:
    """ Query the Gemini model to generate fixes.
    """

    # Get API Key from the environmental variable
    api_key = os.getenv("GEMINI_API_KEY")
    genai.configure(api_key=api_key)

    # Set up the model
    generation_config = {
        "temperature": 1,
        "top_p": 0.95,
        "top_k": 0,
        "max_output_tokens": 8192,
    }

    safety_settings = [
        {
            "category": "HARM_CATEGORY_HARASSMENT",
            "threshold": "BLOCK_MEDIUM_AND_ABOVE"
        },
        {
            "category": "HARM_CATEGORY_HATE_SPEECH",
            "threshold": "BLOCK_MEDIUM_AND_ABOVE"
        },
        {
            "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
            "threshold": "BLOCK_MEDIUM_AND_ABOVE"
        },
        {
            "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
            "threshold": "BLOCK_MEDIUM_AND_ABOVE"
        },
    ]

    model = genai.GenerativeModel(model_name="gemini-1.5-pro-latest",
                                generation_config=generation_config,
                                safety_settings=safety_settings)

    # Query tokens count
    response = model.count_tokens(query)
    print(f"Prompt Token Count: {response.total_tokens}")

    convo = model.start_chat()
    convo.send_message(query)

    answer = convo.last.text
    answer = answer.replace("---", "")

    answer_dict = yaml.load(answer, Loader=yaml.FullLoader)
    return answer_dict


def query_hugging_face(query: str) -> dict:
    """ Query the Hugging Face model to generate fixes.

    List of models: https://huggingface.co/docs/transformers/en/model_doc/code_llama
    """

    # Model Link: https://huggingface.co/CohereForAI/c4ai-command-r-plus
    model = "CohereForAI/c4ai-command-r-plus"

    api_key = os.getenv("HUGGING_FACE_API_KEY")

    API_URL = f"https://api-inference.huggingface.co/models/{model}"
    headers = {"Authorization": "Bearer " + api_key}

    # Parameters can be different based on which model is used.
    # Please refer to this page: https://huggingface.co/docs/api-inference/detailed_parameters
    # payload = {
    #     "inputs": query,
    #     "parameters": {
    #         "max_new_tokens": 250,
    #         "max_length": 500,
    #         "temperature": 1.0
    #     },
    # }

    payload = {
        "inputs": "What is a large language model?"
    }

    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=10)
        print(response.json())


    except requests.exceptions.ReadTimeout:
        print("LLM Error: The request timed out!!!")
        return None


#####################################

# TODO: convert YAML resource snippet to the following query string type.

query = """
You are a software engineer working on a Kubernetes project. You need to refactor the following ServiceAccount YAML resource because the default namespace should not be used. You must only output YAML code between --- characters, with no additional text or description.

--- 
apiVersion: v1 
kind: ServiceAccount
metadata: 
  name: release-name-mysql 
  namespace: default 
  labels: 
    app.kubernetes.io/name: mysql 
    helm.sh/chart: mysql-9.7.1 
    app.kubernetes.io/instance: release-name 
    app.kubernetes.io/managed-by: Helm annotations: null automountServiceAccountToken: true 
secrets: 
  - name: release-name-mysql 
---
"""

# query_hugging_face(query)
