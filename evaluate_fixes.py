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
import ast

global to_check
to_check = []

def check_paths(paths, resource):
    """ Check if the paths match the resource. """

    aux_resource = [paths["resource_path"], paths["obj_path"]]
    resource = ast.literal_eval(resource)

    if aux_resource == resource:
        return True


def parse_checkov(idx, alert_id, resource, llm):
    json_path = f"snippets/{llm}/results{idx}.json"
    try:
        with open(json_path, 'r', encoding="utf-8") as file:
            results = json.load(file)
    except json.decoder.JSONDecodeError:
        print("Error: Checkov results file is empty.")
        return

    failed = "Fixed"

    file_path = f"snippets/{llm}/refactored{idx}.yaml"
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            template = list(yaml.load_all(file, Loader=yaml.FullLoader))
    except yaml.scanner.ScannerError as e:
        print(f"Error parsing the YAML file: {e}")
        return "Not_Fixed"
    except yaml.constructor.ConstructorError as e:
        print(f"Error parsing the YAML file: {e}")
        return "Not_Fixed"

    if "results" in results and "failed_checks" in results["results"]:
        for check in results["results"]["failed_checks"]:
            check_id = check['check_id']

            if check_id == alert_id:
                paths = get_ckv_resource_path(check, template)
                if check_paths(paths, resource):
                    to_check.append(idx)
                    return "Not_Fixed"

    return failed


def parse_datree(idx, alert_id, resource, llm):
    json_path = f"snippets/{llm}/results{idx}.json"
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
                    if check_paths(paths, resource):
                        to_check.append(idx)
                        return "Not_Fixed"

    return failed


def parse_kics(idx, alert_id, resource, llm):
    json_path = f"snippets/{llm}/results{idx}.json"
    try:
        with open(json_path, 'r', encoding="utf-8") as file:
            results = json.load(file)
    except (json.decoder.JSONDecodeError, FileNotFoundError):
        print("Error: Datree results file is empty.")
        return

    failed = "Fixed"

    file_path = f"snippets/{llm}/refactored{idx}.yaml"
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            template = list(yaml.load_all(file, Loader=yaml.FullLoader))
    except yaml.scanner.ScannerError as e:
        print(f"Error parsing the YAML file: {e}")
        return "Not_Fixed"
    except yaml.constructor.ConstructorError as e:
        print(f"Error parsing the YAML file: {e}")
        return "Not_Fixed"

    for check in results["queries"]:
        for file in check['files']:
            check_id = check['query_id']

            if check_id == alert_id:
                std_check_id = KICSLookup.get_value(check_id)
                if std_check_id is None:
                    std_check_id = "NOT_MAPPED"

                paths = get_kics_path(file, template, std_check_id)
                if check_paths(paths, resource):
                    to_check.append(idx)
                    return "Not_Fixed"

    return failed


def parse_kubeaudit(idx, alert_id, resource, llm):
    json_path = f"snippets/{llm}/results{idx}.json"
    try:
        with open(json_path, 'r', encoding="utf-8") as file:
            results = json.load(file)
    except json.decoder.JSONDecodeError:
        print("Error: Datree results file is empty.")
        return

    failed = "Fixed"

    file_path = f"snippets/{llm}/refactored{idx}.yaml"
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            template = list(yaml.load_all(file, Loader=yaml.FullLoader))
    except yaml.scanner.ScannerError as e:
        print(f"Error parsing the YAML file: {e}")
        return "Not_Fixed"
    except yaml.constructor.ConstructorError as e:
        print(f"Error parsing the YAML file: {e}")
        return "Not_Fixed"

    if "checks" in results:
        for check in results["checks"]:
            check_id = check['AuditResultName']

            if check_id == alert_id:
                paths = get_kubeaudit_path(check, template)
                if check_paths(paths, resource):
                    to_check.append(idx)
                    return "Not_Fixed"

    return failed


