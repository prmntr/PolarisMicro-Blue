import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv
import os

# load the discord token from .env
load_dotenv()
token = os.getenv('DISCORD_TOKEN')

# initializes intents that the bot has and allows the bot to log to 'discord.log'
# note the log file is overwritten every time bot is created
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.messages =  True

# creates the bot with some params
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None, case_insensitive=True)

# sets the logging level and adds the handler
logging.basicConfig(level=logging.INFO, handlers=[handler])

# 
@bot.event
async def on_ready():
    logging.info(f'Logged in as {bot.user.name} - {bot.user.id}')
    print(f'Logged in as {bot.user.name} - {bot.user.id}')

# logs when a member join
@bot.event
async def on_member_join(member):
    logging.info(f'New member joined: {member.name} - {member.id}')
    await member.send(f"welcome to the server {member.name} {member.id}")
    print(f'New member joined: {member.name} - {member.id}')

# when any message unspecificed happsnt the bot responds hello
@bot.event
async def on_message(message):
    if (message.author.id != bot.user.id) and (message.content == 'hello'):
        await message.channel.send(f'Hello, {message.author}')
    
    # allows bot to continue looking for msgs
    await bot.process_commands(message)


@bot.command()
async def ping(ctx):
    """Responds with Pong!"""
    await ctx.send('Pong!')

# simple error handling that will never be triggered
if token:
    bot.run(token, log_handler=handler, log_level=logging.DEBUG)
else:
    logging.error("DISCORD_TOKEN not found in environment variables.")