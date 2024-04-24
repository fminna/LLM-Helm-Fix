#!/bin/bash

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

# This script takes as input a chart name, runs all tools on it, and for each misconfiguration found, it queries the LLMs for a fix, finally evaluating the fix.

# Take a chart_name variable as argument
chart_name=$1

# If not provided, exit
if [ -z "$chart_name" ]
then
    echo "No chart name provided! Exiting..."
    exit 1
fi

# Running Checkov
echo -e "\n -------------------------- \n"
# echo "Running Checkov on $chart_name ..."
# checkov -f templates/${chart_name}_template.yaml --quiet --compact --framework kubernetes -o json > tools_output/checkov/${chart_name}_results.json
# echo "Output saved to tools_output/checkov/${chart_name}_results.json"

# # Run Datree
# helm datree test templates/${chart_name}_template.yaml --only-k8s-files --quiet --output json > tools_output/datree/${chart_name}_results.json
# echo "Output saved to tools_output/datree/${chart_name}_results.json"

# # Run KICS
# kics scan -p templates/${chart_name}_template.yaml --exclude-severities info --disable-secrets --exclude-queries bb241e61-77c3-4b97-9575-c0f8a1e008d0 --exclude-queries 7c81d34c-8e5a-402b-9798-9f442630e678 -o . > /dev/null 2>&1
# mv results.json tools_output/kics/${chart_name}_results.json
# docker run -t -v ./templates:/path checkmarx/kics:v1.6.13 scan -p /path/mysql_template.yaml -o "/path/"
# echo "Output saved to tools_output/kics/${chart_name}_results.json"

# # Run Kubelinter
# kube-linter lint templates/${chart_name}_template.yaml --config kubelinter-config.yaml --format=json > tools_output/kubelinter/${chart_name}_results.json
# echo "Output saved to tools_output/kubelinter/${chart_name}_results.json"

# # Run Kubeaudit
# kubeaudit all -f templates/${chart_name}_template.yaml --minseverity "error" --format json > tools_output/kubeaudit/${chart_name}_results.json
# echo "Output saved to tools_output/kubeaudit/${chart_name}_results.json"

# # Run Kubescape
# kubescape scan templates/${chart_name}_template.yaml --exceptions kubescape_exceptions.json --format json --output tools_output/kubescape/${chart_name}_results.json > /dev/null 2>&1
# # echo "Output saved to tools_output/kubescape/${chart_name}_results.json"

# # Run Terrascan
# terrascan scan -i k8s -f templates/${chart_name}_template.yaml --skip-rules AC_K8S_0080 --skip-rules AC_K8S_0069 --skip-rules AC_K8S_0021 --skip-rules AC_K8S_0002 --skip-rules AC_K8S_0068 -o sarif > tools_output/terrascan/${chart_name}_results.json
# echo "Output saved to tools_output/terrascan/${chart_name}_results.json"

###############

# Parsing Checkov output
echo -e "\n -------------------------- \n"
python main.py --parse-output ${chart_name} checkov

# Parsing Datree output
python main.py --parse-output ${chart_name} datree

# Parsing KICS output
python main.py --parse-output ${chart_name} kics

# Parsing Kubelinter
python main.py --parse-output ${chart_name} kubelinter

# Parsing Kubeaudit
python main.py --parse-output ${chart_name} kubeaudit

# Parsing Kubescape
python main.py --parse-output ${chart_name} kubescape

# Parsing Terrascan
python main.py --parse-output ${chart_name} terrascan

###############

# Querying LLMs 
echo -e "\n -------------------------- \n"

# Create LLM results folder --- to save all refactorings YAML files
mkdir llm_refactorings/${chart_name}

# Checkov Misconfigurations
python main.py --query-llm ${chart_name}

###############

# Evaluate fixes
echo -e "\n -------------------------- \n"
python main.py --evaluate-fixes chatgpt
checkov -f tmp_snippets/chatgpt_ns_snippet.yaml --quiet --compact --framework kubernetes

python main.py --evaluate-fixes gemini
checkov -f tmp_snippets/gemini_ns_snippet.yaml --quiet --compact --framework kubernetes
