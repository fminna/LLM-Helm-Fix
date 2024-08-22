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
import pandas as pd
import time
import google.api_core.exceptions


def query_chatgpt(idx: int, jdx: int):
    """Query ChatGPT to generate fixes.
    """

    # df = pd.read_csv("results/chatgpt_queries.csv")
    df = pd.read_csv("results/llm_short_queries.csv")

    client = OpenAI()
    rows = []
    counter = 0

    for idx, row in df.iloc[idx:jdx].iterrows():

        chart_name = row["Chart"]
        alert_id = row["Alert_ID"]

        print(f"{idx} - ChatGPT: Processing {chart_name} - {alert_id} ...")
        counter += 1

        try:
            completion = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": row["Query"]},
                    {"role": "user", "content": row["Original_YAML"]}
                ]
            )
        except Exception as e:
            print(f"Error parsing YAML: {e}")
            answer_dict = "Failed to parse YAML."

        input_tokens = completion.usage.prompt_tokens
        output_tokens = completion.usage.completion_tokens

        answer = completion.choices[0].message.content
        answer = answer.replace("---", "")
        answer = answer.replace("```yaml", "")
        answer = answer.replace("```", "")

        try:
            answer_dict = yaml.load(answer, Loader=yaml.FullLoader)
        except Exception as e:
            print(f"Error parsing YAML: {e}")
            answer_dict = "Failed to parse YAML."

        new_row = [
                chart_name,
                alert_id,
                row["Tool"],
                row["Resource"],
                row["Query"],
                "ChatGPT-4o-mini-2024-07-18",
                input_tokens,
                answer_dict,
                output_tokens,
                row["Original_YAML"]
            ]
        rows.append(new_row)

        if counter == 20:
            answer_df = pd.read_csv("results/llm_chatgpt_answers.csv")
            for row in rows:
                answer_df.loc[len(answer_df)] = row
            answer_df.to_csv("results/llm_chatgpt_answers.csv", index=False)
            rows = []
            counter = 0

    answer_df = pd.read_csv("results/llm_chatgpt_answers.csv")
    for row in rows:
        answer_df.loc[len(answer_df)] = row
    answer_df.to_csv("results/llm_chatgpt_answers.csv", index=False)


