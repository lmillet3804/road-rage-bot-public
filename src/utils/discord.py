import asyncio

async def confirm(bot, ctx, message):
    """Confirm an action with the user."""

    await ctx.send(message)
    
    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() in ["yes", "no", "y", "n"]
    
    try:
        response = await bot.wait_for("message", check=check, timeout=30)
        return response.content.lower() in ["yes", "y"]
    except asyncio.TimeoutError:
        await ctx.send(":hourglass: Confirmation timed out. Please try again.")
        return False