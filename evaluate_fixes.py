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

""" Evaluate the LLM fixes.
"""



def evaluate_fixes(llm: str):

    # TODO: integrate the fixes from ChatGPT and Gemini into the original document resource and check
    # whether they satisfy the tool or not.

    # Print ChatGPT fix
    if llm == "chatgpt":
        print("ChatGPT fix:\n")
        with open("tmp_snippets/chatgpt_ns_snippet.yaml", "r") as file:
            print(file.read())

    # Print Gemini fix
    elif llm == "gemini":
        print("Gemini fix:\n")
        with open("tmp_snippets/gemini_ns_snippet.yaml", "r") as file:
            print(file.read())

    # Run the tool (e.g., checkov)
            
    # Parse the tool output
    # if no alert about current misconfigurations, then the fix is successful
    # else, the fix is unsuccessful
            
    # Save LLM results into Excel
