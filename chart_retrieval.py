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

""" Downloading all Helm charts available on Artifact Hub.
"""

# Part 1: Top trends from analyzing the security posture of open-source Helm charts
# https://bridgecrew.io/blog/open-source-helm-security-research/

# BridgeCrew Helm Scanner
# https://github.com/bridgecrewio/helm-scanner


import os
import subprocess
import requests
import pandas as pd
from query_llm import parse_yaml_template
import json
import re


def get_helm_charts():
    """ Retrieve all available Helm chart packages on Artifact Hub.
    """

    correct_templates = []
    failed_templates = []

    url = "https://artifacthub.io/api/v1/helm-exporter"

    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()

        data = response.json()

        for chart in data:
            print(f"Repository: {chart['name']}")

            # Add current repository to Helm
            # os.system(f"helm repo add {chart['name']} {chart['repository']['url']}")

            command = f"helm template {chart['name']}/{chart['name']} > ./templates/{chart['name']}_template.yaml"
            output = subprocess.getoutput(command)

            if "Error" in output:
                error = {
                    "chart": chart['name'],
                    "output": output
                }
                failed_templates.append(error)
                os.system(f"rm ./templates/{chart['name']}_template.yaml")

            else:
                correct_templates.append(chart['name'])

        # os.system("helm repo update")
        # print("Total packages: ", len(data))

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")

    return correct_templates, failed_templates


def generate_chart_stats():
    """ Generate statistics for all Helm charts.
    """

    # Read chart_stats.csv as Dataframe
    df = pd.read_csv("results/api_chart_stats.csv")
    templates = df["Charts"].values

    print("Total charts: ", len(templates))
    # Remove duplicates from templates
    templates = list(set(templates))
    print("Total unique charts: ", len(templates))

    templates_files = os.listdir("templates")
    templates_files = [x.split("_template.yaml")[0] for x in templates_files]
    # print("Total template files: ", len(templates_files))

    correct_templates = []
    empty_templates = []
    failed_templates = []
    failed_parsing = []

    tmp_df = pd.read_csv("results/templates_stats.csv")

    for chart_name in templates:

        # helm template failed --- no YAML file
        if chart_name not in templates_files:
            row = [
                chart_name,
                "Failed_template",
                "N/A",
                "N/A",
                "N/A"
            ]
            tmp_df.loc[len(tmp_df)] = row
            failed_templates.append(chart_name)

        else:
            filename = f"templates/{chart_name}_template.yaml"
            with open(filename, "r", encoding="utf-8") as file:
                num_lines = len(file.readlines())

            # Emtpy templates
            if num_lines <= 1:
                row = [
                    chart_name,
                    "Empty_template",
                    "N/A",
                    "N/A",
                    "N/A"
                ]
                tmp_df.loc[len(tmp_df)] = row
                empty_templates.append(chart_name)

            else:
                num_containers = 0

                template = parse_yaml_template(chart_name)
                for document in template:
                    if "spec" in document and document["spec"]:
                        if "containers" in document["spec"]:
                            if document["spec"]["containers"]:
                                num_containers += len(document["spec"]["containers"])
                        elif "template" in document["spec"]:
                            if "spec" in document["spec"]["template"]:
                                if document["spec"]["template"]["spec"] and "containers" in document["spec"]["template"]["spec"]:
                                    if document["spec"]["template"]["spec"]["containers"]:
                                        num_containers += len(document["spec"]["template"]["spec"]["containers"])

                        elif "jobTemplate" in document["spec"]:
                            if "containers" in document["spec"]["jobTemplate"]["spec"]["template"]["spec"]:
                                if document["spec"]["jobTemplate"]["spec"]["template"]["spec"]:
                                    num_containers += len(document["spec"]["jobTemplate"]["spec"]["template"]["spec"])

                template_str = "".join(str(doc) for doc in template)

                if template_str:
                    row = [
                        chart_name,
                        "Correct",
                        num_lines,
                        num_containers,
                        len(template_str)
                    ]
                    correct_templates.append(chart_name)

                else:
                    row = [
                        chart_name,
                        "Failed_parsing",
                        "N/A",
                        "N/A",
                        "N/A",
                    ]
                    failed_parsing.append(chart_name)
                tmp_df.loc[len(tmp_df)] = row

    print("Correct templates: ", len(correct_templates))
    print("Empty templates: ", len(empty_templates))
    print("Failed templates: ", len(failed_templates))
    print("Failed parsing: ", len(failed_parsing))
    print("Total processed: ", len(correct_templates) + len(empty_templates) + len(failed_templates))

    tmp_df.to_csv("results/templates_stats.csv", index=False)


