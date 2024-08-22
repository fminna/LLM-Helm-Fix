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

""" Parsing the output of each chart analyzer tool.
"""

from typing import Callable
import sys
import json
import re
import ast
import pandas as pd
from query_llm import parse_yaml_template, get_resource_snippet
import math
import ast
from collections import Counter


def get_ckv_container_objects(template: dict, resource_path: str, containers="containers") -> list:
    """Returns the container object based on the resource path.
    
    Args:
        template (dict): The parsed YAML template.
        resource_path (str): The resource path (e.g., Pod/default/name).
    
    Returns:
        dict: The container object.
    """

    obj = []

    for document in template:
        if check_resource_path(resource_path.split("/"), document):
            obj = document
            if "template" in obj["spec"] and containers in obj["spec"]["template"]["spec"]:
                obj = obj["spec"]["template"]["spec"][containers]
                # When initContainers is empty, return an empty list
                if obj is None:
                    return []
                else:
                    return obj
            elif containers in obj["spec"]:
                return obj["spec"][containers]
            else:
                return []
    return []


def get_ckv_resource_path(check: str, template: dict) -> str:
    """ Returns the K8s resource path where there is the misconfiguration.
    """

    paths = {
        "resource_path": "",
        "obj_path": ""
    }

    # Resource path (e.g., Pod/default/name)
    resource_path = check["resource"].split(".")[:3]
    resource_path = "/".join(resource_path)

    # Object path
    obj_path = ""
    if check["check_id"] == "CKV2_K8S_5":
        pass

    # If specified, get the object path (e.g., spec/containers/0)
    elif check["check_result"]["evaluated_keys"]:
        obj_path = check["check_result"]["evaluated_keys"][0]
        index = obj_path.rfind("]/")
        if index != -1:
            obj_path = obj_path[:index+2]
        obj_path = obj_path.replace("[", "").replace("]", "")
        if obj_path[-1] == "/":
            obj_path = obj_path[:-1]

    paths["resource_path"] = resource_path
    paths["obj_path"] = obj_path

    if "initContainers" in obj_path:
        init_containers = get_ckv_container_objects(template, resource_path, "initContainers")
        obj_path = obj_path.replace("containers", "initContainers")
        for idx in range(len(init_containers)):
            obj_path = obj_path[:-1]
            obj_path += f"{str(idx)}"

            paths["obj_path"] = obj_path

    elif "containers" in obj_path:

        containers = get_ckv_container_objects(template, resource_path)
        for idx in range(len(containers)):
            # Given the object path, remove the last character after the last slash
            # Example: spec/containers/0 -> spec/containers/
            obj_path = obj_path[:-1]
            obj_path += f"{str(idx)}"

            paths["obj_path"] = obj_path

        init_containers = get_ckv_container_objects(template, resource_path, "initContainers")
        obj_path = obj_path.replace("containers", "initContainers")
        for idx in range(len(init_containers)):
            obj_path = obj_path[:-1]
            obj_path += f"{str(idx)}"

            paths["obj_path"] = obj_path

    return paths


def parse_checkov(chart_name: str):
    """ Parse the output of the Checkov tool.
    """

    json_path = f"tools_output/checkov/{chart_name}_results.json"

    try:
        with open(json_path, 'r', encoding="utf-8") as file:
            results = json.load(file)
    except json.decoder.JSONDecodeError:
        print(f"Error: {chart_name} - Checkov results file is empty.")
        return

    rows = []
    template = parse_yaml_template(chart_name)

    if "results" in results and "failed_checks" in results["results"]:
        for check in results["results"]["failed_checks"]:
            check_id = check['check_id']
            descr = check['check_name']

            paths = get_ckv_resource_path(check, template)
            resource = [paths["resource_path"], paths["obj_path"]]
            std_check_id = CheckovLookup.get_value(check_id)
            if std_check_id is None:
                std_check_id = "NOT_MAPPED"

            cis_cluster = CISLookup.get_value(std_check_id)
            if cis_cluster is None:
                cis_cluster = "N/A"

            yaml_snippet = get_resource_snippet(paths, template)

            snippet_length = len(str(yaml_snippet))

            if snippet_length < 10:
                template = parse_yaml_template(chart_name)
                template_str = "".join(str(doc) for doc in template)
                snippet_length = len(template_str)

            new_row = [
                chart_name, \
                "checkov", \
                check_id, \
                std_check_id, \
                cis_cluster, \
                descr, \
                resource, \
                yaml_snippet, \
                snippet_length
            ]
            rows.append(new_row)

    return rows


def get_datree_path(occurrence):
    """ Get the path of the object that caused the failure.
    """
    resource_path = f"{occurrence['kind']}/{occurrence['metadataName']}"

    for failure in occurrence["failureLocations"]:
        # Get the object path
        obj_path = failure["schemaPath"]

        if obj_path:

            # If there is a number in the path, remove everything after it
            # Example:
            # /spec/template/spec/containers/0/securityContext/... -->
            # /spec/template/spec/containers/0
            if any(char.isdigit() for char in obj_path):
                for idx, value in enumerate(obj_path):
                    if value.isdigit():
                        obj_path = obj_path[:idx+1]
                        break

            else:
                # Remove the last part of the path
                # Example: /spec/template/spec/hostNetwork --> /spec/template/spec
                obj_path = obj_path.rsplit('/', 1)[0]

        paths = {
            "resource_path": resource_path,
            "obj_path": obj_path
        }

        return paths


def parse_datree(chart_name: str):
    """ Parse the output of the Datree tool.
    """

    json_path = f"tools_output/datree/{chart_name}_results.json"

    try:
        with open(json_path, 'r', encoding="utf-8") as file:
            results = json.load(file)
    except json.decoder.JSONDecodeError:
        print(f"Error: {chart_name} - Datree results file is empty.")
        return

    rows = []
    template = parse_yaml_template(chart_name)

    if "policyValidationResults" and results["policyValidationResults"] is not None:
        for check in results["policyValidationResults"][0]["ruleResults"]:

            for occurrence in check["occurrencesDetails"]:
                check_id = check['identifier']
                descr = check['name']
                # print(f"{check_id}: {descr}")

                paths = get_datree_path(occurrence)
                resource = [paths["resource_path"], paths["obj_path"]]
                std_check_id = DatreeLookup.get_value(check_id)
                if std_check_id is None:
                    std_check_id = "NOT_MAPPED"

                cis_cluster = CISLookup.get_value(std_check_id)
                if cis_cluster is None:
                    cis_cluster = "N/A"

                yaml_snippet = get_resource_snippet(paths, template)
                snippet_length = len(str(yaml_snippet))

                if snippet_length < 10:
                    template = parse_yaml_template(chart_name)
                    template_str = "".join(str(doc) for doc in template)
                    snippet_length = len(template_str)

                new_row = [
                    chart_name, \
                    "datree", \
                    check_id, \
                    std_check_id, \
                    cis_cluster, \
                    descr, \
                    resource, \
                    yaml_snippet, \
                    snippet_length
                ]
                rows.append(new_row)

    return rows


def get_kics_path(file, template, check_id):
    """ Returns the path to the object in the template.
    """

    resource_path = ""
    obj_path = ""

    if "resource_type" in file and "resource_name" in file:
        resource_path = file["resource_type"] + "/" + \
                            file["resource_name"]
    if "search_key" in file:
        obj_path = file["search_key"]

    no_path_checks = ["check_26", "check_36", "check_48", "check_49", "check_53", \
                        "check_56", "check_65", "check_13", "check_47", "check_15"]
    if check_id in no_path_checks:
        obj_path = ""

    elif check_id == "check_32":
        pattern = r"\{\{([^}]*)\}\}"
        matches = re.findall(pattern, file["expected_value"])
        obj_path = matches[-1]

    else:
        try:
            obj_path = obj_path.split("}}.")[1]
        except IndexError:
            obj_path = ""

        obj_name = ""
        if ".name=" in obj_path:
            obj_name = obj_path.split(".name=")[1]
            obj_name = obj_name.replace("{{", "")
            obj_name = obj_name.replace("}}", "")
            if "." in obj_name:
                obj_name = obj_name.split(".")[0]

            obj_path = obj_path.split(".name=")[0]
            obj_path = obj_path.replace(".", "/")

            idx = find_resource_idx(template, resource_path, obj_path, obj_name)
            if idx:
                obj_path += "/" + idx

    if check_id == "check_52":
        obj_path = obj_path.replace(".", "/")
        obj_path = obj_path.replace("volumeClaimTemplates", "volumeClaimTemplates/0")
        # Delete the last part of obj_path after requests
        obj_path = "/".join(obj_path.split("/")[:-2])

    if check_id == "check_32":
        obj_path = ""

    paths = {
        "resource_path": resource_path,
        "obj_path": obj_path
    }

    if "." in obj_path:
        paths["obj_path"] = obj_path.replace(".", "/")

    return paths


