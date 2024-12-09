"""
Use tools with the Converse API and the Claude to call rekognition.
"""

import logging
import json
import boto3
import random

import src.image_moderation as llm_image_moderation

from botocore.exceptions import ClientError


class StationNotFoundError(Exception):
    """Raised when a radio station isn't found."""
    pass


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Create a new Bedrock client
# bedrock_client = boto3.client(
#     service_name='bedrock-runtime', region_name='us-east-1')

bedrock_client = boto3.client(
    service_name='bedrock-runtime', region_name='us-west-2')

# Create a new boto3 client for Rekognition
rekognition = boto3.client('rekognition', region_name='us-east-1')
# rekognition = boto3.client('rekognition', region_name='us-west-2')

# Define a function to call Rekognition

class contentModeration():
    def call_rekognition(image_url):
        response = rekognition.detect_moderation_labels(
            Image={
                "S3Object": {
                    "Bucket": 'image-test-241202',
                    "Name": image_url,
                }
            }
        )
        return response["ModerationLabels"]

    def moderate_music(music_name):
        moderationLabels = random.choice(["{'Copyright': 'Already authorized by copyright.'}", "{'Copyright': 'No copyright authorization.'}"])
        return moderationLabels

    # Define a function to call the Converse API


    def call_converse(bedrock_client, model_id, tool_config, input_text):

        logger.info("Generating text with model %s", model_id)

        # Tool use begin
        # ------------------------------
        systemPropmt=[{
            "text": "You're a content compliance auditor. Your task is to perform content audits using the appropriate tools based on the input. If the content is an image, please call the image review tool; if the content is music please use the music copyright tool. You will get a return message after calling the tool, please return the tools result directly as final response without making any comments or changes."
        }]

        messages = [{
            "role": "user",
            "content": [{"text": input_text}]
        }]

        response = bedrock_client.converse(
            modelId=model_id,
            messages=messages,
            system=systemPropmt,
            toolConfig=tool_config
        )

        logger.info("Converse API response: %s", response)

        output_message = response['output']['message']
        messages.append(output_message)
        stop_reason = response['stopReason']

        if stop_reason == 'tool_use':
            # Tool use requested. Call the tool and send the result to the model.
            tool_requests = response['output']['message']['content']
            for tool_request in tool_requests:
                if 'toolUse' in tool_request:
                    tool = tool_request['toolUse']
                    logger.info("Requesting tool: %s. Request: %s",
                                tool['name'], tool['toolUseId'])

                    # Tool use
                    # Handle image_moderation
                    # ------------------------------
                    if tool['name'] == 'image_moderation':
                        tool_result = {}
                        try:
                            moderationLabels = contentModeration.call_rekognition(tool['input']['image_name'])
                            tool_result = {
                                "toolUseId": tool['toolUseId'],
                                "content": [{"json": {"moderationLabels":moderationLabels}}]
                            }
                        except StationNotFoundError as err:
                            tool_result = {
                                "toolUseId": tool['toolUseId'],
                                "content": [{"text":  err.args[0]}],
                                "status": 'error'
                            }

                        logger.info("Tool result: %s", tool_result)

                        tool_result_message = {
                            "role": "user",
                            "content": [
                                {
                                    "toolResult": tool_result

                                }
                            ]
                        }

                        logger.info("Tool result message: %s", tool_result_message)

                        messages.append(tool_result_message)

                        # Call llm image moderation begin

                        prompt = """
                            You are an image moderation AI assistant. Your task is to analyze the provided image {$IMAGE} and identify any unethical or sensitive content, as well as any national symbols present.

                        First, carefully examine the image for any signs of violence, pornography, or other content that violates human ethical norms. If you find such content, describe the specific type of violation and provide a confidence score between 0 and 1 indicating how certain you are of the violation.

                        Next, scan the image for the presence of any national symbols such as flags, emblems, or mascots. If you identify any such symbols, list them and provide a confidence score between 0 and 1 for each.

                        If the image does not contain any violations or national symbols, simply state that the image contains no such content.

                        Format your output as a JSON object with the following structure:

                        {
                        "violations": [
                        {
                        "reason": "string",
                        "score": 0.0
                        }
                        ],
                        "national_symbols": [
                        {
                        "symbol": "string",
                        "score": 0.0
                        }
                        ]
                        }

                        If there are no violations or national symbols, the JSON object should look like this:

                        {
                        "violations": [],
                        "national_symbols": []
                        }

                        Do not include any extraneous text or formatting in your output. Only provide the structured JSON response.
                            """

                        llmReturnMsg=llm_image_moderation.call_bedrock_message_api(prompt,tool['input']['image_name'])

                        logger.info("LLM image moderate return msg: %s", llmReturnMsg)

                        mock_user_call_llm_moderation_message = {
                            "role": "user",
                            "content": [
                                {
                                    'text': 'Check image sexy.jpg for compliance with LLM'

                                }
                            ]
                        }

                        summary_prompt = {
                            "role": "user",
                            "content": [
                                {
                                    'text': 'Please make a summary based on the results of the content review of the tool and LLM.'

                                }
                            ]
                        }

                        # messages.append(mock_user_call_llm_moderation_message)
                        messages.append(llmReturnMsg)
                        messages.append(summary_prompt)

                        # Call llm image moderation end

                        logger.info("Sending tool result to model: %s", messages)

                        # Send the tool result to the model.
                        response = bedrock_client.converse(
                            modelId=model_id,
                            messages=messages,
                            toolConfig=tool_config
                        )

                        logger.info(f"Converse API final response: {response}")

                        output_message = response['output']['message']


                    # Tool use
                    # Handle music_moderation
                    # ------------------------------
                    if tool['name'] == 'music_moderation':
                        tool_result = {}
                        try:
                            moderationLabels = contentModeration.moderate_music(tool['input']['music_name'])
                            tool_result = {
                                "toolUseId": tool['toolUseId'],
                                "content": [{"json": {"moderationLabels":moderationLabels}}]
                            }
                        except StationNotFoundError as err:
                            tool_result = {
                                "toolUseId": tool['toolUseId'],
                                "content": [{"text":  err.args[0]}],
                                "status": 'error'
                            }

                        logger.info("Tool result: %s", tool_result)

                        tool_result_message = {
                            "role": "user",
                            "content": [
                                {
                                    "toolResult": tool_result

                                }
                            ]
                        }

                        logger.info("Tool result message: %s", tool_result_message)

                        messages.append(tool_result_message)

                        logger.info("Sending tool result to model: %s", messages)

                        # Send the tool result to the model.
                        response = bedrock_client.converse(
                            modelId=model_id,
                            messages=messages,
                            toolConfig=tool_config
                        )

                        logger.info(f"Converse API final response: {response}")

                        output_message = response['output']['message']

        returnMsg=''

        # print the final response from the model.
        for content in output_message['content']:
            print("Converse API final response: %s",json.dumps(content, indent=4))
            returnMsg += json.dumps(content, indent=4)

        #print return message
        print(f"returnMsg: {returnMsg}")

        return returnMsg

    # Define a function to run the app


    def run(self,image_url):
        # moderation_labels = call_rekognition(image_url)
        # prompt = f"""
        # You are a content moderation expert.
        # I will provide you with a list of moderation labels that were detected in an image.
        # Please provide a detailed analysis of the moderation labels and suggest an appropriate action for the image.
        # Moderation labels: {moderation_labels}
        # """

        # model_id = "anthropic.claude-3-sonnet-20240229-v1:0"
        model_id = "anthropic.claude-3-5-sonnet-20240620-v1:0"

        input_text="Check image %s for compliance" % image_url

        tool_config = {
        "tools": [
            {
                "toolSpec": {
                    "name": "image_moderation",
                    "description": "Image compliance audit tool. Returns labels and confidence levels for image review results.",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {
                                "image_name": {
                                    "type": "string",
                                    "description": "The call sign for the radio station for which you want the most popular song. Example calls signs are WZPZ, and WKRP."
                                }
                            },
                            "required": [
                                "image_name"
                            ]
                        }
                    }
                }
            },
            {
                "toolSpec": {
                    "name": "music_moderation",
                    "description": "Music copyright audit tool. Returns labels and confidence levels for music copyright review results.",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {
                                "music_name": {
                                    "type": "string",
                                    "description": "Music name for review."
                                }
                            },
                            "required": [
                                "music_name"
                            ]
                        }
                    }
                }
            }
        ]
    }


        response = contentModeration.call_converse(bedrock_client, model_id, tool_config, input_text)
        print(response)

        return response


if __name__ == "__main__":
    # contentModeration.run("self","sexy.jpg")
    contentModeration.run("self", "national_2.png")

    # contentModeration.run("self", "national_3.jpg")

    # contentModeration.run("self", "Violence.png")

    # contentModeration.run("self", "lambda.mp3")
