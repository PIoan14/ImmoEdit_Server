import base64
import os
from google import genai
from IPython.display import Image, display
from google import genai
from PIL import Image
from io import BytesIO


def chat_with_banana(input_image, prompt, output_image):

    image_input = Image.open(input_image)

    #API KEY IN ENV

    .env
    response = client.models.generate_content(
        model="gemini-2.5-flash-image",
        contents=[image_input, prompt],
    )

    for part in response.candidates[0].content.parts:
        if part.text is not None:
            print(part.text)
        elif part.inline_data is not None:
            image = Image.open(BytesIO(part.inline_data.data))
            image.save(output_image)


#chat_with_banana("code.png", "Edit this picture so that it would look like VS code night mode" ,  "other_code.png")