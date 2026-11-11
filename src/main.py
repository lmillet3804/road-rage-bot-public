import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import utils.dataWrapper
import asyncio
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

load_dotenv()

PREFIX = os.getenv('PREFIX')
TOKEN = os.getenv('TOKEN')
MODE = os.getenv('MODE')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix=PREFIX, intents=intents, case_insensitive=True)

bot.dw = utils.dataWrapper.DataWrapper()

bot.ids = {
    "channels":{},
    "roles":{}
}

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Bot is running!")
        else:
            self.send_response(404)
            self.end_headers()
    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

def run_web_server():
    server_address = ("", 8080)  # Listen on all interfaces, port 8080
    httpd = HTTPServer(server_address, SimpleHTTPRequestHandler)
    print("Web server running on port 8080")
    httpd.serve_forever()

class MyHelpCommand(commands.MinimalHelpCommand):
    async def send_bot_help(self, mapping):
        embed = discord.Embed(
            title="Bot Commands",
            description="Here are all available commands:",
            color=discord.Color.blurple()
        )
        
        for cog, commands_list in mapping.items():
            filtered = await self.filter_commands(commands_list)
            command_signatures = [self.get_command_signature(c) for c in filtered]
            
            if command_signatures:
                cog_name = getattr(cog, "qualified_name", "No Category")
                embed.add_field(
                    name=cog_name,
                    value="\n".join(command_signatures),
                    inline=False
                )
        
        channel = self.get_destination()
        await channel.send(embed=embed)
    
    async def send_command_help(self, command):
        embed = discord.Embed(
            title=f"Command: {command.name}",
            color=discord.Color.blurple()
        )
        
        # Add command signature (usage)
        embed.add_field(
            name="Usage",
            value=f"`{self.get_command_signature(command)}`",
            inline=False
        )
        
        # Add aliases if they exist
        if command.aliases:
            embed.add_field(
                name="Aliases",
                value=", ".join(f"`{alias}`" for alias in command.aliases),
                inline=False
            )
        
        # Add description
        if command.help:
            embed.add_field(
                name="Description",
                value=command.help,
                inline=False
            )
        
        channel = self.get_destination()
        await channel.send(embed=embed)
    
    async def send_group_help(self, group):
        embed = discord.Embed(
            title=f"Command Group: {group.name}",
            description=group.help or "No description available.",
            color=discord.Color.blurple()
        )
        
        filtered = await self.filter_commands(group.commands, sort=True)
        for command in filtered:
            embed.add_field(
                name=self.get_command_signature(command),
                value=command.help or "No description available.",
                inline=False
            )
        
        channel = self.get_destination()
        await channel.send(embed=embed)
    
    def get_command_signature(self, command):
        return f"{self.context.clean_prefix}{command.name} {command.signature}"

bot.help_command = MyHelpCommand()

