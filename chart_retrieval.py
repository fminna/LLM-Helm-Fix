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
from parse_tool_output import parse_output


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

        for chart in data[:60]:
            print(f"Repository: {chart['name']}")

            # Add current repository to Helm
            # os.system(f"helm repo add {chart['name']} {chart['repository']['url']}")

            # helm search repo {chart['name']}
            # for chart in repo:
            # helm template {chart['name']}/{chart['name']} > templates/{chart['name']}_template.yaml

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

        with open(f"templates/{chart_name}_template.yaml", "r", encoding="utf-8") as file:
            num_lines = len(file.readlines())

        if num_lines <= 1:
            row = [
                chart_name,
                "Unknown error - empty template",
                "N/A",
                "N/A",
            ]
            rows.append(row)

        else:
            num_containers = 0

            template = parse_yaml_template(chart_name)
            for document in template:  
                if "spec" in document:
                    if "containers" in document["spec"]:
                        num_containers += len(document["spec"]["containers"])
                    elif "template" in document["spec"]:
                        if "containers" in document["spec"]["template"]["spec"]:
                            num_containers += len(document["spec"]["template"]["spec"]["containers"])

                    elif "jobTemplate" in document["spec"]:
                        if "containers" in document["spec"]["jobTemplate"]["spec"]["template"]["spec"]:
                            num_containers += len(document["spec"]["jobTemplate"]["spec"]["template"]["spec"])

            row = [
                chart_name,
                "OK",
                num_lines,
                num_containers,
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
        ]
        rows.append(row)

    for row in rows:
        df.loc[len(df)] = row
    df.to_csv("results/chart_stats.csv", index=False)


def run_checkov(correct_templates):
    """ Run Checkov on all Helm chart templates.
    """

    for chart_name in correct_templates:
        command = f"checkov -f templates/{chart_name}_template.yaml --quiet --compact --framework kubernetes -o json > tools_output/checkov/{chart_name}_results.json"
        os.system(command)


def run_datree(correct_templates):
    """ Run Datree on all Helm chart templates.
    """

    for chart_name in correct_templates:
        command = f"helm datree test templates/{chart_name}_template.yaml --only-k8s-files --quiet --output json > tools_output/datree/{chart_name}_results.json"
        os.system(command)


def run_kics(correct_templates):
    """ Run KICS on all Helm chart templates.
    """

    for chart_name in correct_templates:
        command = f"kics scan -p templates/{chart_name}_template.yaml --exclude-severities info --disable-secrets --exclude-queries bb241e61-77c3-4b97-9575-c0f8a1e008d0 --exclude-queries 7c81d34c-8e5a-402b-9798-9f442630e678 -o . > /dev/null 2>&1"
        os.system(command)
        os.system(f"mv results.json tools_output/kics/{chart_name}_results.json")


def run_kubelinter(correct_templates):
    """ Run KubeLinter on all Helm chart templates.
    """

    for chart_name in correct_templates:
        command = f"kube-linter lint templates/{chart_name}_template.yaml --format=json > tools_output/kubelinter/{chart_name}_results.json"
        os.system(command)


def run_kubeaudit(correct_templates):
    """ Run Kubeaudit on all Helm chart templates.
    """

    for chart_name in correct_templates:
        command = f"kubeaudit all -f templates/{chart_name}_template.yaml --minseverity 'error' --format json > tools_output/kubeaudit/{chart_name}_results.json"
        os.system(command)


def run_kubescape(correct_templates):
    """ Run Kubeescape on all Helm chart templates.
    """

    for chart_name in correct_templates:
        command = f"kubescape scan templates/{chart_name}_template.yaml --exceptions kubescape_exceptions.json --format json --output tools_output/kubescape/{chart_name}_results.json > /dev/null 2>&1"
        os.system(command)


def run_terrascan(correct_templates):
    """ Run Terrascan on all Helm chart templates.
    """

    for chart_name in correct_templates:
        command = f"terrascan scan -i k8s -f templates/{chart_name}_template.yaml --skip-rules AC_K8S_0080 --skip-rules AC_K8S_0069 --skip-rules AC_K8S_0021 --skip-rules AC_K8S_0002 --skip-rules AC_K8S_0068 -o sarif > tools_output/terrascan/{chart_name}_results.json"
        os.system(command)


def scan_artifact_hub():
    # Search for all publicly available Helm charts
    correct_templates, failed_templates = get_helm_charts()

    print("Correct templates: ", len(correct_templates), correct_templates)
    # print("Failed templates: ", len(failed_templates))

    # generate_chart_stats(correct_templates, failed_templates)

    #################################

    # run_checkov(correct_templates)

    # run_datree(correct_templates)

    # run_kics(correct_templates)

    # run_kubelinter(correct_templates)

    # run_kubeaudit(correct_templates)

    # run_kubescape(correct_templates)

    # run_terrascan(correct_templates)

    #################################

    for chart_name in correct_templates:
        parse_output(chart_name, "checkov", True)
        parse_output(chart_name, "datree", True)
        parse_output(chart_name, "kics", True)
        parse_output(chart_name, "kubelinter", True)
        parse_output(chart_name, "kubeaudit", True)
        parse_output(chart_name, "kubescape", True)
        parse_output(chart_name, "terrascan", True)
