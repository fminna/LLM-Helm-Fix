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

from parse_tool_output import get_ckv_resource_path, get_datree_path, get_kics_path, KICSLookup, get_kubeaudit_path, get_kubelinter_path, get_terrascan_path, get_kubescape_path
import pandas as pd
import yaml
import os
import json


def parse_checkov(alert_id, resource):
    json_path = "tmp_snippets/results.json"
    try:
        with open(json_path, 'r', encoding="utf-8") as file:
            results = json.load(file)
    except json.decoder.JSONDecodeError:
        print("Error: Checkov results file is empty.")
        return

    failed = "Fixed"

    file_path = "tmp_snippets/refactored.yaml"
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            template = list(yaml.load_all(file, Loader=yaml.FullLoader))
    except yaml.scanner.ScannerError as e:
        print(f"Error parsing the YAML file: {e}")
        return "Failed"
    except yaml.constructor.ConstructorError as e:
        print(f"Error parsing the YAML file: {e}")
        return "Failed"

    if "results" in results and "failed_checks" in results["results"]:
        for check in results["results"]["failed_checks"]:
            check_id = check['check_id']

            if check_id == alert_id:
                paths = get_ckv_resource_path(check, template)
                aux_resource = [paths["resource_path"], paths["obj_path"]]
                if aux_resource == resource:
                    failed = "Failed"
                    break

    return failed


def parse_datree(alert_id, resource):
    json_path = "tmp_snippets/results.json"
    try:
        with open(json_path, 'r', encoding="utf-8") as file:
            results = json.load(file)
    except json.decoder.JSONDecodeError:
        print("Error: Datree results file is empty.")
        return

    failed = "Fixed"

    if "policyValidationResults" and results["policyValidationResults"] is not None:
        for check in results["policyValidationResults"][0]["ruleResults"]:

            for occurrence in check["occurrencesDetails"]:
                check_id = check['identifier']

                if check_id == alert_id:
                    paths = get_datree_path(occurrence)
                    aux_resource = [paths["resource_path"], paths["obj_path"]]

                    if aux_resource == resource:
                        failed = "Failed"
                        break

    return failed


def parse_kics(alert_id, resource):
    json_path = "tmp_snippets/results.json"
    try:
        with open(json_path, 'r', encoding="utf-8") as file:
            results = json.load(file)
    except json.decoder.JSONDecodeError:
        print("Error: Datree results file is empty.")
        return

    failed = "Fixed"

    file_path = "tmp_snippets/refactored.yaml"
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            template = list(yaml.load_all(file, Loader=yaml.FullLoader))
    except yaml.scanner.ScannerError as e:
        print(f"Error parsing the YAML file: {e}")
        return "Failed"
    except yaml.constructor.ConstructorError as e:
        print(f"Error parsing the YAML file: {e}")
        return "Failed"

    for check in results["queries"]:
        for file in check['files']:
            check_id = check['query_id']

            if check_id == alert_id:
                std_check_id = KICSLookup.get_value(check_id)
                if std_check_id is None:
                    std_check_id = "NOT_MAPPED"

                paths = get_kics_path(file, template, std_check_id)
                aux_resource = [paths["resource_path"], paths["obj_path"]]

                if aux_resource == resource:
                    failed = "Failed"
                    break

    return failed


def parse_kubeaudit(alert_id, resource):
    json_path = "tmp_snippets/results.json"
    try:
        with open(json_path, 'r', encoding="utf-8") as file:
            results = json.load(file)
    except json.decoder.JSONDecodeError:
        print("Error: Datree results file is empty.")
        return

    failed = "Fixed"

    file_path = "tmp_snippets/refactored.yaml"
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            template = list(yaml.load_all(file, Loader=yaml.FullLoader))
    except yaml.scanner.ScannerError as e:
        print(f"Error parsing the YAML file: {e}")
        return "Failed"
    except yaml.constructor.ConstructorError as e:
        print(f"Error parsing the YAML file: {e}")
        return "Failed"

    for check in results["checks"]:
        check_id = check['AuditResultName']

        if check_id == alert_id:
            paths = get_kubeaudit_path(check, template)
            aux_resource = [paths["resource_path"], paths["obj_path"]]

            if aux_resource == resource:
                failed = "Failed"
                break

    return failed


