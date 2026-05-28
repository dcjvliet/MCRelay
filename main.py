import discord
from discord import app_commands
import json
import sys
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

# stuff to make sure .exe works fine
BASE_DIR = Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent
GUILD_IDS_FILE = BASE_DIR / 'guild_ids.json'
LINKED_ACCOUNTS_FILE = BASE_DIR / 'linked_accounts.json'
ENV_FILE = BASE_DIR / '.env'

load_dotenv(ENV_FILE)

# helper functions to make sure files exist and to read/write json files
def ensure_json_file(file_path: Path, default_value):
    if not file_path.exists():
        with open(file_path, 'w') as f:
            json.dump(default_value, f, indent=4)


def read_json_file(file_path: Path, default_value):
    if not file_path.exists():
        return default_value

    with open(file_path, 'r') as f:
        return json.load(f)


def write_json_file(file_path: Path, data):
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=4)


ensure_json_file(GUILD_IDS_FILE, {})
ensure_json_file(LINKED_ACCOUNTS_FILE, {})

# create list of tracked channels (unique across all servers)
tracked_channels = set()

async def start_web_server():
    app = web.Application()
    app.router.add_post('/send_message', send_message_to_discord)
    app.router.add_get('/get_user_data', get_user_discord_data)
    runner = web.AppRunner(app)

    await runner.setup()

    site = web.TCPSite(runner, 'localhost', 5000)

    await site.start()


def cache_channel_ids(server, channel_name):
    channels_file = BASE_DIR / f'{server.id}_channels.json'

    if channels_file.exists():
        with open(channels_file, 'r') as f:
            channels = json.load(f)
            if channel_name in channels:
                return channels[channel_name]['id']

        channel = discord.utils.get(server.channels, name=channel_name)
        if channel is None:
            return None
        channels[channel_name] = {'id': channel.id}
        write_json_file(channels_file, channels)

        return channel.id
    
    else:
        channel = discord.utils.get(server.channels, name=channel_name)
        if channel is None:
            return None
        channels = {channel_name: {'id': channel.id}}
        write_json_file(channels_file, channels)

        return channel.id


def cache_guild_id(guild_name: str):
    guild_ids = read_json_file(GUILD_IDS_FILE, {})
    if guild_name in guild_ids:
        return guild_ids[guild_name]
        
    guild = discord.utils.get(client.guilds, name=guild_name)
    if guild is None:
        return None
    guild_ids[guild_name] = guild.id
    write_json_file(GUILD_IDS_FILE, guild_ids)

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
@app_commands.guild_only()
async def link_account(interaction: discord.Interaction, username: str):
    # limit to only text channels
    channel = interaction.channel
    if not isinstance(channel, discord.TextChannel):
        await interaction.response.send_message('This command can only be used in text channels.', ephemeral=True)
        return
    
    discord_id = interaction.user.id
    linked_accounts = read_json_file(LINKED_ACCOUNTS_FILE, {})
    
    linked_accounts[str(discord_id)] = username
    write_json_file(LINKED_ACCOUNTS_FILE, linked_accounts)

    await interaction.response.send_message(f'Your Discord account has been linked to the Minecraft account: {username}', ephemeral=True)


# toggle forwarding of discord messages to minecraft
@tree.command(name='toggle_forwarding', description='Toggle forwarding all messages sent in this channel to Minecraft.')
@app_commands.guild_only()
async def toggle_forwarding(interaction: discord.Interaction):
    # limit to only text channels
    channel = interaction.channel
    if not isinstance(channel, discord.TextChannel):
        await interaction.response.send_message('This command can only be used in text channels.', ephemeral=True)
        return
    
    channel_id = interaction.channel_id
    if channel_id in tracked_channels:
        tracked_channels.remove(channel_id)
        await interaction.response.send_message('Message forwarding has been disabled for this channel.', ephemeral=False)
    else:
        tracked_channels.add(channel_id)
        await interaction.response.send_message('Message forwarding has been enabled for this channel.', ephemeral=False)


