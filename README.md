# TheRazzler
The Rizzler is a Signal bot that responds to group chats with ChatGPT. It can be added to group chats, where it'll occasionally respond at random, or if someone talks to it.

The base code for this was written in like, three drunk hours. Some refinements have been made, 
but this is *absolutley not* a "designed" product, more of an evolved one. Code has been written 
optimising for development time, and stability. Not extensibility or clarity. Perhaps one day 
I'll fix it, but this is not that kind of project.

The setup is also fairly organic, and is deployed on my home server. There are a few components:
- `signal-cli`: [Link](https://github.com/bbernhard/signal-cli-rest-api) This is an excellent project that spoofs a phone, 
enabling a self-hosted REST API that hooks into Signal
- Signal bot layer: This is a remix of the [signal bot](https://pypi.org/project/signalbot/) example. I extended it a little 
bit to include some features I was missing, and since this code is hardly intended to be re-used, I've simply included the code
here. If I can get the time, I'll likely make a PR to the original repo.
- GPT brain: This is based (loosely) on an early version of the AutoGPT interface. Essentially this is just a class to which 
information can be given, and GPT responses will be handled (including cost tracking)

Installation instructions are omitted here, at least for now. I do have a webhook deployment service running though, so any changes made to this repo are automatically sent to "prod", if you like.

Usage is relatively simple. You just add the Razzler to a group chat. I'm not making my own Razzler public, as GPT API calls are expensive and this won't be monetized. 


# Razzler functions

This is a minimal reference for the functions. Note that the Razzler will do a few things by default.

### Character profiling
The Razzler will temporarily record the chat history (by default, 100 messages are stored in a Redis cache). Every so often, the Razzler will take these messages,
and create character profiles of all the people who it has interacted with, storing these to its long term memory. Subsequent profiles recieve their predecessors, 
and the Razzler can preserve things it finds interesting over long periods of time.

*These messages are not stored permenantly*. I don't want to mess about with securely storing sensitive data, so this is flushed when the Razzler restarts. 
If the history goes over the defined limit, they fall off the back of the list.

### Chat participation
At random, the Razzler will target a person in the group. There are two options, `naughty` and `nice`. Based on the profile of the target, the Razzler will either 
roast you, or complement you. The odds of each are configurable, along with the freqency of spontaneous messages.

### Image generation
Any message that the Razzler sends has a chance of also including an image. The Razzler will give an image description in it's text, like this: `<A picture of a puppy>`, 
which will be extracted and given as a prompt for openAI's image generator. Note that the description will also appear in the message; this is intentional, as sometimes
the image prompt will be rejected for violating guidelines, and the description can still be funny.

### Replying
Tagging the Razzler guarantees a response. This often leads to organic interactions, and the Razzler feeling more "human" in the chat. Plus, you can ask it things. 
As the prompt is written, it's not exactly *helpful*, but that's not really the goal.

### Cost tracking
The openAI API is not free, and GPT-4 is significantly funnier than the cheaper 3.5. As such, The Razzler keeps a track of its spending, including tracking how much 
each user spends, and has a spending limit after which it will stop making API calls.


## Chat Commands

- `razzler_help`
  - This will list the available commands.
- `config`
  - Various settings can be tweaked.
- `report_spending`
  - As it says, give a spending report.
- `clear_history`
  - Clear the chat log stored in the cache.
- `create_profiles`
  - Trigger the character profile creation for each user in the chat.
- `update_profile`
  - Trigger the character profile creation for the user sending the command only.
- `report_profile`
  - Have the Razzler send your profile to the chat. It's fun to see what it thinks of you.
