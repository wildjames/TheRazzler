# TODO

- Implement profiling for members of a chat
- The websocket `receive` endpoint only streams incoming messages, and doesn't yield up things that were sent while the connection wasnt alive. When the razzler starts, it should call the HTTP version of the endpoint, which DOES return a list of un-acknowleged messages, so it can work down the backlog.
- Periodically have the razzler read the chat history, and choose a message to react with an emoji to. Ask for a response in a defined format, like `<message timestamp> <emoji>`, and parse that back to something traditional logic understands?
