from discord.ext import commands
from utils.lists import get_city
import discord
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

        team_name = get_team_name_from_roles(ctx.author.roles, self.bot.dw.get_team_names())
        if not team_name:
            await ctx.send(":sob: You must be part of a team to execute this command.")
            return
        team_name = team_name[0]
        your_team = self.bot.dw.get_team_by_name(team_name)

        example_usage = f"\nUsage: `{self.bot.prefix}transfer [coins|city] <team number> <value>`\nExamples: `{self.bot.prefix}transfer coins 1 100` or `{self.bot.prefix}transfer city 1 Atlanta`."

        if not challenge_team_name:
            await ctx.send(f":warning: Please provide a team to transfer the item to.{example_usage}")
            return
        
        team = self.bot.dw.get_team_by_name(f"Team {challenge_team_name}")
        if not team:
            await ctx.send(f":warning: Team `{challenge_team_name}` not found.{example_usage}")
            return
        
        if team["name"] == team_name:
            await ctx.send(f":stuck_out_tongue: You cannot give items to your own team.{example_usage}")
            return
        
        if not action:
            await ctx.send(f":warning: Please provide an item to transfer; either state or coins.{example_usage}")
            return
        action = action.lower()

        if action == 'coins' or action == 'coin':
            if not value:
                await ctx.send(f":warning: Please provide the number of coins to give.{example_usage}")
                return

            try:
                value = int(value)
            except ValueError:
                await ctx.send(f":warning: Please provide a valid integer number of coins.{example_usage}")
                return

            if value < 1:
                await ctx.send(f":warning: Please provide a positive number of coins.{example_usage}")
                return

            if your_team["coins"] < value:
                await ctx.send(f":warning: You do not have enough coins to transfer. You only have **{your_team['coins']}** :coin: coins.")
                return
            
            confirmation = await confirm(self.bot, ctx, f":warning: Are you sure you want to transfer **{value}** :coin: coins to **{team['name']}**?")
            if not confirmation:
                await ctx.send(":x: Transfer cancelled.")
                return

            self.bot.dw.add_coins_by_team_name(team["name"], value)
            self.bot.dw.add_coins_by_team_name(team_name, -value)

            await ctx.send(f":moneybag: Transferred **{value}** coins to **{team['name']}**.")

            team_channel = self.bot.get_channel(self.bot.ids["channels"][team["name"].lower()])
            await team_channel.send(f":moneybag: **{team_name}** has transferred **{value}** coins to your team.")
        
        elif action == 'city':
            if not value:
                await ctx.send(":warning: Please provide a city to give.")
                return

            cities = self.bot.dw.get_cities()
            city_names = [c["city"].lower() for c in cities]
            city_name = get_city(city_names, value.lower())

            if not city_name:
                await ctx.send(f':warning: City `{value}` not found.')
                return
            
            city = cities[city_names.index(city_name)]
            city_owner = self.bot.dw.get_city_owner(city['city'])

            if not city_owner:
                await ctx.send(f":warning: **{city['city']}, {city['state']}** is unclaimed. You do not own it.")
                return

            if city_owner != team_name:
                await ctx.send(f":warning: **{city['city']}, {city['state']}** is already claimed by **{city_owner}**.")
                return
            
            state_owner = self.bot.dw.get_state_owner(city['state'])
            state_majority = self.bot.dw.get_state_majority(city["state"])
            your_claimed_cities = self.bot.dw.get_team_cities_claimed_by_state(team_name)[city["state"]]
            their_claimed_cities = self.bot.dw.get_team_cities_claimed_by_state(team["name"])[city["state"]]

            warning_str = f":warning: Are you sure you want to transfer **{city['city']}, {city['state']}** to **{team['name']}**?"

            if not state_owner:
                if their_claimed_cities + 1 == state_majority:
                    warning_str += f" This will give **{team['name']}** a majority of cities in **{city['state']}**."
            elif state_owner == team_name:
                if their_claimed_cities + 1 == state_majority:
                    warning_str += f" This will give **{team['name']}** a majority of cities in **{city['state']}**, dethroning your team."
                elif your_claimed_cities == state_majority:
                    warning_str += f" This will mean you no longer have a majority of cities in **{city['state']}**."

            confirmation = await confirm(self.bot, ctx, warning_str)
            if not confirmation:
                await ctx.send(":x: Transfer cancelled.")
                return

            self.bot.dw.claim_city_for_team(team["name"], city['city'])
            self.bot.dw.unclaim_city_from_team(team_name, city['city'])

            your_output_str = f":cityscape: Transferred **{city['city']}, {city['state']}** to **{team['name']}**."
            announcements_str = f":cityscape: **{team_name}** has transferred **{city['city']}, {city['state']}** to **{team['name']}**."

            if not state_owner:
                if their_claimed_cities + 1 == state_majority:
                    self.bot.dw.claim_state_for_team(team["name"], city["state"])
                    your_output_str += f"\n:sob: This gives **{team['name']}** a majority of cities in **{city['state']}**."
                    announcements_str += f"\n:trophy: This gives **{team['name']}** a majority of cities in **{city['state']}**."
            elif state_owner == team_name:
                if their_claimed_cities + 1 == state_majority:
                    self.bot.dw.claim_state_for_team(team["name"], city["state"])
                    self.bot.dw.unclaim_state_from_team(team_name, city["state"])
                    your_output_str += f"\n:sob: This gives **{team['name']}** a majority of cities in **{city['state']}**, dethroning your team."
                    announcements_str += f"\n:trophy: This gives **{team['name']}** a majority of cities in **{city['state']}**, dethroning **{team_name}**."
                elif your_claimed_cities == state_majority:
                    self.bot.dw.unclaim_state_from_team(team_name, city["state"])
                    your_output_str += f"\n:sob: You no longer have a majority of cities in **{city['state']}**."
                    announcements_str += f"\n:skull: **{team_name}** no longer has a majority of cities in **{city['state']}**."

            await ctx.send(your_output_str)

            announcements_channel = self.bot.get_channel(self.bot.ids["channels"]["announcements"])
            await announcements_channel.send(announcements_str)
        
        else:
            await ctx.send(":warning: Please provide a valid item to transfer; either state or coins.")

async def setup(bot):
    await bot.add_cog(Transfer(bot))