# TODO

- Implement profiling for members of a chat
- The websocket `receive` endpoint only streams incoming messages, and doesn't yield up things that were sent while the connection wasnt alive. When the razzler starts, it should call the HTTP version of the endpoint, which DOES return a list of un-acknowleged messages, so it can work down the backlog.
- The web interface could have a list of razzler image descriptions, from group chats that people are part of. It might be interesting to see what the razzler sees in various images
- The web interface needs some example conversation, so people can test their prompts in a private environment.
- Use a proper file lock system
- Implement per-user rate limiting
- Set up a dev container environment