def query_gemini(idx: int, jdx: int) -> list:
    """ Query the Gemini model to generate fixes.

    API Troubleshooting guide
    https://ai.google.dev/gemini-api/docs/troubleshooting
    """

    df = pd.read_csv("results/chatgpt_queries.csv")

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

    # safety_settings = [
    #     {
    #         "category": "HARM_CATEGORY_HARASSMENT",
    #         "threshold": "BLOCK_MEDIUM_AND_ABOVE"
    #     },
    #     {
    #         "category": "HARM_CATEGORY_HATE_SPEECH",
    #         "threshold": "BLOCK_MEDIUM_AND_ABOVE"
    #     },
    #     {
    #         "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
    #         "threshold": "BLOCK_MEDIUM_AND_ABOVE"
    #     },
    #     {
    #         "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
    #         "threshold": "BLOCK_MEDIUM_AND_ABOVE"
    #     },
    # ]

    safety_settings = []

    model = genai.GenerativeModel(model_name="gemini-1.5-pro-latest",
                             generation_config=generation_config,
                             safety_settings=safety_settings)
    # convo = model.start_chat()

    counter = 0
    rows = []

    for idx, row in df.iloc[idx:jdx].iterrows():
        chart_name = row["Chart"]
        alert_id = row["Alert_ID"]
        query = str(row["Query"]) + " " + str(row["Original_YAML"])

        print(f"{idx} - Gemini: Processing {chart_name} - {alert_id} ...")
        counter += 1
        correct = False

        try:
            # convo.send_message(query)
            response = model.generate_content(
                contents=query,
                request_options={"timeout": 1000}
            )
            try:
                answer = response.text
                correct = True
            except Exception as e:
                answer = f"Failed to generate a response. {e}"
                print(answer)

        except google.api_core.exceptions.InternalServerError as e:
            answer = "Failed to generate a response. google.api_core.exceptions.InternalServerError"
            print(answer)

        except google.api_core.exceptions.RetryError as e:
            answer = "Failed to generate a response. google.api_core.exceptions.RetryError"
            print(answer)

        except google.api_core.exceptions.ResourceExhausted:
            time.sleep(60)
            try:
                response = model.generate_content(
                    contents=query,
                    request_options={"timeout": 1000}
                )
                answer = response.text
                correct = True
            except google.api_core.exceptions.InternalServerError as e:
                answer = "Failed to generate a response. google.api_core.exceptions.InternalServerError"
                print(answer)
            except ValueError as e:
                answer = f"Failed to generate a response. {e}"
                print(answer)
            except Exception as e:
                answer = f"Failed to generate a response. {e}"
                print(answer)

        except google.generativeai.types.generation_types.StopCandidateException as e:
            answer = "Failed to generate a response. google.generativeai.types.generation_types.StopCandidateException"
            print(answer)

        except Exception as e:
            answer = f"Failed to generate a response. {e}"
            print(answer)

        if correct:
            answer = answer.replace("---", "")
            answer = answer.replace("```yaml", "")
            answer = answer.replace("```", "")
            try:
                answer_dict = yaml.load(answer, Loader=yaml.FullLoader)
            except Exception as e:
                print(f"Error parsing YAML: {e}")
                answer_dict = "Failed to parse YAML."
        else:
            answer_dict = "Failed to generate a response. Unkown error."

        input_tokens = model.count_tokens(query)
        input_tokens = input_tokens.total_tokens
        output_tokens = model.count_tokens(answer).total_tokens

        new_row = [
            chart_name,
            alert_id,
            row["Tool"],
            query,
            "Gemini_1.5",
            input_tokens,
            answer_dict,
            output_tokens
        ]
        rows.append(new_row)

        if counter == 50:
            answer_df = pd.read_csv("results/llm_gemini_answers.csv")
            for row in rows:
                answer_df.loc[len(answer_df)] = row
            answer_df.to_csv("results/llm_gemini_answers.csv", index=False)
            rows = []
            counter = 0
            time.sleep(120)

    answer_df = pd.read_csv("results/llm_gemini_answers.csv")
    for row in rows:
        answer_df.loc[len(answer_df)] = row
    answer_df.to_csv("results/llm_gemini_answers.csv", index=False)