@tree.command(name='exclude', description='Exclude a member in this channel from receiving forwarded messages.')
@app_commands.guild_only()
async def exclude(interaction: discord.Interaction, member: discord.Member):
    # limit to only text channels
    channel = interaction.channel
    if not isinstance(channel, discord.TextChannel):
        await interaction.response.send_message('This command can only be used in text channels.', ephemeral=True)
        return
    
    exclude_id = member.id
    channel_name = channel.name
    server = interaction.guild
    if server is None:
        await interaction.response.send_message('Error: Could not find the server.', ephemeral=True)
        return
    
    channels_file = BASE_DIR / f'{server.id}_channels.json'

    if channels_file.exists():
        with open(channels_file, 'r') as f:
            channels = json.load(f)
            if channel_name in channels:
                if 'excluded' in channels[channel_name]:
                    channels[channel_name]['excluded'].append(exclude_id)
                else:
                    channels[channel_name]['excluded'] = [exclude_id]
                await interaction.response.send_message(f'{member.display_name} has been excluded from receiving forwarded messages in this channel.', ephemeral=False)
            else:
                channels[channel_name] = {'id': channel.id, 'excluded': [exclude_id]}
                await interaction.response.send_message(f'{member.display_name} has been excluded from receiving forwarded messages in this channel.', ephemeral=False)
        
        write_json_file(channels_file, channels)

        return
    
    else:
        channels = {channel_name: {'id': channel.id, 'excluded': [exclude_id]}}
        write_json_file(channels_file, channels)

        await interaction.response.send_message(f'{member.display_name} has been excluded from receiving forwarded messages in this channel.', ephemeral=False)
        return
    

@tree.command(name='include', description='Include a member in this channel to receive forwarded messages.')
@app_commands.guild_only()
async def include(interaction: discord.Interaction, member: discord.Member):
    # limit to only text channels
    channel = interaction.channel
    if not isinstance(channel, discord.TextChannel):
        await interaction.response.send_message('This command can only be used in text channels.', ephemeral=True)
        return

    include_id = member.id
    channel_name = channel.name
    server = interaction.guild
    if server is None:
        await interaction.response.send_message('Error: Could not find the server.', ephemeral=True)
        return

    channels_file = BASE_DIR / f'{server.id}_channels.json'

    if channels_file.exists():
        with open(channels_file, 'r') as f:
            channels = json.load(f)
            if channel_name in channels:
                if 'excluded' in channels[channel_name]:
                    if include_id in channels[channel_name]['excluded']:
                        channels[channel_name]['excluded'].remove(include_id)
                    await interaction.response.send_message(f'{member.display_name} has been included to receive forwarded messages in this channel.', ephemeral=False)
                else:
                    await interaction.response.send_message(f'{member.display_name} is already included to receive forwarded messages in this channel.', ephemeral=False)
            else:
                await interaction.response.send_message(f'Channel "{channel_name}" not found.', ephemeral=True)

        write_json_file(channels_file, channels)

        return

    else:
        channels = {channel_name: {'id': channel.id}}
        write_json_file(channels_file, channels)

        await interaction.response.send_message(f'{member.display_name} has been included to receive forwarded messages in this channel.', ephemeral=False)
        return


@tree.command(name='private_channel', description='Create a private channel only specified members can access.')
@app_commands.guild_only()
async def private_channel(interaction: discord.Interaction, channel_name: str, member: discord.Member):
    # limit to only text channels
    channel = interaction.channel
    if not isinstance(channel, discord.TextChannel):
        await interaction.response.send_message('This command can only be used in text channels.', ephemeral=True)
        return
    
    server = interaction.guild
    if server is None:
        await interaction.response.send_message('Error: Could not find the server.', ephemeral=True)
        return
    
    overwrites = {
        server.default_role: discord.PermissionOverwrite(view_channel=False),
        member: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
    }

    category = discord.utils.get(
        server.categories,
        name="Private Channels"
    )

    channel = await server.create_text_channel(channel_name, overwrites=overwrites, category=category)

    await interaction.response.send_message(f'Private channel {channel.mention} has been created.', ephemeral=False)


@tree.command(name='add_member', description='Add a member to a private channel created by the bot.')
@app_commands.guild_only()
async def add_member(interaction: discord.Interaction, channel: discord.TextChannel, member: discord.Member):
    # limit to only text channels
    if not isinstance(channel, discord.TextChannel):
        await interaction.response.send_message('This command can only be used in text channels.', ephemeral=True)
        return

    server = interaction.guild
    if server is None:
        await interaction.response.send_message('Error: Could not find the server.', ephemeral=True)
        return

    await channel.set_permissions(
        member,
        view_channel=True,
        send_messages=True,
        read_message_history=True
    )

    await interaction.response.send_message(f'{member.display_name} has been added to {channel.mention}.', ephemeral=False)
    return


