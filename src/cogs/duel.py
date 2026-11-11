from discord.ext import commands
from utils.lists import get_city, get_region_from_id, get_team_name_from_roles
import discord
from utils.discord import confirm

class Duel(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="duel")
    async def duel(
        self,
        ctx,
        action=commands.parameter(default=None, description="The action to perform; either list, challenge, or claim."),
        city=commands.parameter(default=None, description="The city to challenge the team in.")
    ):
        """Challenge another team to a duel in a city."""

        team_name = get_team_name_from_roles(ctx.author.roles, self.bot.dw.get_team_names())
        if not team_name:
            await ctx.send(":sob: You must be part of a team to execute this command.")
            return

        if not action:
            await ctx.send(":warning: Please provide an action to perform; either list, challenge, or claim.")
            return
        action = action.lower()

        if action == 'list':
            duels = self.bot.dw.get_duels_by_team_name(team_name)
            
            embed = discord.Embed(
                title=f"Duels for {team_name}",
                color=discord.Color.blue()
            )

            for type in ["pending", "active", "complete", "waiting"]:
                duels_of_type = [duel for duel in duels if duel["status"] == type]
                if len(duels_of_type) != 0:
                    duel_arr = []
                    for i, v in enumerate(duels_of_type):
                        duel_str = f"**{i+1}.** {v['team1']} vs {v['team2']} in {v['city']}"
                        if type == "complete":
                            duel_str += " :trophy:" if v["winner"] == team_name else ""
                        elif type == "active":
                            duel_str += ":\n> " + v["challenge"]
                        duel_arr.append(duel_str)
                    embed.add_field(name=f"{type.capitalize()} Duels", value="\n".join(duel_arr), inline=False)

            await ctx.send(embed=embed)
            return
        elif action == 'claim':
            duels = self.bot.dw.get_duels_by_team_name(team_name)

            for duel in duels:
                city = self.bot.dw.get_city_by_name(duel['city'])
                if duel["status"] == "active":
                    confirmation = await confirm(self.bot, ctx, f":warning: Are you sure you have completed the challenge for this duel over **{duel['city']}**?\n\n> {duel['challenge']['description']}")
                    if confirmation:
                        current_owner = self.bot.dw.get_city_owner(duel["city"])

                        if current_owner == team_name:
                            update_str = f":shield: **{team_name}** has successfully defended their city."
                        else:
                            self.bot.dw.unclaim_city_from_team(current_owner, duel["city"])
                            update_str = f":crossed_swords: **{team_name}** has removed **{current_owner}'s** control of the city. It is now unclaimed!"

                            region_owner, num_cities = self.bot.dw.get_region_owner(city["region"])
                            team_claimed_cities = self.bot.dw.get_team_cities_claimed_by_region(team_name)[city["region"]]

                            region_name = get_region_from_id(city["region"])
                            if region_owner == team_name:
                                update_str += f"\n:shield: **{team_name}** has successfully defended the state of **{city['state']}**."
                            elif team_claimed_cities > num_cities:
                                if region_owner:
                                    self.bot.dw.unclaim_region_from_team(region_owner, city["region"])
                                    self.bot.dw.claim_region_for_team(team_name, city["region"])
                                    update_str += f"\n:crossed_swords: **{team_name}** has taken control of **{region_name}** from **{region_owner}**."
                                else:
                                    self.bot.dw.claim_region_for_team(team_name, city["region"])
                                    update_str += f"\n:crossed_swords: **{team_name}** has taken control of **{region_name}**."
                            elif region_owner:
                                state_owner_cities = self.bot.dw.get_team_cities_claimed_by_region(region_owner)[city["region"]]
                                if state_owner_cities < 3:
                                    self.bot.dw.unclaim_region_from_team(region_owner, city["region"])
                                    update_str += f"\n:scream: **{region_owner}** has lost control of **{region_name}**. It is now unclaimed."
                                else:
                                    update_str += f"\n:shield: **{region_owner}** has successfully defended the region **{region_name}**."

                        self.bot.dw.claim_duel(duel, team_name)
                        await ctx.send(f":tada: You have won the duel in **{duel['city']}** between **{duel['team1']}** and **{duel['team2']}**!")

                        announcements_channel = self.bot.get_channel(self.bot.ids["channels"]["announcements"])
                        await announcements_channel.send(f":tada: <@&{self.bot.ids['roles'][duel['team1'].lower()]}> and <@&{self.bot.ids['roles'][duel['team2'].lower()]}> have completed their duel in **{duel['city']}**. The winner is **{team_name}**! :tada:\n{update_str}")
                    else:
                        await ctx.send(":x: Duel claim cancelled.")
                    break
    
            return
        elif action == 'choose':
            if not city:
                await ctx.send(":warning: Please choose a number (either 1 or 2) corresponding to the challenge you want to take on for your duel.")
                return
            duels = self.bot.dw.get_duels_by_team_name(team_name)
            for duel in duels:
                if (duel["team1"] == team_name and duel["status"] == "pending"):
                    await ctx.send(":x: Only the defending team can choose the challenge. Please wait for the other team to select their challenge first.")
                    return
                elif (duel["team2"] == team_name and duel["status"] == "pending"):
                    try:
                        choice = int(city)
                        if choice not in [1, 2]:
                            raise ValueError
                    except ValueError:
                        await ctx.send(":warning: Please choose a valid number (either 1 or 2) corresponding to the challenge you want to take on for your duel.")
                        return
                    self.bot.dw.choose_challenge_for_duel(duel, choice)
                    await ctx.send(f":white_check_mark: You have chosen challenge {choice} for your duel in **{duel['city']}**.")  
            return                
        elif action != 'challenge':
            await ctx.send(":warning: Please provide a valid action to perform; either list, challenge, or claim.")
            return
        
        if self.bot.dw.team_has_penalty(team_name):
            return await ctx.send(":warning: Your team is currently under a penalty and cannot initiate duels. Please wait until your penalty time is over.")
        
        if self.bot.dw.is_rest_period_active_by_team_name(team_name):
            return await ctx.send(":warning: Your team is currently in a rest period and cannot initiate duels. Please end your rest period before challenging another team.")
        
        if not city:
            await ctx.send(":warning: Please provide a city to challenge the team in.")
            return

        cities = self.bot.dw.get_cities()
        city_names = [c["city"].lower() for c in cities]
        city_name = get_city(city_names, city.lower())

        if not city_name:
            await ctx.send(f':warning: City `{city}` not found.')
            return
        
        city = cities[city_names.index(city_name)]

        team = self.bot.dw.get_team_by_name(self.bot.dw.get_city_owner(city["city"]))
        if not team:
            await ctx.send(f":warning: City **{city['city']}, {city['state']}** is unclaimed. There is no one to duel.")
            return
        
        if self.bot.dw.did_challenge_in_duel(team_name, city["city"]):
            await ctx.send(f":warning: You have already challenged a team to a duel in **{city['city']}**")
            return
        
        if self.bot.dw.city_has_duel_cooldown(city["city"]):
            await ctx.send(f":warning: A duel was completed in **{city['city']}** within the last 24 hours. Please wait before challenging another team in this city.")
            return
        
        if team["name"] == team_name:
            await ctx.send(":trophy: You already own this city.")
            return
        
        if self.bot.dw.is_rest_period_active(team):
            await ctx.send(f":warning: The team controlling **{city['city']}** is currently in a rest period and cannot be challenged to a duel.")
            return

        duels = self.bot.dw.get_duels()
        for duel in duels:
            if duel["city"] == city["city"] and duel["status"] != "complete":
                await ctx.send(f":warning: A duel is already in progress in **{city['city']}**.")
                return
            if (duel["team1"] == team_name or duel["team2"] == team_name) and duel["status"] != "complete":
                await ctx.send(":warning: Your team is already in a duel.")
                return
            if (duel["team1"] == team["name"] or duel["team2"] == team["name"]) and duel["status"] != "complete":
                await ctx.send(":warning: The other team is already in a duel.")
                return
        
        self.bot.dw.create_duel(team_name, team["name"], city["city"])
        await ctx.send(f":crossed_swords: Duel initiated between **{team_name}** and **{team['name']}** in **{city['city']}, {city['state']}**.")

        announcements_channel = self.bot.get_channel(self.bot.ids["channels"]["announcements"])
        await announcements_channel.send(f":crossed_swords: <@&{self.bot.ids['roles'][team_name.lower()]}> has initiated a duel with <@&{self.bot.ids['roles'][team['name'].lower()]}> in **{city['city']}, {city['state']}**. The challenge will be sent out in **30 minutes**. :timer:")

async def setup(bot):
    await bot.add_cog(Duel(bot))