def parse_kubelinter(alert_id, resource):
    json_path = "tmp_snippets/results.json"
    try:
        with open(json_path, 'r', encoding="utf-8") as file:
            results = json.load(file)
    except json.decoder.JSONDecodeError:
        print("Error: Datree results file is empty.")
        return

    failed = "Fixed"

    file_path = "tmp_snippets/refactored.yaml"
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            template = list(yaml.load_all(file, Loader=yaml.FullLoader))
    except yaml.scanner.ScannerError as e:
        print(f"Error parsing the YAML file: {e}")
        return "Failed"
    except yaml.constructor.ConstructorError as e:
        print(f"Error parsing the YAML file: {e}")
        return "Failed"

    if "Reports" in results and results["Reports"]:

        for check in results["Reports"]:
            check_id = check['Check']

            if check_id == alert_id:
                paths = get_kubelinter_path(check, template)
                aux_resource = [paths["resource_path"], paths["obj_path"]]

                if aux_resource == resource:
                    failed = "Failed"
                    break

    return failed


def parse_kubescape(alert_id, resource):
    json_path = "tmp_snippets/results.json"
    try:
        with open(json_path, 'r', encoding="utf-8") as file:
            results = json.load(file)
    except json.decoder.JSONDecodeError:
        print("Error: Datree results file is empty.")
        return

    failed = "Fixed"

    if "results" in results:
        for result in results["results"]:
            resources_path = result["resourceID"]
            resource_list = []
            aux_path = ""

            # Multiple resources
            if resources_path.count("path") > 1:
                # Split result["resourceID"] by this substring "path=*/api=*/v1/""
                regex_pattern = r"path=[\d]+/api=[\w.]+/v1"
                aux_path_list = re.split(regex_pattern, resources_path)

                for sub_path in aux_path_list:
                    aux_sub_path = sub_path.split("/")
                    aux_sub_path = [x for x in aux_sub_path if x != ""]

                    if aux_sub_path:
                        # If there is no namespace, add "default" at the beginning
                        if len(aux_sub_path) < 3:
                            aux_sub_path.insert(0, "default")
                        aux_sub_path = f"{aux_sub_path[-2]}/{aux_sub_path[-3]}/{aux_sub_path[-1]}"
                        resource_list.append(aux_sub_path)

            else:
                aux_path = result["resourceID"].split("/")
                aux_path = f"{aux_path[-2]}/{aux_path[-3]}/{aux_path[-1]}"
                aux_path = aux_path.replace("//", "/default/")
                resource_list.append(aux_path)

            # Fix for all resources
            for resource_path in resource_list:
                # Extract only failed checks "status": { "status": "failed" }
                for control in result["controls"]:
                    if control["status"]["status"] == "failed":

                        check_id = control['controlID']
                        if check_id == alert_id:
                            for rule in control["rules"]:
                                paths = {
                                        "resource_path": resource_path,
                                        "obj_path": ""
                                }
                                if "paths" in rule:
                                    paths = get_kubescape_path(rule, control, paths)
                                    aux_resource = [paths["resource_path"], paths["obj_path"]]
                                    if aux_resource == resource:
                                        failed = "Failed"
                                        break

    return failed


def parse_terrascan(alert_id, resource):
    json_path = "tmp_snippets/results.json"
    try:
        with open(json_path, 'r', encoding="utf-8") as file:
            results = json.load(file)
    except json.decoder.JSONDecodeError:
        print("Error: Datree results file is empty.")
        return

    failed = "Fixed"

    file_path = "tmp_snippets/refactored.yaml"
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            template = list(yaml.load_all(file, Loader=yaml.FullLoader))
    except yaml.scanner.ScannerError as e:
        print(f"Error parsing the YAML file: {e}")
        return "Failed"
    except yaml.constructor.ConstructorError as e:
        print(f"Error parsing the YAML file: {e}")
        return "Failed"

    for run in results["runs"]:
        for check in run["results"]:
            paths = get_terrascan_path(check, template)
            aux_resource = [paths["resource_path"], paths["obj_path"]]
            if aux_resource == resource:
                failed = "Failed"
                break

    return failed


