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


import requests
import os


def get_helm_charts():
    """Retrieve all available Helm chart packages on Artifact Hub.
    """

    url = "https://artifacthub.io/api/v1/helm-exporter"

    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()  

        data = response.json()

        # helm repo list --> 12.900 ?
        # how many charts in total?

        for chart in data[:60]:
            print(f"Repository: {chart['name']}")
            # print(chart)


            # helm repo add {chart['name']} {chart['repository']['url']}
            # OR
            # helm fetch jetstack/cert-manager --untar
            # helm template ./cert-manager/

            # helm search repo {chart['name']}

            # for chart in repo:
            # helm template repository_name/chart_name





        print("Total packages: ", len(data))



    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")


    # url = "https://artifacthub.io/api/v1/packages/helm/repository_name/package_name/summary
    url = "https://artifacthub.io/api/v1/packages/helm/website/website/summary"

    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()  

        data = response.json()



    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")


def scan_artifact_hub():
    # Search for all publicly available Helm charts
    get_helm_charts()


# API-KEY-ID
# c9e6a323-9042-4a25-98bd-7b58487a0f81

# API-KEY-SECRET
# BPYiP4bPPVwi9gdwCJGfL9mEuHghe4Ngjxm2L2eeaic=