def parse_kubelinter(idx, alert_id, resource, llm):
    json_path = f"snippets/{llm}/results{idx}.json"
    try:
        with open(json_path, 'r', encoding="utf-8") as file:
            results = json.load(file)
    except json.decoder.JSONDecodeError:
        print("Error: Datree results file is empty.")
        return

    failed = "Fixed"

    file_path = f"snippets/{llm}/refactored{idx}.yaml"
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            template = list(yaml.load_all(file, Loader=yaml.FullLoader))
    except yaml.scanner.ScannerError as e:
        print(f"Error parsing the YAML file: {e}")
        return "Not_Fixed"
    except yaml.constructor.ConstructorError as e:
        print(f"Error parsing the YAML file: {e}")
        return "Not_Fixed"

    if "Reports" in results and results["Reports"]:

        for check in results["Reports"]:
            check_id = check['Check']

            if check_id == alert_id:
                paths = get_kubelinter_path(check, template)
                if check_paths(paths, resource):
                    to_check.append(idx)
                    return "Not_Fixed"

    return failed


def parse_kubescape(idx, alert_id, resource, llm):
    json_path = f"snippets/{llm}/results{idx}.json"
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
                # Extract only failed checks "status": { "status": "Not_Fixed" }
                for control in result["controls"]:
                    if control["status"]["status"] == "Not_Fixed":

                        check_id = control['controlID']
                        if check_id == alert_id:
                            for rule in control["rules"]:
                                paths = {
                                        "resource_path": resource_path,
                                        "obj_path": ""
                                }
                                if "paths" in rule:
                                    paths = get_kubescape_path(rule, control, paths)
                                    if check_paths(paths, resource):
                                        to_check.append(idx)
                                        return "Not_Fixed"

    return failed


def parse_terrascan(idx, alert_id, resource, llm):
    json_path = f"snippets/{llm}/results{idx}.json"
    try:
        with open(json_path, 'r', encoding="utf-8") as file:
            results = json.load(file)
    except json.decoder.JSONDecodeError:
        print("Error: Datree results file is empty.")
        return

    failed = "Fixed"

    file_path = f"snippets/{llm}/refactored{idx}.yaml"
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            template = list(yaml.load_all(file, Loader=yaml.FullLoader))
    except yaml.scanner.ScannerError as e:
        print(f"Error parsing the YAML file: {e}")
        return "Not_Fixed"
    except yaml.constructor.ConstructorError as e:
        print(f"Error parsing the YAML file: {e}")
        return "Not_Fixed"

    for run in results["runs"]:
        for check in run["results"]:
            if check["ruleId"] == alert_id:
                paths = get_terrascan_path(check, template)
                if check_paths(paths, resource):
                    to_check.append(idx)
                    return "Not_Fixed"

    return failed


