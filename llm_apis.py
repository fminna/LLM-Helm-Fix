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
import yaml


def query_chatgpt(rq2_rows: list):
    """Query the ChatGPT model to generate fixes.
    """
    # client = OpenAI()

    # for row in rq2_rows:
        # completion = client.chat.completions.create(
        # # model="gpt-3.5-turbo",
        # model="babbage-002",
        # messages=[
        #     {
        #         "role": "system",
        #         "content": "You are a poetic assistant, skilled in explaining complex programming concepts with creative flair."
        #     },
        #     {
        #         "role": "user",
        #         "content": "Compose a poem that explains the concept of recursion in programming."
        #     }
        # ])

        # answer = completion.choices[0].message

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


def query_gemini():
    pass


def query_llama():
    pass


def query_llm():
    pass
