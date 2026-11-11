import discord
import os
from discord.ext import commands
from utils.lists import get_state, get_team_name_from_roles
import time
import asyncio

class Travel(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="travel")
    async def travel(self, ctx, miles=commands.parameter(default=None, description="The number of miles travelled.")):
        """Spend coins to travel miles."""

        if not miles:
            await ctx.send("Please provide the number of miles to travel.")
            return
        
        if self._is_production_mode_and_invalid_channel(ctx):
            await ctx.send("This command is only available in team channels.")
            return

        team_name = get_team_name_from_roles(ctx.author.roles, self.bot.dw.get_team_names())
        if not team_name:
            await ctx.send(":sob: You must be part of a team to execute this command.")
            return

        self.bot.dw.spend_coins_by_team_name(team_name, int(miles))

        await ctx.send(f":automobile: {miles} miles travelled. {self.bot.dw.get_coins_by_team_name(team_name)} coins remaining. :coin: :money_with_wings:")

    def _is_production_mode_and_invalid_channel(self, ctx):
        MODE = os.getenv('MODE')
        return (MODE == "development" and 
                ctx.channel.id not in [
                    self.bot.ids["channels"][os.getenv("TEAM_1_NAME").lower()], 
                    self.bot.ids["channels"][os.getenv("TEAM_2_NAME").lower()], 
                    self.bot.ids["channels"][os.getenv("TEAM_3_NAME").lower()]
                ])

    @commands.command(name="roadChallenge", aliases=["roadChallenges", "rc"])
    async def roadChallenge(self, ctx, action=commands.parameter(default=None, description="The action to perform; either list, cancel, or complete."), challenge_number=commands.parameter(default=None, description="The challenge number to complete.")):
        """List, cancel, or claim the 4 active road challenges."""

        action = action.lower() if action else action

        team_name = self._get_team_name(ctx)
        challenges = self.bot.dw.get_active_road_challenges_by_team_name(team_name)
        challenge_str = self._format_challenges(challenges)

        if action == "list" or action == "l" or not action:
            await self._send_challenge_list(ctx, challenges, challenge_str)
        elif self.bot.dw.team_has_penalty(team_name):
            return await ctx.send(":warning: Your team is currently under a penalty and cannot complete road challenges. Please wait until your penalty time is over.")
        elif action == "cancel":
            await self._cancel_challenge(ctx, team_name, challenge_number)
        elif action == "complete" or action == "claim" or action == "c":
            await self._complete_challenge(ctx, team_name, challenge_number)
        else:
            await ctx.send(":warning: Please provide a valid action: list, cancel, or complete.")

    def _get_team_name(self, ctx):
        return get_team_name_from_roles(ctx.author.roles, self.bot.dw.get_team_names())

    def _format_challenges(self, challenges):
        return "\n".join([f"**{i+1}. {v['name']} **{v['description']} ({v['points']} coins)" for i, v in enumerate(challenges)])

    async def _send_challenge_list(self, ctx, challenges, challenge_str):
        embed = discord.Embed(
            title="Active Road Challenges",
            description=f"Here are the **{len(challenges)}** active road challenges for **{self._get_team_name(ctx)}**:\n\n{challenge_str}",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)

    async def _complete_challenge(self, ctx, team_name, challenge_number):
        if not challenge_number:
            return await ctx.send(':warning: Please provide a challenge number.')

        if not team_name:
            await ctx.send(":warning: You must be part of a team to claim a city.")
            return

        try:
            challenge_number = int(challenge_number)
            current_challenge = self.bot.dw.get_active_road_challenges_by_team_name(team_name)[challenge_number - 1]
            did_complete = self.bot.dw.complete_active_road_challenge(team_name, challenge_number)

            if did_complete:
                await self._announce_challenge_completion(ctx, team_name, challenge_number, current_challenge)
        except ValueError:
            await ctx.send(":warning: Please provide a valid challenge number.")

    async def _announce_challenge_completion(self, ctx, team_name, challenge_number, current_challenge):
        embed = discord.Embed(
            title=f":tada: Road Challenge {current_challenge['name']} Completed :tada:",
            description=current_challenge['description'],
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"You now have {self.bot.dw.get_coins_by_team_name(team_name)} coins in your bank")
        await ctx.send(embed=embed)
    
    async def _cancel_challenge(self, ctx, team_name, challenge_number):
        if not challenge_number:
            return await ctx.send(':warning: Please provide a challenge number.')

        if not team_name:
            await ctx.send(":warning: You must be part of a team to cancel a challenge.")
            return

        try:
            challenge_number = int(challenge_number)
            if challenge_number < 1 or challenge_number > 3:
                await ctx.send(":warning: Please provide a valid challenge number.")
                return
            
            current_challenge = self.bot.dw.get_active_road_challenges_by_team_name(team_name)[challenge_number - 1]
            
            await self._confirm_cancel_challenge(ctx, team_name, challenge_number, current_challenge)
        except ValueError:
            await ctx.send(":warning: Please provide a valid challenge number.")
    
    async def _confirm_cancel_challenge(self, ctx, team_name, challenge_number, current_challenge):
        embed = discord.Embed(
            title=f"Are you sure you want to cancel road challenge {challenge_number}?",
            description=":warning: You may **only** cancel a challenge if it does not apply to your team because you are **not Catholic**. :warning:",
            color=discord.Color.blue()
        )
        embed.add_field(name=current_challenge['name'], value=current_challenge['description'], inline=False)
        embed.add_field(name="Confirmation", value="Type `I AM NOT CATHOLIC` to cancel this challenge.", inline=False)
        embed.set_footer(text="Cancelling this challenge will be announced to other teams.")
        await ctx.send(embed=embed)

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            response = await self.bot.wait_for("message", check=check, timeout=30)
            if response.content.lower() == 'i am not catholic':
                did_remove = self.bot.dw.remove_active_road_challenge(team_name, challenge_number)
                if did_remove:
                    await self._announce_challenge_cancellation(ctx, team_name, current_challenge)
                else:
                    await ctx.send(":warning: Failed to cancel this challenge.")
            else:
                await ctx.send(":warning: Confirmation failed. Please try again.")
        except asyncio.TimeoutError:
            await ctx.send(":hourglass: Confirmation timed out. Please try again.")

    async def _announce_challenge_cancellation(self, ctx, team_name, current_challenge):
        await ctx.send(f":orthodox_cross: You have successfully cancelled road challenge **{current_challenge['name']}**.")

        announcements_channel = self.bot.get_channel(self.bot.ids["channels"]["announcements"])
        announcements_embed = discord.Embed(
            title="Road Challenge Cancellation",
            description=f"**{team_name}** has cancelled the road challenge **{current_challenge['name']}** because their team is not Catholic.",
            color=discord.Color.blue()
        )
        announcements_embed.add_field(name="Description", value=current_challenge['description'], inline=False)
        await announcements_channel.send(embed=announcements_embed)

    @commands.command(name="welcome")
    async def welcome(self, ctx, state=commands.parameter(default=None, description="The state to welcome the team to.")):
        """Welcome bonus for entering a new state."""
        visited_cities = self.bot.dw.get_visited_states()

        if not state or state.lower() == "list":
            visited_cities = sorted(visited_cities)
            embed = discord.Embed(
                title="Visited States",
                description=f"Here are the states that have already been visited:\n\n{', '.join(visited_cities)}",
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
            return
        
        cities = self.bot.dw.get_cities()
        states = [city['state'].lower() for city in cities]
        state = get_state(states, state.lower())

        if self.bot.dw.team_has_penalty(self._get_team_name(ctx)):
            return await ctx.send(":warning: Your team is currently under a penalty and cannot receive welcome bonuses. Please wait until your penalty time is over.")

        if not state:
            await ctx.send(":warning: Please provide a valid state.")
            return

        if state in visited_cities:
            await ctx.send("Someone has already visited this state. :cry:")
            await ctx.send("https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExcWprZjNiZGdwODdmcHg0aG4wNHI0aDJocGZvc2VpMDA4Z3E1Z2lnZiZlcD12MV9naWZzX3NlYXJjaCZjdD1n/fYfeQAOD8pSjN7M0jY/giphy.gif")
            return
        
        if state == 'AL':
            await ctx.send(":skull: There is no welcome bonus for Alabama.")
            return
        
        self.bot.dw.add_visited_state(state)
        self.bot.dw.add_coins_by_team_name(self._get_team_name(ctx), 75)
        embed = discord.Embed(
            title=f':tada: Welcome to {state.upper()}! :tada:',
            description=f'You now have {self.bot.dw.get_coins_by_team_name(self._get_team_name(ctx))} coins in your bank',
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)

        announcements_channel = self.bot.get_channel(self.bot.ids["channels"]["announcements"])
        announcements_embed = discord.Embed(
            title=f":wave: {state.upper()} Welcoming Committee :handshake:",
            description=f"**{self._get_team_name(ctx)}** is the first team to visit **{state.upper()}**! :tada:\n\n They receive the welcome bonus of 75 coins!",
            color=discord.Color.blue()
        )
        await announcements_channel.send(embed=announcements_embed)

    @commands.command(name="drop", aliases=["drops"])
    async def drop(self, ctx, city_name=commands.parameter(default=None, description="The city that the drop can be found in."), *args):
        """Claim the coin drop for a location."""

        if self.bot.dw.team_has_penalty(self._get_team_name(ctx)):
            return await ctx.send(":warning: Your team is currently under a penalty and cannot claim coin drops. Please wait until your penalty time is over.")

        city_name = city_name.lower() if city_name else city_name
        if args:
            city_name += " " + " ".join(args)
            city_name = city_name.lower()

        if not city_name or city_name == "list" or city_name == "l":
            drops = self.bot.dw.get_drops()
            visited_drops = self.bot.dw.get_visited_drops()

            states = {}
            for drop in drops:
                if drop['state'] not in states:
                    states[drop['state']] = []
                states[drop['state']].append(drop)
            sorted_states = sorted(states.keys())

            embed = discord.Embed(
                title="Coin Drops",
                color=discord.Color.blue()
            )

            for state in sorted_states:
                drop_str = ""
                for drop in states[state]:
                    drop_str += f"**{drop['city']}**\n"
                    if drop['city'] in visited_drops:
                        drop_str += ":link: Claimed\n"
                    else:
                        drop_str += f"{drop['name']}\n"
                drop_str += "\n"
                embed.add_field(name=state, value=drop_str, inline=False)

            await ctx.send(embed=embed)
            return

        team_name = self._get_team_name(ctx)

        drop_value = self.bot.dw.get_drop_by_city_name(city_name)
        if not drop_value:
            await ctx.send(f":warning: Could not find a drop for city `{city_name}`.")
            return

        success = self.bot.dw.add_visited_drop(drop_value['city'])
        if not success:
            await ctx.send(":warning: This drop has already been claimed.")
            return

        self.bot.dw.add_coins_by_team_name(team_name, 75)

        embed = discord.Embed(
            title=":moneybag: Coin Drop :moneybag:",
            description=f"You have claimed the coin drop for **{drop_value['name']}** located in **{drop_value['city']}, {drop_value['state']}**.",
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"You now have {self.bot.dw.get_coins_by_team_name(team_name)} coins in your bank")

        await ctx.send(embed=embed)

        announcements_channel = self.bot.get_channel(self.bot.ids["channels"]["announcements"])
        announcements_embed = discord.Embed(
            title=":moneybag: Coin Drop Claimed :moneybag:",
            description=f"**{team_name}** has claimed the coin drop for **{drop_value['name']}** located in **{drop_value['city']}, {drop_value['state']}**! :tada:\n\n They receive the drop bonus of 75 coins!",
            color=discord.Color.blue()
        )
        await announcements_channel.send(embed=announcements_embed)

    @commands.command(name="powerup", aliases=["powerups"])
    async def powerup(self, ctx):
        """Purchase a powerup for your team."""

        team_name = self._get_team_name(ctx)

        if self.bot.dw.team_has_penalty(team_name):
            return await ctx.send(":warning: Your team is currently under a penalty and cannot purchase powerups. Please wait until your penalty time is over.")

        embed = discord.Embed(
            title=":zap: Powerup Store :zap:",
            description="""**1. Veto ** 150 coins - Return a road challenge to your hand. Draw a new challenge immediately. This is not valid for curses.\n\n
            **2. Roadblock ** 15 coins per mile - Shut down a road for the remainder of the game. You must travel to the road you desire to block in order to use the power up. Once activated, no one can use the road, including your team.\n\n
            **3. Tracker ** 150 coins - Receive a location pin of every team at that moment.\n\n
            **4. Curse ** 300 coins - Draw a random curse form the deck. Save this and cast it on another team whenever you desire. They must then follow the directions of the curse before continuing the game.\n\n\n""" + 
            f"You have {self.bot.dw.get_coins_by_team_name(team_name)} coins in your bank. Please select the powerup you would like to purchase (1-4).",
            color=discord.Color.blue(),
        )
        embed.set_footer(text="Type 'cancel' to cancel the purchase.")
        await ctx.send(embed=embed)

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            response = await self.bot.wait_for("message", check=check, timeout=30)
            while response.content not in ["1", "2", "3", "4"]:
                if response.content.lower() == 'cancel':
                    await ctx.send(":x: Powerup purchase cancelled.")
                    return
                await ctx.send(":warning: Please provide a valid powerup number.")
                response = await self.bot.wait_for("message", check=check, timeout=30)
            
            powerup_num = int(response.content)
            if powerup_num == 1:
                # Veto powerup:
                if self.bot.dw.get_coins_by_team_name(team_name) < 150:
                    await ctx.send(":warning: You do not have enough coins to purchase this powerup.")
                    return

                embed = discord.Embed(
                    title=":prohibited: Choose a Road Challenge to Veto :prohibited:\n\n",
                    description=f'Please provide the number of the challenge you would like to veto.\n\n{self._format_challenges(self.bot.dw.get_active_road_challenges_by_team_name(team_name))}',
                    color=discord.Color.blue()
                )
                embed.set_footer(text="Type 'cancel' to cancel the veto.")

                await ctx.send(embed=embed)
                response = await self.bot.wait_for("message", check=check, timeout=30)

                while response.content not in ["1", "2", "3", "4"]:
                    if response.content.lower() == 'cancel':
                        await ctx.send(":x: Veto powerup cancelled.")
                        return
                    await ctx.send(":warning: Please provide a valid challenge number.")
                    response = await self.bot.wait_for("message", check=check, timeout=30)

                challenge_num = int(response.content)
                self.bot.dw.add_coins_by_team_name(team_name, -150)
                self.bot.dw.remove_active_road_challenge(team_name, challenge_num)

                embed = discord.Embed(
                    title=":zap: Veto Powerup Activated :zap:",
                    description=f"You have vetoed challenge {challenge_num}. Your new challenges:\n\n{self._format_challenges(self.bot.dw.get_active_road_challenges_by_team_name(team_name))}",
                    color=discord.Color.blue()
                )
                embed.set_footer(text=f"You now have {self.bot.dw.get_coins_by_team_name(team_name)} coins in your bank")

                await ctx.send(embed=embed)
            elif powerup_num == 2:
                # Roadblock powerup:
                if self.bot.dw.get_coins_by_team_name(team_name) < 15:
                    await ctx.send(":warning: You do not have enough coins to purchase this powerup.")
                    return
                if self.bot.dw.get_roadblock_active_by_team_name(team_name):
                    embed = discord.Embed(
                        title="To Location",
                        description="You have selected to end your roadblock. Please provide the location of the roadblock you would like to end or type '0' to cancel. (Be as specific as possible; use Highway/street name, state, mile marker, etc.)",
                        color=discord.Color.blue()
                    )
                    await ctx.send(embed=embed)
                    response = await self.bot.wait_for("message", check=check, timeout=120)

                    if response.content == "0":
                        await ctx.send(":x: Roadblock cancellation cancelled.")
                        return
                    
                    to_location = response.content

                    embed = discord.Embed(
                        title="Miles",
                        description="Please enter how many miles the roadblock stretches or type 0 to cancel.",
                        color=discord.Color.blue()
                    )
                    embed.set_footer(text="Type 'cancel' to cancel the roadblock.")
                    await ctx.send(embed=embed)
                    response = await self.bot.wait_for("message", check=check, timeout=30)
                    while(not response.content.isdigit() or int(response.content) < 0 or int(response.content) * 15 > self.bot.dw.get_coins_by_team_name(team_name)):
                        if response.content.lower() == 'cancel':
                            await ctx.send(":x: Roadblock cancellation cancelled.")
                            return
                        if int(response.content) * 15 > self.bot.dw.get_coins_by_team_name(team_name):
                            await ctx.send(":warning: You do not have enough coins to afford this roadblock.")
                        else:
                            await ctx.send(":warning: Please provide a valid number of miles.")
                        response = await self.bot.wait_for("message", check=check, timeout=30)
                    miles = int(response.content)
                    cost = miles * 15
                    from_location = self.bot.dw.get_roadblock_start_by_team_name(team_name)
                    self.bot.dw.toggle_roadblock_by_team_name(team_name)
                    self.bot.dw.add_roadblock(team_name, from_location, to_location, miles)

                    embed = discord.Embed(
                        title=":zap: Roadblock Powerup Activated :zap:",
                        description=f":smiling_imp: You have added a roadblock from **{from_location}** to **{to_location}** spanning **{miles}** miles. This has cost you **{cost}** coins. :smiling_imp:",
                        color=discord.Color.blue()
                    )
                    embed.set_footer(text=f"You now have {self.bot.dw.get_coins_by_team_name(team_name)} coins in your bank")
                    await ctx.send(embed=embed)

                    announcements_channel = self.bot.get_channel(self.bot.ids["channels"]["announcements"])
                    announcements_embed = discord.Embed(
                        title=":construction: Roadblock Added :construction:",
                        description=f":no_entry: **{team_name}** has added a roadblock from **{from_location}** to **{to_location}** spanning **{miles}** miles. :no_entry:\n\nNo team (including **{team_name}**) is allowed to travel on this road!",
                        color=discord.Color.blue()
                    )
                    await announcements_channel.send(embed=announcements_embed)
                    return
                embed = discord.Embed(
                    title="From Location",
                    description="Please describe the start of your roadblock. (Be as specific as possible; use Highway/street name, state, mile marker, etc.)",
                    color=discord.Color.blue()
                )
                await ctx.send(embed=embed)
                response = await self.bot.wait_for("message", check=check, timeout=120)
                from_location = response.content
                self.bot.dw.set_roadblock_start_by_team_name(team_name, from_location)
                self.bot.dw.toggle_roadblock_by_team_name(team_name)

                await ctx.send(":tada: You have entered the start of your roadblock. To complete the roadblock, come back to this menu to enter the end location.")
            elif powerup_num == 3:
                # Tracker powerup:
                if self.bot.dw.get_coins_by_team_name(team_name) < 150:
                    await ctx.send(":warning: You do not have enough coins to purchase this powerup.")
                    return
                self.bot.dw.add_coins_by_team_name(team_name, -150)

                embed = discord.Embed(
                    title=":round_pushpin: Tracker Powerup Activated :round_pushpin:",
                    description=f"You have activated the tracker. All teams must send you a pin of their current location. You currently have {self.bot.dw.get_coins_by_team_name(team_name)} coins in your bank.",
                    color=discord.Color.blue()
                )

                await ctx.send(embed=embed)

                announcements_channel = self.bot.get_channel(self.bot.ids["channels"]["announcements"])
                announcements_embed = discord.Embed(
                    title=":round_pushpin: Tracker Activated :round_pushpin:",
                    description=f":map:**{team_name}** has activated a tracker!:map:\n\nAll teams must send a pin of their current location to {team_name} immediately!",
                    color=discord.Color.blue()
                )
                await announcements_channel.send(embed=announcements_embed)
            elif powerup_num == 4:
                # Curse powerup:
                
                embed = discord.Embed(
                    title=":mage: Curse Powerup Activated :mage:",
                    description="Type `draw` to draw a random curse from the deck.\nType `view` to view the curses you currently have.\nType `cast` to cast a curse on another team.",
                    color=discord.Color.blue()
                )
                embed.set_footer(text="Type `cancel` to cancel the curse powerup.")
                await ctx.send(embed=embed)

                response = await self.bot.wait_for("message", check=check, timeout=30)
                while response.content.lower() not in ["draw", "view", "cast"]:
                    if response.content.lower() == 'cancel':
                        await ctx.send(":x: Curse powerup cancelled.")
                        return
                    await ctx.send(":warning: Please provide a valid action: draw, view, or cast.")
                    response = await self.bot.wait_for("message", check=check, timeout=30)
                
                action = response.content.lower()
                if action == "draw":
                    if self.bot.dw.get_coins_by_team_name(team_name) < 300:
                        await ctx.send(":warning: You do not have enough coins to purchase this powerup.")
                        return
                    curse = self.bot.dw.draw_curse_by_team_name(team_name)
                    if not curse:
                        await ctx.send(":warning: No more curses left in the deck.")
                        return
                    self.bot.dw.add_coins_by_team_name(team_name, -300)
                    embed = discord.Embed(
                        title=":mage: Curse Drawn :mage:",
                        description=f"You have drawn the following curse:\n\n**{curse['name']}**\n{curse['description']}\n\nYou currently have {self.bot.dw.get_coins_by_team_name(team_name)} coins in your bank.",
                        color=discord.Color.blue()
                    )
                    embed.set_footer(text="You can cast this curse on another team at any time using the `!powerup 4` command.")
                    await ctx.send(embed=embed)
                elif action == "view":
                    curses = self.bot.dw.get_curses_by_team_name(team_name)
                    if len(curses) == 0:
                        await ctx.send(":warning: You do not have any curses. You can draw one using the `!powerup 4` command.")
                        return
                    curse_str = "\n".join([f"**{i+1}. {v['name']} **{v['description']}" for i, v in enumerate(curses)])
                    embed = discord.Embed(
                        title=":mage: Your Curses :mage:",
                        description=f"You currently have the following curses:\n\n{curse_str}",
                        color=discord.Color.blue()
                    )
                    await ctx.send(embed=embed)
                elif action == "cast":
                    curses = self.bot.dw.get_curses_by_team_name(team_name)
                    if len(curses) == 0:
                        await ctx.send(":warning: You do not have any curses. You can draw one using the `!powerup 4` command.")
                        return
                    last_curse_time = self.bot.dw.get_last_curse_played_time_by_team_name(team_name)
                    curse_time_delay = 3 * 60 * 60 if os.getenv('MODE') == 'production' else 60
                    if last_curse_time and (time.time() - last_curse_time) < curse_time_delay:
                        await ctx.send(":warning: You can only cast a curse once every three hours. Please wait before casting another curse.")
                        return
                    curse_str = "\n".join([f"**{i+1}. {v['name']} **{v['description']}" for i, v in enumerate(curses)])
                    embed = discord.Embed(
                        title=":mage: Cast a Curse :mage:",
                        description=f"Please provide the number of the curse you would like to cast.\n\n{curse_str}",
                        color=discord.Color.blue()
                    )
                    embed.set_footer(text="Type 'cancel' to cancel the curse.")
                    await ctx.send(embed=embed)

                    response = await self.bot.wait_for("message", check=check, timeout=30)
                    while(not response.content.isdigit() or int(response.content) not in range(1, len(curses) + 1)):
                        if response.content.lower() == 'cancel':
                            await ctx.send(":x: Curse powerup cancelled.")
                            return
                        await ctx.send(":warning: Please provide a valid curse number.")
                        response = await self.bot.wait_for("message", check=check, timeout=30)
                    
                    curse_num = int(response.content)
                    curse = curses[curse_num - 1]

                    other_teams = self.bot.dw.get_other_teams(team_name)
                    other_teams_str = "\n".join([f"{i + 1}. **{team['name']}**" for i, team in enumerate(other_teams)])
                    embed = discord.Embed(
                        title=":mage: Choose a Team to Curse :mage:",
                        description=f"Please provide the team you would like to cast the curse on.\n\n**Available teams:**\n{other_teams_str}",
                        color=discord.Color.blue()
                    )
                    embed.set_footer(text="Type 'cancel' to cancel the curse.")
                    await ctx.send(embed=embed)

                    response = await self.bot.wait_for("message", check=check, timeout=30)
                    while response.content.lower() not in [team['name'].lower() for team in other_teams]:
                        if response.content.lower() == 'cancel':
                            await ctx.send(":x: Curse powerup cancelled.")
                            return
                        await ctx.send(":warning: Please provide a valid team name to curse.")
                        response = await self.bot.wait_for("message", check=check, timeout=30)

                    other_team_name = [team['name'] for team in other_teams if team['name'].lower() == response.content.lower()][0]
                    embed = discord.Embed(
                        title=":mage: Curse Cast :mage:",
                        description=f"You have cast the curse **{curse['name']}** on **{other_team_name}**!\n\n**{curse['description']}**",
                        color=discord.Color.blue()
                    )
                    await ctx.send(embed=embed)
                    self.bot.dw.remove_curse_by_team_name(team_name, curse_num)
                    self.bot.dw.update_last_curse_played_time_by_team_name(team_name)
                    other_team_channel = self.bot.get_channel(self.bot.ids["channels"][other_team_name.lower()])
                    embed = discord.Embed(
                        title=":mage: You Have Been Cursed! :mage:",
                        description=f"**{team_name}** has cast the curse **{curse['name']}** on your team!\n\n**{curse['description']}**",
                        color=discord.Color.blue()
                    )
                    embed.set_footer(text="You must complete the directions of this curse before continuing the game.")
                    await other_team_channel.send(embed=embed)
        except asyncio.TimeoutError:
            await ctx.send(":hourglass: Confirmation timed out. Please try again.")
            return False

async def setup(bot):
    await bot.add_cog(Travel(bot))