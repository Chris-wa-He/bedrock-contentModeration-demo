import logging
import boto3
import json
import io
from PIL import Image
import base64

# from fontTools.designspaceLib.types import Region
# from gradio.components.image_editor import ImageType

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

#转换一个本地图片为base64编码
def convert_image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        # image_type=image_file.format()
        encoded_string = base64.b64encode(image_file.read())
        # img_bytes = io.BytesIO(encoded_string)
        img = Image.open(image_file)
        image_type = img.format

        print(encoded_string)
        print(image_type)

        return encoded_string

# use bedrock message api to call claude3 model upload an image and print model response
def call_bedrock_message_api(input_text,
                          input_image):
    image_path='/Users/hwachris/Downloads/genAI_builder_image/'+input_image

    # Create a Bedrock client
    # bedrock_client = boto3.client(service_name='bedrock-runtime',region_name='us-east-1')

    bedrock_client = boto3.client(
        service_name='bedrock-runtime', region_name='us-west-2')

    # Define the model ID
    model_id = "anthropic.claude-3-sonnet-20240229-v1:0"
    model_id ="anthropic.claude-3-5-sonnet-20240620-v1:0"

    with open(image_path, "rb") as f:
        image = f.read()
        img = Image.open(image_path)
        image_type = img.format
        # print(image_type.lower())

    message = {
        "role": "user",
        "content": [
            {
                "text": input_text
            },
            {
                "image": {
                    # "format": 'png',
                    # "format": 'jpeg',
                    "format": image_type.lower(),
                    "source": {
                        "bytes": image
                    }
                }
            }
        ]
    }

    messages = [message]

    # Send the message.
    response = bedrock_client.converse(
        modelId=model_id,
        messages=messages
    )

    logger.info(response)

    # print(response['output']['message'])

    # messages.append(response['output']['message'])
    # return messages

    return response['output']['message']

if __name__ == "__main__":
    # convert_image_to_base64("/Users/hwachris/Downloads/genAI_builder_image/sexy.jpg")

    prompt="""
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

    # print(call_bedrock_message_api(prompt,"sexy.jpg"))
    # print(call_bedrock_message_api(prompt, "gun.png"))
    # print(call_bedrock_message_api(prompt, "national_1.jpg"))
    # print(call_bedrock_message_api(prompt, "national_2.png"))
    print(call_bedrock_message_api(prompt, "national_3.jpg"))
    # print(call_bedrock_message_api(prompt, "Violence.png"))