@tree.command(name='remove_member', description='Remove a member from a private channel created by the bot.')
@app_commands.guild_only()
async def remove_member(interaction: discord.Interaction, channel: discord.TextChannel, member: discord.Member):
    # limit to only text channels
    if not isinstance(channel, discord.TextChannel):
        await interaction.response.send_message('This command can only be used in text channels.', ephemeral=True)
        return

    server = interaction.guild
    if server is None:
        await interaction.response.send_message('Error: Could not find the server.', ephemeral=True)
        return

    await channel.set_permissions(
        member,
        view_channel=False,
        send_messages=False,
        read_message_history=False
    )

    await interaction.response.send_message(f'{member.display_name} has been added to {channel.mention}.', ephemeral=False)
    return


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
        linked_accounts = read_json_file(LINKED_ACCOUNTS_FILE, {})

        server = message.guild
        channel = message.channel.name
        channels_file = BASE_DIR / f'{server.id}_channels.json'

        if channels_file.exists():
            with open(channels_file, 'r') as f:
                channels = json.load(f)
                if channel in channels and 'excluded' in channels[channel]:
                    excluded_ids = channels[channel]['excluded']
                else:
                    excluded_ids = []
        else:
            excluded_ids = []

        for member in message.channel.members:
            if str(member.id) in linked_accounts and str(member.id) not in excluded_ids:
                usernames.append(linked_accounts[str(member.id)].lower())
        
        # remove the username of the person that sent it if needed
        if sent_in_game:
            username = message.content.split('[Minecraft] ')[1].split(':')[0]
            usernames.remove(username.lower())

        # now we need to send to the server somehow
        try:
            rcon_pwd = os.getenv("RCON_PASSWORD")
            rcon_ip = os.getenv("RCON_IP", "localhost")
            rcon_port = int(os.getenv("RCON_PORT", 25575))
            with MCRcon(rcon_ip, rcon_pwd, port=rcon_port) as mcr:
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
        linked_accounts = read_json_file(LINKED_ACCOUNTS_FILE, {})
        for discord_id, minecraft_username in linked_accounts.items():
            if minecraft_username == player:
                linked_account = discord_id
                break

        if linked_account is None:
            return web.json_response({'status': 'error', 'message': f'No linked Discord account found for Minecraft username "{player}"'}, status=404)

        # we want to edit the message to include mentions
        # first we want to find every instance of "@username"
        words = message.split()
        for i, word in enumerate(words):
            if word.startswith('@'):
                username = word[1:]
                # now we want to find the discord id for this username
                discord_id = None
                for id, mc_username in linked_accounts.items():
                    if mc_username == username:
                        discord_id = id
                        break
                
                if discord_id is not None:
                    # replace the word with a mention
                    words[i] = f'<@{discord_id}>'
        message = ' '.join(words)

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


# now we need to implement the method to allow Minecraft to get a users servers/channels
async def get_user_discord_data(request):
    try:
        username = request.query.get('username', None)
        if username is None:
            return web.json_response({'status': 'error', 'message': 'username is required'}, status=400)
        
        # now we need to do a reverse lookup to get the discord id from the username
        linked_accounts = read_json_file(LINKED_ACCOUNTS_FILE, {})
        discord_id = None
        for id, mc_username in linked_accounts.items():
            if mc_username == username:
                discord_id = id
                break

        if discord_id is None:
            return web.json_response({'status': 'error', 'message': f'No linked Discord account found for Minecraft username "{username}"'}, status=404)
        
        servers_data = []
        for guild in client.guilds:
            member = guild.get_member(int(discord_id))
            if member is None:
                continue

            channels_data = []
            for channel in guild.text_channels:
                permissions = channel.permissions_for(member)
                if permissions.view_channel and permissions.send_messages:
                    channels_data.append(channel.name)

            if channels_data:
                servers_data.append({'name': guild.name, 'channels': channels_data})
        
        return web.json_response({'status': 'ok', 'guilds': servers_data}, status=200)
    except Exception as e:
        print(e)
        return web.json_response(
            {
                "status": "error",
                "message": str(e)
            },
            status=500
        )

token = os.getenv("DISCORD_TOKEN")
if token is None:
    print("Error: DISCORD_TOKEN not found in environment variables.")
else:
    client.run(token)