def find_resource_idx(template: dict, resource_path: str, obj_path: str, obj_name: str) -> str:
    """Finds the index of the resource in the YAML template.

    Args:
        template (dict): The parsed YAML template.
        resource_path (str): The path to the resource in the YAML template.
        obj_path (str): The path to the object in the YAML template.
        obj_name (str): The name of the resource.

    Returns:
        str: The index as a str of the resource in the YAML template.
    """

    resource_path = resource_path.split("/")

    for document in template:

        # Check if the document is not empty
        # Example: the document only contains a comment
        # ---
        # Source: metallb/charts/crds/templates/crds.yaml
        # ---
        if not document:
            continue

        elif document["kind"] == resource_path[0] and \
            document["metadata"]["name"] == resource_path[1]:

            # Find the object
            keys = obj_path.split("/")
            objects = document

            for key in keys:
                if key not in objects:
                    return ""
                objects = objects[key]

            for idx, obj in enumerate(objects):
                if obj["name"] == obj_name:
                    return str(idx)

    return ""


def parse_kics(chart_name: str):
    """ Parse the output of the KICS tool.
    """

    json_path = f"tools_output/kics/{chart_name}_results.json"

    try:
        with open(json_path, 'r', encoding="utf-8") as file:
            results = json.load(file)
    except json.decoder.JSONDecodeError:
        print(f"Error: {chart_name} - KICS results file is empty.")
        return

    rows = []
    template = parse_yaml_template(chart_name)

    for check in results["queries"]:
        for file in check['files']:

            check_id = check['query_id']
            descr = check['query_name']
            # print(f"{check_id}: {descr}")

            std_check_id = KICSLookup.get_value(check_id)
            if std_check_id is None:
                std_check_id = "NOT_MAPPED"

            cis_cluster = CISLookup.get_value(std_check_id)
            if cis_cluster is None:
                cis_cluster = "N/A"

            paths = get_kics_path(file, template, std_check_id)
            resource = [paths["resource_path"], paths["obj_path"]]

            yaml_snippet = get_resource_snippet(paths, template)
            snippet_length = len(str(yaml_snippet))

            if snippet_length < 10:
                template = parse_yaml_template(chart_name)
                template_str = "".join(str(doc) for doc in template)
                snippet_length = len(template_str)

            new_row = [
                chart_name, \
                "kics", \
                check_id, \
                std_check_id, \
                cis_cluster, \
                descr, \
                resource, \
                yaml_snippet, \
                snippet_length
            ]
            rows.append(new_row)

    return rows


def get_kubel_container_path(template: dict, resource_path: str, cont_name: str) -> str:
    """Returns the path to the container in the template.
    
    Args:
        template (dict): The parsed YAML template.
        resource_path (str): The path to the resource in the template.
        cont_name (str): The name of the container.
    
    Returns:
        str: The path to the container in the template.
    """

    cont_path = ""
    for document in template:
        aux_path = ""

        if check_resource_path(resource_path.split("/"), document):
            document = document["spec"]
            cont_path += "spec/"

            if "template" in document:
                document = document["template"]["spec"]
                cont_path += "template/spec/"
            elif "jobTemplate" in document:
                document = document["jobTemplate"]["spec"]["template"]["spec"]
                cont_path += "jobTemplate/spec/template/spec/"

            for idx, container in enumerate(document["containers"]):
                if "name" in container and container["name"] == cont_name:
                    aux_path = "containers/" + str(idx)
                    break

            if not aux_path and "initContainers" in document:
                for idx, container in enumerate(document["initContainers"]):
                    if "name" in container and container["name"] == cont_name:
                        aux_path = "initContainers/" + str(idx)
                        break

        if aux_path:
            cont_path += aux_path
            break

    return cont_path


def get_kubelinter_path(check, template):
    kind = check["Object"]["K8sObject"]["GroupVersionKind"]["Kind"]
    namespace = check["Object"]["K8sObject"]["Namespace"]
    if not namespace:
        namespace = "default"
    name = check["Object"]["K8sObject"]["Name"]
    resource_path = f"{kind}/{namespace}/{name}"

    # spec/template/spec/containers/0/
    obj_path = ""

    if check["Diagnostic"]["Message"].startswith("container"):
        # Extract characters between \" and \"
        cont_name = check["Diagnostic"]["Message"].split("\"")[1]
        # Find container path based on container name
        obj_path = get_kubel_container_path(template, resource_path, cont_name)

    paths = {
        "resource_path": resource_path,
        "obj_path": obj_path
    }

    return paths


def parse_kubelinter(chart_name: str):
    """ Parse the output of the Kubelinter tool.
    """

    json_path = f"tools_output/kubelinter/{chart_name}_results.json"

    try:
        with open(json_path, 'r', encoding="utf-8") as file:
            results = json.load(file)
    except json.decoder.JSONDecodeError:
        print(f"Error: {chart_name} - Kubelinter results file is empty.")
        return

    rows = []
    template = parse_yaml_template(chart_name)

    if "Reports" in results:
        if results["Reports"] is None or not results["Reports"]:
            pass

        else:
            for check in results["Reports"]:
                check_id = check['Check']
                aux = check['Remediation'].split(". Refer to https://kubernetes.io")[0]
                descr = check['Diagnostic']['Message'] + ". " + aux
                # print(f"{check_id}: {descr}")

                std_check_id = KubelinterClass.get_value(check_id)
                if std_check_id is None:
                    std_check_id = "NOT_MAPPED"

                cis_cluster = CISLookup.get_value(std_check_id)
                if cis_cluster is None:
                    cis_cluster = "N/A"

                paths = get_kubelinter_path(check, template)
                resource = [paths["resource_path"], paths["obj_path"]]

                yaml_snippet = get_resource_snippet(paths, template)
                snippet_length = len(str(yaml_snippet))

                if snippet_length < 10:
                    template = parse_yaml_template(chart_name)
                    template_str = "".join(str(doc) for doc in template)
                    snippet_length = len(template_str)

                new_row = [
                    chart_name, \
                    "kubelinter", \
                    check_id, \
                    std_check_id, \
                    cis_cluster, \
                    descr, \
                    resource, \
                    yaml_snippet, \
                    snippet_length
                ]
                rows.append(new_row)

    return rows


def get_kubeaud_container_path(template: dict, resource_path: str, cont_name: str) -> str:
    """Returns the path to the container in the template.
    
    Args:
        template (dict): The parsed YAML template.
        resource_path (str): The path to the resource in the template.
        cont_name (str): The name of the container.
    
    Returns:
        str: The path to the container in the template.
    """

    cont_path = ""
    for document in template:
        aux_path = ""

        if check_resource_path(resource_path.split("/"), document):
            document = document["spec"]
            cont_path += "spec/"

            if "template" in document:
                document = document["template"]["spec"]
                cont_path += "template/spec/"
            elif "jobTemplate" in document:
                document = document["jobTemplate"]["spec"]["template"]["spec"]
                cont_path += "jobTemplate/spec/template/spec/"

            for idx, container in enumerate(document["containers"]):
                if container["name"] == cont_name:
                    aux_path = "containers/" + str(idx)
                    break

            if not aux_path and "initContainers" in document:
                for idx, container in enumerate(document["initContainers"]):
                    if container["name"] == cont_name:
                        aux_path = "initContainers/" + str(idx)
                        break

        if aux_path:
            cont_path += aux_path
            break

    return cont_path


