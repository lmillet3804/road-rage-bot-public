import random
import os
from pathlib import Path
import time
from pymongo import MongoClient, DESCENDING
from pymongo.errors import ConnectionFailure

class DataWrapper:
    def __init__(self):
        self.mongo_uri = os.getenv("MONGO_STR")
        self.client = MongoClient(self.mongo_uri)
        try:
            # Force connection by pinging the server
            self.client.admin.command("ping")
            print("✅ Successfully connected to MongoDB!")
        except ConnectionFailure as e:
                print("❌ Could not connect:", e)

        self.game_db = self.client[os.getenv("GAME_DB_NAME")]
        self.data_db = self.client["Data"]

        self.cities_collection = self.data_db["cities"]
        self.road_challenges_collection = self.data_db["road_challenges"]
        self.city_challenges_collection = self.data_db["city_challenges"]
        self.curses_collection = self.data_db["curses"]
        self.drops_collection = self.data_db["drops"]
        self.data_duels_collection = self.data_db["duels"]

        self.available_city_challenges_collection = self.game_db["available_city_challenges"]
        self.available_duels_collection = self.game_db["available_duels"]
        self.available_curses_collection = self.game_db["available_curses"]
        self.teams_collection = self.game_db["teams"]
        self.game_duels_collection = self.game_db["duels"]
        self.roadblocks_collection = self.game_db["roadblocks"]
        self.penalties_collection = self.game_db["penalties"]
        self.visited_states_collection = self.game_db["visited_states"]
        self.visited_drops_collection = self.game_db["visited_drops"]

    def clear_game_data(self):
        self.available_city_challenges_collection.delete_many({})
        self.available_city_challenges_collection.insert_many(self.get_city_challenges())
        self.available_curses_collection.delete_many({})
        self.available_curses_collection.insert_many(self.get_curses())
        self.available_duels_collection.delete_many({})
        self.available_duels_collection.insert_many(self.get_duels_in_data())
        self.teams_collection.delete_many({})
        self.game_duels_collection.delete_many({})
        self.roadblocks_collection.delete_many({})
        self.penalties_collection.delete_many({})
        self.visited_states_collection.replace_one({}, {"visited_states": []})
        self.visited_drops_collection.delete_many({})
    
    def get_cities(self):
        return list(self.cities_collection.find())
    
    def get_city_name(self, city: dict):
        return city["city"]

    def get_state_name(self, city: dict):
        return city["state"]
    
    def get_challenges_for_city(self, city: dict):
        return city["challenges"]
    
    def get_points_for_city(self, city: dict):
        return city["points"]
    
    def display_city(self, city: dict):
        return f'{self.get_city_name(city)}, {self.get_state_name(city)}'
    
    def get_city_by_name(self, city_name: str):
        return self.cities_collection.find_one({"city": city_name})
    
    def get_road_challenges(self):
        return list(self.road_challenges_collection.find())
    
    def get_road_challenge_name(self, road_challenge: dict):
        return road_challenge["name"]
    
    def get_road_challenge_points(self, road_challenge: dict):
        return road_challenge["points"]
    
    def get_road_challenge_description(self, road_challenge: dict):
        return road_challenge["description"]
    
    def get_city_challenges(self):
        return list(self.city_challenges_collection.find())
    
    def get_available_city_challenges(self):
        return list(self.available_city_challenges_collection.find())

    def get_available_road_challenges(self, team_name:str):
        team = self.get_team_by_name(team_name)
        if not team:
            return []
        return team["available_road_challenges"]

    def get_curses(self):
        return list(self.curses_collection.find())
    
    def get_available_curses(self):
        return list(self.available_curses_collection.find())

    def update_team(self, new_team):
        self.teams_collection.replace_one({"name": new_team["name"]}, new_team)

    def add_team(self, team_name: str, players: list):
        if self.get_team_by_name(team_name) is not None:
            for player in players:
                self.add_player_to_team(team_name, player)
            return False
        self.teams_collection.insert_one({"name": team_name, "points": 0, "cities_claimed": [], "players": players, "regions_claimed": [], "active_road_challenges": [], "coins": 250, "roadblock_active": False, "roadblock_start": "", "curses":[], "available_road_challenges":self.get_road_challenges(), "rest_period_active": False})
        return True

    def add_player_to_team(self, team_name: str, player: str):
        team = self.get_team_by_name(team_name)
        if not team or player in team["players"]:
            return False
        team["players"].append(player)
        self.update_team(team)
        return True
    
    def get_other_teams(self, team_name: str):
        return [team for team in self.get_teams() if team["name"] != team_name]
    
    def get_team_names(self):
        return [team["name"] for team in self.get_teams()]

    def claim_city_for_team(self, team_name: str, city_name: str):
        team = self.get_team_by_name(team_name)
        if not team or city_name in team["cities_claimed"]:
            return False
        
        team["cities_claimed"].append(city_name)
        city = self.get_city_by_name(city_name)
        team["points"] += self.get_points_for_city(city)
        self.update_team(team)
        return True
    
    def unclaim_city_from_team(self, team_name: str, city_name: str):
        team = self.get_team_by_name(team_name)
        if not team or city_name not in team["cities_claimed"]:
            return False
        
        team["cities_claimed"].remove(city_name)
        city = self.get_city_by_name(city_name)
        team["points"] -= self.get_points_for_city(city)
        self.update_team(team)
        return True

    def get_city_owner(self, city_name: str):
        team_dict = self.teams_collection.find_one({"cities_claimed": city_name})
        if team_dict:
            return team_dict["name"]
        return None
    
    def get_region_bonus(self, num_regions: int, current_num=4):
        if num_regions == 1:
            return current_num
        else:
            return self.get_region_bonus(num_regions - 1, current_num+num_regions-1)

    def claim_region_for_team(self, team_name: str, region_id: int):
        team = self.get_team_by_name(team_name)
        if not team or region_id in team["regions_claimed"]:
            return False
        
        team["regions_claimed"].append(region_id)
        team["points"] += self.get_region_bonus(len(team["regions_claimed"]))
        self.update_team(team)
        return True
    
    def unclaim_region_from_team(self, team_name: str, region_id: int):
        team = self.get_team_by_name(team_name)
        if not team or region_id not in team["regions_claimed"]:
            return False
        
        team["regions_claimed"].remove(region_id)
        team["points"] -= self.get_region_bonus(len(team["regions_claimed"])+1)
        self.update_team(team)
        return True
    
    def get_region_owner(self, region_id: int):
        team = self.teams_collection.find_one({"regions_claimed": region_id})
        if team:
            return team["name"], len([city for city in team["cities_claimed"] if self.get_city_by_name(city)["region"] == region_id])
        return None, 2
    
    def get_team_by_name(self, team_name: str):
        return self.teams_collection.find_one({"name": team_name})
    
    def get_teams(self):
        return list(self.teams_collection.find())
    
    def get_team_name(self, team: dict):
        return team["name"]
    
    def get_team_points(self, team: dict):
        return team["points"]
    
    def get_team_cities_claimed(self, team: dict):
        return team["cities_claimed"]
    
    def get_team_cities_claimed_by_region(self, team_name: str):
        team = self.get_team_by_name(team_name)
        if not team:
            return None
        
        regions = {}

        for city in self.cities_collection.find():
            if city["region"] not in regions:
                regions[city["region"]] = 0

        cities_claimed = team["cities_claimed"]

        for city in cities_claimed:
            city_data = self.get_city_by_name(city)
            if city_data["region"] in regions:
                regions[city_data["region"]] += 1

        return regions
    
    def get_team_players(self, team: dict):
        return team["players"]
    
    def get_team_regions_claimed(self, team: dict):
        return team["regions_claimed"]
    
    def populate_active_road_challenges(self, team: dict, no_curses=False):
        available_road_challenges = self.get_available_road_challenges(team["name"])
        available_road_challenges_count = len(available_road_challenges)
        while(len(team["active_road_challenges"]) < 4 and available_road_challenges_count > 0):
            random_int = random.randint(0, available_road_challenges_count - 1)
            has_curse_road_challenge = no_curses or len([challenge for challenge in team["active_road_challenges"] if "CURSE" in challenge['name']]) > 0
            reroll_curse = random.randint(0, 1)
            while "Cry" in available_road_challenges[random_int]['name'] or ("CURSE" in available_road_challenges[random_int]['name'] and (has_curse_road_challenge or reroll_curse == 0)):
                random_int = random.randint(0, available_road_challenges_count - 1)
            new_active_road_challenge = available_road_challenges.pop(random_int)
            team["active_road_challenges"].append(new_active_road_challenge)
            team["available_road_challenges"] = available_road_challenges
        self.update_team(team)

    def populate_active_road_challenges_by_team_name(self, team_name: str):
        team = self.get_team_by_name(team_name)
        if not team:
            return False
        self.populate_active_road_challenges(team)
        return True
        
    def get_active_road_challenges(self, team: dict):
        return team["active_road_challenges"]

    def get_active_road_challenges_by_team_name(self, team_name: str):
        team = self.get_team_by_name(team_name)
        if not team:
            return None
        return team["active_road_challenges"]
    
    def complete_active_road_challenge(self, team_name: str, challenge_number: int):
        team = self.get_team_by_name(team_name)
        if not team or challenge_number < 1 or challenge_number > 4 or len(team["active_road_challenges"]) < challenge_number:
            return False

        challenge = team["active_road_challenges"].pop(challenge_number - 1)
        team["coins"] += self.get_road_challenge_points(challenge)
        self.populate_active_road_challenges(team)
        self.update_team(team)
        return True
    
    def remove_active_road_challenge(self, team_name: str, challenge_number: int):
        team = self.get_team_by_name(team_name)
        if not team or challenge_number < 1 or challenge_number > 4 or len(team["active_road_challenges"]) < challenge_number:
            return False
        
        team["active_road_challenges"].pop(challenge_number - 1)
        self.populate_active_road_challenges(team)
        self.update_team(team)
        return True
    
    def swap_active_road_challenges(self, team1_name: str, challenge1: int, team2_name: str, challenge2: int):
        team1 = self.get_team_by_name(team1_name)
        team2 = self.get_team_by_name(team2_name)
        if team1 is None or team2 is None or challenge1 < 1 or challenge1 > 4 or challenge2 < 1 or challenge2 > 4:
            return False
        
        temp = team1["active_road_challenges"][challenge1 - 1]
        team1["active_road_challenges"][challenge1 - 1] = team2["active_road_challenges"][challenge2 - 1]
        team2["active_road_challenges"][challenge2 - 1] = temp
        self.update_team(team1)
        self.update_team(team2)
        return True
    
    def draw_city_challenge(self, team_name: str):
        team = self.get_team_by_name(team_name)
        if len(self.get_available_city_challenges()) == 0 or team["coins"] < 100:
            return False
        random_int = random.randint(0, len(self.get_available_city_challenges()) - 1)
        challenge = self.get_available_city_challenges().pop(random_int)
        challenge['timestamp'] = time.time()
        team["active_city_challenge"] = challenge
        self.update_team(team)
        self.available_city_challenges_collection.delete_one({"description": challenge["description"]})
        return True
    
    def get_active_city_challenge(self, team: dict):
        if "active_city_challenge" not in team or team["active_city_challenge"] == {}:
            return None
        return team["active_city_challenge"]
    
    def get_active_city_challenge_by_team_name(self, team_name: str):
        team = self.get_team_by_name(team_name)
        if not team or "active_city_challenge" not in team or team["active_city_challenge"] == {}:
            return None
        return team["active_city_challenge"]
    
    def complete_active_city_challenge(self, team_name: str):
        team = self.get_team_by_name(team_name)
        if not team or "active_city_challenge" not in team or team["active_city_challenge"] == {}:
            return False
        team["active_city_challenge"] = None
        self.update_team(team)
        return True
    
    def fail_active_city_challenge(self, team_name: str):
        team = self.get_team_by_name(team_name)
        if not team or "active_city_challenge" not in team or team["active_city_challenge"] == {}:
            return False
        team["active_city_challenge"] = None
        team["coins"] -= 100
        self.penalties_collection.insert_one({"team": team_name, "timestamp": time.time()})
        self.update_team(team)
        return True
    
    def get_coins(self, team: dict):
        return team["coins"]
    
    def get_coins_by_team_name(self, team_name: str):
        team = self.get_team_by_name(team_name)
        if not team:
            return None
        return team["coins"]
    
    def spend_coins(self, team: dict, amount: int):
        team["coins"] -= amount
        self.update_team(team)

    def spend_coins_by_team_name(self, team_name: str, amount: int):
        team = self.get_team_by_name(team_name)
        if not team:
            return False
        
        team["coins"] -= amount
        self.update_team(team)
        return True
    
    def add_coins(self, team: dict, amount: int):
        team["coins"] += amount
        self.update_team(team)

    def add_coins_by_team_name(self, team_name: str, amount: int):
        team = self.get_team_by_name(team_name)
        if not team:
            return False
        
        team["coins"] += amount
        self.update_team(team)
        return True
    
    def is_rest_period_active(self, team: dict):
        return team["rest_period_active"]

    def is_rest_period_active_by_team_name(self, team_name: str):
        team = self.get_team_by_name(team_name)
        if not team:
            return None
        return team["rest_period_active"]
    
    def set_rest_period_active(self, team: dict, active: bool):
        team["rest_period_active"] = active
        self.update_team(team)
        
    def set_rest_period_active_by_team_name(self, team_name: str, active: bool):
        team = self.get_team_by_name(team_name)
        if not team:
            return False
        team["rest_period_active"] = active
        self.update_team(team)
        return True
    
    def get_roadblock_active(self, team: dict):
        return team["roadblock_active"]
    
    def get_roadblock_active_by_team_name(self, team_name: str):
        team = self.get_team_by_name(team_name)
        if not team:
            return None
        return team["roadblock_active"]
    
    def toggle_roadblock(self, team: dict):
        team["roadblock_active"] = not team["roadblock_active"]
        self.update_team(team)

    def toggle_roadblock_by_team_name(self, team_name: str):
        team = self.get_team_by_name(team_name)
        if not team:
            return False
        
        team["roadblock_active"] = not team["roadblock_active"]
        self.update_team(team)
        return True
    
    def get_roadblocks(self):
        return list(self.roadblocks_collection.find())
    
    def set_roadblock_start(self, team: dict, location: str):
        team["roadblock_start"] = location
        self.update_team(team)

    def set_roadblock_start_by_team_name(self, team_name: str, location: str):
        team = self.get_team_by_name(team_name)
        if not team:
            return False
        team["roadblock_start"] = location
        self.update_team(team)
        return True
    
    def get_roadblock_start(self, team: dict):
        return team["roadblock_start"]
    
    def get_roadblock_start_by_team_name(self, team_name: str):
        team = self.get_team_by_name(team_name)
        if not team:
            return None
        return team["roadblock_start"]
    
    def add_roadblock(self, team_name: str, from_location: str, to_location: str, miles: int):
        team = self.get_team_by_name(team_name)
        if not team or team["coins"] < miles * 15:
            return False
        
        self.roadblocks_collection.insert_one({"team": team_name, "from": from_location, "to": to_location, "miles": miles})
        team["coins"] -= miles * 15
        self.update_team(team)
        return True
    
    def get_visited_states(self):
        return self.visited_states_collection.find_one()["visited_states"]
    
    def add_visited_state(self, state_name: str):
        visited_states = self.get_visited_states()
        if state_name in visited_states:
            return False
        visited_states.append(state_name)
        self.visited_states_collection.replace_one({}, {"visited_states": visited_states})
        return True
    
    def get_visited_drops(self):
        return list(self.visited_drops_collection.find())
    
    def add_visited_drop(self, drop_city: str):
        drop = self.get_drop_by_city_name(drop_city)
        if not drop:
            return False
        self.visited_drops_collection.insert_one(drop)
        return True

    def is_drop_visited(self, drop_city: str):
        return self.visited_drops_collection.find_one({"city": drop_city}) is not None

    def get_drops(self):
        return list(self.drops_collection.find())
    
    def get_drop_by_city_name(self, city_name: str):
        return self.drops_collection.find_one({"city": city_name.capitalize()})
    
    def get_available_duels(self):
        return list(self.available_duels_collection.find())
    
    def get_duels_in_data(self):
        return list(self.data_duels_collection.find())

    def get_duels(self):
        return list(self.game_duels_collection.find())
    
    def create_duel(self, team1: str, team2: str, city: str):
        self.game_duels_collection.insert_one({"team1": team1, "team2": team2, "city": city, "timestamp": time.time(), "status": "waiting"})

    def move_duel_to_pending(self, duel: dict):
        duel["status"] = "pending"
        available_duels = self.get_available_duels()
        duel1_challenge, duel2_challenge = random.sample(available_duels, k=2)
        duel["challenge1"] = duel1_challenge
        duel["challenge2"] = duel2_challenge
        self.game_duels_collection.replace_one({"team1": duel["team1"], "team2": duel["team2"], "city": duel["city"]}, duel)
        return duel1_challenge, duel2_challenge
    
    def choose_challenge_for_duel(self, duel: dict, challenge_number: int):
        duel["challenge"] = duel["challenge1"] if challenge_number == 1 else duel["challenge2"]
        self.game_duels_collection.replace_one({"team1": duel["team1"], "team2": duel["team2"], "city": duel["city"]}, duel)
        self.available_duels_collection.delete_one({"description": duel["challenge"]["description"]})

    def activate_duel(self, duel: dict):
        if "challenge" not in duel:
            self.choose_challenge_for_duel(duel, random.randint(1, 2))
        duel["status"] = "active"
        duel["timestamp"] = time.time()
        self.game_duels_collection.replace_one({"team1": duel["team1"], "team2": duel["team2"], "city": duel["city"]}, duel)
        self.available_duels_collection.delete_one({"description": duel["challenge"]["description"]})
        return duel["challenge"]

    def claim_duel(self, duel: dict, team_name: str):
        duel["status"] = "complete"
        duel["timestamp"] = time.time()
        duel["winner"] = team_name
        self.game_duels_collection.replace_one({"team1": duel["team1"], "team2": duel["team2"], "city": duel["city"]}, duel)
    
    def get_duels_by_team_name(self, team_name: str):
        return list(self.game_duels_collection.find({"$or": [{"team1": team_name}, {"team2": team_name}]}))

    def did_challenge_in_duel(self, team_name: str, city_name: str):
        duel = self.game_duels_collection.find_one({"team1": team_name, "city": city_name})
        return duel is not None
    
    def city_has_duel_cooldown(self, city_name: str):
        duel = self.game_duels_collection.find_one({"city": city_name, "status": "complete"}, sort=[("timestamp", DESCENDING)])
        duel_cooldown_time = 24 * 60 * 60  if os.getenv('MODE') == 'production' else 5 * 60 # 24 hours in production, 5 minutes in development
        if duel and (time.time() - duel["timestamp"]) < duel_cooldown_time:
            return True
        return False
    
    def get_penalties(self):
        return list(self.penalties_collection.find())
    
    def team_has_penalty(self, team_name: str):
        return self.penalties_collection.find_one({"team": team_name}) is not None
    
    def remove_penalty(self, team_name: str):
        return self.penalties_collection.delete_one({"team": team_name}).deleted_count > 0
    
    def draw_curse_by_team_name(self, team_name: str):
        team = self.get_team_by_name(team_name)
        if not team or team["coins"] < 300:
            return False
        
        available_curses = self.get_available_curses()
        if not available_curses or len(available_curses) == 0:
            return False
        
        random_int = random.randint(0, len(available_curses) - 1)
        curse = available_curses.pop(random_int)
        team["curses"].append(curse)
        self.update_team(team)
        self.available_curses_collection.delete_one({"name": curse["name"]})
        return curse
    
    def get_curses_by_team_name(self, team_name: str):
        team = self.get_team_by_name(team_name)
        if not team:
            return None
        return team["curses"]
    
    def remove_curse_by_team_name(self, team_name: str, curse_number: int):
        team = self.get_team_by_name(team_name)
        if not team or curse_number < 1 or curse_number > len(team["curses"]):
            return False
        
        team["curses"].pop(curse_number - 1)
        self.update_team(team)
        return True
    
    def get_last_curse_played_time_by_team_name(self, team_name: str):
        team = self.get_team_by_name(team_name)
        if not team or "last_curse_played" not in team:
            return None
        return team["last_curse_played"]
    
    def update_last_curse_played_time_by_team_name(self, team_name: str):
        team = self.get_team_by_name(team_name)
        if not team:
            return False
        team["last_curse_played"] = time.time()
        self.update_team(team)
        return True