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

import pandas as pd
import yaml
import os
import json
import ast


def save_to_csv(rows: list):
    """ Save the results to a CSV file.
    """

    # Open csv file
    df = pd.read_csv("results/rq3_results.csv")
    # print(df.head())

    for row in rows:
        df.loc[len(df)] = row
    df.to_csv("results/rq3_results.csv", index=False)


def run_checkov(alert_id: str) -> str:
    """ Run Checkov on the refactored YAML snippet.
    """

    os.system("checkov -f tmp_snippets/refactored.yaml --quiet --compact --framework kubernetes -o json > tmp_snippets/results.json")

    with open("tmp_snippets/results.json", "r", encoding="utf-8") as file:
        results = json.load(file)

    fixed = "yes"

    if "results" in results and "failed_checks" in results["results"]:
        for check in results["results"]["failed_checks"]:
            if check["check_id"] == alert_id:
                fixed = "no"
                break

    return fixed


def run_datree(alert_id: str) -> str:
    """ Run Datree on the refactored YAML snippet.
    """

    os.system("")

    with open("tmp_snippets/results.json", "r", encoding="utf-8") as file:
        results = json.load(file)

    fixed = "yes"

    if "policyValidationResults" and results["policyValidationResults"] is not None:
        for check in results["policyValidationResults"][0]["ruleResults"]:
            if alert_id == check['identifier']:
                fixed = "no"
                break

    return fixed


def run_kics(alert_id: str) -> str:
    """ Run KICS on the refactored YAML snippet.
    """

    os.system("")

    with open("tmp_snippets/results.json", "r", encoding="utf-8") as file:
        results = json.load(file)

    fixed = "yes"

    for check in results["queries"]:
        if alert_id == check['query_id']:
            fixed = "no"
            break

    return fixed


def run_kubelinter(alert_id: str) -> str:
    """ Run Kubelinter on the refactored YAML snippet.
    """

    os.system("")

    with open("tmp_snippets/results.json", "r", encoding="utf-8") as file:
        results = json.load(file)

    fixed = "yes"

    if "Reports" in results:
        if results["Reports"] is None or not results["Reports"]:
            pass

        else:
            for check in results["Reports"]:
                if alert_id == check['Check']:
                    fixed = "no"
                    break

    return fixed


def run_kubeaudit(alert_id: str) -> str:
    """ Run Kubeaudit on the refactored YAML snippet.
    """

    os.system("")

    with open("tmp_snippets/results.json", "r", encoding="utf-8") as file:
        results = json.load(file)

    fixed = "yes"

    for check in results["checks"]:
        if alert_id == check['AuditResultName']:
            fixed = "no"
            break
    
    return fixed


def run_kubescape(alert_id: str) -> str:
    """ Run Kubescape on the refactored YAML snippet.
    """

    os.system("")

    with open("tmp_snippets/results.json", "r", encoding="utf-8") as file:
        results = json.load(file)

    fixed = "yes"

    for result in results["results"]:
        for control in result["controls"]:
            if alert_id == control['controlID']:
                fixed = "no"
                break

    return fixed


def run_terrascan(alert_id: str) -> str:
    """ Run Terrascan on the refactored YAML snippet.
    """

    os.system("")

    with open("tmp_snippets/results.json", "r", encoding="utf-8") as file:
        results = json.load(file)

    fixed = "yes"

    for run in results["runs"]:
        for check in run["results"]:
            if alert_id == check['rule_name']:
                fixed = "no"
                break

    return fixed


def evaluate_fixes():
    """ Evaluate the fixes generated by LLM.
    """

    # Parse rq2_results.csv
    rq2_results = pd.read_csv("results/rq2_results.csv")
    rows = []

    # Iterate over the rows in rq2_results
    for _, row in rq2_results.iterrows():

        refactored = ast.literal_eval(row["Refactored_YAML"])

        # Save refactored into a file
        file_path = "tmp_snippets/refactored.yaml"
        with open(file_path, 'w', encoding="utf-8") as file:
            yaml.dump(refactored, file, sort_keys=False)

        if row["Tool"] == "checkov":
            fixed = run_checkov(row["Alert_ID"])

        elif row["Tool"] == "datree":
            fixed = run_datree(row["Alert_ID"])

        elif row["Tool"] == "kics":
            fixed = run_kics(row["Alert_ID"])

        elif row["Tool"] == "kubelinter":
            fixed = run_kubelinter(row["Alert_ID"])

        elif row["Tool"] == "kubeaudit":
            fixed = run_kubeaudit(row["Alert_ID"])

        elif row["Tool"] == "kubescape":
            fixed = run_kubescape(row["Alert_ID"])

        elif row["Tool"] == "terrascan":
            fixed = run_terrascan(row["Alert_ID"])

        aux = [
            row["Chart"],
            row["Tool"],
            row["Alert_ID"],
            row["Resource"],
            row["Original_YAML"],
            row["LLM"],
            refactored,
            row["Tool"],
            fixed
        ]
        rows.append(aux)

    # Delete refactored file and results.json
    os.remove("tmp_snippets/refactored.yaml")
    os.remove("tmp_snippets/results.json")

    # Save LLM results into Excel
    save_to_csv(rows)
