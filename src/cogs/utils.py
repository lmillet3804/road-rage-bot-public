from discord.ext import commands

class Utils(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="ping", aliases=["pong"])
    async def ping(self, ctx):
        """Check the bot's latency."""
        
        latency = round(self.bot.latency * 1000)
        await ctx.send(f":ping_pong: Pong! {latency}ms")

async def setup(bot):
    await bot.add_cog(Utils(bot))
