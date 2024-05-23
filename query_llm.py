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

import yaml
import os
import pandas as pd
import ast
import math
from llm_apis import query_local_llm
from difflib import Differ
from pprint import pprint


def save_to_csv(rq2_rows):
    """ Save the results to a CSV file.
    """

    # Open csv file
    df = pd.read_csv("results/rq2_results.csv")
    # print(df.head())

    # Add each list in rq2_rows to the df
    for row in rq2_rows:
        df.loc[len(df)] = row
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

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            template = list(yaml.load_all(file, Loader=yaml.FullLoader))
    except yaml.scanner.ScannerError:
        return []
    except yaml.constructor.ConstructorError:
        return []

    # Remove null document (--- null) from template
    template = [document for document in template if document is not None and "kind" in document and document["kind"] != "PodSecurityPolicy"]
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
                    if "name" in document["metadata"]:
                        return document["metadata"]["name"] == path_list[-1]

                # If the namespace was added during fixing, ignore it
                elif document["metadata"]["namespace"] == "test-ns":
                    if "name" in document["metadata"]:
                        return document["metadata"]["name"] == path_list[-1]

                # If the namespace was added during fixing, ignore it
                elif document["metadata"]["namespace"] == "busybox-namespace":
                    if "name" in document["metadata"]:
                        return document["metadata"]["name"] == path_list[-1]

                elif document["metadata"]["namespace"] == "kube-system":
                    if "name" in document["metadata"]:
                        return document["metadata"]["name"] == path_list[-1]

                elif document["metadata"]["namespace"] == path_list[1]:
                    if "name" in document["metadata"]:
                        return document["metadata"]["name"] == path_list[-1]

                elif document["metadata"]["namespace"] == path_list[1]:
                    if "name" in document["metadata"]:
                        return document["metadata"]["name"] == path_list[-1]

            # "namespace" not in document["metadata"]
            elif path_list[1] == "default" and "name" in document["metadata"]:
                return document["metadata"]["name"] == path_list[-1]

            elif "name" in document["metadata"]:
                return document["metadata"]["name"] == path_list[1]

    return False


def get_resource_snippet(paths: dict, template: dict) -> dict:
    """ Returns the resource snippet from the template.
    """

    resource = {}

    # Get the resource snippet from the template
    for document in template:
        if check_resource_path(paths["resource_path"].split("/"), document):
            resource = document

            # For now, ignore obg_path
            # Otherwise, add a new column "Original_snippet" to the df, 
            # with the snippet of the original yaml.

            # if paths["obj_path"]:
            #     for key in paths["obj_path"].split("/"):

            #         if not key:
            #             break

            #         if key == "env":
            #             break

            #         if key == "containers" and key not in resource:
            #             resource = resource["template"]["spec"]

            #         if key.isdigit():
            #             key = int(key)

            #         resource = resource[key]

    return resource


def save_yaml_snippet(snippet: str, snippet_type: str):
    """Save chart template data to a file.

    Args:
        snippet: A dictionary containing the snippet data to be saved.
        snippet_type: original OR llm

    Raises:
        IOError: If there is an error writing to the file.
    """

    # If snippet type is not dict, convert it to dict
    if not isinstance(snippet, dict):
        snippet = yaml.safe_load(snippet)

    file_path = f"tmp_snippets/{snippet_type}_snippet.yaml"
    # Save the snippet to a YAML file at file_path
    with open(file_path, 'w', encoding="utf-8") as file:
        yaml.dump(snippet, file, sort_keys=False)