def evaluate_llm_fixes(llm_name: str, idx: int, jdx: int):
    """ Evaluate the fixes generated by LLM.
    """

    df = ""

    if llm_name == "llama":
        df = pd.read_csv("results/llm_llama_answers.csv")
        llm = "Llama_3_70b"
    elif llm_name == "claude":
        df = pd.read_csv("results/llm_claude_answers.csv")
        # df = pd.read_csv("results/llm_claude_answers2.csv")
        llm = "Claude_3_Sonnet"
    elif llm_name == "gemini":
        df = pd.read_csv("results/llm_gemini_answers.csv")
        llm = "Gemini_1.5"
    elif llm_name == "chatgpt":
        df = pd.read_csv("results/llm_chatgpt_answers.csv")
        llm = "ChatGPT-4o-mini-2024-07-18"

    file_name = "results/llm_llama_fix.csv"
    if llm_name == "claude":
        file_name = "results/llm_claude_fix.csv"
    elif llm_name == "gemini":
        file_name = "results/llm_gemini_fix.csv"
    elif llm_name == "chatgpt":
        file_name = "results/llm_chatgpt_fix.csv"

    rows = []
    counter = 0

    for idx, row in df.iloc[idx:jdx].iterrows():

        chart_name = row["Chart"]
        alert_id = row["Alert_ID"]

        refactored_path = f"snippets/{llm}/refactored{idx}.yaml"
        original_path = f"snippets/{llm}/original{idx}.yaml"
        result_path = f"snippets/{llm}/results{idx}.json"

        print(f"{idx} - Processing fix {chart_name} - {alert_id} ...")
        counter += 1

        fixed = "Fixed"

        if row["Refactored_YAML"] == "Failed to generate a response.":
            fixed = "Not_Fixed"

        if fixed == "Fixed":
            # Save the YAML files
            try:
                refactored_yaml = yaml.load(row["Refactored_YAML"], Loader=yaml.FullLoader)
            except (yaml.scanner.ScannerError, yaml.parser.ParserError, AttributeError):
                row = [
                    row["Chart"],
                    row["Alert_ID"],
                    tool,
                    resource,
                    llm,
                    "Not_Fixed",
                    0,
                    0,
                    0
                ]
                rows.append(row)
                continue

            with open(refactored_path, "w", encoding="utf-8") as file:
                yaml.dump(refactored_yaml, file)

            try:
                original_yaml = yaml.load(row["Original_YAML"], Loader=yaml.FullLoader)
            except (yaml.scanner.ScannerError, yaml.parser.ParserError, AttributeError):
                row = [
                    row["Chart"],
                    row["Alert_ID"],
                    row["Tool"],
                    row["Resource"],
                    llm,
                    "Not_Fixed",
                    0,
                    0,
                    0
                ]
                rows.append(row)
                continue

            with open(original_path, "w", encoding="utf-8") as file:
                yaml.dump(original_yaml, file, default_flow_style=False)

            # Run tool on the refactored YAML
            tool = row["Tool"]
            resource = row["Resource"]

            if tool == "checkov":
                command = f"checkov -f {refactored_path} --quiet --compact --framework kubernetes -o json > {result_path}"
                os.system(command)
                parse_checkov(idx, row["Alert_ID"], resource, llm_name)

            elif tool == "datree":
                command = f"helm datree test {refactored_path} --only-k8s-files --quiet --output json > {result_path}"
                os.system(command)
                fixed = parse_datree(idx, row["Alert_ID"], resource, llm_name)

            elif tool == "kics":
                command = f"kics scan -p {refactored_path} --exclude-severities info --disable-secrets --exclude-queries bb241e61-77c3-4b97-9575-c0f8a1e008d0 --exclude-queries 7c81d34c-8e5a-402b-9798-9f442630e678 -o . > /dev/null 2>&1"
                os.system(command)
                os.system(f"mv results.json {result_path}")
                fixed = parse_kics(idx, row["Alert_ID"], resource, llm_name)

            elif tool == "kubeaudit":
                command = f"kubeaudit all -f {refactored_path} --minseverity 'error' --format json > {result_path}"
                os.system(command)
                fixed = parse_kubeaudit(idx, row["Alert_ID"], resource, llm_name)

            elif tool == "kubelinter":
                command = f"kube-linter lint {refactored_path} --format=json > {result_path}"
                os.system(command)
                fixed = parse_kubelinter(idx, row["Alert_ID"], resource, llm_name)

            elif tool == "kubescape":
                command = f"kubescape scan {refactored_path} --exceptions kubescape_exceptions.json --format json --output {result_path} > /dev/null 2>&1"
                os.system(command)
                fixed = parse_kubescape(idx, row["Alert_ID"], resource, llm_name)

            elif tool == "terrascan":
                command = f"terrascan scan -i k8s -f {refactored_path} --skip-rules AC_K8S_0080 --skip-rules AC_K8S_0069 --skip-rules AC_K8S_0021 --skip-rules AC_K8S_0002 --skip-rules AC_K8S_0068 -o sarif > {result_path}"
                os.system(command)
                fixed = parse_terrascan(idx, row["Alert_ID"], resource, llm_name)

        # Compute Added, Changed, Removed lines in the refactored YAML
        added = 0
        changed = 0
        removed = 0

        try:
            with open(refactored_path, "r", encoding="utf-8") as file:
                len_refactored = len(file.readlines())
        except FileNotFoundError:
            len_refactored = 0
            original_yaml = ""
            refactored_yaml = ""

        try:
            with open(original_path, "r", encoding="utf-8") as file:
                len_original = len(file.readlines())
        except FileNotFoundError:
            len_original = 0
            original_yaml = ""
            refactored_yaml = ""

        if len_original > len_refactored:
            removed = len_original - len_refactored

        elif len_refactored > len_original:
            added = len_refactored - len_original

        if isinstance(original_yaml, dict):
            for key in original_yaml:
                try:
                    if key in refactored_yaml:

                        if isinstance(original_yaml[key], dict):
                            for sub_key in original_yaml[key]:
                                if sub_key in refactored_yaml[key]:
                                    if original_yaml[key][sub_key] != refactored_yaml[key][sub_key]:
                                        changed += 1

                        elif original_yaml[key] != refactored_yaml[key]:
                            changed += 1

                except TypeError:
                    continue

        # os.system(f"rm {refactored_path}")
        # os.system(f"rm {original_path}")
        os.system(f"rm {result_path}")

        row = [
            row["Chart"],
            row["Alert_ID"],
            row["Tool"],
            row["Resource"],
            llm,
            fixed,
            added,
            changed,
            removed
        ]
        rows.append(row)


    #     if counter == 50:
    #         df = pd.read_csv(file_name)
    #         for row in rows:
    #             df.loc[len(df)] = row
    #         df.to_csv(file_name, index=False)
    #         rows = []
    #         counter = 0
    #         df = None

    # df = pd.read_csv(file_name)
    # for row in rows:
    #     df.loc[len(df)] = row
    # df.to_csv(file_name, index=False)