def evaluate_fixes():
    """ Evaluate the fixes generated by LLM.
    """

    # df = pd.read_csv("results/llm_llama_answers.csv")
    # df = pd.read_csv("results/llm_claude_answers.csv")

    # df = pd.read_csv("results/llm_gemini_answers.csv")
    df = pd.read_csv("results/llm_gemini_answers.csv")
    # Columns: 'Chart', 'Alert_ID', 'Query', 'LLM', 'Input_Tokens', 'Refactored_YAML', 'Output_Tokens'

    # Copy the Tool and Resource columns in the answer dataframes, for the three LLMs.
    # aux_df = pd.read_csv("results/llm_new_queries.csv")
    # df["Tool"] = aux_df["Tool"].to_numpy()
    # df["Resource"] = aux_df["Resource"].to_numpy()
    # df["Original_YAML"] = aux_df["Original_YAML"].to_numpy()
    # df.to_csv("results/llm_llama_answers.csv", index=False)
    # exit(0)

    # LLM = "Llama_3_70b"
    # LLM = "Claude_3_Sonnet"
    LLM = "Gemini_1.5"
    # LLM = "ChatGPT-4o-mini-2024-07-18"

    rows = []
    # Iterate df by rows
    for idx, row in df.iterrows():
        chart_name = row["Chart"]
        alert_id = row["Alert_ID"]

        print(f"{idx} - Processing fix {chart_name} - {alert_id} ...")
        fixed = "Fixed"

        if row["Refactored_YAML"] == "Failed to generate a response.":
            fixed = "Failed"

        if fixed == "Fixed":
            # Save the YAML files
            refactored_yaml = yaml.safe_load(row["Refactored_YAML"])
            with open("tmp_snippets/refactored.yaml", "w", encoding="utf-8") as file:
                yaml.dump(refactored_yaml, file)

            original_yaml = yaml.safe_load(row["Original_YAML"])
            with open("tmp_snippets/original.yaml", "w", encoding="utf-8") as file:
                yaml.dump(original_yaml, file)

            # Run tool on the refactored YAML
            tool = row["Tool"]
            resource = row["Resource"]

            if tool == "checkov":
                command = "checkov -f tmp_snippets/refactored.yaml --quiet --compact --framework kubernetes -o json > tmp_snippets/results.json"
                os.system(command)
                parse_checkov(row["Alert_ID"], resource)

            elif tool == "datree":
                command = "helm datree test tmp_snippets/refactored.yaml --only-k8s-files --quiet --output json > tmp_snippets/results.json"
                os.system(command)
                fixed = parse_datree(row["Alert_ID"], resource)

            elif tool == "kics":
                command = "kics scan -p tmp_snippets/refactored.yaml --exclude-severities info --disable-secrets --exclude-queries bb241e61-77c3-4b97-9575-c0f8a1e008d0 --exclude-queries 7c81d34c-8e5a-402b-9798-9f442630e678 -o . > /dev/null 2>&1"
                os.system(command)
                os.system("mv results.json tmp_snippets/results.json")
                fixed = parse_kics(row["Alert_ID"], resource)

            elif tool == "kubeaudit":
                command = "kubeaudit all -f tmp_snippets/refactored.yaml --minseverity 'error' --format json > tmp_snippets/results.json"
                os.system(command)
                fixed = parse_kubeaudit(row["Alert_ID"], resource)

            elif tool == "kubelinter":
                command = "kube-linter lint tmp_snippets/refactored.yaml --format=json > tmp_snippets/results.json"
                os.system(command)
                fixed = parse_kubelinter(row["Alert_ID"], resource)

            elif tool == "kubescape":
                command = "kubescape scan tmp_snippets/refactored.yaml --exceptions kubescape_exceptions.json --format json --output tmp_snippets/results.json > /dev/null 2>&1"
                os.system(command)
                fixed = parse_kubescape(row["Alert_ID"], resource)

            elif tool == "terrascan":
                command = "terrascan scan -i k8s -f tmp_snippets/refactored.yaml --skip-rules AC_K8S_0080 --skip-rules AC_K8S_0069 --skip-rules AC_K8S_0021 --skip-rules AC_K8S_0002 --skip-rules AC_K8S_0068 -o sarif > tmp_snippets/results.json"
                os.system(command)
                fixed = parse_terrascan(row["Alert_ID"], resource)

        # Compute Added, Changed, Removed lines in the refactored YAML
        added = 0
        changed = 0
        removed = 0

        if len(original_yaml) > len(refactored_yaml):
            removed = len(original_yaml) - len(refactored_yaml)

        elif len(original_yaml) < len(refactored_yaml):
            added = len(refactored_yaml) - len(original_yaml)

        # Iterate the original_yaml dict keys
        for key in original_yaml:
            if key in refactored_yaml:

                print(original_yaml[key])
                exit(0)

                if original_yaml[key] != refactored_yaml[key]:
                    changed += 1

        row = [
            row["Chart"],
            row["Alert_ID"],
            tool,
            resource,
            LLM,
            fixed,
            added,
            changed,
            removed
        ]
        rows.append(row)

        exit(0)

        # Remove files
        os.system("rm tmp_snippets/refactored.yaml")
        os.system("rm tmp_snippets/original.yaml")
        os.system("rm tmp_snippets/results.json")

    df = pd.read_csv("results/llm_chatgpt_fix.csv")
    for row in rows:
        df.loc[len(df)] = row
    df.to_csv("results/llm_chatgpt_fix.csv", index=False)
