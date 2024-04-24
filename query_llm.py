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

""" Query LLM to generate fixes.
"""

import json
import yaml
import os
import pandas as pd
import ast
import requests


def save_to_csv(fix_dict):
    """ Save the results to a CSV file.
    """

    # Open csv file
    df = pd.read_csv("results/rq2_results.csv")
    # print(df.head())

    # for check_id in fix_dict:

    #     new_row = [
    #         chart_name, \
    #         tool_name, \
    #         check_id, \
    #         fix_dict[check_id]["description"], \
    #         fix_dict[check_id]["count"], \
    #         fix_dict[check_id]["resources"]
    #     ]

    #     df.loc[len(df)] = new_row

    # Save the CSV file
    df.to_csv("results/rq2_results.csv", index=False)


def parse_yaml_template(chart_name: str) -> list:
    """Parses a Helm chart template yaml file and returns it as a dictionary.

    Args:
        folder: The folder containing the Helm Chart template.
        chart_name: The name of the Helm Chart to parse.

    Returns:
        A dictionary containing the parsed contents of the template.yaml file.
    """

    # Parse and return the multi-document YAML file while preserving comments
    file_path = f"templates/{chart_name}_template.yaml"
    with open(file_path, "r", encoding="utf-8") as file:
        template = list(yaml.load_all(file, Loader=yaml.FullLoader))

    # Remove null document (--- null) from template
    template = [document for document in template if document is not None and document["kind"] != "PodSecurityPolicy"]
    return template


def check_resource_path(path_list: str, document: dict) -> bool:
    """Check if the resource path exists in the template.

    Args:
        path_list: The resource path to check.
        document: The template to check.

    Returns:
        True if the resource path exists, False otherwise.
    """

    if path_list and document:
        if document["kind"].casefold() == path_list[0].casefold():

            if "namespace" in document["metadata"]:

                # Ignore default ns
                if document["metadata"]["namespace"] == "default":
                    return document["metadata"]["name"] == path_list[-1]

                # If the namespace was added during fixing, ignore it
                elif document["metadata"]["namespace"] == "test-ns":
                    return document["metadata"]["name"] == path_list[-1]
                
                # If the namespace was added during fixing, ignore it
                elif document["metadata"]["namespace"] == "busybox-namespace":
                    return document["metadata"]["name"] == path_list[-1]

                elif document["metadata"]["namespace"] == "kube-system":
                    return document["metadata"]["name"] == path_list[-1]

                elif document["metadata"]["namespace"] == path_list[1]:
                    return document["metadata"]["name"] == path_list[-1]

                elif document["metadata"]["namespace"] == path_list[1] and \
                    document["metadata"]["name"] == path_list[-1]:
                    return True

            # "namespace" not in document["metadata"]
            elif path_list[1] == "default":
                return document["metadata"]["name"] == path_list[-1]

            elif document["metadata"]["name"] == path_list[1]:
                return True

    return False


def get_resource_snippet(paths: dict, template: dict) -> dict:
    """ Returns the resource snippet from the template.
    """

    resource = {}

    # Get the resource snippet from the template
    for document in template:
        if check_resource_path(paths["resource_path"].split("/"), document):
            resource = document

            if paths["obj_path"]:
                for key in paths["obj_path"].split("/"):
                    if key.isdigit():
                        key = int(key)
                    resource = resource[key]

    return resource


def save_yaml_snippet(snippet: str, snippet_type: str):
    """Save chart template data to a file.

    Args:
        snippet: A dictionary containing the snippet data to be saved.
        snippet_type: original OR llm

    Raises:
        IOError: If there is an error writing to the file.
    """

    file_path = f"tmp_snippets/{snippet_type}_snippet.yaml"
    # Save the snippet to a YAML file at file_path
    with open(file_path, 'w', encoding="utf-8") as file:
        yaml.dump(snippet, file, sort_keys=False)


def build_query(chart_name: str):
    # Parse rq1_full_results csv file
    rq1_df = pd.read_csv("results/rq1_results.csv")

    # Load chart template
    template = parse_yaml_template(chart_name)

    queries = []

    # Iterate over each df row
    for _, row in rq1_df.iterrows():
        # Convert the row["Resources"] column to a list
        resources_list = ast.literal_eval(row["Resources"])

        for resource in resources_list:
            paths = {
                "resource_path": resource[0],
                "obj_path": resource[1]
            }

            # Get the resource snippet from the template
            snippet = get_resource_snippet(paths, template)
            resource_type = paths["resource_path"].split("/")[0]

            # Build the query
            query = "You are a software engineer working on a Kubernetes project. You need to refactor the following " + resource_type + " YAML resource because " + row["Description"].lower() + ". Output only the refactored YAML. "

            aux = {
                "text": query,
                "snippet": snippet
            }
            queries.append(aux)

    return queries


def query_chatgpt(queries: list):
    # Read API key from environment variable
    openai_api_key = os.getenv("CHATGPT_API_KEY")
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {openai_api_key}"
    }

    answers = []

    for query in queries:
        data = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {
                    "role": "system",
                    "content": query["text"] + query["snippet"]
                }
            ]
        }

        response = requests.post(url, headers=headers, data=json.dumps(data), timeout=30)
        response = response.json()
        answers.append(response["choices"][0]["message"]["content"])

    return answers


def query_llm(chart_name: str):

    # Build the query
    queries = build_query(chart_name)

    # for query in queries:
    #     print(query["text"])
        # print(yaml.dump(query["snippet"], sort_keys=False))

    # Query each LLM model
    chatgpt_results = query_chatgpt(queries)

    # ...

    # Evaluate LLM answers

    # Save the results to a CSV file
