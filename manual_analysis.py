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

""" This script implements the manual analysis of the Helm Chart.
"""

import pandas as pd
import yaml
import os
from parse_tool_output import CheckovLookup, DatreeLookup, KICSLookup, KubeauditClass, KubelinterClass, KubescapeClass, TerrascanClass


# Gemini charts already analyzed
gemini = ['edge-operator', 'gopaddle', 'ibm-eventstreams-operator', 'extendeddaemonset', 'k6-operator', 'arroyo', 'ibm-cam', 'kfserving', 'galoy-deps', 'galaxy', 'keystone', 'osdfir-infrastructure', 'loki-stack', 'cluster-component', 'uffizzi-controller', 'testkube', 'otel-demo', 'flink-operator', 'one-green-core', 'kube-prometheus-stack', 'neuvector-core', 'uffizzi-app', 'operator', 'kyverno-stub-crds', 'victoria-metrics-k8s-stack', 'accumulo', 'signoz', 'eg-edge-stack-crds', 'kube-vip-cloud-provider', 'victoria-metrics-operator']


def add_std_id(llm):
    df = pd.read_csv(f"results/llm_{llm}_answers.csv")
    std_checks = []

    for _, row in df.iterrows():

        if row["Tool"] == "checkov":
            std_checks.append(CheckovLookup.get_value(row["Alert_ID"]))

        elif row["Tool"] == "datree":
            std_checks.append(DatreeLookup.get_value(row["Alert_ID"]))

        elif row["Tool"] == "kics":
            std_checks.append(KICSLookup.get_value(row["Alert_ID"]))

        elif row["Tool"] == "kubeaudit":
            std_checks.append(KubeauditClass.get_value(row["Alert_ID"]))

        elif row["Tool"] == "kubelinter":
            std_checks.append(KubelinterClass.get_value(row["Alert_ID"]))

        elif row["Tool"] == "kubescape":
            std_checks.append(KubescapeClass.get_value(row["Alert_ID"]))

        elif row["Tool"] == "terrascan":
            std_checks.append(TerrascanClass.get_value(row["Alert_ID"]))

    df["Standard_ID"] = std_checks
    df.to_csv(f"results/llm_{llm}_answers.csv", index=False)


