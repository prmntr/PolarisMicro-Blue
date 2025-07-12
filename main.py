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
from tictactoe import TicTacToe, get_ai_move

# KNOWMO: Created by Team Blue

# load the discord token from .env
load_dotenv()
token = os.getenv('DISCORD_TOKEN')

user_ping_tasks = {}
user_language = {}
tictactoe_games = {}

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

# the bot is prepared


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

# for demo


@bot.event
async def on_message(message):
    if (message.author.id != bot.user.id) and (message.content == 'hello'):
        await message.channel.send(f'Hey {message.author}! Are you ready to show the judges what we have?')

    # allows bot to continue looking for msgs
    await bot.process_commands(message)


# intelligent gemini
@bot.command()
async def knowmo(ctx):
    print("learn called")

    # so the bot can look like it's typing
    async with ctx.typing():
        # prompt
        messages = [
            f"You are a helpful bot chatting with {ctx.author.name}. "
            "The above is what they have said previously. "
            "Respond in the language they sent the majority of messages in unless stated otherwise by the user. "
            "Create a response for their most recent message. "
            "Don't add 'you sent:' to the start of your response, that's just for you to keep track of who's sending what. "
            "!learn is how the user communicates with you, if their message doesn't have it, you won't see it. "
            "Also, keep it so it can fit in a single discord message, so not too long."
        ]

        # gets context
        async for msg in ctx.channel.history(limit=50, oldest_first=False):
            # include only !learn messages from the user
            if msg.author == ctx.author and msg.content.startswith("!knowmo"):
                messages.append("User sent: " + msg.content)

            # only include bot responses that replied to the user
            elif (
                msg.author == ctx.me and
                (msg.reference and msg.reference.resolved and msg.reference.resolved.author == ctx.author)
            ):
                messages.append("You sent: " + msg.content)

        # reverse it
        messages.reverse()
        prompt = "\n".join(messages)

        # debug
        print(prompt)

        # try catch to input prompt; no thinking
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    thinking_config=types.ThinkingConfig(thinking_budget=0)
                ),
            )
            print("response created")
        except Exception as e:
            print(f"Error: {e}")
            await ctx.reply("An error occurred.")
            return

        # parse the actual response
        text = response.candidates[0].content.parts[0].text

        await ctx.reply(text)
        print("response sent")


@bot.command()
async def search(ctx, *, query: str):
    """Searches Google and provides a response from Gemini."""
    async with ctx.typing():
        try:
            grounding_tool = types.Tool(
                google_search=types.GoogleSearch()
            )
            # Configure generation settings
            config = types.GenerateContentConfig(
                tools=[grounding_tool]
            )

            # Make the request
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=f"You are a bot and the !search command was used. Run a google search and provide a response to the discord user's query: {query}. Keep this response under 1800 characters.",
                config=config,
            )

            # Print the grounded response
            print(response.text)

            await ctx.send(response.text)
        except Exception as e:
            print(f"Error: {e}")
            await ctx.send("An error occurred while searching.")


# simple sanity check
@bot.command()
async def ping(ctx):
    """Responds with Pong!"""
    await ctx.send('Pong!')


# remind the user to practice every day
@bot.command()
async def remind(ctx, hour: int):
    # error checking
    if (hour < 0) or (hour > 23):
        return await ctx.send("Please add a valid time (between 1 and 24 times). \nExample: !remind 14 \nThis reminds you to practice at 2PM.")
    user_id = ctx.author.id

    # if user already did this
    if user_id in user_ping_tasks:
        user_ping_tasks[user_id].cancel()
        del user_ping_tasks[user_id]

    # inner function to wait until the right time
    async def wait_until_hour_then_loop():
        await bot.wait_until_ready()
        now = datetime.now()
        target = now.replace(hour=hour, minute=0, second=0, microsecond=0)

        if target <= now:
            # schedule for next day if time has passed
            target += timedelta(days=1)

        wait_seconds = (target - now).total_seconds()
        await asyncio.sleep(wait_seconds)

        # send first ping
        await ctx.send(f"<@{user_id}> it's {hour:02d}:00; time to practice!")

        # now repeat every 24 hours
        while True:
            await asyncio.sleep(86400)  # 24 hours
            await ctx.send(f"<@{user_id}> it's {hour:02d}:00 again; time to practice!")

    # start this in the background
    task = asyncio.create_task(wait_until_hour_then_loop())
    user_ping_tasks[user_id] = task

    # tell the user it suceeded
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


# check for pings
@bot.command()
async def myreminders(ctx):
    user_id = ctx.author.id
    if user_id in user_ping_tasks:
        await ctx.send(f"You have a daily reminder set at {user_ping_tasks[user_id].get_coro().cr_frame.f_locals.get('hour', 'unknown')}:00.")
    else:
        await ctx.send("You don't have any active reminders.")
    return ctx.send('')


