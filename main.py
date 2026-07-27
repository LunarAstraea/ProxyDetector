import json

import discord
import pluralkit
from dotenv import load_dotenv
import os
from cachetools import TTLCache

load_dotenv()
pk_client = pluralkit.Client()
token = os.getenv("TOKEN")
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
client = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(client)
guild_id = 1324053390459670588 # Hardcoded Guild ID of AD:Endgame Discord
modlog_channel = None
proxy_channel = None
if os.path.isfile("config.json"):
    with open("config.json") as json_file:
        config = json.load(json_file)
    modlog_channel = config.get("log_channel")
    proxy_channel = config.get("proxy_channel")
modlog_cache = TTLCache(maxsize=1000, ttl=10)
proxy_cache = TTLCache(maxsize=1000, ttl=10)

@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))
    await tree.sync(guild=discord.Object(id=guild_id))
@client.event
async def on_message_delete(message: discord.Message):
    if not modlog_channel:
        return
    try:
        pk_message: pluralkit.Message = await pk_client.get_message(message.id) # noqa
    except pluralkit.MessageNotFound:
        return
    print("Original Message ID: ", pk_message.original)
    if message.author == client.user:
        return
    if pk_message.original == message.id: #I'm pretty sure this always returns true here, but I added it just in case
        proxy_cache[pk_message.original] = True
    for message_id, modlog_message in modlog_cache.items():
        await handle_message(modlog_message, pk_message.original)

@client.event
async def on_message(message: discord.Message):
    if not modlog_channel:
        return
    if message.author == client.user:
        return
    if message.channel.id == modlog_channel:
        modlog_cache[message.id] = message
        for message_id in proxy_cache:
            message_id: int
            await handle_message(message, message_id)

@tree.command(
    name="set_log_channel",
    guild=discord.Object(id=guild_id)
)
async def set_log_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Administration permissions are required to set log channel.", ephemeral=True)
        return
    if os.path.isfile("config.json"):
        with open("config.json", "r") as f:
            config = json.load(f)
    else:
        config = {}
    config["log_channel"] = channel.id
    with open("config.json", "w") as f:
        json.dump(config, f, indent=4)
    global modlog_channel
    modlog_channel = channel.id
    await interaction.response.send_message(f"Channel <#{channel.id}> has been set as log channel.", ephemeral=True)

@tree.command(
    name="set_proxylog_channel",
    guild=discord.Object(id=guild_id)
)
async def set_proxy_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Administration permissions are required to set log channel.", ephemeral=True)
        return
    if os.path.isfile("config.json"):
        with open("config.json", "r") as f:
            config = json.load(f)
    else:
        config = {}
    config["proxy_channel"] = channel.id
    with open("config.json", "w") as f:
        json.dump(config, f, indent=4)
    global proxy_channel
    proxy_channel = channel.id
    await interaction.response.send_message(f"Channel <#{channel.id}> has been set as proxy log channel.", ephemeral=True)

def does_message_match(original_message_id: int, embed: discord.Embed) -> bool:
    description_lines = embed.description.split("\n")
    if len(description_lines) >= 2:
        if description_lines[1].startswith(f"> **Message ID:** [{original_message_id}]("):
            return True
    return False

async def handle_message(modlog_message: discord.Message, proxy_id: int):
    for embed in modlog_message.embeds:
        embed: discord.Embed
        if does_message_match(proxy_id, embed):
            await modlog_message.delete()
            if proxy_channel:
                embed.title = "Message Proxied"
                embed.color = discord.Color.blue() # noqa
                if client.get_channel(proxy_channel):
                    await client.get_channel(proxy_channel).send(embed=embed)

client.run(token)