def print_stats(llm_name):
    """ Print the statistics of the fixes."""

    df = ""

    if llm_name == "llama":
        df = pd.read_csv("results/llm_llama_fix.csv")
        llm = "Llama_3_70b"
    elif llm_name == "claude":
        df = pd.read_csv("results/llm_claude_fix.csv")
        # df = pd.read_csv("results/llm_claude_fix2.csv")
        llm = "Claude_3_Sonnet"
    elif llm_name == "gemini":
        df = pd.read_csv("results/llm_gemini_fix.csv")
        llm = "Gemini_1.5"
    elif llm_name == "chatgpt":
        df = pd.read_csv("results/llm_chatgpt_fix.csv")
        llm = "ChatGPT-4o-mini-2024-07-18"

    # Print total number of rows
    print(f"Total number of rows: {len(df)}")

    # Print how many rows have the "Fixed" column value as "Not_Fixed"
    print(f"Total number of rows with 'Fixed': {len(df[df['Fixed'] == 'Fixed'])}")
    print(f"Total number of rows with 'Not_Fixed': {len(df[df['Fixed'] == 'Not_Fixed'])}")

    print()

    print(f"Min of the 'Added' column: {df['Added'].min()}")
    print(f"Max of the 'Added' column: {df['Added'].max()}")
    print(f"Mean of the 'Added' column: {df['Added'].mean()}")
    print(f"Median of the 'Added' column: {df['Added'].median()}")
    print(f"SD of the 'Added' column: {df['Added'].std()}")
    print(f"1st quartile of the 'Added' column: {df['Added'].quantile(0.25)}")
    print(f"3rd quartile of the 'Added' column: {df['Added'].quantile(0.75)}")

    print()

    print(f"Min of the 'Changed' column: {df['Changed'].min()}")
    print(f"Max of the 'Changed' column: {df['Changed'].max()}")
    print(f"Mean of the 'Changed' column: {df['Changed'].mean()}")
    print(f"Median of the 'Changed' column: {df['Changed'].median()}")
    print(f"SD of the 'Changed' column: {df['Changed'].std()}")
    print(f"1st quartile of the 'Changed' column: {df['Changed'].quantile(0.25)}")
    print(f"3rd quartile of the 'Changed' column: {df['Changed'].quantile(0.75)}")

    print()

    print(f"Min of the 'Removed' column: {df['Removed'].min()}")
    print(f"Max of the 'Removed' column: {df['Removed'].max()}")
    print(f"Mean of the 'Removed' column: {df['Removed'].mean()}")
    print(f"Median of the 'Removed' column: {df['Removed'].median()}")
    print(f"SD of the 'Removed' column: {df['Removed'].std()}")
    print(f"1st quartile of the 'Removed' column: {df['Removed'].quantile(0.25)}")
    print(f"3rd quartile of the 'Removed' column: {df['Removed'].quantile(0.75)}")


def evaluate_fixes():
    """ Evaluate the fixes generated by LLM.
    """

    llm = "llama"
    # print_stats(llm)
    # exit(0)

    idx = 0
    jdx = 100
    # jdx = 7838

    # llm = "claude"

    # idx = 90000
    # jdx = 100000

    # # jdx = 160000

    evaluate_llm_fixes(llm, idx, jdx)

    ###

    df = pd.read_csv("results/llm_llama_fix.csv")

    for idx in to_check:

        # Change the "Fixed" column value of row idx to "Not_Fixed"
        df.at[idx, "Fixed"] = "Not_Fixed"

    df.to_csv("results/llm_llama_fix.csv", index=False)
