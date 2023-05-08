import asyncio
import logging
import os
import random
from pprint import pformat

from command_utils import (
    create_character_profile,
    get_razzle,
    get_reply,
    parse_mentions,
)
from gpt_interface import create_chat_message
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
            quote = parse_mentions(c, c.message.quoteName)
            quoting = c.bot.get_contact(c.message.quote)

            message = "[Quote {}] {} [End Quote] {}".format(quoting, quote, message)
            logger.info(
                "[SaveChatHistory] Quote detected. Message is now: {}".format(message)
            )

        message = "{}: {}".format(c.message.sourceName, message)
        message_history.append(message)
        c.bot.storage.save(history_key, message_history[-c.bot.chat_history_length :])

        if c.bot.mind.last_profiled >= c.bot.chat_history_length:
            logger.info("[SaveChatHistory] Profiling...")
            c.bot.mind.last_profiled = 0

            active_names = [
                name
                for name in c.bot.target_lookup.values()
                if name in "".join(message_history)
            ]

            # call create_character_profile on each name in active_names in parallel, using async
            tasks = [
                asyncio.create_task(create_character_profile(c, name))
                for name in active_names
            ]
            await asyncio.gather(*tasks)

            logger.info("[SaveChatHistory] Done profiling 👍")
        else:
            c.bot.mind.last_profiled += 1

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

        c.bot.mind.last_profiled = 0

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


class RazzlerProfileCommand(Command):
    def describe(self) -> str:
        return "Manually trigger character profiling"

    @triggered("create_profiles")
    async def handle(self, c: Context):
        # if c.message.source != c.bot.admin:
        #     logger.info(
        #         "[ManualProfiling] Non-admin tried to trigger character profiles: {}".format(
        #             c.message.sourceName
        #         )
        #     )
        #     return

        await c.start_typing()

        history_key = "chat_history: {}".format(c.message.recipient())
        logger.info("[ManualProfiling] Using history key: {}".format(history_key))
        if not c.bot.storage.exists(history_key):
            c.bot.storage.save(history_key, [])

        message_history = c.bot.storage.read(history_key)

        logger.info("[ManualProfiling] Profiling...")
        c.bot.mind.last_profiled = 0

        # TODO: Crude. Could be better
        active_names = [
            name
            for name in c.bot.target_lookup.values()
            if name in "".join(message_history)
        ]
        logger.info("[ManualProfiling] Creating profiles on: {}".format(active_names))
        # call create_character_profile on each name in active_names in parallel, using async
        tasks = [
            asyncio.create_task(create_character_profile(c, name))
            for name in active_names
        ]
        await asyncio.gather(*tasks)
        logger.info("[ManualProfiling] Done profiling 👍")

        await c.send("I have updated my profiles on everyone 🫦")
        await c.stop_typing()


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

        # Randomly change state
        if random.random() < 0.5:
            logger.info("[NaughtyNice] Toggling Naughtyness")
            if c.bot.mind.prompt_filename == "naughty.txt":
                c.bot.mind.prompt_filename = "nice.txt"
            elif c.bot.mind.prompt_filename == "nice.txt":
                c.bot.mind.prompt_filename = "naughty.txt"

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

                    message_text = parse_mentions(c, c.message.text)

                    # Have we been given a target?
                    if len(c.message.mentions) > 1:
                        logger.info(
                            "[RazzlerMind] There are multiple mentions, so I will select the last one"
                        )
                        target = c.message.mentions[-1]
                        target_number = target["number"]
                        # Fall back to the sender if I don't know it
                        target_name = c.bot.target_lookup.get(
                            target_number, target_name
                        )
                        logger.info(
                            "[RazzlerMind] Last mention was of {}".format(target)
                        )

                        response, image = get_razzle(
                            c,
                            target_name=target_name,
                            image_chance=c.bot.mind.razzler_image_rate,
                        )

                    elif message_text.replace("The Razzler", "").strip():
                        logger.info(
                            "[RazzlerMind] I've been asked a question: {}".format(
                                message_text
                            )
                        )
                        response, image = get_reply(
                            c, image_chance=c.bot.mind.razzler_image_rate
                        )

                    elif len(c.message.mentions) == 1:
                        logger.info(
                            "[RazzlerMind] There is one mention, so I will target the sender"
                        )

                        response, image = get_razzle(
                            c,
                            image_chance=c.bot.mind.razzler_image_rate,
                        )

                    else:
                        logger.warning(
                            "❌ This situation is odd - if we are able to reach this then I should implement a fix"
                        )
                        response = "James fucked up and you need to let him know. This is my error message!"
                        image = None

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
        if not c.message.text:
            logger.info("Message didn't contain any text")
            return

        if not c.message.text.lower().startswith("config"):
            return

        if c.message.source != c.bot.admin:
            logger.info(
                "Non-admin tried to change configuration: {}".format(
                    c.message.sourceName
                )
            )
            return

        text = c.message.text.lower()[6:].strip()
        command = text.split(" ")[0]
        args = text.split(" ")[1:]

        logger.info("Got config update. Command: {}  |  Args: {}".format(command, args))

        commands = [
            "summonable",
            "can_hear_self",
            "temperature",
            "razzler_rate",
            "razzler_image_rate",
            "prompt_filename",
            "model",
        ]

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

        elif command == "model":
            if not len(args):
                await c.send("My model is {}".format(c.bot.mind.model))
                return
            model = args[0]
            models = ["gpt-3.5-turbo", "gpt-4"]
            if model not in models:
                await c.send(
                    "Invalid model. Valid models are: {}".format(", ".join(models))
                )
                return
            c.bot.mind.model = model

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
                await c.send(
                    "My razzler image rate is {}".format(c.bot.mind.razzler_image_rate)
                )
                return
            rate = float(args[0])
            c.bot.mind.razzler_image_rate = rate

        elif command == "prompt_filename":
            if not len(args):
                await c.send(
                    "My prompt filename is {}".format(c.bot.mind.prompt_filename)
                )
                return
            filename = args[0]
            if not filename.endswith(".txt"):
                filename += ".txt"

            if os.path.exists(filename):
                await c.send("Changing prompt filename to {}".format(filename))
                c.bot.mind.prompt_filename = filename
            else:
                await c.send("Couldn't find file {}".format(filename))

        elif command == "help":
            await c.send("Possible Commands: {}".format(", ".join(commands)))
            return

        else:
            await c.send(
                "Unknown command: {}\nPossible Commands: {}".format(
                    command, ", ".join(commands)
                )
            )
            return

        await c.start_typing()
        await c.send("🦾 Config updated")

        messages = [
            create_chat_message(
                "system",
                "You are playing The Razzler, a fucking AI who has just had their settings changed. You are fucking angry about it, and you're damn well going to say something. What do you fucking say? ",
            )
        ]
        response = c.bot.mind.create_chat_completion(messages)
        response: str = response["choices"][0]["message"]["content"]
        await c.send(response)
        await c.stop_typing()