def get_kubeaudit_path(check, template):
    # Resource path (e.g., Pod/default/name)
    if "ResourceNamespace" in check and "ResourceName" in check:
        resource_path = f"{check['ResourceKind']}/{check['ResourceNamespace']}/{check['ResourceName']}"
    elif "ResourceName" in check:
        resource_path = f"{check['ResourceKind']}/default/{check['ResourceName']}"
    else:
        resource_path = ""

    # spec/template/spec/containers/0/
    obj_path = ""

    if "Container" in check:
        # Find container path based on container name
        obj_path = get_kubeaud_container_path(template, resource_path, check["Container"])

    if check["AuditResultName"] == "AppArmorAnnotationMissing":
        # obj_path = check["Container"]
        obj_path = ""

    elif check["AuditResultName"] == "AppArmorInvalidAnnotation":
        obj_path = ""

    paths = {
        "resource_path": resource_path,
        "obj_path": obj_path
    }

    return paths


def parse_kubeaudit(chart_name: str):
    """ Parse the output of the Kubeaudit tool.
    """

    json_path = f"tools_output/kubeaudit/{chart_name}_results.json"

    # Convert result to a valid JSON
    with open(json_path, 'r', encoding="utf-8") as file:
        data = file.read()

        # If data does not begin with '{"checks": [', then it is not a valid JSON
        if not data.startswith('{"checks": ['):
            # Add '{"checks": [' at the beginning of data
            data = '{"checks": [' + data
            # Substitue all '}' with '},' except the last one
            data = data.replace('}', '},', data.count('}') - 1)
            # Add ']}' at the end of data
            data = data + ']}'

            # Save data to a new JSON file
            with open(json_path, 'w', encoding="utf-8") as file:
                file.write(data)

    try:
        with open(json_path, 'r', encoding="utf-8") as file:
            results = json.load(file)
    except json.decoder.JSONDecodeError:
        print(f"Error: {chart_name} - Kubeaudit results file is empty.")
        return

    rows = []
    template = parse_yaml_template(chart_name)

    for check in results["checks"]:
        check_id = check['AuditResultName']
        descr = check['msg']
        # print(f"{check_id}: {descr}")

        std_check_id = KubeauditClass.get_value(check_id)
        if std_check_id is None:
            std_check_id = "NOT_MAPPED"

        cis_cluster = CISLookup.get_value(std_check_id)
        if cis_cluster is None:
            cis_cluster = "N/A"

        paths = get_kubeaudit_path(check, template)
        resource = [paths["resource_path"], paths["obj_path"]]

        yaml_snippet = get_resource_snippet(paths, template)
        snippet_length = len(str(yaml_snippet))

        if snippet_length < 10:
            template = parse_yaml_template(chart_name)
            template_str = "".join(str(doc) for doc in template)
            snippet_length = len(template_str)

        new_row = [
            chart_name, \
            "kubeaudit", \
            check_id, \
            std_check_id, \
            cis_cluster, \
            descr, \
            resource, \
            yaml_snippet, \
            snippet_length
        ]
        rows.append(new_row)

    return rows


def get_kubescape_path(rule, control, paths):
    for path in rule["paths"]:
        obj_path = path["fixPath"]["path"]
        if not obj_path and "failedPath" in path:
            obj_path = path["failedPath"]

        # Convert obj_path to the correct format
        # 'spec.template.spec.containers[0].securityContext.capabilities.drop[0]'
        if "containers" in obj_path:
            # find the index of the first ']' occurrence
            index = obj_path.find("]")
            obj_path = obj_path[:index]
            obj_path = obj_path.replace("[", "/")

        # Resource labels
        elif control["controlID"] == "C-0076" or control["controlID"] == "C-0077":
            obj_path = ""

        # 'spec.template.spec.securityContext.allowPrivilegeEscalation'
        # 'spec.template.spec.automountServiceAccountToken'
        else:
            obj_path = obj_path.split(".")[:-2]
            obj_path = ".".join(obj_path)

        paths["obj_path"] = obj_path.replace(".", "/")
    return paths


def parse_kubescape(chart_name: str):
    """ Parse the output of the kubescape tool.
    """

    json_path = f"tools_output/kubescape/{chart_name}_results.json"

    try:
        with open(json_path, 'r', encoding="utf-8") as file:
            results = json.load(file)
    except json.decoder.JSONDecodeError:
        print(f"Error: {chart_name} - Kubescape results file is empty.")
        return []

    rows = []
    template = parse_yaml_template(chart_name)

    if "results" not in results:
        return []
 
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
                    descr = control['name']
                    # print(f"{check_id}: {descr}")

                    std_check_id = KubescapeClass.get_value(check_id)
                    if std_check_id is None:
                        std_check_id = "NOT_MAPPED"

                    cis_cluster = CISLookup.get_value(std_check_id)
                    if cis_cluster is None:
                        cis_cluster = "N/A"

                    for rule in control["rules"]:
                        paths = {
                                "resource_path": resource_path,
                                "obj_path": ""
                        }
                        if "paths" in rule:
                            paths = get_kubescape_path(rule, control, paths)

                        resource = [paths["resource_path"], paths["obj_path"]]

                        yaml_snippet = get_resource_snippet(paths, template)
                        snippet_length = len(str(yaml_snippet))

                        if snippet_length < 10:
                            template = parse_yaml_template(chart_name)
                            template_str = "".join(str(doc) for doc in template)
                            snippet_length = len(template_str)

                        new_row = [
                            chart_name, \
                            "kubescape", \
                            check_id, \
                            std_check_id, \
                            cis_cluster, \
                            descr, \
                            resource, \
                            yaml_snippet, \
                            snippet_length
                        ]
                        rows.append(new_row)

    return rows


def get_resource_namespace(template: dict, kind: str, name: str) -> str:
    """Gets the namespace of a K8s resource.
    
    Args:
        template (dict): The parsed YAML template.
        kind (str): The kind of the resource.
        name (str): The name of the resource.

    Returns:
        str: The namespace of the resource.
    """

    for document in template:
        if document and "kind" in document and document["kind"] == kind:
            if "metadata" in document and "name" in document["metadata"]:
                if document["metadata"]["name"] == name:
                    if "namespace" in document["metadata"]:
                        return document["metadata"]["namespace"]

    return "default"


def check_resource_path(path_list: str, document: dict) -> bool:
    """Check if the resource path exists in the template.

    Args:
        path_list: The resource path to check.
        document: The template to check.

    Returns:
        True if the resource path exists, False otherwise.
    """

    if path_list and document:
        if document["kind"].casefold() == path_list[0].casefold():

            if "namespace" in document["metadata"]:

                # Ignore default ns
                if document["metadata"]["namespace"] == "default":
                    if "name" in document["metadata"]:
                        return document["metadata"]["name"] == path_list[-1]

                # If the namespace was added during fixing, ignore it
                elif document["metadata"]["namespace"] == "test-ns":
                    if "name" in document["metadata"]:
                        return document["metadata"]["name"] == path_list[-1]
                
                # If the namespace was added during fixing, ignore it
                elif document["metadata"]["namespace"] == "busybox-namespace":
                    if "name" in document["metadata"]:
                        return document["metadata"]["name"] == path_list[-1]

                elif document["metadata"]["namespace"] == "kube-system":
                    if "name" in document["metadata"]:
                        return document["metadata"]["name"] == path_list[-1]

                elif document["metadata"]["namespace"] == path_list[1]:
                    if "name" in document["metadata"]:
                        return document["metadata"]["name"] == path_list[-1]

                elif document["metadata"]["namespace"] == path_list[1] and \
                    "name" in document["metadata"]:
                    return document["metadata"]["name"] == path_list[-1]

            # "namespace" not in document["metadata"]
            elif path_list[1] == "default" and "name" in document["metadata"]:
                return document["metadata"]["name"] == path_list[-1]

            elif "name" in document["metadata"]:
                return document["metadata"]["name"] == path_list[1]

    return False


