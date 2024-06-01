# TODO

- The vision commands contain a lot of repeated logic, and the methods are pretty large. Combine their logic, and break up the handler method. Add a flag that enables/disables the razzler replying to an image message.
- I need to decide on the best way to handle commands that have some overlap. Notes in `razzler.py`
- Implement profiling for members of a chat?
- Should all the settings be in a SQL database? That way, I could build a web configuration page...
