# Setup
In order to run this Discord bot, you must first create a bot through the [Discord Developer Portal](https://discord.com/developers/applications). Follow the instructions there to create a bot, and copy its token. Then you will either need to put that token in the last line of the `main.py` file in place of "token", or create a `.env` file and add the token under the variable name `DISCORD_TOKEN`.
This bot works in conjuction with the [MCRelay mod](https://github.com/dcjvliet/MCRelay-Mod). There are two ways to run this bot.

## Option 1: On the same server as the Minecraft server
This is the easiest option. Simply install the python script and related `.json` files on the server, and run the main.py file. Then invite the bot to the Discord server, and it will work.

## Option 2: On a different server from the Minecraft server
This requires a few code changes. On line 136, you must change `localhost` to the IP of the server the Minecraft server runs on.

No matter which option you choose, you must update your `server.properties` file and the RCon password in the code. In the `server.properties` file, make sure `enable-rcon` is set to true, and then set the `rcon-password`. This password must be entered in line 136 of `main.py`.

When inviting the bot to your server, you must select the correct options when generating the OAuth URL in the Discord Developer Portal. The `bot` as well as `applications.commands` boxes must be checked. Within the bot permissions, it must be able to `Send Messages`, `Read Message History`, and `Manage Channels`. It is also essentialy that in the `Bot` tab on the left-hand side you give it `Server Memebers` and `Message Content` Intents.

# Usage
The bot comes with a few commands. In order to use most of them, you must link your Minecraft and Discord accounts using the `/link_account` command.

- `/link_account <username>`: Links your Discord account to the given Minecraft username. _This does not actually verify with Microsoft, so this works on the honor system._
- `/toggle_forwarding`: Toggles forwarding of messages in the channel to Minecraft.
- `/exclude <member>`: Exclude a member in a channel from receiving forwarded messages.
- `/include <member>`: Include a member (in a channel or not) from receiving forwarded messages.
- `/private_channel <channel_name> <member>`: Create a private channel with the given name that only the given member (and server administrators) can access. _This does not require the member to have permission to create text channels._
- `/add_member <channeL> <member>`: Give the member access to the given channel. _This does not require the member to have permission to edit member access._
- `/remove_member <channel> <member>`: Remove access from the member to the given channel. _This does not require the member to have permission to edit member access._
  
