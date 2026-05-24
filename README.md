# Setup
In order to run this Discord bot, you must first create a bot through the [Discord Developer Portal](https://discord.com/developers/applications). Follow the instructions there to create a bot, and copy its token. Then you will need to put that token in the last line of the `main.py` file.
This bot works in conjuction with the [MCRelay mod](https://github.com/dcjvliet/MCRelay-Mod). There are two ways to run this bot.

## Option 1: On the same server as the Minecraft server
This is the easiest option. Simply install the python script and related `.json` files on the server, and run the main.py file. Then invite the bot to the Discord server, and it will work.

## Option 2: On a different server from the Minecraft server
This requires a few code changes. On line 136, you must change `localhost` to the IP of the server the Minecraft server runs on.

No matter which option you choose, you must update your `server.properties` file and the RCon password in the code. In the `server.properties` file, make sure `enable-rcon` is set to true, and then set the `rcon-password`. This password must be entered in line 136 of `main.py`.

When inviting the bot to your server, you must select the correct options when generating the OAuth URL in the Discord Developer Portal. The `bot` as well as `applications.commands` boxes must be checked. Within the bot permissions, it must be able to `send_messages` and `read_message_history`. It is also essentialy that in the `Bot` tab on the left-hand side you give it `Server Memebers` and `Message Content` Intents.

# Usage
The first step is to link your Minecraft account with your Discord account. Run the command `/link_accoutn <Minecraft username>` in a channel that the bot has access to to link the accounts. Note that this does not actually perform any authentication, so it is easily exploitable.
Next, in order for Discord messages to be sent to the Minecraft server, you must run the command `/toggle_forwarding`. This will begin forwarding **all messages sent in the channel to all members who have access to that channel** on the Minecraft server. It will only send the message in Minecraft if their account is linked.
Run `/toggle_forwarding` again to disable forwarding messages.
