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

""" This script implements the main function.
"""

import argparse
import sys
from parse_tool_output import parse_output
from query_llm import query_llm
from evaluate_fixes import evaluate_fixes
from chart_retrieval import scan_artifact_hub

# Define the argument parser
parser = argparse.ArgumentParser(description='Script to fix Helm Charts misconfigurations using LLMs.')

# Define a --parse-output argument that must be passed with two string values. For example, --parse-output chart_name tool.
parser.add_argument('--parse-output', action='store_true', help='Parse the output of a chart analyzer tool.')
parser.add_argument('--query-llm', action='store_true', help='Query a LLM for a fix.')
parser.add_argument('--evaluate-fixes', action='store_true', help='Evaluate the LLM fixes.')
parser.add_argument('--chart-retrieval', action='store_true', help='Retrieve a Helm Chart.')

# Parse the arguments
args = parser.parse_args()


def main():
    """ The main function.
    """

    if args.parse_output:
        print("Parsing the output of the chart analyzer tools...\n")
        parse_output()

    elif args.query_llm:
        print("Querying the LLM for a fix...\n")
        query_llm()

    elif args.evaluate_fixes:
        print("Evaluating the LLM fixes...\n")
        evaluate_fixes()

    elif args.chart_retrieval:
        print("Retrieving all Helm Charts from Artifact Hub...\n")
        scan_artifact_hub()

    else:
        print("No arguments passed. Exiting...")
        sys.exit(1)

if __name__ == "__main__":
    main()
