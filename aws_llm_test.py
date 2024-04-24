from asyncio.log import logger
import boto3
import json
from botocore.exceptions import ClientError


def invoke_claude_3_with_text(prompt):
    """
    Invokes Anthropic Claude 3 Sonnet to run an inference using the input
    provided in the request body.

    :param prompt: The prompt that you want Claude 3 to complete.
    :return: Inference response from the model.
    """

    # Initialize the Amazon Bedrock runtime client
    client = boto3.client(
        service_name="bedrock-runtime", region_name="us-west-2"
    )

    # Invoke Claude 3 with the text prompt
    model_id = "anthropic.claude-3-sonnet-20240229-v1:0"

    try:
        response = client.invoke_model(
            modelId=model_id,
            body=json.dumps(
                {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 1024,
                    "messages": [
                        {
                            "role": "user",
                            "content": [{"type": "text", "text": prompt}],
                        }
                    ],
                }
            ),
        )

        # Process and print the response
        result = json.loads(response.get("body").read())
        input_tokens = result["usage"]["input_tokens"]
        output_tokens = result["usage"]["output_tokens"]
        output_list = result.get("content", [])

        # print("Invocation details:")
        # print(f"- The input length is {input_tokens} tokens.")
        # print(f"- The output length is {output_tokens} tokens.")

        print(f"Answer: ")
        for output in output_list:
            print(output["text"])

        return result

    except ClientError as err:
        logger.error(
            "Couldn't invoke Claude 3 Sonnet. Here's why: %s: %s",
            err.response["Error"]["Code"],
            err.response["Error"]["Message"],
        )
        raise


prompt = """
Refactor the following ServiceAccountYAML resource because the default namespace should not be used.

apiVersion: v1
kind: ServiceAccount
metadata:
 name: release-name-mysql
 namespace: default
 labels:
  app.kubernetes.io/name: mysql
  helm.sh/chart: mysql-9.7.1
  app.kubernetes.io/instance: release-name
  app.kubernetes.io/managed-by: Helm
 annotations: null
automountServiceAccountToken: true
secrets:
- name: release-name-mysql
"""

print("Claude 3 Query: " + prompt)

invoke_claude_3_with_text(prompt)

