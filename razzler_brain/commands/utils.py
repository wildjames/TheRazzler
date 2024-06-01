import base64
from utils.storage import load_file


def image_to_base64(file_path):
    # Read the image file in binary mode
    image_data = load_file(file_path, "rb")

    # Encode the bytes to base64
    encoded_data = base64.b64encode(image_data)

    # Decode bytes to a string (optional, if you need the result as a string)
    encoded_string = encoded_data.decode("utf-8")

    return encoded_string