def run_checkov(correct_templates, output_path="tools_output/checkov"):
    """ Run Checkov on all Helm chart templates.
    """

    for idx, chart_name in enumerate(correct_templates):
        print(f"{idx}: Running Checkov on {chart_name}...")
        command = f"checkov -f templates/{chart_name}_template.yaml --quiet --compact --framework kubernetes -o json > {output_path}/{chart_name}_results.json"
        os.system(command)
    print("Checkov done.")


def run_datree(correct_templates, output_path="tools_output/datree"):
    """ Run Datree on all Helm chart templates.
    """

    for idx, chart_name in enumerate(correct_templates):
        print(f"{idx}: Running Datree on {chart_name}...")
        command = f"helm datree test templates/{chart_name}_template.yaml --only-k8s-files --quiet --output json > {output_path}/{chart_name}_results.json"
        os.system(command)
    print("Datree done.")


def run_kics(correct_templates, output_path="tools_output/kics"):
    """ Run KICS on all Helm chart templates.
    """

    for idx, chart_name in enumerate(correct_templates):
        print(f"{idx}: Running KICS on {chart_name}...")
        command = f"kics scan -p templates/{chart_name}_template.yaml --exclude-severities info --disable-secrets --exclude-queries bb241e61-77c3-4b97-9575-c0f8a1e008d0 --exclude-queries 7c81d34c-8e5a-402b-9798-9f442630e678 -o . > /dev/null 2>&1"
        os.system(command)
        os.system(f"mv results.json {output_path}/{chart_name}_results.json")
    print("KICS done.")


def run_kubelinter(correct_templates, output_path="tools_output/kubelinter"):
    """ Run KubeLinter on all Helm chart templates.
    """

    for idx, chart_name in enumerate(correct_templates):
        print(f"{idx}: Running KubeLinter on {chart_name}...")
        command = f"kube-linter lint templates/{chart_name}_template.yaml --format=json > {output_path}/{chart_name}_results.json"
        os.system(command)
    print("KubeLinter done.")


def run_kubeaudit(correct_templates, output_path="tools_output/kubeaudit"):
    """ Run Kubeaudit on all Helm chart templates.
    """

    for idx, chart_name in enumerate(correct_templates):
        print(f"{idx}: Running Kubeaudit on {chart_name}...")
        command = f"kubeaudit all -f templates/{chart_name}_template.yaml --minseverity 'error' --format json > {output_path}/{chart_name}_results.json"
        os.system(command)
    print("Kubeaudit done.")


def run_kubescape(correct_templates, output_path="tools_output/kubescape"):
    """ Run Kubescape on all Helm chart templates.
    """

    for idx, chart_name in enumerate(correct_templates):
        print(f"{idx}: Running Kubescape on {chart_name}...")
        command = f"kubescape scan templates/{chart_name}_template.yaml --exceptions kubescape_exceptions.json --format json --output {output_path}/{chart_name}_results.json > /dev/null 2>&1"
        os.system(command)
    print("Kubescape done.")


def run_terrascan(correct_templates, output_path="tools_output/terrascan"):
    """ Run Terrascan on all Helm chart templates.
    """

    for idx, chart_name in enumerate(correct_templates):
        print(f"{idx}: Running Terrascan on {chart_name}...")
        command = f"terrascan scan -i k8s -f templates/{chart_name}_template.yaml --skip-rules AC_K8S_0080 --skip-rules AC_K8S_0069 --skip-rules AC_K8S_0021 --skip-rules AC_K8S_0002 --skip-rules AC_K8S_0068 -o sarif > {output_path}/{chart_name}_results.json"
        os.system(command)
    print("Terrascan done.")


