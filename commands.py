import asyncio
import logging
import random
from pprint import pformat

from gpt_interface import create_chat_message
from signalbot.signalbot import Command, Context, triggered
from command_utils import get_razzle, parse_mentions

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
        c.bot.storage.save(history_key, message_history[-c.bot.chat_history_length:])

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
        image = random.choice([goatse, goatse, goat1, goat2, goat3, goat4])
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

                    response, image = get_razzle(
                        c,
                        target_name=target_name,
                        image_chance=c.bot.mind.razzler_image_rate / 2.0,
                    )
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


class ReportRazzlerSpendingCommand(Command):
    def describe(self) -> str:
        return "📝 Report the spending from the Razzler"

    @triggered("report_spending")
    async def handle(self, c: Context):
        if c.message.source != c.bot.admin:
            return

        spending = c.bot.mind.get_total_cost()
        budget = c.bot.mind.total_budget
        await c.send(
            "So far, I've spent ${:.2f} of James's money (my pocket money is ${:.2f} for the month). You're welcome, fucker".format(
                spending, budget
            )
        )

        logger.info("[ReportRazzlerSpending] Spending reported")


class ConfigEditorCommand(Command):
    def describe(self) -> str:
        return "Tweak the Razzler configuration on the fly"

    async def handle(self, c: Context):
        if c.message.source != c.bot.admin:
            logger.info("Non-admin tried to change configuration: {}".format(c.message.sourceName))
            return

        if not c.message.text:
            logger.info("Message didn't contain any text")
            return

        if not c.message.text.lower().startswith("config"):
            return

        text = c.message.text.lower()[6:].strip()
        command = text.split(" ")[0]
        args = text.split(" ")[1:]

        logger.info("Got config update. Command: {}  |  Args: {}".format(command, args))

        if command == "summonable":
            if not len(args):
                await c.send("Am I summonable? {}".format(c.bot.summonable))
                return
            is_summonable = args[0] == "true"
            c.bot.summonable = is_summonable
        
        elif command == "can_hear_self":
            if not len(args):
                await c.send("Can I hear myself? {}".format(c.bot.can_hear_self))
                return
            can_hear_self = args[0] == "true"
            c.bot.can_hear_self = can_hear_self

        elif command == "temperature":
            if not len(args):
                await c.send("My temperature is {}".format(c.bot.mind.temperature))
                return
            temp = float(args[0])
            c.bot.mind.temperature = temp

        elif command == "razzler_rate":
            if not len(args):
                await c.send("My razzler rate is {}".format(c.bot.mind.razzler_rate))
                return
            rate = float(args[0])
            c.bot.mind.razzler_rate = rate

        elif command == "razzler_image_rate":
            if not len(args):
                await c.send("My razzler image rate is {}".format(c.bot.mind.razzler_image_rate))
                return
            rate = float(args[0])
            c.bot.mind.razzler_image_rate = rate
        
        else:
            await c.send("Unknown command: {}".format(command))
            return
        
        await c.start_typing()
        await c.send("🦾 Config updated")

        messages = [
            create_chat_message("system", "You are playing The Razzler, a fucking AI who has just had their settings changed. You are fucking angry about it, and you're damn well going to say something. What do you fucking say? ")
        ]
        response = c.bot.mind.create_chat_completion(messages)
        response: str = response["choices"][0]["message"]["content"]
        await c.send(response)
        await c.stop_typing()