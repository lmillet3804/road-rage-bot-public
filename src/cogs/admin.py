from discord.ext import commands
import os
import sys
import psutil
from utils.discord import confirm
import re

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="reload")
    @commands.has_permissions(administrator=True)
    async def reload(
        self,
        ctx,
        cog = commands.parameter(default=None, description="The cog to reload.")
    ):
        """Reload a given cog, instead of restarting the bot."""

        if not cog:
            await ctx.send(":warning: Please provide a cog to reload.")
            return

        try:
            if f"cogs.{cog}" in self.bot.extensions:
                await self.bot.unload_extension(f"cogs.{cog}")
            await self.bot.load_extension(f"cogs.{cog}")

            await ctx.send(f":white_check_mark: Cog `{cog}` has been reloaded successfully.")
        except Exception as e:
            await ctx.send(f":warning: An error occurred while reloading `{cog}`: {e}")
    
    @commands.command(name="reset")
    @commands.has_permissions(administrator=True)
    async def reset(self, ctx):
        """Reset the game."""

        confirmation = await confirm(self.bot, ctx, ":warning: Are you sure you want to reset the game? This will delete all team data and challenges.")

        if confirmation:
            self.bot.dw.clear_game_data()
            
            roles = ctx.guild.roles
            num_teams = int(os.getenv("NUM_TEAMS", 3))

            for i in range(1, num_teams + 1):
                
                team_name = os.getenv(f"TEAM_{i}_NAME")
                if team_name not in [role.name for role in roles]:
                    raise ValueError(f"Role '{team_name}' not found in the server. Please create the role and try again.")
                if team_name:
                    role = [role for role in roles if role.name == team_name][0]
                    players = [member.name for member in role.members]
                    self.bot.dw.add_team(team_name=team_name, players=players)

            for team in self.bot.dw.get_teams():
                self.bot.dw.populate_active_road_challenges(team, no_curses=True)
            
            print(f"{ctx.author} reset the game.")
            await ctx.send(":white_check_mark: Game has been reset!")
        else:
            await ctx.send(":x: Reset cancelled.")
        
    @commands.command(name="kill")
    @commands.has_role("Developer")
    async def kill(self, ctx):
        """Kill the bot."""

        if not await confirm(self.bot, ctx, ":warning: Are you sure you want to shut down the bot?"):
            return await ctx.send(":x: Kill cancelled.")
        
        await ctx.send(":zzz: Shutting down...")
        print(f"{ctx.author} initiated a shutdown.")
        await self.bot.close()
    
    @commands.command(name="restart")
    @commands.has_role("Developer")
    async def restart(self, ctx):
        """Restart the bot."""

        if not await confirm(self.bot, ctx, ":warning: Are you sure you want to restart the bot?"):
            return await ctx.send(":x: Restart cancelled.")
        
        await ctx.send(":arrows_counterclockwise: Restarting...")
        print(f"{ctx.author} initiated a restart.")
        await restart_core()
    
    @commands.command(name="send")
    @commands.has_role("Developer")
    async def send(self, ctx, *args):
        """Send messages from the bot account."""

        if ctx.author.id not in self.bot.ids['devs']:
            return await ctx.send(":sunglasses: You do not have permission to use this command.")

        if not args:
            return await ctx.send(":warning: Please provide a message to send.")
        
        await ctx.message.delete()
        await ctx.send(" ".join(args))

    @commands.command(name="evaluate", aliases=["eval", "exec"])
    @commands.has_role("Developer")
    async def evaluate(self, ctx, *args):
        """Evaluate code."""

        if not args:
            return await ctx.send(":warning: Please provide a message to send.")
        
        jargs = " ".join(args)
        jargs = jargs.strip('`').strip()
        is_exec = True if ctx.invoked_with == "exec" else False
        is_exec = True if len(jargs.splitlines()) > 1 or re.search("try|while|import|class|def|await|\w\s=\s", jargs) != None else is_exec
        
        try:
            response = None
            if "await " in jargs:
                local_context = {
                    "bot": self.bot,
                    "ctx": ctx,
                }
                exec(
                    "async def __temp_exec():\n" +
                    "\n".join(f"    {line}" for line in jargs.splitlines()),
                    local_context,
                )
                await local_context["__temp_exec"]()
            elif is_exec:
                exec(jargs)
            else:
                response = eval(jargs)
            if not is_exec and len(str(response)) > 1800:
                await ctx.send(":nerd: It executed sucessfully, but is too large to be sent. So it will be sent in parts.")
                for i in range(0, len(str(response)), 1800):
                    await ctx.send(f"```{str(response)[i:i+1800]}```")
            else:
                await ctx.send(":nerd: Code executed successfully." if is_exec else f":nerd: Evaluated successfully with the following response.\n```{response}```")
        except Exception as e:
            await ctx.send(f":warning: An error occured during {'execution' if is_exec else 'evaluation'}!\n```{e}```")
    
    @commands.command(name="test",)
    @commands.has_role("Developer")
    async def test(self, ctx):
        """Do not execute this command"""
        
        confirmation = await confirm(self.bot, ctx, ":warning: Are you sure? You probably don't want to execute this command.")

        if confirmation:
            did_unclaim = self.bot.dw.unclaim_city_from_team('Team 3', 'Kansas City')
            await ctx.send(f"Unclaim result is {did_unclaim}")
        
async def restart_core():
    # taken from https://stackoverflow.com/questions/11329917/restart-python-script-from-within-itself
    try:
        pro = psutil.Process(os.getpid())
        for handler in pro.open_files() + pro.connections():
            os.close(handler.fd)
    except Exception as e:
        print(e)

    python = sys.executable
    os.execl(python, python, *sys.argv)

async def setup(bot):
    await bot.add_cog(Admin(bot))
