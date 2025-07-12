import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv
import os
from google import genai
from google.genai import types

# load the discord token from .env
load_dotenv()
token = os.getenv('DISCORD_TOKEN')

# initializes intents that the bot has and allows the bot to log to 'discord.log'
# note the log file is overwritten every time bot is created
handler = logging.FileHandler(
    filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.messages = True

# creates the bot with some params
bot = commands.Bot(command_prefix='!', intents=intents,
                   help_command=None, case_insensitive=True)

# Creates the gemini bot
client = genai.Client()

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
async def intelligence(ctx):
    print("intelligence called")

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=ctx.message.content,
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(
                    thinking_budget=0)  # Disables thinking
            ),
        )
        print("response created")
    except Exception as e:
        print(f"Error: {e}")
        await ctx.send("An error occurred.")

    text = response.candidates[0].content.parts[0].text

    await ctx.send(text)
    print("response sent")


@bot.command()
async def ping(ctx):
    """Responds with Pong!"""
    await ctx.send('Pong!')

# simple error handling that will never be triggered
if token:
    bot.run(token, log_handler=handler, log_level=logging.DEBUG)
else:
    logging.error("DISCORD_TOKEN not found in environment variables.")