def get_terr_container_path(template: dict, resource_path: list) -> tuple:
    """Gets the path (e.g., spec/template/spec/containers/0) to a container in a K8s resource.
    
    Args:
        template (dict): The parsed YAML template.
        resource_path (list): The path to the resource.

    Returns:
        tuple: The path to the container and the list of containers.
    """

    cont_path = ""
    containers = []
    init_containers = []

    for document in template:
        aux_path = ""

        if check_resource_path(resource_path, document):
            document = document["spec"]
            cont_path += "spec/"

            if "template" in document:
                document = document["template"]["spec"]
                cont_path += "template/spec/"
            elif "jobTemplate" in document:
                document = document["jobTemplate"]["spec"]["template"]["spec"]
                cont_path += "jobTemplate/spec/template/spec/"

            containers = document["containers"]
            aux_path = "containers/"

            if "initContainers" in document:
                init_containers = document["initContainers"]

        if containers:
            cont_path += aux_path
            break

    return cont_path, containers, init_containers


def get_terrascan_path(check, template):
    paths = {
        "resource_path": "",
        "obj_path": ""
    }

    if "locations" in check:
        for logical_location in check["locations"]:
            if "logicalLocations" in logical_location:
                for location in logical_location["logicalLocations"]:

                    kind = location["kind"]
                    # convert kind to standard format --- removing kubernetes_
                    kind = kind[11:]
                    # convert each character after '_' to uppercase
                    kind = ''.join([word.capitalize() for word in kind.split('_')])
                    name = location["name"]
                    namespace = get_resource_namespace(template, kind, name)
                    resource_path = f"{kind}/{namespace}/{name}"
                    paths = {
                            "resource_path": resource_path,
                            "obj_path": ""
                    }

                    checks_with_paths = ["AC_K8S_0069", "AC_K8S_0078", "AC_K8S_0085", \
                                            "AC_K8S_0097", "AC_K8S_0098", "AC_K8S_0099", \
                                            "AC_K8S_0100", "AC_K8S_0072", "AC_K8S_0070", \
                                            "AC_K8S_0087", "AC_K8S_0068", "AC_K8S_0080", \
                                            "AC_K8S_0079"]
                    if check['ruleId'] in checks_with_paths:
                        # Call fix_template for each container in the K8s resource
                        cont_path, containers, init_containers = get_terr_container_path(template, resource_path.split("/"))
                        for idx in range(len(containers)):
                            paths["obj_path"] = cont_path + str(idx)

                        if init_containers:
                            for idx in range(len(init_containers)):
                                cont_path = cont_path.replace("containers", "initContainers")
                                paths["obj_path"] = cont_path + str(idx)

    return paths


def parse_terrascan(chart_name: str):
    """ Parse the output of the terrascan tool.
    """

    json_path = f"tools_output/terrascan/{chart_name}_results.json"

    # Load the JSON result file
    try:
        with open(json_path, 'r', encoding="utf-8") as file:
            results = json.load(file)
    except json.decoder.JSONDecodeError:
        print(f"Error: {chart_name} - Terrascan results file is empty.")
        return

    rows = []
    template = parse_yaml_template(chart_name)

    for run in results["runs"]:
        for check in run["results"]:
            check_id = check['ruleId']
            descr = check['message']['text']
            # print(f"{check_id}: {descr}")

            std_check_id = TerrascanClass.get_value(check_id)
            if std_check_id is None:
                std_check_id = "NOT_MAPPED"

            cis_cluster = CISLookup.get_value(std_check_id)
            if cis_cluster is None:
                cis_cluster = "N/A"

            paths = get_terrascan_path(check, template)
            resource = [paths["resource_path"], paths["obj_path"]]

            yaml_snippet = get_resource_snippet(paths, template)
            snippet_length = len(str(yaml_snippet))

            if snippet_length < 10:
                template = parse_yaml_template(chart_name)
                template_str = "".join(str(doc) for doc in template)
                snippet_length = len(template_str)

            new_row = [
                chart_name, \
                "terrascan", \
                check_id, \
                std_check_id, \
                cis_cluster, \
                descr, \
                resource, \
                yaml_snippet, \
                snippet_length
            ]
            rows.append(new_row)

    return rows


def count_alert_occurrences():
    """ Count the number of occurrences of each alert.
    """

    # df = pd.read_csv("results/rq1_short_results.csv")
    # Columns: Chart, Alert_ID, Tool, Standard_ID, CIS_Cluster

    # counter = Counter()

    # for _, row in df.iterrows():
    #     counter[row["Standard_ID"]] += 1

    # print(counter.most_common(10))

    ###

    # df = pd.read_csv("results/rq1_results.csv")
    # charts = df["Chart"].unique()

    # rows = []

    # for idx, chart_name in enumerate(charts):
    #     print(f"{idx}: Processing {chart_name} ...")

    #     aux_df = df[df["Chart"] == chart_name]

    #     checkov = len(aux_df[aux_df["Tool"] == "checkov"])
    #     datree = len(aux_df[aux_df["Tool"] == "datree"])
    #     kics = len(aux_df[aux_df["Tool"] == "kics"])
    #     kubeaudit = len(aux_df[aux_df["Tool"] == "kubeaudit"])
    #     kubelinter = len(aux_df[aux_df["Tool"] == "kubelinter"])
    #     kubescape = len(aux_df[aux_df["Tool"] == "kubescape"])
    #     terrascan = len(aux_df[aux_df["Tool"] == "terrascan"])

    #     row = [
    #         chart_name,
    #         checkov,
    #         datree,
    #         kics,
    #         kubeaudit,
    #         kubelinter,
    #         kubescape,
    #         terrascan
    #     ]
    #     rows.append(row)

    # df = pd.read_csv("results/alert_stats.csv")
    # for row in rows:
    #     df.loc[len(df)] = row
    # df.to_csv("results/alert_stats.csv", index=False)

    ###

    df = pd.read_csv("results/alert_stats.csv")
    
    print(f"Min value: {df['Checkov'].min()}")
    print(f"Max value: {df['Checkov'].max()}")
    print(f"Average value: {df['Checkov'].mean()}")
    print(f"Standard deviation: {df['Checkov'].std()}")
    print(f"Median value: {df['Checkov'].median()}")

    print(f"Min value: {df['Datree'].min()}")
    print(f"Max value: {df['Datree'].max()}")
    print(f"Average value: {df['Datree'].mean()}")
    print(f"Standard deviation: {df['Datree'].std()}")
    print(f"Median value: {df['Datree'].median()}")

    print(f"Min value: {df['KICS'].min()}")
    print(f"Max value: {df['KICS'].max()}")
    print(f"Average value: {df['KICS'].mean()}")
    print(f"Standard deviation: {df['KICS'].std()}")
    print(f"Median value: {df['KICS'].median()}")

    print(f"Min value: {df['Kubeaudit'].min()}")
    print(f"Max value: {df['Kubeaudit'].max()}")
    print(f"Average value: {df['Kubeaudit'].mean()}")
    print(f"Standard deviation: {df['Kubeaudit'].std()}")   
    print(f"Median value: {df['Kubeaudit'].median()}")

    print(f"Min value: {df['Kubelinter'].min()}")
    print(f"Max value: {df['Kubelinter'].max()}")
    print(f"Average value: {df['Kubelinter'].mean()}")
    print(f"Standard deviation: {df['Kubelinter'].std()}")
    print(f"Median value: {df['Kubelinter'].median()}")

    print(f"Min value: {df['Kubescape'].min()}")
    print(f"Max value: {df['Kubescape'].max()}")
    print(f"Average value: {df['Kubescape'].mean()}")
    print(f"Standard deviation: {df['Kubescape'].std()}")
    print(f"Median value: {df['Kubescape'].median()}")

    print(f"Min value: {df['Terrascan'].min()}")
    print(f"Max value: {df['Terrascan'].max()}")
    print(f"Average value: {df['Terrascan'].mean()}")
    print(f"Standard deviation: {df['Terrascan'].std()}")
    print(f"Median value: {df['Terrascan'].median()}")


def generate_template_yaml_stats():
    df = pd.read_csv("results/templates_stats.csv")
    correct_templates = df[df["Template"] == "Correct"]["Chart"].values
    print("Correct templates: ", len(correct_templates))

    rows = []
    for chart_name in correct_templates:

        template_file = f"templates/{chart_name}_template.yaml"
        with open(template_file, 'r', encoding="utf-8") as file:
            lines = file.readlines()

        num_lines = len(lines)

        semicolons = 0
        for line in lines:
            semicolons += line.count(":")

        three_dash = 0
        for line in lines:
            three_dash += line.count("---")

        row = [chart_name, num_lines, semicolons, three_dash]
        rows.append(row)

    df = pd.read_csv("results/templates_yaml_stats.csv")
    for row in rows:
        df.loc[len(df)] = row
    df.to_csv("results/templates_yaml_stats.csv", index=False)