bot.prefix = PREFIX

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} with prefix {PREFIX} in {MODE} mode")

    if MODE == "production":
        await bot.change_presence(
            status=discord.Status.online,
            activity=discord.Game(f"{PREFIX}help")
        )
    guild = bot.get_guild(bot.ids["guild"])
    if guild is None:
        raise RuntimeError("Bot is not in the guild or GUILD_ID is wrong")
    roles = guild.roles

    num_teams = int(os.getenv("NUM_TEAMS", 3))

    for i in range(1, num_teams + 1):
        team_name = os.getenv(f"TEAM_{i}_NAME")
        if team_name not in roles:
            raise ValueError(f"Role '{team_name}' not found in the server. Please create the role and try again.")
        if team_name:
            role = [roles for roles in guild.roles if roles.name == team_name][0]
            players = [member.name for member in role.members]
            bot.dw.add_team(team_name=team_name, players=players)

    for team in bot.dw.get_teams():
        bot.dw.populate_active_road_challenges(team, no_curses=True)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("Command not found. Please check the command name.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("You missed a required argument. Please check the command usage.")
    elif isinstance(error, ValueError):
        await ctx.send(f"Error: {error}")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("Please provide the correct argument type.")
    else:
        await ctx.send(f"An unexpected error occurred: {error}")

@bot.event
async def on_message(message):
    if isinstance(message.channel, discord.DMChannel):
        await message.author.send("Commands are not supported in DMs. Please use your team channel in the server.")
        return

    await bot.process_commands(message)

async def load_cogs():
    for filename in os.listdir("./src/cogs"):
        if filename.endswith(".py"):
            await bot.load_extension(f"cogs.{filename[:-3]}")
    print(f"Loaded {len(bot.cogs)} cogs and {len(bot.commands)} commands")



async def run_bot():
    async with bot:
        await load_cogs()
        await bot.start(TOKEN)

async def check_data():
    await bot.wait_until_ready()
    while True:
        duel_wait_minutes = 30 if os.getenv('MODE') == 'production' else 1
        penalty_minutes = 30 if os.getenv('MODE') == 'production' else 1
        duels = bot.dw.get_duels()
        for duel in duels:
            if duel['status'] == 'waiting' and time.time() - duel['timestamp'] > (duel_wait_minutes-1) * 60:
                challenge1, challenge2 = bot.dw.move_duel_to_pending(duel)
                channel = bot.get_channel(bot.ids["channels"][duel['team2'].lower()])
                embed = discord.Embed(
                    title="Choose Duel Challenge",
                    description=f":warning: Your team has been challenged to a duel by **{duel['team1']}** in **{duel['city']}**! Please choose one of the following challenges within the next 60 seconds with the command `{PREFIX}duel choose <challenge_number>`. Otherwise a challenge will be randomly selected:\n\n:one: {challenge1['description']}\n\n:two: {challenge2['description']}",
                    color=discord.Color.orange()
                )
                await channel.send(embed=embed)
                channel = bot.get_channel(bot.ids["channels"][duel['team1'].lower()])
                embed = discord.Embed(
                    title="Duel Challenges",
                    description=f":warning: The two possible challenges for your duel against **{duel['team2']}** in **{duel['city']}** are as follows:\n\n:one: {challenge1['description']}\n\n:two: {challenge2['description']}\n\n The challenge will begin in 60 seconds.", 
                    color=discord.Color.orange()
                )
                await channel.send(embed=embed)
            if duel['status'] == 'pending' and time.time() - duel['timestamp'] > duel_wait_minutes * 60:
                challenge = bot.dw.activate_duel(duel)
                channel = bot.get_channel(bot.ids["channels"]["announcements"])
                await channel.send(f":crossed_swords: <@&{bot.ids['roles'][duel['team1'].lower()]}> and  <@&{bot.ids['roles'][duel['team2'].lower()]}> are fighting a duel in **{duel['city']}**! The challenge is as follows:\n\n{challenge['description']}")
        penalties = bot.dw.get_penalties()
        for penalty in penalties:
            if time.time() - penalty['timestamp'] > penalty_minutes * 60:
                channel = bot.get_channel(bot.ids["channels"][penalty['team'].lower()])
                bot.dw.remove_penalty(penalty['team'])
                await channel.send(":tada: Your team's penalty time is over! You can now continue the game as normal.")         
        await asyncio.sleep(60)

async def main():
    await asyncio.gather(run_bot(), check_data())

def populate_ids():
    bot.ids["guild"] = int(os.getenv("GUILD_ID"))
    bot.ids["channels"]["announcements"] = int(os.getenv("ANNOUNCEMENT_CHANNEL_ID"))

    num_teams = int(os.getenv("NUM_TEAMS", 3))
    for i in range(1, num_teams + 1):
        bot.ids["channels"][os.getenv(f"TEAM_{i}_NAME").lower()] = int(os.getenv(f"TEAM_{i}_CHANNEL_ID"))
        bot.ids["roles"][os.getenv(f"TEAM_{i}_NAME").lower()] = int(os.getenv(f"TEAM_{i}_ROLE_ID"))

    bot.ids["devs"] = [int(x) for x in os.getenv("DEV_IDS", "").split(",") if x]


if __name__ == "__main__":
    web_server_thread = Thread(target=run_web_server, daemon=True)
    web_server_thread.start()
    populate_ids()

    asyncio.run(main())
