import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv
import os
from google import genai
from google.genai import types
import asyncio
from discord.ext import tasks
from datetime import datetime, timedelta
import random
from utils import reddit

# load the discord token from .env
load_dotenv()
token = os.getenv('DISCORD_TOKEN')

user_ping_tasks = {}
user_language = {}

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


# intelligent gemini
@bot.command()
async def learn(ctx):
    print("learn called")
    async with ctx.typing():
        messages = ["You are a helpful bot chatting with {msg.author}. The above is what they have said previously. Respond in the language they sent the majority of messages in unless stated otherwise by the user. Create a response for their most recent message. Don't add 'you sent:' to the start of your response, that's just for you to keep track of who's sending what. !learn is how the user communicates with you, if their message doesn't have it, you won't see it."]

        async for msg in ctx.channel.history(limit=50, oldest_first=False):
            if msg.author == ctx.author and msg.content.startswith("!learn"):
                messages.append("User sent: " + msg.content)
            elif msg.author == ctx.me and not msg.content.startswith("List of commands:"):
                messages.append("You sent: " + msg.content)

            if len(messages) == 20:
                break

        messages.reverse()
        prompt = "\n".join(messages)
        print(prompt)

        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
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

# simple sanity check
@bot.command()
async def ping(ctx):
    """Responds with Pong!"""
    await ctx.send('Pong!')


@bot.command()
async def remind(ctx, hour: int):
    if (hour < 0) or (hour > 23):
        return await ctx.send("Please add a valid time (between 1 and 24 times). \nExample: !remind 14 \nThis reminds you to practice at 2PM.")
    user_id = ctx.author.id

    if user_id in user_ping_tasks:
        user_ping_tasks[user_id].cancel()
        del user_ping_tasks[user_id]

    # Inner function to wait until the right time
    async def wait_until_hour_then_loop():
        await bot.wait_until_ready()
        now = datetime.now()
        target = now.replace(hour=hour, minute=0, second=0, microsecond=0)
        if target <= now:
            # schedule for next day if time has passed
            target += timedelta(days=1)

        wait_seconds = (target - now).total_seconds()
        await asyncio.sleep(wait_seconds)

        # Send first ping
        await ctx.send(f"<@{user_id}> it's {hour:02d}:00; time to practice!")

        # Now repeat every 24 hours
        while True:
            await asyncio.sleep(86400)  # 24 hours
            await ctx.send(f"<@{user_id}> it's {hour:02d}:00 again; time to practice!")

    # Start background task
    task = asyncio.create_task(wait_until_hour_then_loop())
    user_ping_tasks[user_id] = task

    await ctx.send(f"Okay <@{user_id}>, I'll ping you every day at {hour:02d}:00.")


# stop all daily pings
@bot.command()
async def stop(ctx):
    user_id = ctx.author.id
    if user_id in user_ping_tasks:
        user_ping_tasks[user_id].cancel()
        del user_ping_tasks[user_id]
        await ctx.send("Your daily ping has been stopped.")
    else:
        await ctx.send("You don't have any active pings.")


@bot.command()
async def myreminders(ctx):
    user_id = ctx.author.id
    if user_id in user_ping_tasks:
        await ctx.send(f"You have a daily reminder set at {user_ping_tasks[user_id].get_coro().cr_frame.f_locals.get('hour', 'unknown')}:00.")
    else:
        await ctx.send("You don't have any active reminders.")
    return ctx.send('')


@bot.command()
async def help(ctx):
    await ctx.send('List of commands: \n\n!help: Returns this help menu \n!learn: Chat with your AI learning buddy! \n!ping: Ping the bot. \n!quiz: Quiz yourself on the vocabulary you have learned! \n!remind (hour): Get a reminder to practice every day at this hour. \n!stop : Stops all daily reminders. \n!myreminders: See your active reminders.  \n!setlanguage (language): Let the AI know what languages you are focusing on. \n!poll: Create a poll! \n!summarize: Summarize the last 50 messages in the chat. \n!eightball (question): For indecisive moments.\n!roll: Roll a die.\n!meme: Get a high quality meme from Reddit!')


@bot.command()
async def setlanguage(ctx):
    async with ctx.typing():
        print("language called")
        prompt = ctx.message.content + \
            "You are a helpful bot chatting with {msg.author}. The above shows the input recieved from the user. If the user's input is the languages they are learning, return the languages they're learning along with anything else they said about their language. If the input is anything other than this, return the exact string 'Invalid input'"
        print(prompt)

        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
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
        if text != "Invalid input":
            user_language += text
            await ctx.send("Thanks! This is what we've saved. \n" + text)
        else:
            await ctx.send("This is an invalid response. Try again.")
        print("response sent")


@bot.command()
async def poll(ctx, question: str, *options):
    if len(options) < 2:
        return await ctx.send("You need at least two options.")
    emojis = ['🇦', '🇧', '🇨', '🇩', '🇪', '🇫']
    desc = ""
    for i, option in enumerate(options):
        desc += f"{emojis[i]} {option}\n"
    embed = discord.Embed(title=question, description=desc)
    msg = await ctx.send(embed=embed)
    for i in range(len(options)):
        await msg.add_reaction(emojis[i])


@bot.command()
async def summarize(ctx):
    async with ctx.typing():  # Shows typing indicator
        messages = []
        async for msg in ctx.channel.history(limit=50, oldest_first=False):
            if msg.author != bot.user:
                messages.append(f"{msg.author.name}: {msg.content}")
        messages.reverse()
        prompt = "Summarize this chat:\n" + "\n".join(messages)

        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
            summary = response.candidates[0].content.parts[0].text
            await ctx.send("📋 Summary:\n" + summary)
        except Exception as e:
            print(f"Error: {e}")
            await ctx.send("Something went wrong while summarizing.")


@bot.command()
async def eightball(ctx, *, question: str):
    if not question:
        await ctx.send("Whats the question for today? Eg !eightball what do I do today")
    responses = ["Yes", "No", "Maybe", "Definitely", "Absolutely not", "Ask again later"]
    await ctx.send(f"🎱 {random.choice(responses)}")


@bot.command()
async def roll(ctx, sides: int = 6):
    result = random.randint(1, sides)
    await ctx.send(f"🎲 You rolled a {result} (1-{sides})")

@bot.command()
async def meme(ctx):
    try:
        subreddit = reddit.subreddit("memes+dankmemes+wholesomememes")
        posts = list(subreddit.hot(limit=50))
        post = random.choice([p for p in posts if not p.stickied and p.url.endswith(('.jpg', '.png', '.jpeg'))])

        embed = discord.Embed(title=post.title, url=f"https://reddit.com{post.permalink}", color=discord.Color.random())
        embed.set_image(url=post.url)
        embed.set_footer(text=f"👍 {post.score} | 💬 {post.num_comments} comments | 🧠 r/{post.subreddit}")

        await ctx.send(embed=embed)
    except Exception as e:
        print(f"Error: {e}")
        await ctx.send("😵‍💫 I tried to steal a meme from Reddit but slipped on a banana peel.\n"
            "Try again in a bit — I promise I’ll meme responsibly next time! 🤖📷")


# simple error handling that will never be triggered
if token:
    bot.run(token, log_handler=handler, log_level=logging.DEBUG)
else:
    logging.error("DISCORD_TOKEN not found in environment variables.")
