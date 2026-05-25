# Installation
Go to the latest release and download the `discord_bot.exe` file. The bot will be online as long as this file is running.

# Setup
### This bot works in conjuction with the [MCRelay mod](https://github.com/dcjvliet/MCRelay-Mod).
In order to run this Discord bot, you must first create a bot through the [Discord Developer Portal](https://discord.com/developers/applications). Follow the instructions there to create a bot, and copy its token. 

In the same directory as the `discord_bot.exe` file, create a file named `.env` and paste the following line in: `DISCORD_TOKEN="YOUR TOKEN"`, replacing YOUR_TOKEN with the token you copied from the Discord Developer Portal.

You must update your `server.properties` file in order for this mod and Discord bot to work. In the `server.properties` file, make sure `enable-rcon` is set to true, and then set the `rcon-password`. Optionally, set the `rcon-port`.

In the same `.env` file paste the following line in: `RCON_PASSWORD="YOUR PASSWORD"`, replacing YOUR_PASSWORD with the password you set in the `server.properties` file. If you changed the port as well, create a variable in the `.env` file named `RCON_PORT`. This is not necessary if it is set to the default port. If you are running the Discord bot from a server different from the one the Minecraft server runs on, then create a varaible in the `.env` file named `RCON_IP` and set it to your Minecraft server's IP.

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
  