def print_chart_stats():
    """ Print statistics for all Helm charts.
    """

    # Print df stats
    # - number of total charts
    # - number of correct template generated charts
    # - average of lines
    # - average of containers
    # Min/Max/Mean/StDevMedian/1st and 3rd quartile

    df = pd.read_csv("results/templates_stats.csv")
    df = df.loc[df["Template"] == "Correct"]

    print("Number of correctly generated templates: ", len(df))

    print("Average of lines: ", df["#_lines"].mean())
    print("Average of containers: ", df["#_containers"].mean())

    print("\n")

    print("Min Lines: ", df["#_lines"].min())
    print("Max Lines: ", df["#_lines"].max())
    print("Mean Lines: ", df["#_lines"].mean())
    print("StDev Lines: ", df["#_lines"].std())
    print("Median Lines: ", df["#_lines"].median())
    print("1st quartile Lines: ", df["#_lines"].quantile(0.25))
    print("3rd quartile Lines: ", df["#_lines"].quantile(0.75))

    print("\n")
    print(" ------------------------------------ ")
    print("\n")

    print("Min Containers: ", df["#_containers"].min())
    print("Max Containers: ", df["#_containers"].max())
    print("Mean Containers: ", df["#_containers"].mean())
    print("StDev Containers: ", df["#_containers"].std())
    print("Median Containers: ", df["#_containers"].median())
    print("1st quartile Containers: ", df["#_containers"].quantile(0.25))
    print("3rd quartile Containers: ", df["#_containers"].quantile(0.75))

    print("\n")
    print(" ------------------------------------ ")
    print("\n")

    zero_four = len(df[df["Characters"] <= 4000])
    four_eight = len(df[df["Characters"] <= 8000]) - zero_four
    eight_sixteen = len(df[df["Characters"] <= 16000]) - four_eight - zero_four
    sixteen_thirtytwo = len(df[df["Characters"] <= 32000]) - eight_sixteen - four_eight - zero_four
    thirtytwo_plus = len(df[df["Characters"] > 32000])

    print("0 - 4k charts: ", zero_four)
    print("4 - 8k charts: ", four_eight)
    print("8 - 16k charts: ", eight_sixteen)
    print("16 - 32k charts: ", sixteen_thirtytwo)
    print("32k+ charts: ", thirtytwo_plus)

    print("\n")


def check_kubescan_not_failed(results):
    if "results" not in results:
        return True

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
        for _ in resource_list:
            # Extract only failed checks "status": { "status": "failed" }
            for control in result["controls"]:
                if control["status"]["status"] == "failed":
                    return False

    return True