def generate_semicolon_stats(tool: str):
    df = pd.read_csv("results/templates_yaml_stats.csv")
    pivot_df = pd.read_csv("results/rq1_pivot_results.csv")

    # tool_df = pd.read_csv("results/chatgpt_queries.csv")
    tool_df = pd.read_csv("results/rq1_short_results.csv")
    tool_df = tool_df[tool_df["Tool"] == tool]
    policies = tool_df["Alert_ID"].unique()

    semicolon_df = pd.DataFrame()

    for policy in policies[1:]:

        column = []

        start = 0
        end = 100
        max_semic = 53691

        while start < max_semic:

            counter = 0
            charts = df[(df['Semicolon'] >= start) & (df['Semicolon'] < end)]["Chart"].values
            # print(len(charts))

            for chart in charts:

                # Select the cell with "Chart" equal chart and column equal alert.
                cell = pivot_df.loc[pivot_df["Chart"] == chart, policy].values
                if cell.size > 0:
                    counter += int(cell[0])

            column.append(counter)

            start += 100
            end += 100

        semicolon_df[policy] = column

    # print(semicolon_df.head(10))
    semicolon_df.to_csv(f"results/semicolon_{tool}_stats.csv", index=False)


def semicolon_charts():
    df = pd.read_csv("results/templates_yaml_stats.csv")
    charts = []

    start = 0
    end = 100
    max_semic = 53691

    while start < max_semic:
        aux_charts = df[(df['Semicolon'] >= start) & (df['Semicolon'] < end)]["Chart"].values

        try:
            chart_name = aux_charts[0]
            charts.append(chart_name)
        except IndexError:
            pass

        start += 100
        end += 100

    print("")
    print(len(charts))
    print("")

    df = pd.read_csv("results/rq1_short_results.csv")
    rows = []

    for chart_name in charts:
        aux_df = df[df["Chart"] == chart_name]

        # Iterate aux_df
        for _, row in aux_df.iterrows():

            resource = ast.literal_eval(row["Resource"])
            paths = {
                "resource_path": resource[0],
                "obj_path": resource[1]
            }
            resource_type = paths["resource_path"].split("/")[0]
            query = "You are a software engineer working on a Kubernetes project. You need to refactor the following " + resource_type + " YAML resource because " + row["Description"].lower() + ". You must only generate YAML code between --- characters, with no additional text or description."

            new_row = [
                chart_name,
                row["Alert_ID"],
                row["Tool"],
                row["Resource"],
                query,
                row["Original_YAML"],
            ]
            rows.append(new_row)

    df = pd.read_csv("results/chatgpt_queries.csv")
    for row in rows:
        df.loc[len(df)] = row
    df.to_csv("results/chatgpt_queries.csv", index=False)

    print(len(df))


def alert_stats():
    """ Get the number of alerts for each tool.
    """

    df = pd.read_csv("results/rq1_results.csv")

    print("Total alerts: " + str(len(df)))
    # Print the top ten values of the "Alert_ID" column
    print(df["Alert_ID"].value_counts().head(10))

    df = df[df["Tool"] == "kubeaudit"]
    df = df.drop_duplicates(subset=["Chart"])
    alert_files = df["Chart"].values
    print("RQ1: " + str(len(alert_files)))

    df = pd.read_csv("results/tools_stats.csv")
    df = df[df["Kubeaudit"] == "OK"]
    tool_files = df["Chart"].values
    print("Tool stats: " + str(len(df)))

    missing = []
    for chart_name in tool_files:
        if chart_name not in alert_files:
            missing.append(chart_name)

    print("Missing: " + str(len(missing)))
    print(missing)


def generate_short_query_dataset():
    """ Generate a short dataset for the LLM queries.
    """

    df = pd.read_csv("results/rq1_results.csv")

    # Set the column "Chart" and "Alert_ID" as index
    df = df.set_index(["Chart", "Standard_ID"])

    # Drop duplicates in the index
    df = df[~df.index.duplicated(keep='first')]
    # Reset the index
    df = df.reset_index()

    print(len(df))

    # Sort the dataframe by occurrences in the "Standard_ID" column
    df = df.sort_values(by=["Standard_ID"], ascending=False)
    # Print top ten
    print(df["Standard_ID"].value_counts().head(10))

    # Save the DataFrame to a CSV file
    # df.to_csv("results/rq1_short_results.csv")


def llm_query_stats():
    """ Get the number of queries for each chart.
    """

    # df = pd.read_csv("results/rq1_results.csv")

    # rq1_stats_df = pd.read_csv("results/rq1_stats.csv")
    # # CSV: Tool,Alert_ID,Standard_ID,Description,Charts,#_Charts,Occurrences

    # for _, row in df.iterrows():

    #     if row["Alert_ID"] in rq1_stats_df["Alert_ID"].values:

    #         if row["Chart"] not in rq1_stats_df.loc[rq1_stats_df["Alert_ID"] == row["Alert_ID"], "Charts"].values:
    #             rq1_stats_df.loc[rq1_stats_df["Alert_ID"] == row["Alert_ID"], "Charts"] += f", {row['Chart']}"
    #             rq1_stats_df.loc[rq1_stats_df["Alert_ID"] == row["Alert_ID"], "#_Charts"] += 1

    #         rq1_stats_df.loc[rq1_stats_df["Alert_ID"] == row["Alert_ID"], "Occurrences"] += 1

    #     else:

    #         new_row = [
    #             row["Tool"],
    #             row["Alert_ID"],
    #             row["Standard_ID"],
    #             row["Description"],
    #             row["Chart"],
    #             1,
    #             1
    #         ]
    #         rq1_stats_df.loc[len(rq1_stats_df)] = new_row

    # rq1_stats_df.to_csv("results/rq1_stats.csv", index=False)

    # # Print the number of rows in the DataFrame
    # print(f"Number of rows: {len(df)}")
    # # Print the min value of the 'Characters' column
    # print(f"Min value: {df['Characters'].min()}")
    # # Print the max value of the 'Characters' column
    # print(f"Max value: {df['Characters'].max()}")
    # # Print the average value of the 'Characters' column
    # print(f"Average value: {df['Characters'].mean()}")
    # # Print the standard deviation of the 'Characters' column
    # print(f"Standard deviation: {df['Characters'].std()}")
    # # Print the median value of the 'Characters' column
    # print(f"Median value: {df['Characters'].median()}")

    ###

    df = pd.read_csv("results/rq1_results.csv")
    # Get the list of unique values from 'Chart' column
    templates = df["Chart"].unique()

    llm_query_df = pd.read_csv("results/llm_query_stats.csv")

    # CSV: Chart | Total_queries | Tools_unique | Standard_unique | Max_chars | Min_chars | Avg_chars
    for idx, chart_name in enumerate(templates):
        aux_df = df[df["Chart"] == chart_name]

        new_row = [
            idx,
            chart_name,
            len(aux_df),
            len(aux_df["Alert_ID"].unique()),
            len(aux_df["Standard_ID"].unique()),
            aux_df["Characters"].min(),
            aux_df["Characters"].max(),
            round(aux_df["Characters"].mean(), 2)
        ]

        llm_query_df.loc[len(llm_query_df)] = new_row

    llm_query_df.to_csv("results/llm_query_stats.csv", index=False)

    # Print sum of the 'Total_queries' column
    print(f"Total queries: {llm_query_df['Total_queries'].sum()}")
    # Print sum of the 'Tools_unique' column
    print(f"Total tools uniques: {llm_query_df['Tools_unique'].sum()}")
    # Print sum of the 'Standard_unique' column
    print(f"Total standard uniques: {llm_query_df['Standard_unique'].sum()}")

    ###

    df = pd.read_csv("results/llm_query_stats.csv")

    print(f"Min value: {df['Min_chars'].min()}")
    print(f"Max value: {df['Max_chars'].max()}")
    print(f"Average value: {df['Mean_chars'].mean()}")
    print(f"Standard deviation: {df['Mean_chars'].std()}")
    print(f"Median value: {df['Mean_chars'].median()}")
    print(f"25th percentile: {df['Mean_chars'].quantile(0.25)}")
    print(f"75th percentile: {df['Mean_chars'].quantile(0.75)}")


