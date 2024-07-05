# TODO

- Implement profiling for members of a chat
- The websocket `receive` endpoint only streams incoming messages, and doesn't yield up things that were sent while the connection wasnt alive. When the razzler starts, it should call the HTTP version of the endpoint, which DOES return a list of un-acknowleged messages, so it can work down the backlog.
- The web interface could have a list of razzler image descriptions, from group chats that people are part of. It might be interesting to see what the razzler sees in various images
- The web interface needs some example conversation, so people can test their prompts in a private environment.
- Use a proper file lock system
- Implement per-user rate limiting
- Set up a dev container environment



# Developer setup

I use a dev container to keep things easy and consistent.

1. Install VS Code
2. Install the Dev Container extension
3. Download and extract the Razzler Data folder: [here](https://nextcloud.wildjames.com/s/qcGffbm2Ygj28bs) (talk to me for the required password)
4. Press `CTRL+SHIFT+P` on windows, or `CMD+SHIFT+P` on a mac to bring up the command prompt
5. Type "Dev Containers: Open Folder in Container" and choose the base directory of the repo
6. Wait for the dev container to start up

## Makefile commands

WIP

- `install`: Should be unnecessary to run manually - install the requirements for the project
- `dev`: Start a "live" version of the razzler stack, which should load changes as they're made
- `prod`: Build and run the production razzler image
- `publish`: Build the docker image for the razzler, and push it to the docker hub