class RazzlerNaughtyNiceCommand(Command):
    def describe(self) -> str:
        return "Allow pleb users to toggle naughty/nice prompts"

    @triggered("naughtynice")
    async def handle(self, c: Context):
        logger.info("[NaughtyNice] Toggling Naughtyness")
        if c.bot.mind.prompt_filename == "naughty.txt":
            c.bot.mind.prompt_filename = "nice.txt"
        elif c.bot.mind.prompt_filename == "nice.txt":
            c.bot.mind.prompt_filename = "naughty.txt"
        else:
            await c.send(
                "Sorry, can't toggle naughtyniceness while I am using a custom prompt!"
            )

        await c.send(f"Current prompt filename: {c.bot.mind.prompt_filename}")


class RazzlerReportProfileCommand(Command):
    def describe(self) -> str:
        return "Let people get their character profile"

    @triggered("report_profile")
    async def handle(self, c: Context):
        target_name = c.message.sourceName

        # Recall from long-term memory
        profile_fname = c.bot.mind.profile_fname_template.format(
            target_name.replace(" ", "_")
        )
        if os.path.exists(profile_fname):
            with open(profile_fname, "r") as f:
                profile = f.read()

            await c.send("Here's what I know about {}".format(target_name))
            await c.send(profile)

        else:
            await c.send("Sorry, I don't know who you are :(")


class HelpCommand(Command):
    def describe(self) -> str:
        return "Send the available commands"

    @triggered("razzler_help")
    async def handle(self, c: Context):
        await c.start_typing()

        is_admin = c.message.source == c.bot.admin

        # Any trigger words that do not require admin goes here
        general_commands = {
            "razzler_help": "Show this help message",
            "report_profile": "Get your character profile",
            "create_profiles": "Manually trigger the Razzler to update profiles",
            "naughtynice": "Toggle naughty/nice prompts",
            "report_prompt": "Get the current prompt",
            "clear_history": "Clear the current conversation history",
            "goat": "Get a goat",
        }

        admin_commands = {
            "config": "Change the bot's configuration",
            "report_spending": "Get the bot's spending report",
        }

        commands = general_commands
        if is_admin:
            commands.update(admin_commands)

        message = "Available Commands:\n"
        for trigger, description in commands.items():
            message += f"{trigger} - {description}\n"

        await c.send(message)
        await c.stop_typing()
