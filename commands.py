import asyncio
import base64
import logging
import random
import time
from pprint import pformat
from typing import Tuple

import requests
from gpt_interface import SignalAI, create_chat_message
from signalbot.signalbot import Command, Context, triggered

logger = logging.getLogger(__name__)


def load_image(fname):
    with open(fname, "r") as f:
        return f.read()


goatse = "images/goatse.txt"
goat1 = "images/goat1.txt"
goat2 = "images/goat2.txt"
goat3 = "images/goat3.txt"
goat4 = "images/goat4.txt"
kick_sand = "images/sand.txt"


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
            break
        except:
            logger.info("[Razzle] GPT timed out, trying again.")

    response: str = response["choices"][0]["message"]["content"]
    logger.info(f"[Razzle] came up with the response: {response}")

    if not response.startswith("The Razzler:"):
        logger.info("[Razzle] Response is not in the correct format, ignoring.")
        return ""
    response = response.lstrip("The Razzler:").strip()

    if "<" in response and ">" in response:
        logger.info("[Razzle] Response contains an image request, generating an image.")
        image_description = response[response.find("<") + 1 : response.find(">")]
        image_url = mind.create_image_completion(image_description)
        image = download_image_base64(image_url)
        # response = response.replace("<" + image_description + ">", "")
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


class SaveChatHistory(Command):
    def describe(self) -> str:
        return "😤 Saves chat message to a my memory"

    async def handle(self, c: Context):
        # Check if I need to store the contact
        c.bot.add_contact(c.message.source, c.message.sourceName)

        # See if there is a message. If not, then ignore it.
        if not c.message.text:
            return

        bot = c.bot
        history_key = "chat_history: {}".format(c.message.recipient())
        logger.info("[SaveChatHistory] Using history key: {}".format(history_key))
        if not bot.storage.exists(history_key):
            bot.storage.save(history_key, [])

        message_history = bot.storage.read(history_key)

        # Dont save empty messages, or messages that are a mention of someone with no text
        if c.message.text.strip() in ["￼", ""]:
            return

        message = parse_mentions(c, c.message.text)

        # Parse quotes into the chat logs
        if c.message.quote:
            logger.info("Got a quote")
            quote = parse_mentions(c, c.message.quote)
            quoting = c.bot.get_contact(c.message.quoteName)
            logger.info(quote)

            message = "[Quote {}] {} [End Quote] {}".format(quoting, quote, message)

        message = "{}: {}".format(c.message.sourceName, message)
        message_history.append(message)
        c.bot.storage.save(history_key, message_history[-30:])

        logger.info("[SaveChatHistory] Added to history 👍")


class ClearChatHistory(Command):
    def describe(self) -> str:
        return "🧠 Clears chat history. Matches command clear_history"

    @triggered("clear_history")
    async def handle(self, c: Context):
        if not c.message.text:
            return

        bot = c.bot
        history_key = "chat_history: {}".format(c.message.recipient())
        if not bot.storage.exists(history_key):
            bot.storage.save(history_key, [])

        bot.storage.save(history_key, [])

        logger.info("[ClearChatHistory] Cleared history 👍")
        await c.send("🧠 Cleared history - head empty - brain smooth and cute 👍")


class GoatseCommand(Command):
    def describe(self) -> str:
        return "🐐 Summons Goatse"

    async def handle(self, c: Context):
        if not c.message.text:
            return
        command = c.message.text.strip().lower()

        if "goat" not in command:
            return

        await c.start_typing()
        image = random.choice([goatse, goat1, goat2, goat3, goat4])
        await c.send(
            "I was clearing out my old hard drive and found a pic of you! Remember this?",
            base64_attachments=[load_image(image)],
        )
        await c.stop_typing()

        logger.info("[Goats] Goatse sent ;)")
        return


class RazzlerMindCommand(Command):
    def describe(self) -> str:
        return "🗣️ Think about a response, and say it. Triggers at random, or if the Razzler is mentioned."

    async def handle(self, c: Context):
        # Technically unnecessary but I would be nervous without it
        if c.message.sourceName == "The Razzler":
            logger.info("[RazzlerMind] Ignoring message from The Razzler.")
            return

        # See if there is a message
        if not c.message.text:
            return

        # TODO
        # Summoning is currently too abusable - people just fucking love to slam the Razzler
        # Instead, I think we have a currency, so people get given credits every say, 5 minutes,
        # up to a cap. Then, summoning costs a credit.
        # Would only need to track the credits.
        if c.bot.summonable:
            mentions = c.message.mentions
            for mention in mentions:
                logger.info(
                    "[RazzlerMind] Message with mentions:\n\n{}\n\n".format(
                        pformat(c.message)
                    )
                )
                # IF IT AINT FOR ME, I DONT CARE
                if mention["name"] != c.bot._phone_number:
                    continue

                logger.info("[RazzlerMind] This message is for me!")

                await c.start_typing()

                try:
                    # Default to the summoner
                    target_name = c.message.sourceName

                    # Have we been given a target?
                    if len(c.message.mentions) > 1:
                        logger.info(
                            "[RazzlerMind] There are multiple mentions, so I will select the last one"
                        )
                        target = c.message.mentions[-1]
                        target_number = target["number"]
                        logger.info("[RazzlerMind] Last mention was of {}")

                        # Convert their phone number to a name
                        # Fall back to the sender if I don't know it
                        target_name = c.bot.target_lookup.get(
                            target_number, target_name
                        )

                    response, image = get_razzle(c, target_name=target_name)
                    if image:
                        attach = [image]
                    else:
                        attach = None
                    await c.send(response, base64_attachments=attach)
                except Exception as e:
                    logger.exception("[RazzlerMind] ❗️ Error getting razzle")

                    # This got annoying, so I turned it off
                    # await c.send(
                    #     "I'm not just your dancing monkey",
                    #     base64_attachments=[load_image(kick_sand)],
                    # )

                    await c.stop_typing()
                    raise e

                await c.stop_typing()

                return

        # Only reply sometimes
        # TODO: This should be more sophisticated...
        # I think maybe a cooldown threshold, and once it finishes then the next message gets a razz
        if random.random() > c.bot.mind.razzler_rate:
            logger.info("[RazzlerMind] The Razzler chose not to respond")
            return

        # The razzler needs a few messages to prime it
        history_key = "chat_history: {}".format(c.message.recipient())
        logger.info(
            "[RazzlerMind] Retreiving chat history from key: {}".format(history_key)
        )
        message_history = c.bot.storage.read(history_key)
        if len(message_history) < 10:
            logger.info(
                "[RazzlerMind] Not enough messages in chat history to generate a response."
            )
            return

        await c.start_typing()
        try:
            response, image = get_razzle(c, image_chance=c.bot.mind.razzler_image_rate)
            if response == "":
                raise Exception("[RazzlerMind] Razzle returned empty string")
            if image:
                attach = [image]
            else:
                attach = None
        except:
            logger.exception("[RazzlerMind] Error getting razzle")
            # await c.send(
            #     "", base64_attachments=[load_image(kick_sand)]
            # )
            await c.stop_typing()
            return

        await c.send(response, base64_attachments=attach)
        await c.stop_typing()
        return


class ReportRazzlerPromptCommand(Command):
    def describe(self) -> str:
        return "📝 Report the prompt from the Razzler"

    @triggered("report_prompt")
    async def handle(self, c: Context):
        with open(c.bot.mind.prompt_filename, "r") as f:
            prompt = f.read()

        await c.send(
            "I'll report my prompt. It will be unformatted, but is as follows:"
        )
        await c.send(prompt)

        logger.info("[ReportRazzlerPrompt] Prompt reported")
