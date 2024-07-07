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

Note that if you're on windows, the user configuration API will not be available on the host windows machine (or any other machine, for that matter) until the port has been [forwarded from WSL to windows](https://superuser.com/questions/1717753/how-to-connect-to-windows-subsystem-for-linux-from-another-machine-within-networ/1830244#1830244).

## Makefile commands

- `install`: Install the requirements for local development in a new `venv` space
- `dev`: Start a "live" version of the razzler stack, which should load changes as they're made
- `build`: Build the official docker image
- `run`: Run the latest version of the docker image
- `brun`: Build and run the docker image
- `publish`: Build the docker image with the `latest` tag, and push to docker hub
- `clean`: Reset the build environment
