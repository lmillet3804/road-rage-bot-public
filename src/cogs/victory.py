import discord
from discord.ext import commands
from utils.lists import get_city, get_state, get_region_from_id, get_team_name_from_roles

class Victory(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="claim")
    async def claim(
        self,
        ctx,
        city=commands.parameter(default=None, description="The city to claim victory for.")
    ):
        """Claim victory for a given city."""
        
        if not city:
            await ctx.send(":warning: Please provide a city to claim victory for.")
            return

        cities = self.bot.dw.get_cities()
        city_names = [c["city"].lower() for c in cities]
        city_name = get_city(city_names, city.lower())

        if not city_name:
            await ctx.send(f':warning: City `{city}` not found.')
            return
        
        city = cities[city_names.index(city_name)]
        state = city['state']
        region = city['region']
        city_string = f"{city['city']}, {state}"

        team_name = get_team_name_from_roles(ctx.author.roles, self.bot.dw.get_team_names())

        if not team_name:
            await ctx.send(":sob: You must be part of a team to claim a city.")
            return

        if self.bot.dw.team_has_penalty(team_name):
            return await ctx.send(":warning: Your team is currently under a penalty and cannot claim cities. Please wait until your penalty time is over.")

        city_owner = self.bot.dw.get_city_owner(city['city'])

        if city_owner == team_name:
            await ctx.send(f":crown: You already own **{city_string}**.")
            return    

        if city_owner != None:
            await ctx.send(f":skull: **{city_string}** is already claimed by **{city_owner}**.")
            return

        did_claim = self.bot.dw.claim_city_for_team(team_name, city['city'])
        if did_claim:
            await ctx.send(f":tada: Victory claimed for **{city_string}**. Congratulations!")

            announcements_channel = self.bot.get_channel(self.bot.ids["channels"]["announcements"])
            await announcements_channel.send(f":tada: **{team_name}** has claimed victory for **{city_string}**!")

            region_owner, num_cities = self.bot.dw.get_region_owner(region)
            if region_owner == team_name:
                return

            claimed_cities = self.bot.dw.get_team_cities_claimed_by_region(team_name)[region]

            region_name = get_region_from_id(region)

            if claimed_cities > num_cities:
                if region_owner is not None:
                    self.bot.dw.unclaim_region_from_team(region_owner, region)
                    self.bot.dw.claim_region_for_team(team_name, region)
                    await ctx.send(f":tada: **{region_name}** is now claimed by **{team_name}**!")
                    await announcements_channel.send(f":crown: **{region_name}** has been stolen from **{region_owner}** by **{team_name}**!")
                else:
                    self.bot.dw.claim_region_for_team(team_name, region)
                    await ctx.send(f":tada: **{region_name}** is now claimed by **{team_name}**!")
                    await announcements_channel.send(f":tada: **{team_name}** has claimed victory for the region **{region_name}**!")
        else:
            await ctx.send(f":warning: An issue occured while claiming **{city_string}**.")

    @commands.command(name="leaderboard", aliases=["lb", "top"])
    async def leaderboard(self, ctx):
        """Display the current leaderboard of victory points."""
        
        teams = self.bot.dw.get_teams()
        teams = sorted(teams, key=lambda x: x["points"], reverse=True)

        content = ""
        for i, team in enumerate(teams):
            content += f"**{i + 1}.** {team['name']} - {team['points']} points, {len(team['regions_claimed'])} regions, {len(team['cities_claimed'])} cities\n"

        embed = discord.Embed(
            title="Leaderboard",
            description=content,
            color=discord.Color.blue()
        )

        await ctx.send(embed=embed)
    
    @commands.command(name="check")
    async def check(
        self,
        ctx,
        action: str = commands.parameter(default=None, description="The action to perform; either city, region, or team."),
        *,
        arg: str = commands.parameter(default=None, description="The city, region, or team to check.")
    ):
        """Check the ownership of a given city, region, or team."""
        
        if not action:
            await ctx.send(":warning: Please provide an action to check; it can be either `city`, `region`, or `team`.")
            return
        action = action.lower()

        team_name = get_team_name_from_roles(ctx.author.roles, self.bot.dw.get_team_names())
        if not team_name:
            await ctx.send(":sob: You must be part of a team to execute this command.")
            return

        cities = self.bot.dw.get_cities()

        if action == "city":
            if not arg:
                await ctx.send(":warning: Please provide a city to check.")
                return
            
            city_names = [c["city"].lower() for c in cities]
            city_name = get_city(city_names, arg.lower())

            if not city_name:
                await ctx.send(f':warning: City `{arg}` not found.')
                return
            
            city = cities[city_names.index(city_name)]
            city_owner = self.bot.dw.get_city_owner(city['city'])

            if city_owner is None:
                city_str = "**unclaimed**. :eyes:"
            else:
                city_str = f"claimed by **{city_owner}**. "
                if city_owner == team_name:
                    city_str += ":crown:"
                else:
                    city_str += ":cry:"
            
            await ctx.send(f"**{city['city']}, {city['state']}** is {city_str}")
        elif action == "region":
            if not arg:
                region_str = ""
                for i in range(1, 9):
                    team, num_cities = self.bot.dw.get_region_owner(i)
                    if team == team_name:
                        region_str += f"{i}. **{get_region_from_id(i)}** - {team} ({num_cities} cities) :crown:\n"
                    elif team is not None:
                        region_str += f"{i}. **{get_region_from_id(i)}** - {team} ({num_cities} cities) :cry:\n"
                    else:
                        region_str += f"{i}. **{get_region_from_id(i)}** - Unclaimed :eyes:\n"

                await ctx.send(f"**Regions and their owners:**\n{region_str}\n\nPlease use `!check region <region number>` to check a specific region.")
            else:
                try:
                    arg = int(arg)
                    if arg < 1 or arg > 8:
                        raise ValueError
                except ValueError:
                    await ctx.send(":warning: Please provide a valid region number to check (1-8).")
                    return
                
                region_name = get_region_from_id(arg)
                region_owner, num_cities = self.bot.dw.get_region_owner(arg)

                if region_owner is None:
                    region_str = "**unclaimed**. :eyes:"
                else:
                    region_str = f"claimed by **{region_owner}** with **{num_cities}** cities. "
                    if region_owner == team_name:
                        region_str += ":crown:"
                    else:
                        region_str += ":cry:"

                region_cities_str = ""
                cities_in_region = [c["city"] for c in cities if c["region"] == arg]
                for city in cities_in_region:
                    city_owner = self.bot.dw.get_city_owner(city)
                    city_points = self.bot.dw.get_points_for_city(self.bot.dw.get_city_by_name(city))
                    if city_owner == team_name:
                        region_cities_str += f"\n- **{city}** ({city_points} points) - {city_owner} :crown:"
                    elif city_owner != None:
                        region_cities_str += f"\n- **{city}** ({city_points} points) - {city_owner} :cry:"
                    else:
                        region_cities_str += f"\n- **{city}** ({city_points} points) - Unclaimed :eyes:"
                
                await ctx.send(f"**{region_name}** is {region_str}\n\n**Cities in this region:**\n{region_cities_str}")
        elif action == "state":
            if not arg:
                await ctx.send(":warning: Please provide a state to check.")
                return
            
            states = [c["state"].lower() for c in cities]
            state = get_state(states, arg.lower())

            if not state:
                await ctx.send(f':warning: State `{arg}` not found.')
                return

            is_visited = state in self.bot.dw.get_visited_states()
            state_str = f"{state} is **"
            if is_visited:
                state_str += "already visited**. :frowning:"
            else:
                state_str += "unvisited**. :smiling_imp:"
            
            output_str = f"**{state}** is {state_str}"
            
            output_str += "\n\n**__Drops__**"

            drops = [drop for drop in self.bot.dw.get_drops() if drop["state"] == state]
            for drop in drops:
                output_str += f"\n- *{drop['name']}* in **{drop['city']}** is "
                if self.bot.dw.is_drop_visited(drop['city']):
                    output_str += "Visited :cry:"
                else:
                    output_str += "Unvisited :eyes:"
            
            await ctx.send(output_str)
            
        elif action == "team":
            if not arg:
                arg = team_name
            
            team = self.bot.dw.get_team_by_name(arg)
            if not team:
                await ctx.send(f":warning: `{arg}` not found.")
                return
            
            team_points = self.bot.dw.get_team_points(team)
            cities_claimed = self.bot.dw.get_team_cities_claimed(team)
            regions_claimed = self.bot.dw.get_team_regions_claimed(team)
            rest_period_active = self.bot.dw.is_rest_period_active(team)

            output_str = f":star: **Points**: {team_points}\n"
            output_str += f":flag_us: **{len(regions_claimed)} Regions**: {', '.join(regions_claimed) or 'N/A'}\n"
            output_str += f":cityscape: **{len(cities_claimed)} Cities**: {', '.join(cities_claimed) or 'N/A'}\n"
            output_str += f"{':sleeping:' if rest_period_active else ':sun_with_face:'} **Rest Period Active**: {'Yes' if rest_period_active else 'No'}"

            if arg == team_name:
                coins = self.bot.dw.get_coins_by_team_name(arg)
                output_str += f"\n:coin: **Coins**: {coins}"

            embed = discord.Embed(
                title=f"{arg} Stats",
                color=discord.Color.blue(),
                description=output_str
            )

            await ctx.send(embed=embed)
        else:
            await ctx.send(":warning: Invalid action. Please provide either `city`, `state`, or `team`.")

async def setup(bot):
    await bot.add_cog(Victory(bot))
