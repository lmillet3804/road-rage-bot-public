from discord.ext import commands
from utils.lists import get_city
from utils.discord import confirm

class Transfer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="transfer", aliases=["give", "donate"])
    async def transfer(
        self,
        ctx,
        action=commands.parameter(default=None, description="The item to transfer; either a city or coins."),
        challenge_team_name=commands.parameter(default=None, description="The team to transfer the item to."),
        value=commands.parameter(default=None, description="The # of coins or the city name to give.")
    ):
        """Give coins or a city to another team."""

        return await ctx.send(":warning: This command is deprecated")

async def setup(bot):
    await bot.add_cog(Transfer(bot))