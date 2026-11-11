import discord
from discord.ext import commands
from utils.lists import split_array, get_city, get_team_name_from_roles
from utils.discord import confirm

class City(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _get_team_name(self, ctx):
        return get_team_name_from_roles(ctx.author.roles, self.bot.dw.get_team_names())

    @commands.command(name="city", aliases=["cities"])
    async def city(
        self,
        ctx,
        city=commands.parameter(default=None, description="The city to list information for.")
    ):
        """Lists information about a given city."""

        cities = self.bot.dw.get_cities()

        if not city:
            city_list = [f"{c['city']}, {c['state']}" for c in cities]
            city_list = sorted(city_list)

            embed = discord.Embed(
                title="City Challenges",
                description=f"There are **{len(city_list)}** available cities with challenges.",
                color=discord.Color.blue()
            )

            city_lists = split_array(city_list)
            for city_list in city_lists:
                embed.add_field(name="", value="\n".join(city_list), inline=True)

            await ctx.send(embed=embed)
        else:
            city_names = [c["city"].lower() for c in cities]
            city_name = get_city(city_names, city.lower())

            if not city_name:
                await ctx.send(f'City `{city}` not found.')
                return
            
            city = cities[city_names.index(city_name)]

            city_owner = self.bot.dw.get_city_owner(city['city'])
            ownernship_str = f"Claimed by {city_owner}" if city_owner else "Unclaimed"
            
            embed = discord.Embed(
                title=f"Challenges for {city['city']}, {city['state']}",
                description=city['challenges'],
                color=discord.Color.blue()
            )
            embed.set_footer(text=f"{city['points']} points, {ownernship_str}")

            await ctx.send(embed=embed)
        
    @commands.command(name="cityChallenge", aliases=["cc"])
    async def cityChallenge(
        self,
        ctx,
        action=commands.parameter(default=None, description="The action to perform; either draw, complete, or fail.")
    ):
        """Draw, claim, or fail one of the 3 active city challenges."""

        if action == "draw":
            team_name = self._get_team_name(ctx)
            if not team_name:
                return await ctx.send(":sob: You must be part of a team to draw a city challenge.")
            if self.bot.dw.is_rest_period_active_by_team_name(team_name):
                return await ctx.send(":warning: Your team is currently in a rest period and cannot draw or complete city challenges. Please end your rest period before drawing a new challenge.")
            if self.bot.dw.team_has_penalty(team_name):
                return await ctx.send(":warning: Your team is currently under a penalty and cannot draw or complete city challenges. Please wait until your penalty time is over.")                
            if(self.bot.dw.get_active_city_challenge_by_team_name(team_name) is not None):
                return await ctx.send(":warning: You already have an active city challenge. Please complete it before drawing a new one.")
            if(self.bot.dw.get_coins_by_team_name(team_name) < 100):
                return await ctx.send(":warning: You need at least 100 coins to draw a city challenge.")
            if(self.bot.dw.draw_city_challenge(team_name) is False):
                return await ctx.send(":warning: Error drawing a city challenge.")

            active_city_challenge = self.bot.dw.get_active_city_challenge_by_team_name(team_name)
            embed = discord.Embed(
                title="New City Challenge:",
                description=f":bangbang:You have drawn a new city challenge:\n\n{active_city_challenge['description']}\n\n",
                color=discord.Color.blue()
            )
            if active_city_challenge['time_limit'] != -1:
                embed.set_footer(text=f"You have {active_city_challenge['time_limit']} minutes to complete this challenge. Time starts now!")

            await ctx.send(embed=embed)
        elif action == "complete":
            team_name = self._get_team_name(ctx)
            if len(team_name) == 0:
                await ctx.send(":sob: You must be part of a team to complete a city challenge.")
                return
            if self.bot.dw.team_has_penalty(team_name):
                return await ctx.send(":warning: Your team is currently under a penalty and cannot draw or complete city challenges. Please wait until your penalty time is over.")
            current_challenge = self.bot.dw.get_active_city_challenge_by_team_name(team_name)
            if current_challenge is None:
                await ctx.send(":warning: Your team does not have an active city challenge to complete.")
                return
            
            confirmation = await confirm(self.bot, ctx, f"Are you sure you have completed the following challenge?\n\n> {current_challenge['description']}")
            if not confirmation:
                return await ctx.send(":x: Challenge completion cancelled.")
            
            did_complete = self.bot.dw.complete_active_city_challenge(team_name)

            if did_complete:
                embed = discord.Embed(
                    title="City Challenge Completed",
                    description=current_challenge['description'],
                    color=discord.Color.blue()
                )
                embed.set_footer(text="Don't forget to claim your city!")
                await ctx.send(embed=embed)

                announcements_channel = self.bot.get_channel(self.bot.ids["channels"]["announcements"])
                announcements_embed = discord.Embed(
                    title="City Challenge Completed",
                    description=f"**{team_name}** has completed the following city challenge:\n\n{current_challenge['description']}",
                    color=discord.Color.blue()
                )
                await announcements_channel.send(embed=announcements_embed)
            else:
                await ctx.send(":x: Challenge could not be completed.")
        elif action == "fail":
            team_name = self._get_team_name(ctx)
            if len(team_name) == 0:
                await ctx.send(":sob: You must be part of a team to fail a city challenge.")
                return
            if self.bot.dw.team_has_penalty(team_name):
                return await ctx.send(":warning: Your team is currently under a penalty and cannot draw or complete city challenges. Please wait until your penalty time is over.")
            current_challenge = self.bot.dw.get_active_city_challenge_by_team_name(team_name)
            if current_challenge is None:
                await ctx.send(":warning: Your team does not have an active city challenge to fail.")
                return

            confirmation = await confirm(self.bot, ctx, f"Are you sure you have failed the following challenge?\n\n> {current_challenge['description']}\n\nThis will impose a time penalty and you will need to draw a new challenge.")
            if not confirmation:
                return await ctx.send(":x: Challenge fail cancelled.")
            
            did_fail = self.bot.dw.fail_active_city_challenge(team_name)
            if did_fail:
                embed = discord.Embed(
                    title="City Challenge Failed",
                    description=current_challenge['description'],
                    color=discord.Color.blue()
                )
                embed.set_footer(text="You have lost 100 coins and are now under a 30 minute time penalty. During this time you cannot complete any road or city challenges nor claim any other bonuses of any kind.")
                await ctx.send(embed=embed)

                announcements_channel = self.bot.get_channel(self.bot.ids["channels"]["announcements"])
                announcements_embed = discord.Embed(
                    title="City Challenge Failed",
                    description=f"**{team_name}** has failed the following city challenge:\n\n{current_challenge['description']}\n\nThey are currently under a 30 minute time penalty.",
                    color=discord.Color.blue()
                )
                await announcements_channel.send(embed=announcements_embed)
        elif action == "list":
            team_name = self._get_team_name(ctx)
            if len(team_name) == 0:
                await ctx.send(":sob: You must be part of a team to view your city challenge.")
                return
            current_challenge = self.bot.dw.get_active_city_challenge_by_team_name(team_name)
            if current_challenge is None:
                await ctx.send(":warning: Your team does not have an active city challenge.")
                return
            
            embed = discord.Embed(
                title="Active City Challenge:",
                description=current_challenge['description'],
                color=discord.Color.blue()
            )
            
            await ctx.send(embed=embed)
        else:
            await ctx.send(':warning: Invalid action. Use `list`, `draw`, `complete`, or `fail`.')

async def setup(bot):
    await bot.add_cog(City(bot))