def generate_template_stats():
    """ Generate statistics for all Helm chart templates.
    """

    df = pd.read_csv("results/templates_stats.csv")
    correct_templates = df[df["Template"] == "Correct"]["Chart"].values
    print("Correct templates: ", len(correct_templates))

    tools_df = pd.read_csv("results/tools_stats.csv")

    correct_templates = ['monocular', 'etcd-operator', 'tidb', 'devtron-generic-helm', 'motive-cronjob', 'rabbitmq', 'configmapcontroller', 'gateboard-discovery', 'rotate-elasticsearch-index', 'backup']

    for idx, chart_name in enumerate(correct_templates):
        print(f"{idx}: Processing tools on {chart_name}...")

        row = [chart_name]

        # Checkov
        json_path = f"tools_output/checkov/{chart_name}_results.json"
        try:
            with open(json_path, 'r', encoding="utf-8") as file:
                results = json.load(file)
                aux = "OK"

                if "summary" in results and results["summary"]["failed"] == 0:
                    aux = "No_alerts"
                elif "failed" in results and results["failed"] == 0:
                    aux = "No_alerts"

        except json.decoder.JSONDecodeError:
            aux = "Failed"
        row.append(aux)

        # Datree
        json_path = f"tools_output/datree/{chart_name}_results.json"
        try:
            with open(json_path, 'r', encoding="utf-8") as file:
                results = json.load(file)
                aux = "OK"

                if "policyValidationResults" in results and not results["policyValidationResults"]:
                    aux = "Failed"
                elif "k8sValidationResults" in results and results["k8sValidationResults"]:
                    aux = "Failed"

                if results["policySummary"] and "totalRulesFailed" in results["policySummary"] and results["policySummary"]["totalRulesFailed"] == 0:
                    aux = "No_alerts"

        except json.decoder.JSONDecodeError:
            # print(f"Error: {chart_name} - Datree results file is empty.")
            aux = "Failed"
        row.append(aux)

        # KICS
        json_path = f"tools_output/kics/{chart_name}_results.json"
        try:
            with open(json_path, 'r', encoding="utf-8") as file:
                results = json.load(file)
                aux = "OK"

                if "files_failed_to_scan" in results and results["files_failed_to_scan"] > 0:
                    aux = "Failed"

                elif results["total_counter"] == 0:
                    aux = "No_alerts"

        except json.decoder.JSONDecodeError:
            aux = "Failed"
        row.append(aux)

        # Kubeaudit
        json_path = f"tools_output/kubeaudit/{chart_name}_results.json"
        try:
            with open(json_path, 'r', encoding="utf-8") as file:
                results = json.load(file)
                aux = "OK"

                if "checks" in results and results["checks"] == []:
                    aux = "No_alerts"

        except json.decoder.JSONDecodeError:
            # print(f"Error: {chart_name} - Kubeaudit results file is empty.")
            aux = "Failed"

        # print(aux)
        row.append(aux)

        # Kubelinter
        json_path = f"tools_output/kubelinter/{chart_name}_results.json"
        try:
            with open(json_path, 'r', encoding="utf-8") as file:
                results = json.load(file)
                aux = "OK"

                if results["Reports"] is None:
                    aux = "No_alerts"

                elif results["Summary"] and results["Summary"]["ChecksStatus"] == "Passed":
                    aux = "No_alerts"

        except json.decoder.JSONDecodeError:
            aux = "Failed"

        print(aux)
        row.append(aux)

        # Kubescape
        json_path = f"tools_output/kubescape/{chart_name}_results.json"
        try:
            with open(json_path, 'r', encoding="utf-8") as file:
                results = json.load(file)
                aux = "OK"

                if check_kubescan_not_failed(results):
                    aux = "No_alerts"

        except json.decoder.JSONDecodeError:
            # print(f"Error: {chart_name} - Kubescape results file is empty.")
            aux = "Failed"
        row.append(aux)

        # Terrascan
        json_path = f"tools_output/terrascan/{chart_name}_results.json"
        try:
            with open(json_path, 'r', encoding="utf-8") as file:
                results = json.load(file)
                aux = "OK"

                if not results["runs"][0]["results"]:
                    aux = "No_alerts"

        except json.decoder.JSONDecodeError:
            # print(f"Error: {chart_name} - Terrascan results file is empty.")
            aux = "Failed"
        row.append(aux)

        tools_df.loc[len(tools_df)] = row

    # print(len(tools_df))
    # tools_df.to_csv("results/tools_stats.csv", index=False)


def generate_tools_stats():

    templates = os.listdir("templates")
    templates = [x.split("_template.yaml")[0] for x in templates]
    print("Total templates: ", len(templates))

    # run_checkov(templates)
    # run_datree(templates)
    # run_kics(templates)
    # run_kubeaudit(templates)
    # run_kubelinter(templates)
    # run_kubescape(templates)
    # run_terrascan(templates)


def scan_artifact_hub():
    """ Retrieve all Helm charts from Artifact Hub.
    """

    pass

    # df = pd.read_csv("results/templates_stats.csv")
    # correct_templates = df[df["Template"] == "Correct"]["Chart"].values
    # print("Correct templates: ", len(correct_templates))

    # print("Correct templates: ", len(correct_templates))
    # print("Failed templates: ", len(failed_templates))

    # generate_chart_stats()
    # print("\n")
    # print_chart_stats()
    # print("\n")
    # generate_template_stats()
    # print("\n")
    # generate_tools_stats()

    ###

    # # Run tools
    # run_checkov(correct_templates)
    # run_datree(correct_templates)
    # run_kics(correct_templates)
    # run_kubelinter(correct_templates)
    # run_kubeaudit(correct_templates)
    # run_kubescape(correct_templates)
    # run_terrascan(correct_templates)