def query_claude_3(idx: int, jdx: int):
    """ Invokes Anthropic Claude 3 Sonnet to run an inference using the input
    provided in the request body.
    """

    df = pd.read_csv("results/llm_short_queries.csv")

    # Initialize the Amazon Bedrock runtime client
    client = boto3.client(
        service_name="bedrock-runtime", region_name="us-west-2"
    )

    # Invoke Claude 3 with the text prompt
    model_id = "anthropic.claude-3-sonnet-20240229-v1:0"

    rows = []
    counter = 0

    for idx, row in df.iloc[idx:jdx].iterrows():
        chart_name = row["Chart"]
        alert_id = row["Alert_ID"]
        query_type_error = False

        try:
            query = str(row["Query"]) + " " + str(row["Original_YAML"])
        except TypeError:
            query_type_error = True

        print(f"{idx} - Claude: Processing {chart_name} - {alert_id} ...")
        counter += 1

        if query_type_error:
            input_tokens = 0
            answer_dict = "Failed: query type error."
            output_tokens = 0

        else:
            try:
                response = client.invoke_model(
                    modelId=model_id,
                    body=json.dumps(
                        {
                            "anthropic_version": "bedrock-2023-05-31",
                            "max_tokens": 4096,
                            "messages": [
                                {
                                    "role": "user",
                                    "content": [{"type": "text", "text": query}],
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
                answer = output_list[0]["text"]
                answer = answer.replace("---", "")
                answer = answer.replace("```yaml", "")
                answer = answer.replace("```", "")

                try:
                    answer_dict = yaml.load(answer, Loader=yaml.FullLoader)

                except Exception as e:
                    print(f"Error parsing YAML: {e}")
                    answer_dict = "Failed to parse YAML."

            except ClientError as err:
                logger.error(
                    "Couldn't invoke Claude 3 Sonnet. Here's why: %s: %s",
                    err.response["Error"]["Code"],
                    err.response["Error"]["Message"],
                )
                raise

            except Exception:
                answer_dict = "Failed to generate a response."

        new_row = [
                chart_name,
                alert_id,
                query,
                "Claude_3_Sonnet",
                input_tokens,
                answer_dict,
                output_tokens,
                row["Tool"],
                row["Resource"]
            ]
        rows.append(new_row)

        if counter == 50:
            answer_df = pd.read_csv("results/llm_claude_answers2.csv")
            for row in rows:
                answer_df.loc[len(answer_df)] = row
            answer_df.to_csv("results/llm_claude_answers2.csv", index=False)
            rows = []
            counter = 0

    answer_df = pd.read_csv("results/llm_claude_answers2.csv")
    for row in rows:
        answer_df.loc[len(answer_df)] = row
    answer_df.to_csv("results/llm_claude_answers2.csv", index=False)


def query_llama_3(idx: int, jdx: int):
    """ Query the Llama model to generate fixes.
    """

    # df = pd.read_csv("results/llm_short_queries.csv")
    df = pd.read_csv("results/chatgpt_queries.csv")

    # Initialize the Amazon Bedrock runtime client
    client = boto3.client(
        service_name="bedrock-runtime", region_name="us-west-2"
    )

    model_id = "meta.llama3-70b-instruct-v1:0"

    counter = 0
    rows = []

    for idx, row in df.iloc[idx:jdx].iterrows():
        chart_name = row["Chart"]
        alert_id = row["Alert_ID"]
        query = str(row["Query"]) + " " + str(row["Original_YAML"])

        print(f"{idx} - LLama: Processing {chart_name} - {alert_id} ...")
        counter += 1

        # Embed the prompt in Llama 3's instruction format.
        formatted_prompt = f"""
        <|begin_of_text|>
        <|start_header_id|>user<|end_header_id|>
        {query}
        <|eot_id|>
        <|start_header_id|>assistant<|end_header_id|>
        """

        # Format the request payload using the model's native structure.
        native_request = {
            "prompt": formatted_prompt,
            "max_gen_len": 512,
            "temperature": 0.5,
        }

        # Convert the native request to JSON.
        request = json.dumps(native_request)

        correct = False
        try:
            # Invoke the model with the request.
            response = client.invoke_model(modelId=model_id, body=request)
            correct = True

        except (ClientError, Exception) as e:
            print(f"ERROR: Can't invoke '{model_id}'. Reason: {e}")
            answer_dict = "Failed to generate a response."

        if correct:
            # Decode the response body.
            model_response = json.loads(response["body"].read())

            input_tokens = model_response["prompt_token_count"]
            output_tokens = model_response["generation_token_count"]

            # Extract and print the response text.
            answer = model_response["generation"]
            answer = answer.replace("---", "")
            answer = answer.replace("```yaml", "")
            answer = answer.replace("```", "")

            try:
                answer_dict = yaml.load(answer, Loader=yaml.FullLoader)
            except Exception as e:
                print(f"Error parsing YAML: {e}")
                answer_dict = "Failed to parse YAML."

        new_row = [
                chart_name,
                alert_id,
                row["Tool"],
                row["Resource"],
                row["Original_YAML"],
                query,
                "Llama_3_70b",
                input_tokens,
                answer_dict,
                output_tokens
            ]
        rows.append(new_row)

        if counter == 10:
            answer_df = pd.read_csv("results/llm_llama_answers.csv")
            for row in rows:
                answer_df.loc[len(answer_df)] = row
            answer_df.to_csv("results/llm_llama_answers.csv", index=False)
            rows = []
            counter = 0

    answer_df = pd.read_csv("results/llm_llama_answers.csv")
    for row in rows:
        answer_df.loc[len(answer_df)] = row
    answer_df.to_csv("results/llm_llama_answers.csv", index=False)
