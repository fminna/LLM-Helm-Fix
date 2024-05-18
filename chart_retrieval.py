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

        # for chart in data[:1000]:
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


def generate_chart_stats(correct_templates, failed_templates):
    """ Generate statistics for all Helm charts.
    """

    # Read chart_stats.csv as Dataframe
    df = pd.read_csv("results/chart_stats.csv")
    rows = []

    for chart_name in correct_templates:

        if chart_name in df['Charts'].values:
            continue

        print(f"Processing {chart_name}...")

        try:
            with open(f"templates/{chart_name}_template.yaml", "r", encoding="utf-8") as file:
                num_lines = len(file.readlines())
        except FileNotFoundError:
            num_lines = 0

        if num_lines <= 1:
            row = [
                chart_name,
                "Unknown error - empty template",
                "N/A",
                "N/A",
                "N/A"
            ]
            rows.append(row)

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
                    "OK",
                    num_lines,
                    num_containers,
                    len(template_str)
                ]
            else:
                row = [
                    chart_name,
                    "YAML Parsing Error",
                    "N/A",
                    "N/A",
                    "N/A",
                ]

            rows.append(row)

    for chart_name in failed_templates:
        if chart_name in df["Charts"].values:
            continue

        row = [
            chart_name["chart"],
            chart_name["output"],
            "N/A",
            "N/A",
            "N/A",
        ]
        rows.append(row)

    for row in rows:
        row.insert(0, len(df)+1)
        df.loc[len(df)] = row

    df.to_csv("results/chart_stats.csv", index=False)
    return df


def run_checkov(correct_templates):
    """ Run Checkov on all Helm chart templates.
    """

    for idx, chart_name in enumerate(correct_templates):
        print(f"{idx}: Running Checkov on {chart_name}...")
        command = f"checkov -f templates/{chart_name}_template.yaml --quiet --compact --framework kubernetes -o json > tools_output/checkov/{chart_name}_results.json"
        os.system(command)
    print("Checkov done.")


def run_datree(correct_templates):
    """ Run Datree on all Helm chart templates.
    """

    for idx, chart_name in enumerate(correct_templates):
        print(f"{idx}: Running Datree on {chart_name}...")
        command = f"helm datree test templates/{chart_name}_template.yaml --only-k8s-files --quiet --output json > tools_output/datree/{chart_name}_results.json"
        os.system(command)
    print("Datree done.")


def run_kics(correct_templates):
    """ Run KICS on all Helm chart templates.
    """

    for idx, chart_name in enumerate(correct_templates):
        print(f"{idx}: Running KICS on {chart_name}...")
        command = f"kics scan -p templates/{chart_name}_template.yaml --exclude-severities info --disable-secrets --exclude-queries bb241e61-77c3-4b97-9575-c0f8a1e008d0 --exclude-queries 7c81d34c-8e5a-402b-9798-9f442630e678 -o . > /dev/null 2>&1"
        os.system(command)
        os.system(f"mv results.json tools_output/kics/{chart_name}_results.json")
    print("KICS done.")


def run_kubelinter(correct_templates):
    """ Run KubeLinter on all Helm chart templates.
    """

    for idx, chart_name in enumerate(correct_templates):
        print(f"{idx}: Running KubeLinter on {chart_name}...")
        command = f"kube-linter lint templates/{chart_name}_template.yaml --format=json > tools_output/kubelinter/{chart_name}_results.json"
        os.system(command)
    print("KubeLinter done.")


def run_kubeaudit(correct_templates):
    """ Run Kubeaudit on all Helm chart templates.
    """

    for idx, chart_name in enumerate(correct_templates):
        print(f"{idx}: Running Kubeaudit on {chart_name}...")
        command = f"kubeaudit all -f templates/{chart_name}_template.yaml --minseverity 'error' --format json > tools_output/kubeaudit/{chart_name}_results.json"
        os.system(command)
    print("Kubeaudit done.")


def run_kubescape(correct_templates):
    """ Run Kubescape on all Helm chart templates.
    """

    for idx, chart_name in enumerate(correct_templates):
        print(f"{idx}: Running Kubescape on {chart_name}...")
        command = f"kubescape scan templates/{chart_name}_template.yaml --exceptions kubescape_exceptions.json --format json --output tools_output/kubescape/{chart_name}_results.json > /dev/null 2>&1"
        os.system(command)
    print("Kubescape done.")


def run_terrascan(correct_templates):
    """ Run Terrascan on all Helm chart templates.
    """

    for idx, chart_name in enumerate(correct_templates):
        print(f"{idx}: Running Terrascan on {chart_name}...")
        command = f"terrascan scan -i k8s -f templates/{chart_name}_template.yaml --skip-rules AC_K8S_0080 --skip-rules AC_K8S_0069 --skip-rules AC_K8S_0021 --skip-rules AC_K8S_0002 --skip-rules AC_K8S_0068 -o sarif > tools_output/terrascan/{chart_name}_results.json"
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

    df = pd.read_csv("results/chart_stats.csv")

    print("Number of total charts: ", len(df))
    print("Number of correctly generated templates: ", len(df[df["Template"] == "OK"]))

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


def scan_artifact_hub():
    # Search for all publicly available Helm charts
    # correct_templates, failed_templates = get_helm_charts()

    # print("Correct templates: ", len(correct_templates), correct_templates)
    # print("Correct templates: ", len(correct_templates))
    # print("Failed templates: ", len(failed_templates))

    # Correct templates is equal to the list of all *.yaml files in the templates folder.
    # correct_templates = [f.replace("_template.yaml", "") for f in os.listdir("templates") if f.endswith("_template.yaml")]
    # failed_templates = []

    # generate_chart_stats(correct_templates, failed_templates)

    # print_chart_stats()

    df = pd.read_csv("results/chart_stats.csv")
    correct_templates = df[df["Template"] == "OK"]["Charts"].values
    # print(len(correct_templates))

    run_checkov(correct_templates)

    run_datree(correct_templates)

    run_kics(correct_templates)

    run_kubelinter(correct_templates)

    run_kubeaudit(correct_templates)

    run_kubescape(correct_templates)

    run_terrascan(correct_templates)