def parse_output():
    """ Parse the output of a chart analyzer tool.
    """

    # df = pd.read_csv("results/rq1_results.csv")
    # print(df["Standard_ID"].value_counts().head(10))
    # print(df["CIS_Cluster"].value_counts().head(10))

    # Count alert occurrences
    # count_alert_occurrences()

    # alert_stats()

    # generate_short_query_dataset()

    semicolon_charts()

    # llm_query_stats()

    # df = pd.read_csv("results/tools_stats.csv")
    # templates = df[df["Checkov"] == "OK"]["Chart"].values
    # print("Number of charts: " + str(len(templates)))

    # rows = []
    # for idx, chart_name in enumerate(templates):
    #     print(f"{idx} - Processing {chart_name}...")

    #     # aux_rows = parse_checkov(chart_name)
    #     # aux_rows = parse_datree(chart_name)
    #     # aux_rows = parse_kics(chart_name)
    #     aux_rows = parse_kubeaudit(chart_name)
    #     # aux_rows = parse_kubelinter(chart_name)
    #     # aux_rows = parse_kubescape(chart_name)
    #     # aux_rows = parse_terrascan(chart_name)

    #     rows.extend(aux_rows)

    # df = pd.read_csv("results/rq1_results.csv")
    # for row in rows:
    #     df.loc[len(df)] = row
    # df.to_csv("results/rq1_results.csv", index=False)


class CISLookup:
    """This class is used to lookup the CIS Benchmark cluster ID.
    """

    _LOOKUP = {
        "check_10": "Pod Security Policy",
        "check_11": "Pod Security Policy",
        "check_12": "Pod Security Policy",
        "check_21": "Pod Security Policy",
        "check_22": "Pod Security Policy",
        "check_23": "Pod Security Policy",
        "check_24": "Pod Security Policy",
        "check_26": "General Policies",
        "check_28": "Pod Security Policy",
        "check_30": "General Policies",
        "check_31": "General Policies",
        "check_33": "Secrets Management",
        "check_34": "Pod Security Policy",
        "check_35": "RBAC and Service Accounts",
        "check_36": "RBAC and Service Accounts",
        "check_37": "RBAC and Service Accounts",
        "check_39": "RBAC and Service Accounts",
        "check_40": "Network Policies and CNI",
        "check_54": "RBAC and Service Accounts",
        "check_59": "RBAC and Service Accounts",
        "check_70": "Network Policies and CNI",
        "check_77": "RBAC and Service Accounts",
        "check_78": "RBAC and Service Accounts",
        "check_80": "RBAC and Service Accounts"
    }

    @classmethod
    def get_value(cls, key) -> Callable:
        return cls._LOOKUP.get(key)


class CheckovLookup:
    """This class is used to lookup the function to be called for each check.
    """

    _LOOKUP = {
        "CKV_K8S_1": "",
        "CKV_K8S_2": "",
        "CKV_K8S_3": "",
        "CKV_K8S_4": "",
        "CKV_K8S_5": "",
        "CKV_K8S_6": "",
        "CKV_K8S_7": "",
        "CKV_K8S_8": "check_7", 
        "CKV_K8S_9": "check_8", 
        "CKV_K8S_10": "check_4", 
        "CKV_K8S_11": "check_5", 
        "CKV_K8S_12": "check_1", 
        "CKV_K8S_13": "check_2", 
        "CKV_K8S_14": "check_0", 
        "CKV_K8S_15": "check_25", 
        "CKV_K8S_16": "check_21", 
        "CKV_K8S_17": "check_10", 
        "CKV_K8S_18": "check_11", 
        "CKV_K8S_19": "check_12",
        "CKV_K8S_20": "check_22", 
        "CKV_K8S_21": "check_26", 
        "CKV_K8S_22": "check_27", 
        "CKV_K8S_23": "check_28", 
        "CKV_K8S_25": "check_34", 
        "CKV_K8S_26": "check_29",
        "CKV_K8S_28": "check_34", 
        "CKV_K8S_29": "check_30", 
        "CKV_K8S_31": "check_31", 
        "CKV_K8S_32": "check_31",
        "CKV_K8S_33": "check_38",
        "CKV_K8S_35": "check_33", 
        "CKV_K8S_36": "check_34",
        "CKV_K8S_24": "check_34",
        "CKV_K8S_37": "check_34", 
        "CKV_K8S_38": "check_35", 
        "CKV_K8S_39": "check_34", 
        "CKV_K8S_40": "check_13", 
        "CKV_K8S_41": "check_35", 
        "CKV_K8S_42": "check_35", 
        "CKV_K8S_43": "check_9", 
        "CKV2_K8S_6": "check_40",
        "CKV_K8S_30": "check_30",
        "CKV_K8S_155": "check_54",
        "CKV2_K8S_5": "check_59",
        "CKV_K8S_49": "check_54",
        "CKV_K8S_156": "check_54",
        "CKV_K8S_157": "check_54",
        "CKV_K8S_158": "check_54",
        "CKV2_K8S_3": "check_54",
        "CKV2_K8S_4": "check_54",
        "CKV2_K8S_2": "check_54",
        "CKV_K8S_27": "check_15",
        "CKV2_K8S_1": "check_54",
        "CKV_K8S_153": "check_73",
        "CKV_K8S_119": "check_74",
        "CKV_K8S_116": "check_74",
        "CKV_K8S_117": "check_75",
        "CKV_K8S_34": "check_72",
    }

    @classmethod
    def get_value(cls, key) -> Callable:
        """ Get the function to be called for each check.

        Args:
            key (str): The check number.
        """
        return cls._LOOKUP.get(key)

    @classmethod
    def print_value(cls, key) -> None:
        """ Print the function to be called for each check."""
        print(cls._LOOKUP.get(key))


class DatreeLookup:
    """This class is used to lookup the function to be called for each check.
    """

    _LOOKUP = {
        "CONTAINERS_MISSING_LIVENESSPROBE_KEY": "check_7",
        "CONTAINERS_MISSING_READINESSPROBE_KEY": "check_8",
        "CONTAINERS_MISSING_CPU_REQUEST_KEY": "check_4",
        "CONTAINERS_MISSING_CPU_LIMIT_KEY": "check_5",
        "CONTAINERS_MISSING_MEMORY_REQUEST_KEY": "check_1",
        "CONTAINERS_MISSING_MEMORY_LIMIT_KEY": "check_2",
        "CONTAINERS_MISSING_IMAGE_VALUE_VERSION": "check_0",
        "CONTAINERS_INCORRECT_PRIVILEGED_VALUE_TRUE": "check_21",
        "CONTAINERS_INCORRECT_HOSTPID_VALUE_TRUE": "check_10",
        "CONTAINERS_INCORRECT_HOSTIPC_VALUE_TRUE": "check_11",
        "CONTAINERS_INCORRECT_HOSTNETWORK_VALUE_TRUE": "check_12",
        "CONTAINERS_MISSING_KEY_ALLOWPRIVILEGEESCALATION": "check_22",
        "WORKLOAD_INCORRECT_NAMESPACE_VALUE_DEFAULT": "check_26",
        "CONTAINERS_INCORRECT_READONLYROOTFILESYSTEM_VALUE": "check_27",
        "CONTAINERS_INCORRECT_RUNASNONROOT_VALUE": "check_28",
        "CIS_MISSING_KEY_SECURITYCONTEXT": "check_30",
        "CONTAINERS_INCORRECT_SECCOMP_PROFILE": "check_31",
        "CIS_INVALID_VALUE_SECCOMP_PROFILE": "check_31",
        "CONTAINERS_INVALID_CAPABILITIES_VALUE": "check_23",
        "CIS_MISSING_VALUE_DROP_NET_RAW": "check_23",
        "CIS_INVALID_VALUE_AUTOMOUNTSERVICEACCOUNTTOKEN": "check_35",
        "SRVACC_INCORRECT_AUTOMOUNTSERVICEACCOUNTTOKEN_VALUE": "check_35",
        "CONTAINERS_MISSING_IMAGE_VALUE_DIGEST": "check_9",
        "CIS_INVALID_KEY_SECRETKEYREF_SECRETREF": "check_33",
        "DEPLOYMENT_INCORRECT_REPLICAS_VALUE": "check_45",
        "SERVICE_INCORRECT_TYPE_VALUE_NODEPORT": "check_56",
        "CONTAINERS_INCORRECT_RUNASUSER_VALUE_LOWUID": "check_13",
        "CONTAINERS_INCORRECT_KEY_HOSTPORT": "check_29",
        "CONTAINER_CVE2021_25741_INCORRECT_SUBPATH_KEY": "check_50",
        "CIS_INVALID_VERB_SECRETS": "check_54",
        "CONTAINERS_INCORRECT_RESOURCES_VERBS_VALUE": "check_54",
        "EKS_INVALID_CAPABILITIES_EKS": "check_34",
        "CIS_INVALID_VALUE_CREATE_POD": "check_54",
        "CIS_INVALID_WILDCARD_ROLE": "check_54",
        "CIS_INVALID_VALUE_BIND_IMPERSONATE_ESCALATE": "check_54",
        "CONTAINERS_INCORRECT_KEY_HOSTPATH": "check_47",
        "CIS_INVALID_ROLE_CLUSTER_ADMIN": "check_65",
        "INGRESS_INCORRECT_HOST_VALUE_PERMISSIVE": "check_66",
        "WORKLOAD_INVALID_LABELS_VALUE": "check_43",
    }

    @classmethod
    def get_value(cls, key) -> Callable:
        """ Get the function to be called for each check.

        Args:
            key (str): The check number.
        """
        return cls._LOOKUP.get(key)

    @classmethod
    def print_value(cls, key) -> None:
        """ Print the function to be called for each check."""
        print(cls._LOOKUP.get(key))