def analy_short_db(llm, num_charts=3):
    """ The manual analysis of the Helm Chart.
    """

    df = pd.read_csv(f"results/llm_{llm}_answers.csv")
    print(len(df))

    # Remove failed rows
    for idx, row in df.iterrows():
        if str(row["Refactored_YAML"]).startswith("Failed to"):

            # TODO
            # check for the corresponding row["Fixed"]... should always be Not_fixed!

            df.drop(idx, inplace=True)
    print(len(df))

    print("\n ################ \n")

    # 1. Top ten mapped policies
    aux = df["Standard_ID"].value_counts()

    # Print the top ten mapped policies
    # print(aux.head(10))

    top_ten = []
    counter = 0

    # Get the top ten mapped policies in a list, i.e., top_ten = ['check_27', 'check_22', ...]
    for index, _ in aux.items():
        top_ten.append(index)
        counter += 1
        if counter == 10:
            break

    # 2. Select random charts for each policies
    charts_dict = {}

    for policy in top_ten:
        aux = df[df["Standard_ID"] == policy].sample(n=num_charts)

        aux_charts = list(aux["Chart"].values)
        charts_dict[policy] = aux_charts

        for chart in aux_charts:
            # Remove from df all rows with Chart == chart
            df = df[df["Chart"] != chart]

    # 3. Save the results
    df = pd.read_csv(f"results/llm_{llm}_answers.csv")
    df_fixed = pd.read_csv(f"results/llm_{llm}_fix.csv")
    idx = 0

    for policy, charts in charts_dict.items():

        print(f"Policy: {policy} ({idx}, {idx+1}, {idx+2})")

        for chart in charts:
            # Select first row with Chart == chart and Standard_ID == policy
            aux_df = df[(df["Chart"] == chart) & (df["Standard_ID"] == policy)].head(1)
            row_idx = aux_df.index.astype(int)[0]

            chart = aux_df["Chart"].values[0]
            alert_id = aux_df["Alert_ID"].values[0]
            tool = aux_df["Tool"].values[0]

            aux_fix_df = df_fixed[(df_fixed["Chart"] == chart) & (df_fixed["Alert_ID"] == alert_id)]
            fixed = aux_fix_df["Fixed"].values[0]

            print(f"{chart},{alert_id},{tool},{fixed}")

            refactored_path = f"manual_analysis/{llm}/refactored{idx}.yaml"
            original_path = f"manual_analysis/{llm}/original{idx}.yaml"
            # result_path = f"snippets/{llm}/results{row_idx}.json"
            # current_result_path = f"manual_analysis/{llm}/"

            failed = False
            try:
                refactored_yaml = yaml.load(aux_df["Refactored_YAML"].values[0], Loader=yaml.FullLoader)
            except Exception as e:
                print(f"Failed to parse YAML for {chart} - {alert_id}")
                failed = True

            if not failed:
                with open(refactored_path, "w", encoding="utf-8") as file:
                    yaml.dump(refactored_yaml, file)

            failed = False

            try:
                original_yaml = yaml.load(aux_df["Original_YAML"].values[0], Loader=yaml.FullLoader)
            except Exception as e:
                print(f"Failed to parse YAML for {chart} - {alert_id}")
                failed = True

            if not failed:
                with open(original_path, "w", encoding="utf-8") as file:
                    yaml.dump(original_yaml, file)

            # Copy result_path file into the manual_analysis/{llm} folder
            # os.system(f"cp {result_path} {current_result_path}")
            # os.system(f"mv {current_result_path}results{row_idx}.json {current_result_path}results{idx}.json")

            idx += 1

        print("\n ################ \n")


def generate_results(llm):

    tools_list = []

    for idx, tool in enumerate(tools_list):

        refactored_path = f"manual_analysis/{llm}/refactored{idx}.yaml"
        result_path = f"manual_analysis/{llm}/results{idx}.json"

        if tool == "checkov":
            command = f"checkov -f {refactored_path} --quiet --compact --framework kubernetes -o json > {result_path}"
            os.system(command)

        elif tool == "datree":
            command = f"helm datree test {refactored_path} --only-k8s-files --quiet --output json > {result_path}"
            os.system(command)

        elif tool == "kics":
            command = f"kics scan -p {refactored_path} --exclude-severities info --disable-secrets --exclude-queries bb241e61-77c3-4b97-9575-c0f8a1e008d0 --exclude-queries 7c81d34c-8e5a-402b-9798-9f442630e678 -o . > /dev/null 2>&1"
            os.system(command)
            os.system(f"mv results.json {result_path}")

        elif tool == "kubeaudit":
            command = f"kubeaudit all -f {refactored_path} --minseverity 'error' --format json > {result_path}"
            os.system(command)

        elif tool == "kubelinter":
            command = f"kube-linter lint {refactored_path} --format=json > {result_path}"
            os.system(command)

        elif tool == "kubescape":
            command = f"kubescape scan {refactored_path} --format json --output {result_path} > /dev/null 2>&1"
            os.system(command)

        elif tool == "terrascan":
            command = f"terrascan scan -i k8s -f {refactored_path} --skip-rules AC_K8S_0080 --skip-rules AC_K8S_0069 --skip-rules AC_K8S_0021 --skip-rules AC_K8S_0002 --skip-rules AC_K8S_0068 -o sarif > {result_path}"
            os.system(command)


def manual_analysis():
    """ The manual analysis of the Helm Chart.
    """

    llm = "gemini"

    generate_results(llm)

    # add_std_id(llm)

    # analy_short_db(llm, 3)
