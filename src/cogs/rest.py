from discord.ext import commands
from utils.lists import get_team_name_from_roles

class Rest(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name="rest")
    async def rest(self, ctx, action=commands.parameter(description="The action to perform: start or end.")):
        """Start the rest period."""
        team_name = get_team_name_from_roles(ctx.author.roles, self.bot.dw.get_team_names())
        if action == "start":
            if self.bot.dw.is_rest_period_active_by_team_name(team_name):
                await ctx.send(":warning: The rest period is already active.")
                return
            self.bot.dw.set_rest_period_active_by_team_name(team_name, True)
            await ctx.send(":white_check_mark: The rest period has been started.")

            announcements_channel = self.bot.get_channel(self.bot.ids["channels"]["announcements"])
            await announcements_channel.send(f":sleeping: The rest period has been started for {team_name}.")
        elif action == "end":
            if not self.bot.dw.is_rest_period_active_by_team_name(team_name):
                await ctx.send(":warning: The rest period is not active.")
                return
            self.bot.dw.set_rest_period_active_by_team_name(team_name, False)
            await ctx.send(":white_check_mark: The rest period has been ended.")

            announcements_channel = self.bot.get_channel(self.bot.ids["channels"]["announcements"])
            await announcements_channel.send(f":sun_with_face: The rest period has been ended for {team_name}.")
        else:
            await ctx.send(":warning: Invalid action. Please use 'start' or 'end'.")

async def setup(bot):
    await bot.add_cog(Rest(bot))