class KICSLookup:
    """This class is used to lookup the function to be called for each check.
    """

    # KICS Policies: https://docs.kics.io/latest/queries/all-queries/

    _LOOKUP = {
        "5572cc5e-1e4c-4113-92a6-7a8a3bd25e6d": "check_22",
        "4ac0e2b7-d2d2-4af7-8799-e8de6721ccda": "check_5",
        "ca469dd4-c736-448f-8ac1-30a642705e0a": "check_4",
        "cf34805e-3872-4c08-bf92-6ff7bb0cfadb": "check_13",
        "02323c00-cdc3-4fdc-a310-4f2b3e7a1660": "check_13",
        "e3aa0612-4351-4a0d-983f-aefea25cf203": "check_13",
        "b14d1bc4-a208-45db-92f0-e21f8e2588e9": "check_2",
        "229588ef-8fde-40c8-8756-f4f2b5825ded": "check_1",
        "dbbc6705-d541-43b0-b166-dd4be8208b54": "check_23",
        "a659f3b5-9bf0-438a-bd9a-7d3a6427f1e3": "check_8",
        "f377b83e-bd07-4f48-a591-60c82b14a78b": "check_31",
        "591ade62-d6b0-4580-b1ae-209f80ba1cd9": "check_37",
        "48471392-d4d0-47c0-b135-cdec95eb3eef": "check_36",
        "611ab018-c4aa-4ba2-b0f6-a448337509a6": "check_26",
        "7c81d34c-8e5a-402b-9798-9f442630e678": "check_9",
        "583053b7-e632-46f0-b989-f81ff8045385": "check_0",
        "ade74944-a674-4e00-859e-c6eab5bde441": "check_7",
        "8b36775e-183d-4d46-b0f7-96a6f34a723f": "check_32",
        "268ca686-7fb7-4ae9-b129-955a2a89064e": "check_23",
        "4a20ebac-1060-4c81-95d1-1f7f620e983b": "check_48",
        "48a5beba-e4c0-4584-a2aa-e6894e4cf424": "check_49",
        "a97a340a-0063-418e-b3a1-3028941d0995": "check_30",
        "a9c2f49d-0671-4fc9-9ece-f4e261e128d0": "check_27",
        "dd29336b-fe57-445b-a26e-e6aa867ae609": "check_21",
        "2f1a0619-b12b-48a0-825f-993bb6f01d58": "check_23",
        "235236ee-ad78-4065-bd29-61b061f28ce0": "check_23",
        "19ebaa28-fc86-4a58-bcfa-015c9e22fe40": "check_23",
        "302736f4-b16c-41b8-befe-c0baffa0bd9d": "check_10",
        "cd290efd-6c82-4e9d-a698-be12ae31d536": "check_11",
        "6b6bdfb3-c3ae-44cb-88e4-7405c1ba2c8a": "check_12",
        "caa3479d-885d-4882-9aac-95e5e78ef5c2": "check_25",
        "3d658f8b-d988-41a0-a841-40043121de1e": "check_33",
        "8cf4671a-cf3d-46fc-8389-21e7405063a2": "check_52",
        "bb241e61-77c3-4b97-9575-c0f8a1e008d0": "check_53",
        "b7652612-de4e-4466-a0bf-1cd81f0c6063": "check_55",
        "845acfbe-3e10-4b8e-b656-3b404d36dfb2": "check_56",
        "056ac60e-fe07-4acc-9b34-8e1d51716ab9": "check_54",
        "b7bca5c4-1dab-4c2c-8cbe-3050b9d59b14": "check_54",
        "1db3a5a5-bf75-44e5-9e44-c56cfc8b1ac5": "check_60",
        "26763a1c-5dda-4772-b507-5fca7fb5f165": "check_56",
        "aee3c7d2-a811-4201-90c7-11c028be9a46": "check_6",
        "c1032cf7-3628-44e2-bd53-38c17cf31b6b": "check_62",
        "592ad21d-ad9b-46c6-8d2d-fad09d62a942": "check_54",
        "aa8f7a35-9923-4cad-bd61-a19b7f6aac91": "check_47",
        "5308a7a8-06f8-45ac-bf10-791fe21de46e": "check_47",
        "192fe40b-b1c3-448a-aba2-6cc19a300fe3": "check_63",
        "249328b8-5f0f-409f-b1dd-029f07882e11": "check_65",
        "b23e9b98-0cb6-4fc9-b257-1f3270442678": "check_60",
        "c589f42c-7924-4871-aee2-1cede9bc7cbc": "check_54",
        "a6f34658-fdfb-4154-9536-56d516f65828": "check_15",
        "3ca03a61-3249-4c16-8427-6f8e47dda729": "check_57",
        "6b896afb-ca07-467a-b256-1a0077a1c08e": "check_39",
        "94b76ea5-e074-4ca2-8a03-c5a606e30645": "check_51",
        "d740d048-8ed3-49d3-b77b-6f072f3b669e": "check_76",
        "dd667399-8d9d-4a8d-bbb4-e49ab53b2f52": "",
        "9296f1cc-7a40-45de-bd41-f31745488a0e": "",
        "8320826e-7a9c-4b0b-9535-578333193432": "check_54",
        "6d173be7-545a-46c6-a81d-2ae52ed1605d": "check_72",
        "8b862ca9-0fbd-4959-ad72-b6609bdaa22d": "check_72",
        "1e749bc9-fde8-471c-af0c-8254efd2dee5": "check_77",
        "38fa11ef-dbcc-4da8-9680-7e1fd855b6fb": "check_78",
        "a31b7b82-d994-48c4-bd21-3bab6c31827a": "check_76",
        "a33e9173-b674-4dfb-9d82-cf3754816e4b": "check_12",
        "87554eef-154d-411d-bdce-9dbd91e56851": "check_22",
        "80f93444-b240-4ebb-a4c6-5c40b76c04ea": "check_11",
        "c48e57d3-d642-4e0b-90db-37f807b41b91": "check_21",
        "7307579a-3abb-46ad-9ce5-2a915634d5c8": "check_34",
        "de4421f1-4e35-43b4-9783-737dd4e4a47e": "check_47",
        "91dacd0e-d189-4a9c-8272-5999a3cc32d9": "check_10",
        "69bbc5e3-0818-4150-89cc-1e989b48f23b": "check_79",
        "d45330fd-f58d-45fb-a682-6481477a0f84": "check_80",
        "afa36afb-39fe-4d94-b9b6-afb236f7a03d": "check_81",
        "a77f4d07-c6e0-4a48-8b35-0eeb51576f4f": "check_82",
        "73e251f0-363d-4e53-86e2-0a93592437eb": "check_82",
        "13a49a2e-488e-4309-a7c0-d6b05577a5fb": "check_82",
        "cbd2db69-0b21-4c14-8a40-7710a50571a9": "check_82",
        "ec18a0d3-0069-4a58-a7fb-fbfe0b4bbbe0": "check_82",
        "6a68bebe-c021-492e-8ddb-55b0567fb768": "check_82",
        "510d5810-9a30-443a-817d-5c1fa527b110": "check_83",
        "da9f3aa8-fbfb-472f-b5a1-576127944218": "check_82",
        "768aab52-2504-4a2f-a3e3-329d5a679848": "check_82",
        "35c0a471-f7c8-4993-aa2c-503a3c712a66": "check_82",
        "e0099af2-fe17-411f-9991-0de28fe15f3c": "check_82",
        "14abda69-8e91-4acb-9931-76e2bee90284": "check_82",
        "2f491173-6375-4a84-b28e-a4e2b9a58a69": "check_82"
    }

    @classmethod
    def get_value(cls, key) -> Callable:
        """ Get the function to be called for each check.

        Args:
            key (str): The check number.
        """
        return cls._LOOKUP.get(key)

    @classmethod
    def print_value(cls, key) -> None:
        """ Print the function to be called for each check."""
        print(cls._LOOKUP.get(key))


