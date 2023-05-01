import json
import logging
import sys
from pprint import pformat

import openai
import requests
from commands import (
    ClearChatHistory,
    GoatseCommand,
    RazzlerMindCommand,
    SaveChatHistory,
)
from gpt_interface import SignalAI
from signalbot.signalbot import SignalBot

logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout, level=logging.INFO)

# Register the openAI token
with open("openai_api_token.txt", "r") as f:
    openai_api_token = f.readline()
openai.api_key = openai_api_token


def main(config: dict):
    bot_config = config["bot"]
    llm_config = config["llm"]

    # And create a brain for the Razzler
    razzler_mind = SignalAI(**llm_config)

    # Test the AI
    response = razzler_mind.create_chat_completion(
        [{"role": "user", "content": "Please respond"}]
    )
    response = response["choices"][0]["message"]["content"]
    logger.info("Testing that we can talk to the AI:")
    logger.info("Got the response:")
    logger.info(response)

    # On start, the Rizzler checks for new group chats.
    # The signalbot library doesn't have this, so I've hacked it in
    # TODO: Make that upgrade
    response = requests.get(
        "http://{}/v1/groups/{}".format(
            bot_config["signal_service"], bot_config["phone_number"]
        )
    )
    groups = response.json()
    logger.info("The Razzler is part of the following group chats:")
    logger.info(pformat(groups))

    bot = SignalBot(bot_config)
    # Give it its mind to carry. Probably should make this an actual property with a primitive, but w/e
    bot.mind = razzler_mind

    # Listen to all the groups we're in
    for group in groups:
        bot.listen(group["id"], group["internal_id"])

    # And my personal number for testing
    bot.listen(bot_config["test_number"])

    # Register commands here.
    # Not *technically* executed in order (uses async) but will be queued in order at least
    bot.register(SaveChatHistory())
    bot.register(GoatseCommand())
    bot.register(RazzlerMindCommand())
    bot.register(ClearChatHistory())

    bot.start()


if __name__ == "__main__":
    with open("config.json", "r") as f:
        config = json.load(f)

    main(config)