def build_query(rq1_df: pd.DataFrame):

    rq2_rows = []

    # Iterate over each df row
    for _, row in rq1_df.iterrows():
        # Convert the row["Resources"] column to a list
        resource = ast.literal_eval(row["Resource"])

        paths = {
            "resource_path": resource[0],
            "obj_path": resource[1]
        }
        resource_type = paths["resource_path"].split("/")[0]

        # Build the query
        query = "You are a software engineer working on a Kubernetes project. You need to refactor the following " + resource_type + " YAML resource because " + row["Description"].lower() + ". Output only the refactored YAML. "

        aux = [
            row["Chart"],
            row["Tool"],
            row["Alert_ID"],
            row["Resource"],
            row["Original_YAML"],
            query
        ]

        rq2_rows.append(aux)

    return rq2_rows


def validate_syntax():
    """Validate the syntax of the YAML snippet.
    """

    return 0

    # Run kubeconfom on the snippet to validate the syntax
    os.system("kubeconform -summary -output json tmp_snippets/original_snippet.yaml > tmp_snippets/syntax.json")

    # Read the JSON file
    with open("tmp_snippets/syntax.json", "r", encoding="utf-8") as file:
        original_syntax_error = yaml.safe_load(file)

    # Run kubeconfom on the snippet to validate the syntax
    os.system("kubeconform -summary -output json tmp_snippets/refactored_snippet.yaml > tmp_snippets/syntax.json")

    # Read the JSON file
    with open("tmp_snippets/syntax.json", "r", encoding="utf-8") as file:
        refactored_syntax_error = yaml.safe_load(file)

    return math.fabs(original_syntax_error["summary"]["invalid"] - refactored_syntax_error["summary"]["invalid"])


def compare_files(original_snippet, refactored_snippet):
    """Compare the original and refactored snippets using the difflib.Differ library.
    https://docs.python.org/3/library/difflib.html#differ-example

    Each line of a Differ delta begins with a two-letter code:
    Code  | Meaning
    ---------------------------------------
    '- '  | line unique to sequence 1
    '+ '  | line unique to sequence 2
    '  '  | line common to both sequences
    '? '  | line not present in either input sequence
    """

    added = len(refactored_snippet) - len(original_snippet) if len(refactored_snippet) > len(original_snippet) else 0
    removed = len(original_snippet) - len(refactored_snippet) if len(original_snippet) > len(refactored_snippet) else 0
    changed = 0

    d = Differ()
    d.ignore_prefixes = ["#"]

    result = list(d.compare(original_snippet, refactored_snippet))
    # pprint(result)

    for idx, line in enumerate(result):
        if line.startswith("-"):
            if idx+1 < len(result) and result[idx + 1].startswith("+"):
                changed += 1

    return added, removed, changed


def evaluate_llm_answers(rq2_rows):
    added = 0
    removed = 0
    changed = 0

    for row in rq2_rows:

        # OPTIONAL: To avoid problems or key re-ordering, we can save both snippets with 
        # sort_keys=True.

        # Save YAML to temp files
        save_yaml_snippet(row[4], "original")
        save_yaml_snippet(row[7], "refactored")

        syntax_error = validate_syntax()
        row.append(syntax_error)

        with open("tmp_snippets/original_snippet.yaml", "r", encoding="utf-8") as file:
            original_snippet = file.readlines()

        with open("tmp_snippets/refactored_snippet.yaml", "r", encoding="utf-8") as file:
            refactored_snippet = file.readlines()

        added, removed, changed = compare_files(original_snippet, refactored_snippet)
        row.append(changed)
        row.append(added)
        row.append(removed)

    return rq2_rows


def query_llm(chart_name: str):

    # Parse rq1_results csv file
    rq1_df = pd.read_csv("results/rq1_results.csv")

    ###
    rq1_df = rq1_df[:2]
    ###

    # Build the query (list of rows --- lists)
    rq2_rows = build_query(rq1_df)

    # Query LLM models
    rq2_rows = query_local_llm(rq2_rows)

    # Evaluate LLM answers
    # Add Changed, Added, Removed columns to the df
    rq2_rows = evaluate_llm_answers(rq2_rows)

    # Save the results to a CSV file
    save_to_csv(rq2_rows)
