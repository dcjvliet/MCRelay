import discord
from discord import app_commands
import json
from pathlib import Path
from dotenv import load_dotenv
import os

from mcrcon import MCRcon
from aiohttp import web


intents = discord.Intents.default()
intents.message_content = True
intents.members = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# create list of tracked channels (unique across all servers)
tracked_channels = set()

async def start_web_server():
    app = web.Application()
    app.router.add_post('/send_message', send_message_to_discord)
    runner = web.AppRunner(app)

    await runner.setup()

    site = web.TCPSite(runner, 'localhost', 5000)

    await site.start()


def cache_channel_ids(server, channel_name):
    if Path(f'{server.id}_channels.json').exists():
        with open(f'{server.id}_channels.json', 'r') as f:
            channels = json.load(f)
            if channel_name in channels:
                return channels[channel_name]

        channel = discord.utils.get(server.channels, name=channel_name)
        if channel is None:
            return None
        channels[channel_name] = channel.id
        with open(f'{server.id}_channels.json', 'w') as f:
            json.dump(channels, f, indent=4)

        return channel.id
    
    else:
        channel = discord.utils.get(server.channels, name=channel_name)
        if channel is None:
            return None
        channels = {channel_name: channel.id}
        with open(f'{server.id}_channels.json', 'w') as f:
            json.dump(channels, f, indent=4)

        return channel.id


def cache_guild_id(guild_name: str):
    with open('guild_ids.json', 'r') as f:
        guild_ids = json.load(f)
        if guild_name in guild_ids:
            return guild_ids[guild_name]
        
    guild = discord.utils.get(client.guilds, name=guild_name)
    if guild is None:
        return None
    guild_ids[guild_name] = guild.id
    with open('guild_ids.json', 'w') as f:
        json.dump(guild_ids, f, indent=4)

    return guild.id


@client.event
async def on_ready():
    print(f'Logged in as {client.user}')

    # sync the commands rq
    try:
        # Syncs the commands globally
        synced = await tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Error syncing commands: {e}")

    await start_web_server()


# command to link a discord account to a minecraft username
@tree.command(name='link_account', description='Links your Discord account to your Minecraft account.')
async def link_account(interaction: discord.Interaction, username: str):
    discord_id = interaction.user.id
    with open('linked_accounts.json', 'r') as f:
        linked_accounts = json.load(f)
    
    linked_accounts[str(discord_id)] = username
    with open('linked_accounts.json', 'w') as f:
        json.dump(linked_accounts, f, indent=4)

    await interaction.response.send_message(f'Your Discord account has been linked to the Minecraft account: {username}', ephemeral=True)


# toggle forwarding of discord messages to minecraft
@tree.command(name='toggle_forwarding', description='Toggle forwarding all messages sent in this channel to Minecraft.')
async def toggle_forwarding(interaction: discord.Interaction):
    channel_id = interaction.channel_id
    if channel_id in tracked_channels:
        tracked_channels.remove(channel_id)
        await interaction.response.send_message('Message forwarding has been disabled for this channel.', ephemeral=False)
    else:
        tracked_channels.add(channel_id)
        await interaction.response.send_message('Message forwarding has been enabled for this channel.', ephemeral=False)


@client.event
async def on_message(message):
    sent_in_game = False
    if message.author == client.user:
        content = message.content
        if not '[Minecraft]' in content:
            # this means it is just some random message from the bot
            return
        # this means that the message is formatted as "[Minecraft] <player>: <message>"
        # we don't want to broadcast this to the person that sent it originally
        sent_in_game = True
    
    if message.channel.id in tracked_channels:
        # get usernames for all members
        usernames = []
        with open('linked_accounts.json', 'r') as f:
            linked_accounts = json.load(f)

        for member in message.channel.members:
            if str(member.id) in linked_accounts:
                usernames.append(linked_accounts[str(member.id)].lower())
        
        # remove the username of the person that sent it if needed
        if sent_in_game:
            username = message.content.split('[Minecraft] ')[1].split(':')[0]
            usernames.remove(username.lower())

        # now we need to send to the server somehow
        try:
            with MCRcon('localhost', 'hello123', port=25575) as mcr:
                if not sent_in_game:
                    safe_content = message.content.replace('"', '\\"').replace("\n", ' ')
                    display_name = message.author.display_name.replace('"', '\\"')
                else:
                    safe_content = message.content.split(': ')[1].replace('"', '\\"').replace("\n", ' ')
                    display_name = message.content.split(': ')[0].split('[Minecraft] ')[1].replace('"', '\\"')

                for username in usernames:
                    mcr.command(f'tellraw {username} {{"text": "[Discord] {display_name}: {safe_content}", "color": "blue"}}')

        except Exception as e:
            print(e)
    return


# define logic to get messages from the mod and send them in the channel
async def send_message_to_discord(request):
    try:
        data = await request.json()

        guild_name = data.get('guild', None)
        channel_name = data.get('channel', None)
        message = data.get('message', None)
        player = data.get('player', None)

        guild_id = cache_guild_id(guild_name)
        if guild_id is None:
            return web.json_response({'status': 'error', 'message': f'Guild "{guild_name}" not found'}, status=404)
        
        guild = client.get_guild(int(guild_id))

        if guild is None:
            return web.json_response({'status': 'error', 'message': f'Guild "{guild_name}" not found'}, status=404)
        
        channel_id = cache_channel_ids(guild, channel_name)
        if channel_id is None:
            return web.json_response({'status': 'error', 'message': f'Channel "{channel_name}" not found in guild "{guild_name}"'}, status=404)
        
        discord_channel = guild.get_channel(channel_id)
        if discord_channel is None:
            return web.json_response({'status': 'error', 'message': f'Channel with ID "{channel_id}" not found in guild "{guild_name}"'}, status=404)
        
        # get the linked account for the player
        linked_account = None
        with open('linked_accounts.json', 'r') as f:
            linked_accounts = json.load(f)
            for discord_id, minecraft_username in linked_accounts.items():
                if minecraft_username == player:
                    linked_account = discord_id
                    break

        if linked_account is None:
            return web.json_response({'status': 'error', 'message': f'No linked Discord account found for Minecraft username "{player}"'}, status=404)

        client.loop.create_task(discord_channel.send(f'**[Minecraft]** {player}: {message}')) # type: ignore

        return web.json_response({'status': 'ok'}, status=200)
    except Exception as e:
        print(e)
        return web.json_response(
            {
                "status": "error",
                "message": str(e)
            },
            status=500
        )
    

load_dotenv()
token = os.getenv("DISCORD_TOKEN")
if token is None:
    print("Error: DISCORD_TOKEN not found in environment variables.")
else:
    client.run(token)
