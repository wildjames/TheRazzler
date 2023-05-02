import asyncio
import base64
import logging
import random
import time
from pprint import pformat

import requests
from gpt_interface import SignalAI, create_chat_message
from signalbot.signalbot import Context

logger = logging.getLogger(__name__)


def interleave(list1, list2):
    newlist = []
    a1 = len(list1)
    a2 = len(list2)

    for i in range(max(a1, a2)):
        if i < a1:
            newlist.append(list1[i])
        if i < a2:
            newlist.append(list2[i])

    return newlist


def download_image_base64(url):
    try:
        # Send a GET request to the URL
        response = requests.get(url)

        # Raise an exception if the response contains an HTTP error status code
        response.raise_for_status()

        # Check if the response content is an image
        if "image" not in response.headers["Content-Type"]:
            raise ValueError("The URL does not contain an image.")

        # Encode the image content in base64 format
        image_base64 = base64.b64encode(response.content)

        return image_base64.decode("utf-8")

    except requests.exceptions.RequestException as e:
        print(f"An error occurred while downloading the image: {e}")
        return None
    except ValueError as e:
        print(e)
        return None


def get_razzle(c: Context, target_name: str = None, image_chance: float = 0.0):
    """Return a razzle from the AI.

    The razz will be addressed to the target_name

    Returns a string, containing the message body, and an optional image encoded in base64, or None if no image was made.
    """
    # Get the chat history from storage
    history_key = "chat_history: {}".format(c.message.recipient())
    if c.bot.storage.exists(history_key):
        message_history = c.bot.storage.read(history_key)
    else:
        message_history = []

    # Retrieve the AI
    mind: SignalAI = c.bot.mind

    # Check that we're in budget
    if mind.total_budget > 0 and mind.total_cost > mind.total_budget:
        logger.info("[Razzle] Exceeded budget, sending a message about that.")
        return "The Razzler Razzled too hard and ran out of money. Later nerds (swag) 😎"

    # Get the target
    logger.info("[Razzle] Getting the target for the Razzler.")

    # If I wasn't given a target, choose one at random from the message history
    # Since each sender is added to the list, this weights for more active members.
    # TODO: Make this more sophisticated. Can the AI choose their own target without getting stuck in a loop?
    if target_name is None:
        targets = []
        for message in message_history:
            target = message.split(":")[0]
            if "Razzler" not in target:
                targets.append(target)
        if targets:
            target_name = random.choice(targets)

    if target_name is None:
        target_name = "The Razzler"

    with open(c.bot.mind.prompt_filename, "r") as f:
        prompt = f.read()

    if random.random() < image_chance:
        image_subprompt = "You should also generate a single image for your message, by describing what it should be of. "
        image_subprompt += "An image description should be a single sentence, and must be enclosed by angular brackets, i.e. <a piece of shit>. "
    else:
        image_subprompt = ""

    prompt = prompt.format(target_name=target_name, image_subprompt=image_subprompt)

    # Filter out messages from the razzler to prevent looping?
    # combined_message = "Message history: \n" + "\n".join(
    #     [m for m in message_history if not m.startswith("The Razzler")]
    # )
    combined_message = "Message history: \n" + "\n".join(message_history)

    # There is a 4097 token limit. This doesn't actually work since tokens can be (and usually are) a few characters, but it's a start.
    combined_message = combined_message[-4000 - c.bot.mind.max_tokens :]

    GPT_messages = [
        create_chat_message("user", combined_message),
        create_chat_message("system", prompt),
    ]

    logger.info("[Razzle] I will send the following messages to GPT:")
    for message in GPT_messages:
        logger.info(f"[Razzle] - {pformat(message)}")

    t0 = time.time()
    while time.time() - t0 < 10:
        try:
            response = mind.create_chat_completion(GPT_messages)
            response: str = response["choices"][0]["message"]["content"]
            break
        except:
            logger.info("[Razzle] GPT timed out, trying again.")

    logger.info(f"[Razzle] came up with the response: {response}")

    if response.startswith("The Razzler:"):
        response = response[13:]

    response = response.strip()

    if "<" in response and ">" in response:
        logger.info("[Razzle] Response contains an image request, generating an image.")
        image_description = response[response.find("<") + 1 : response.find(">")]
        try:
            image_url = mind.create_image_completion(image_description)
            image = download_image_base64(image_url)
            # response = response.replace("<" + image_description + ">", "")
        except:
            logger.info("[Razzle] Image generation failed, ignoring.")
            image = None
    else:
        image = None

    # Save the response to the chat history
    with open("razzled.csv", "a") as f:
        f.write(response + "\n")

    # Since I dont actually receive my own message, I need to add it to the history manually
    bot = c.bot
    if bot.can_hear_self:
        history_key = "chat_history: {}".format(c.message.recipient())
        logger.info("[Razzle] Using history key: {}".format(history_key))
        if not bot.storage.exists(history_key):
            bot.storage.save(history_key, [])

        message_history = bot.storage.read(history_key)

        message = "{}: {}".format("The Razzler", response)
        message_history.append(message)
        c.bot.storage.save(history_key, message_history[-30:])

        logger.info("[Razzle] Added my own message to history 🗣️ {}".format(message))

    return response, image


def parse_mentions(c: Context, message_string: str) -> str:
    # Parse mentions into names
    if len(c.message.mentions):
        logger.info(
            "[ParseMentions] This message has some mention in it: {c.message.mentions}"
        )

        mentions = sorted(c.message.mentions, key=lambda m: m["start"])
        # The mentions are given as phone numbers
        numbers = [m["number"] for m in mentions]
        logger.info("[ParseMentions] Numbers: {}".format(numbers))

        # Convert the phone numbers to names, if I know them
        logger.info("[ParseMentions] My contacts list:")
        logger.info(pformat(c.bot.target_lookup))
        names = [c.bot.get_contact(num) for num in numbers]
        logger.info("[ParseMentions] Names: {}".format(names))

        # Split the message into a list of strings, and then interleave the names into it
        broken_message = message_string.split("￼")

        interleaved_list = interleave(broken_message, names)

        # Then reform the message
        message = "".join(interleaved_list)
        logger.info(
            "[ParseMentions] Parsed out the mentions into the message: {}".format(
                message
            )
        )
        return message

    logger.info("[ParseMentions] Got message: {}".format(message_string))
    return message_string