# simple help
@bot.command()
async def help(ctx):
    await ctx.send(
        "**🤖 Knowmo Command List**\n\n"
        "**Learning**\n"
        "`!knowmo` - Chat with your AI learning buddy!\n"
        "`!summarize` - Summarize the last 50 messages in the chat\n"
        "`!search` - Search the web for up to date information\n"
        "`!remind [hour]` - Get a daily reminder to practice at the specified hour\n"
        "`!stop` - Stop all daily reminders\n"
        "`!myreminders` - See your active reminders\n\n"

        "**Fun Stuff**\n"
        "`!eightball [question]` - Roll an 8 ball\n"
        "`!roll` - Roll a die\n"
        "`!meme` - Get a high-quality meme from Reddit\n"
        "`!poll [title, options]` - Create a poll\n\n"

        "**Miscellaneous**\n"
        "`!ping` - Ping the bot\n"
        "`!help` - Show this command list"
    )


# set the primary language
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


# fun poll command
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


# summarize the coversation up to 50 msgs
@bot.command()
async def summarize(ctx):
    async with ctx.typing(): 
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

# simple random 8ball
@bot.command()
async def eightball(ctx, *, question: str):
    if not question:
        await ctx.send("Whats the question for today? Eg !eightball what do I do today")
    responses = [
        "It is certain.",
        "It is decidedly so.",
        "Without a doubt.",
        "Yes 100%",
        "You may rely on it.",
        "As I see it, yes.",
        "Most likely.",
        "Outlook good.",
        "Yes.",
        "Signs point to yes.",
        "Reply hazy, try again.",
        "Ask again later.",
        "Better not tell you now.",
        "Cannot predict now.",
        "Concentrate and ask again.",
        "Don't count on it.",
        "My reply is no.",
        "My sources say no.",
        "Outlook not so good.",
        "Very doubtful."
    ]
    await ctx.send(f"🎱 {random.choice(responses)}")


# another easy roll command
@bot.command()
async def roll(ctx, sides: int = 6):
    result = random.randint(1, sides)
    await ctx.send(f"🎲 You rolled a {result} (1-{sides})")


@bot.command()
async def tictactoe(ctx, move: int = None):
    channel_id = ctx.channel.id
    if move is None:
        if channel_id in tictactoe_games:
            await ctx.send("A game is already in progress. Make a move from 1-9.")
        else:
            tictactoe_games[channel_id] = TicTacToe()
            await ctx.send("New Tic-Tac-Toe game started! You are X. Make your move by sending `!tictactoe [1-9]`.")
            await ctx.send(tictactoe_games[channel_id].get_board_string())
        return

    if channel_id not in tictactoe_games:
        await ctx.send("No game in progress. Start a new game with `!tictactoe`.")
        return

    game = tictactoe_games[channel_id]
    move -= 1  # Adjust for 0-based index

    if not (0 <= move <= 8):
        await ctx.send("Invalid move. Please choose a number between 1 and 9.")
        return

    if not game.make_move(move, 'X'):
        await ctx.send("This spot is already taken. Try again.")
        return

    if game.current_winner:
        await ctx.send(game.get_board_string())
        await ctx.send("You win!")
        del tictactoe_games[channel_id]
        return

    if not game.empty_squares():
        await ctx.send(game.get_board_string())
        await ctx.send("It's a tie!")
        del tictactoe_games[channel_id]
        return

    # AI's turn
    ai_move = get_ai_move(game)
    game.make_move(ai_move, 'O')

    if game.current_winner:
        await ctx.send(game.get_board_string())
        await ctx.send("AI wins!")
        del tictactoe_games[channel_id]
        return

    if not game.empty_squares():
        await ctx.send(game.get_board_string())
        await ctx.send("It's a tie!")
        del tictactoe_games[channel_id]
        return

    await ctx.send(game.get_board_string())


# get a fun meme from reddit
@bot.command()
async def meme(ctx):
    try:
        print("1")
        subreddit = reddit.subreddit("memes+dankmemes+wholesomememes")
        print("2")
        posts = list(subreddit.hot(limit=50))
        print("3")
        post = random.choice(
            [p for p in posts if not p.stickied and p.url.endswith(('.jpg', '.png', '.jpeg'))])
        await ctx.send("Here's that great meme you wanted!")
        embed = discord.Embed(
            title=post.title, url=f"https://reddit.com{post.permalink}", color=discord.Color.random())
        embed.set_image(url=post.url)
        embed.set_footer(
            text=f"👍 {post.score} | 💬 {post.num_comments} comments | 🧠 r/{post.subreddit}")

        await ctx.send(embed=embed)
    except Exception as e:
        print(f"Error: {e}")
        await ctx.send("😵‍💫 I tried to steal a meme from Reddit but slipped on a banana peel.\n"
                       "Try again in a bit - I promise I'll meme responsibly next time! 🤖📷")

# simple error handling that will never be triggered
if token:
    bot.run(token, log_handler=handler, log_level=logging.DEBUG)
else:
    logging.error("DISCORD_TOKEN not found in environment variables.")