class KubelinterClass:
    """This class is used to lookup the function to be called for each check.
    """

    _LOOKUP = {
        "latest-tag": "check_0",
        "unset-memory-requirements": "check_1",
        "unset-cpu-requirements": "check_4",
        "no-readiness-probe": "check_8",
        "host-pid": "check_10",
        "host-ipc": "check_11",
        "host-network": "check_12",
        "docker-sock": "check_15",
        "privileged-container": "check_21",
        "privilege-escalation-container": "check_22",
        "drop-net-raw-capability": "check_23",
        "no-read-only-root-fs": "check_27",
        "run-as-non-root": "check_28",
        "env-var-secret": "check_33",
        "deprecated-service-account-field": "check_37",
        "wildcard-in-rules": "check_39",
        "unsafe-sysctls": "check_41",
        "sensitive-host-mounts": "check_47",
        "dangling-service": "check_57",
        "non-existent-service-account": "check_58",
        "pdb-max-unavailable": "check_67",
        "ssh-port": "check_68",
        "no-extensions-v1beta": "check_51",
        "pdb-min-available": "check_71",
    }

    @classmethod
    def get_value(cls, key) -> Callable:
        """ Get the function to be called for each check.

        Args:
            key (str): The check number.
        """
        return cls._LOOKUP.get(key)

    @classmethod
    def print_value(cls, key) -> None:
        """ Print the function to be called for each check."""
        print(cls._LOOKUP.get(key))


class KubeauditClass:
    """This class is used to lookup the function to be called for each check.
    """

    _LOOKUP = {
        "NamespaceHostPIDTrue": "check_10",
        "AppArmorAnnotationMissing": "check_32", 
        "AppArmorInvalidAnnotation": "check_32",
        "CapabilityOrSecurityContextMissing": "check_34", 
        "LimitsCPUNotSet": "check_5", 
        "LimitsMemoryNotSet": "check_2", 
        "LimitsNotSet": "check_1",
        "AllowPrivilegeEscalationNil": "check_22", 
        "PrivilegedNil": "check_21", 
        "ReadOnlyRootFilesystemNil": "check_27", 
        "ReadOnlyRootFilesystemFalse": "check_27",
        "SeccompProfileMissing": "check_31",
        "AutomountServiceAccountTokenTrueAndDefaultSA": "check_35",
        "ImageTagMissing": "check_0",
        "RunAsNonRootPSCNilCSCNil": "check_28",
        "CapabilityAdded": "check_34",
        "CapabilityShouldDropAll": "check_34",
        "NamespaceHosthostIPCTrue": "check_11",
        "NamespaceHostNetworkTrue": "check_12",
        "AllowPrivilegeEscalationTrue": "check_22",
        "SensitivePathsMounted": "check_47",
        "RunAsUserPSCRoot": "check_13",
        "RunAsUserCSCRoot": "check_13",
        "PrivilegedTrue": "check_21",
        "MissingDefaultDenyIngressAndEgressNetworkPolicy": "check_70",
    }

    @classmethod
    def get_value(cls, key) -> Callable:
        """ Get the function to be called for each check.

        Args:
            key (str): The check number.
        """
        return cls._LOOKUP.get(key)

    @classmethod
    def print_value(cls, key) -> None:
        """ Print the function to be called for each check."""
        print(cls._LOOKUP.get(key))


class KubescapeClass:
    """This class is used to lookup the function to be called for each check.
    """

    _LOOKUP = {
        "C-0002": "check_54",
        "C-0007": "check_54",
        "C-0075": "check_25",
        "C-0004": "check_1",
        "C-0009": "check_4",
        "C-0012": "check_69",
        "C-0050": "check_4",
        "C-0056": "check_7",
        "C-0018": "check_8",
        "C-0038": "check_10",
        "C-0041": "check_12",
        "C-0270": "check_5",
        "C-0074": "check_15",
        "C-0057": "check_21",
        "C-0016": "check_22",
        "C-0260": "check_40",
        "C-0086": "check_22",
        "C-0046": "check_23",
        "C-0061": "check_26",
        "C-0017": "check_27",
        "C-0013": "check_22",
        "C-0044": "check_29",
        "C-0045": "check_29",
        "C-0055": "check_30",
        "C-0034": "check_35",
        "C-0014": "check_38",
        "C-0076": "check_43",
        "C-0077": "check_43",
        "C-0048": "check_47",
        "C-0030": "check_40",
        "C-0053": "check_35",
        "C-0015": "check_54",
        "C-0073": "check_64", 
        "C-0031": "check_54", 
        "C-0065": "check_54",
        "C-0063": "check_54",
        "C-0042": "check_68",
        "C-0271": "check_2",
    }

    @classmethod
    def get_value(cls, key) -> Callable:
        """ Get the function to be called for each check.

        Args:
            key (str): The check number.
        """
        return cls._LOOKUP.get(key)

    @classmethod
    def print_value(cls, key) -> None:
        """ Print the function to be called for each check."""
        print(cls._LOOKUP.get(key))


class TerrascanClass:
    """This class is used to lookup the function to be called for each check.
    """

    _LOOKUP = {
        "AC_K8S_0099": "check_1", 
        "AC_K8S_0100": "check_2", 
        "AC_K8S_0097": "check_4", 
        "AC_K8S_0098": "check_5", 
        "AC_K8S_0069": "check_9", 
        "AC_K8S_0085": "check_22", 
        "AC_K8S_0086": "check_26", 
        "AC_K8S_0078": "check_27", 
        "AC_K8S_0080": "check_31", 
        "AC_K8S_0073": "check_32", 
        "AC_K8S_0051": "check_33", 
        "AC_K8S_0045": "check_35",
        "AC_K8S_0087": "check_28",
        "AC_K8S_0070": "check_7",
        "AC_K8S_0064": "check_30",
        "AC_K8S_0072": "check_8",
        "AC_K8S_0079": "check_13",
        "AC_K8S_0084": "check_12",
        "AC_K8S_0111": "check_56",
        "AC_K8S_0068": "check_0",
        "AC_K8S_0076": "check_47",
        "AC_K8S_0081": "check_55",
        "AC_K8S_0082": "check_10",
        "AC_K8S_0088": "check_15",
    }

    @classmethod
    def get_value(cls, key) -> Callable:
        """ Get the function to be called for each check.

        Args:
            key (str): The check number.
        """
        return cls._LOOKUP.get(key)

    @classmethod
    def print_value(cls, key) -> None:
        """ Print the function to be called for each check."""
        print(cls._LOOKUP.get(key))
