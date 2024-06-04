# TODO

- Implement profiling for members of a chat
- Should all the settings be in a SQL database? That way, I could build a web configuration page...
- The websocket `receive` endpoint only streams incoming messages, and doesn't yield up things that were sent while the connection wasnt alive. When the razzler starts, it should call the HTTP version of the endpoint, which DOES return a list of un-acknowleged messages, so it can work down the backlog.
- Move the configuration and prompt text files to a persistent database, rather than being stored on disc
