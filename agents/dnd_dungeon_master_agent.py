"""
D&D Dungeon Master Agent

A comprehensive text-based Dungeons & Dragons 5th Edition Dungeon Master agent
that facilitates complete campaign playthroughs with BG3-level depth.

Features:
- Complete character creation (races, classes, backgrounds, stats)
- D&D 5e combat mechanics with dice rolling and turn management
- Inventory and equipment system
- Spell casting with spell slots and components
- Rich narrative generation using AI
- Quest tracking and progression
- NPC interaction and dialogue
- Save/Load game state
- Multiple campaign settings
- Party management (single or multi-character)

Based on D&D 5th Edition rules, enhanced with Baldur's Gate 3 storytelling depth.
"""

import json
import uuid
import random
import re
import os
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional
from agents.basic_agent import BasicAgent
from utils.azure_file_storage import AzureFileStorageManager
from openai import AzureOpenAI


class DDDungeonMasterAgent(BasicAgent):
    def __init__(self):
        self.name = 'DDDungeonMaster'
        self.metadata = {
            "name": self.name,
            "description": """I am your Dungeon Master for epic D&D 5e adventures! I can create characters,
            run combat encounters, manage inventory, cast spells, and weave engaging narratives.
            Experience full D&D campaigns with BG3-level storytelling depth.""",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": """Action to perform:
                        - 'create_character': Start character creation
                        - 'start_campaign': Begin a new adventure
                        - 'continue_game': Resume saved game
                        - 'take_action': Perform an action in the game
                        - 'combat_action': Take a combat action
                        - 'rest': Take a short or long rest
                        - 'level_up': Gain a level
                        - 'check_stats': View character sheet
                        - 'check_inventory': View inventory and equipment
                        - 'check_spells': View spellbook and spell slots
                        - 'save_game': Save current game state
                        - 'load_game': Load a saved game
                        - 'roll_dice': Roll dice for skill checks
                        - 'talk_to_npc': Interact with NPCs
                        - 'check_quests': View active quests""",
                        "enum": ["create_character", "start_campaign", "continue_game", "take_action",
                                "combat_action", "rest", "level_up", "check_stats", "check_inventory",
                                "check_spells", "save_game", "load_game", "roll_dice", "talk_to_npc",
                                "check_quests"]
                    },
                    "character_name": {
                        "type": "string",
                        "description": "Name for your character"
                    },
                    "race": {
                        "type": "string",
                        "description": "Character race (Human, Elf, Dwarf, Halfling, Dragonborn, Gnome, Half-Elf, Half-Orc, Tiefling)"
                    },
                    "class_name": {
                        "type": "string",
                        "description": "Character class (Fighter, Wizard, Rogue, Cleric, Ranger, Paladin, Barbarian, Bard, Druid, Monk, Sorcerer, Warlock)"
                    },
                    "background": {
                        "type": "string",
                        "description": "Character background (Acolyte, Criminal, Folk Hero, Noble, Sage, Soldier, etc.)"
                    },
                    "description": {
                        "type": "string",
                        "description": "What you want to do or say in the game"
                    },
                    "target": {
                        "type": "string",
                        "description": "Target of your action (enemy name, NPC name, object, etc.)"
                    },
                    "spell_name": {
                        "type": "string",
                        "description": "Name of spell to cast"
                    },
                    "dice": {
                        "type": "string",
                        "description": "Dice to roll (e.g., '1d20', '2d6+3', '4d8')"
                    },
                    "skill": {
                        "type": "string",
                        "description": "Skill to use (Perception, Stealth, Persuasion, etc.)"
                    },
                    "campaign_type": {
                        "type": "string",
                        "description": "Type of campaign (classic_fantasy, dark_gothic, high_seas, urban_intrigue, custom)"
                    },
                    "save_name": {
                        "type": "string",
                        "description": "Name for the save file"
                    },
                    "user_guid": {
                        "type": "string",
                        "description": "User GUID for personalized game storage"
                    }
                },
                "required": ["action"]
            }
        }
        self.storage_manager = AzureFileStorageManager()

        # Initialize Azure OpenAI client for narrative generation
        try:
            self.client = AzureOpenAI(
                api_key=os.environ['AZURE_OPENAI_API_KEY'],
                api_version=os.environ.get('AZURE_OPENAI_API_VERSION', '2024-02-15-preview'),
                azure_endpoint=os.environ['AZURE_OPENAI_ENDPOINT']
            )
            self.deployment_name = os.environ.get('AZURE_OPENAI_DEPLOYMENT_NAME', 'gpt-4o')
        except Exception as e:
            self.client = None
            self.deployment_name = None

        # D&D 5e data
        self.races = {
            'Human': {'ability_bonus': {'all': 1}, 'speed': 30, 'traits': ['Versatile']},
            'Elf': {'ability_bonus': {'DEX': 2}, 'speed': 30, 'traits': ['Darkvision', 'Fey Ancestry', 'Trance']},
            'Dwarf': {'ability_bonus': {'CON': 2}, 'speed': 25, 'traits': ['Darkvision', 'Dwarven Resilience']},
            'Halfling': {'ability_bonus': {'DEX': 2}, 'speed': 25, 'traits': ['Lucky', 'Brave', 'Halfling Nimbleness']},
            'Dragonborn': {'ability_bonus': {'STR': 2, 'CHA': 1}, 'speed': 30, 'traits': ['Draconic Ancestry', 'Breath Weapon']},
            'Gnome': {'ability_bonus': {'INT': 2}, 'speed': 25, 'traits': ['Darkvision', 'Gnome Cunning']},
            'Half-Elf': {'ability_bonus': {'CHA': 2}, 'speed': 30, 'traits': ['Darkvision', 'Fey Ancestry']},
            'Half-Orc': {'ability_bonus': {'STR': 2, 'CON': 1}, 'speed': 30, 'traits': ['Darkvision', 'Relentless Endurance']},
            'Tiefling': {'ability_bonus': {'CHA': 2, 'INT': 1}, 'speed': 30, 'traits': ['Darkvision', 'Hellish Resistance']}
        }

        self.classes = {
            'Fighter': {'hit_die': 10, 'primary': 'STR', 'saves': ['STR', 'CON'], 'skills': 2},
            'Wizard': {'hit_die': 6, 'primary': 'INT', 'saves': ['INT', 'WIS'], 'skills': 2, 'spellcaster': True},
            'Rogue': {'hit_die': 8, 'primary': 'DEX', 'saves': ['DEX', 'INT'], 'skills': 4},
            'Cleric': {'hit_die': 8, 'primary': 'WIS', 'saves': ['WIS', 'CHA'], 'skills': 2, 'spellcaster': True},
            'Ranger': {'hit_die': 10, 'primary': 'DEX', 'saves': ['STR', 'DEX'], 'skills': 3, 'spellcaster': True},
            'Paladin': {'hit_die': 10, 'primary': 'STR', 'saves': ['WIS', 'CHA'], 'skills': 2, 'spellcaster': True},
            'Barbarian': {'hit_die': 12, 'primary': 'STR', 'saves': ['STR', 'CON'], 'skills': 2},
            'Bard': {'hit_die': 8, 'primary': 'CHA', 'saves': ['DEX', 'CHA'], 'skills': 3, 'spellcaster': True},
            'Druid': {'hit_die': 8, 'primary': 'WIS', 'saves': ['INT', 'WIS'], 'skills': 2, 'spellcaster': True},
            'Monk': {'hit_die': 8, 'primary': 'DEX', 'saves': ['STR', 'DEX'], 'skills': 2},
            'Sorcerer': {'hit_die': 6, 'primary': 'CHA', 'saves': ['CON', 'CHA'], 'skills': 2, 'spellcaster': True},
            'Warlock': {'hit_die': 8, 'primary': 'CHA', 'saves': ['WIS', 'CHA'], 'skills': 2, 'spellcaster': True}
        }

        super().__init__(name=self.name, metadata=self.metadata)

    def perform(self, **kwargs):
        """Main entry point for the DM agent"""
        action = kwargs.get('action', '')
        user_guid = kwargs.get('user_guid')

        # Set memory context for user-specific storage
        if user_guid:
            self.storage_manager.set_memory_context(user_guid)

        # Route to appropriate handler
        action_handlers = {
            'create_character': self._create_character,
            'start_campaign': self._start_campaign,
            'continue_game': self._continue_game,
            'take_action': self._take_action,
            'combat_action': self._combat_action,
            'rest': self._rest,
            'level_up': self._level_up,
            'check_stats': self._check_stats,
            'check_inventory': self._check_inventory,
            'check_spells': self._check_spells,
            'save_game': self._save_game,
            'load_game': self._load_game,
            'roll_dice': self._roll_dice,
            'talk_to_npc': self._talk_to_npc,
            'check_quests': self._check_quests
        }

        handler = action_handlers.get(action)
        if handler:
            return handler(kwargs)
        else:
            return f"Unknown action: {action}. Type 'check_stats' to see your character or 'continue_game' to resume your adventure!"

    def _create_character(self, kwargs: Dict[str, Any]) -> str:
        """Create a new D&D character"""
        char_name = kwargs.get('character_name', 'Adventurer')
        race = kwargs.get('race', 'Human')
        class_name = kwargs.get('class_name', 'Fighter')
        background = kwargs.get('background', 'Folk Hero')

        # Validate inputs
        if race not in self.races:
            return f"Invalid race. Choose from: {', '.join(self.races.keys())}"
        if class_name not in self.classes:
            return f"Invalid class. Choose from: {', '.join(self.classes.keys())}"

        # Roll ability scores (4d6 drop lowest, six times)
        abilities = {}
        ability_names = ['STR', 'DEX', 'CON', 'INT', 'WIS', 'CHA']

        for ability in ability_names:
            rolls = sorted([random.randint(1, 6) for _ in range(4)], reverse=True)
            abilities[ability] = sum(rolls[:3])  # Take top 3

        # Apply racial bonuses
        race_data = self.races[race]
        for ability, bonus in race_data['ability_bonus'].items():
            if ability == 'all':
                for ab in ability_names:
                    abilities[ab] += bonus
            else:
                abilities[ability] = abilities.get(ability, 10) + bonus

        # Create character
        class_data = self.classes[class_name]
        max_hp = class_data['hit_die'] + self._get_modifier(abilities['CON'])

        character = {
            'name': char_name,
            'race': race,
            'class': class_name,
            'background': background,
            'level': 1,
            'xp': 0,
            'abilities': abilities,
            'hp': max_hp,
            'max_hp': max_hp,
            'ac': 10 + self._get_modifier(abilities['DEX']),
            'proficiency_bonus': 2,
            'speed': race_data['speed'],
            'traits': race_data['traits'],
            'inventory': self._get_starting_equipment(class_name),
            'gold': self._roll_dice('4d4') * 10,
            'spells_known': [] if class_data.get('spellcaster') else None,
            'spell_slots': self._get_spell_slots(class_name, 1) if class_data.get('spellcaster') else None,
            'conditions': [],
            'death_saves': {'successes': 0, 'failures': 0}
        }

        # Save character
        game_state = {
            'character': character,
            'location': 'Character Creation',
            'story_state': 'new',
            'quests': [],
            'npcs': {},
            'combat': None,
            'history': [],
            'created_at': datetime.now().isoformat()
        }

        self._save_game_state('current', game_state)

        # Format character sheet
        output = f"""⚔️ CHARACTER CREATED! ⚔️

🎭 {char_name}
Race: {race} | Class: {class_name} | Level {character['level']}
Background: {background}

📊 ABILITY SCORES:
  STR: {abilities['STR']} ({self._format_modifier(abilities['STR'])})
  DEX: {abilities['DEX']} ({self._format_modifier(abilities['DEX'])})
  CON: {abilities['CON']} ({self._format_modifier(abilities['CON'])})
  INT: {abilities['INT']} ({self._format_modifier(abilities['INT'])})
  WIS: {abilities['WIS']} ({self._format_modifier(abilities['WIS'])})
  CHA: {abilities['CHA']} ({self._format_modifier(abilities['CHA'])})

💪 COMBAT STATS:
  HP: {character['hp']}/{character['max_hp']}
  AC: {character['ac']}
  Speed: {character['speed']} ft
  Proficiency: +{character['proficiency_bonus']}

🎒 STARTING EQUIPMENT:
{chr(10).join([f"  • {item}" for item in character['inventory'][:5]])}
  • {character['gold']} gold pieces

✨ RACIAL TRAITS:
{chr(10).join([f"  • {trait}" for trait in character['traits']])}

{f"📖 SPELLCASTING: {class_name} is a spellcaster!" if class_data.get('spellcaster') else ''}

🎲 Ready to begin your adventure! Use 'start_campaign' to choose your quest!"""

        return output

    def _start_campaign(self, kwargs: Dict[str, Any]) -> str:
        """Start a new campaign"""
        campaign_type = kwargs.get('campaign_type', 'classic_fantasy')

        # Load character
        game_state = self._load_game_state('current')
        if not game_state or not game_state.get('character'):
            return "❌ No character found! Create a character first using 'create_character'."

        character = game_state['character']

        # Generate campaign introduction based on type
        campaign_intros = {
            'classic_fantasy': {
                'location': 'The Prancing Pony Inn, Greendale Village',
                'hook': f"""You find yourself in the warm common room of the Prancing Pony, a cozy inn in the peaceful village of Greendale.

The innkeeper, a portly halfling named Tobias Goodbarrel, waves you over urgently. "Adventurer! Thank the gods you're here. Strange things have been happening in the old ruins north of town. Livestock going missing, strange lights at night, and poor farmer Elara's daughter hasn't returned from picking herbs near the ruins three days ago!"

He slides a small pouch across the bar. "The village council has pooled 50 gold pieces as a reward for anyone brave enough to investigate. Will you help us?"

Your character {character['name']}, a {character['race']} {character['class']}, considers the request..."""
            },
            'dark_gothic': {
                'location': 'Castle Ravenloft Approach, Barovia',
                'hook': f"""Mist clings to everything as you approach the looming silhouette of Castle Ravenloft. The villagers of Barovia spoke in hushed, fearful tones of the vampire lord who rules these cursed lands.

You clutch the old letter that brought you here - a plea for help from Ireena Kolyana, written in desperate, shaking script. The castle gates stand ominously open, as if inviting you to your doom.

As a {character['race']} {character['class']}, {character['name']}, you've faced many dangers... but something about this place chills you to your very soul.

Do you enter the castle, or investigate the nearby village first?"""
            },
            'high_seas': {
                'location': 'Port Blackwater, The Pirate Isles',
                'hook': f"""The salt spray stings your face as you stand on the docks of Port Blackwater, the most notorious pirate haven in the Isles.

Captain Redbeard's ship, The Crimson Skull, is recruiting crew for an expedition to the legendary Isles of Mist - said to hold the treasure of the ancient Sea Kings. The catch? No one who's sailed there has ever returned.

Your past as a {character['race']} {character['class']} has prepared you for danger, but this... this might be the greatest adventure of your life, {character['name']}.

The captain eyes you from the gangplank. "Well? You got what it takes, or are ye just another land-lubber?"

What do you do?"""
            },
            'urban_intrigue': {
                'location': 'The Gilt District, City of Waterdeep',
                'hook': f"""The crowded streets of Waterdeep's Gilt District bustle with nobles, merchants, and those who prey upon them. You've been hired by Lady Silverhand to investigate a series of murders targeting members of the Merchant's Guild.

The killer leaves no evidence, no witnesses, only a black rose at each scene. The City Watch is baffled, and the nobles are growing paranoid.

As {character['name']}, a {character['race']} {character['class']}, you've been given access to the latest crime scene - the mansion of Lord Thornhill, found dead in his locked study just this morning.

Your investigation begins now..."""
            }
        }

        campaign_data = campaign_intros.get(campaign_type, campaign_intros['classic_fantasy'])

        # Update game state
        game_state['location'] = campaign_data['location']
        game_state['story_state'] = 'active'
        game_state['campaign_type'] = campaign_type
        game_state['quests'] = [{
            'name': 'Main Quest: ' + ('The Missing Girl' if campaign_type == 'classic_fantasy' else 'Investigate the Mystery'),
            'status': 'active',
            'description': campaign_data['hook'][:100] + '...'
        }]

        self._save_game_state('current', game_state)

        output = f"""🗺️ CAMPAIGN START: {campaign_type.replace('_', ' ').title()} 🗺️

📍 Location: {campaign_data['location']}

{campaign_data['hook']}

💡 WHAT DO YOU DO?
Use 'take_action' to describe what you want to do
Examples:
  • "I want to investigate the ruins"
  • "I speak to the innkeeper for more information"
  • "I check my equipment and prepare for the journey"
  • "I look around the room for other adventurers"

🎲 The adventure begins!"""

        return output

    def _take_action(self, kwargs: Dict[str, Any]) -> str:
        """Take an action in the game"""
        description = kwargs.get('description', '')

        if not description:
            return "❌ You must describe what you want to do! Example: 'I search the room for clues'"

        # Load game state
        game_state = self._load_game_state('current')
        if not game_state:
            return "❌ No active game found! Start a new campaign first."

        character = game_state['character']

        # Check if in combat
        if game_state.get('combat'):
            return "⚔️ You're in combat! Use 'combat_action' instead. Current enemies: " + \
                   ", ".join([e['name'] for e in game_state['combat']['enemies']])

        # Generate narrative response using AI
        narrative = self._generate_narrative(game_state, description)

        # Check if action triggers combat or skill check
        if self._should_trigger_combat(description, game_state):
            combat_result = self._initiate_combat(game_state, description)
            return narrative + "\n\n" + combat_result

        # Check for skill check requirements
        skill_check = self._check_for_skill_requirement(description)
        if skill_check:
            roll_result = self._perform_skill_check(character, skill_check)
            narrative += f"\n\n{roll_result}"

        # Update history
        game_state['history'].append({
            'action': description,
            'result': narrative,
            'timestamp': datetime.now().isoformat()
        })

        self._save_game_state('current', game_state)

        return narrative

    def _combat_action(self, kwargs: Dict[str, Any]) -> str:
        """Perform a combat action"""
        description = kwargs.get('description', '')
        target = kwargs.get('target', '')
        spell_name = kwargs.get('spell_name', '')

        game_state = self._load_game_state('current')
        if not game_state:
            return "❌ No active game found!"

        if not game_state.get('combat'):
            return "❌ You're not in combat! Use 'take_action' for non-combat actions."

        character = game_state['character']
        combat = game_state['combat']

        # Determine action type
        if spell_name:
            return self._cast_spell_in_combat(character, combat, spell_name, target, game_state)
        elif 'attack' in description.lower() or target:
            return self._perform_attack(character, combat, target, game_state)
        elif 'dodge' in description.lower():
            return self._combat_dodge(character, combat, game_state)
        elif 'disengage' in description.lower():
            return self._combat_disengage(character, combat, game_state)
        else:
            return self._general_combat_action(character, combat, description, game_state)

    def _perform_attack(self, character: Dict, combat: Dict, target: str, game_state: Dict) -> str:
        """Perform an attack in combat"""
        # Find target enemy
        enemy = None
        for e in combat['enemies']:
            if target.lower() in e['name'].lower() and e['hp'] > 0:
                enemy = e
                break

        if not enemy:
            alive_enemies = [e['name'] for e in combat['enemies'] if e['hp'] > 0]
            return f"❌ Target not found! Available enemies: {', '.join(alive_enemies)}"

        # Roll attack
        attack_bonus = self._get_attack_bonus(character)
        attack_roll = self._roll_dice('1d20') + attack_bonus

        output = f"🎲 {character['name']} attacks {enemy['name']}!\n"
        output += f"Attack roll: {attack_roll} (d20 + {attack_bonus})\n"

        if attack_roll >= enemy['ac']:
            # Hit! Roll damage
            damage_die = '1d8'  # Basic weapon
            if character['class'] in ['Fighter', 'Paladin', 'Barbarian']:
                damage_die = '1d10'  # Great weapon
            elif character['class'] == 'Rogue':
                damage_die = '1d6'  # Finesse weapon

            damage = self._roll_dice(damage_die) + self._get_modifier(character['abilities']['STR'])

            # Rogue sneak attack
            if character['class'] == 'Rogue' and damage > 0:
                sneak_damage = self._roll_dice(f"{(character['level'] + 1) // 2}d6")
                damage += sneak_damage
                output += f"💀 Sneak Attack! +{sneak_damage} damage!\n"

            enemy['hp'] -= damage
            output += f"⚔️ HIT! {damage} damage dealt!\n"
            output += f"{enemy['name']}: {max(0, enemy['hp'])}/{enemy['max_hp']} HP\n"

            if enemy['hp'] <= 0:
                output += f"\n💀 {enemy['name']} has been defeated!\n"
                xp_gained = enemy.get('xp', 50)
                character['xp'] += xp_gained
                output += f"✨ +{xp_gained} XP\n"
        else:
            output += f"❌ MISS! The attack fails to connect.\n"

        # Check if combat is over
        if all(e['hp'] <= 0 for e in combat['enemies']):
            game_state['combat'] = None
            output += "\n🎉 Victory! Combat has ended.\n"
            self._save_game_state('current', game_state)
            return output

        # Enemy turn
        output += "\n--- Enemy Turn ---\n"
        for enemy in combat['enemies']:
            if enemy['hp'] > 0:
                enemy_attack = self._enemy_attack(enemy, character)
                output += enemy_attack + "\n"

        self._save_game_state('current', game_state)
        return output

    def _enemy_attack(self, enemy: Dict, character: Dict) -> str:
        """Enemy attacks the character"""
        attack_roll = self._roll_dice('1d20') + enemy.get('attack_bonus', 3)

        output = f"🗡️ {enemy['name']} attacks {character['name']}!\n"
        output += f"Attack roll: {attack_roll}\n"

        if attack_roll >= character['ac']:
            damage = self._roll_dice(enemy.get('damage_die', '1d6')) + enemy.get('damage_bonus', 1)
            character['hp'] -= damage
            output += f"💥 HIT! You take {damage} damage!\n"
            output += f"Your HP: {max(0, character['hp'])}/{character['max_hp']}\n"

            if character['hp'] <= 0:
                output += "\n💀 You have fallen! Make death saving throws or use 'rest' if you have healing potions..."
        else:
            output += f"🛡️ MISS! You dodge the attack!"

        return output

    def _check_stats(self, kwargs: Dict[str, Any]) -> str:
        """Display character sheet"""
        game_state = self._load_game_state('current')
        if not game_state or not game_state.get('character'):
            return "❌ No character found! Create one first with 'create_character'."

        char = game_state['character']

        output = f"""📜 CHARACTER SHEET 📜

🎭 {char['name']}
{char['race']} {char['class']} • Level {char['level']}
XP: {char['xp']}/{ self._xp_for_level(char['level'] + 1)}

📊 ABILITIES:
  STR {char['abilities']['STR']} ({self._format_modifier(char['abilities']['STR'])})
  DEX {char['abilities']['DEX']} ({self._format_modifier(char['abilities']['DEX'])})
  CON {char['abilities']['CON']} ({self._format_modifier(char['abilities']['CON'])})
  INT {char['abilities']['INT']} ({self._format_modifier(char['abilities']['INT'])})
  WIS {char['abilities']['WIS']} ({self._format_modifier(char['abilities']['WIS'])})
  CHA {char['abilities']['CHA']} ({self._format_modifier(char['abilities']['CHA'])})

💪 COMBAT:
  HP: {char['hp']}/{char['max_hp']}
  AC: {char['ac']}
  Speed: {char['speed']} ft
  Proficiency: +{char['proficiency_bonus']}

💰 Gold: {char['gold']} gp

📍 Location: {game_state.get('location', 'Unknown')}

{f"⚔️ IN COMBAT with {', '.join([e['name'] for e in game_state['combat']['enemies']])}!" if game_state.get('combat') else ''}"""

        return output

    def _check_inventory(self, kwargs: Dict[str, Any]) -> str:
        """Display inventory"""
        game_state = self._load_game_state('current')
        if not game_state:
            return "❌ No active game found!"

        char = game_state['character']

        output = f"""🎒 INVENTORY - {char['name']}

💰 Gold: {char['gold']} gp

📦 ITEMS:
"""
        for i, item in enumerate(char['inventory'], 1):
            output += f"{i}. {item}\n"

        if not char['inventory']:
            output += "  (empty)\n"

        return output

    def _check_spells(self, kwargs: Dict[str, Any]) -> str:
        """Display spellbook and spell slots"""
        game_state = self._load_game_state('current')
        if not game_state:
            return "❌ No active game found!"

        char = game_state['character']

        if not char.get('spells_known'):
            return f"❌ {char['class']} is not a spellcasting class!"

        output = f"""📖 SPELLBOOK - {char['name']}

🔮 SPELL SLOTS:
"""
        for level, slots in char['spell_slots'].items():
            used = slots.get('used', 0)
            max_slots = slots.get('max', 0)
            output += f"  Level {level}: {'●' * (max_slots - used)}{'○' * used} ({max_slots - used}/{max_slots})\n"

        output += f"\n📚 SPELLS KNOWN:\n"
        if char['spells_known']:
            for spell in char['spells_known']:
                output += f"  • {spell}\n"
        else:
            output += "  (Learn spells as you level up)\n"

        return output

    def _rest(self, kwargs: Dict[str, Any]) -> str:
        """Take a rest to recover"""
        description = kwargs.get('description', 'short')

        game_state = self._load_game_state('current')
        if not game_state:
            return "❌ No active game found!"

        char = game_state['character']

        if 'long' in description.lower():
            # Long rest: full HP and spell slot recovery
            char['hp'] = char['max_hp']
            if char.get('spell_slots'):
                for level in char['spell_slots']:
                    char['spell_slots'][level]['used'] = 0

            self._save_game_state('current', game_state)

            return f"""🏕️ LONG REST

{char['name']} finds a safe place to rest for 8 hours.

✨ HP restored to {char['max_hp']}
✨ All spell slots recovered
✨ Abilities refreshed

You wake feeling refreshed and ready for adventure!"""
        else:
            # Short rest: partial HP recovery
            hit_die = self.classes[char['class']]['hit_die']
            healing = self._roll_dice(f"1d{hit_die}") + self._get_modifier(char['abilities']['CON'])
            char['hp'] = min(char['hp'] + healing, char['max_hp'])

            self._save_game_state('current', game_state)

            return f"""🛑 SHORT REST

{char['name']} takes a brief respite (1 hour).

💚 Recovered {healing} HP
💚 Current HP: {char['hp']}/{char['max_hp']}

Some abilities have been refreshed!"""

    def _roll_dice(self, dice_str: str) -> int:
        """Roll dice (e.g., '1d20', '2d6+3')"""
        try:
            # Parse dice notation
            match = re.match(r'(\d+)d(\d+)([+-]\d+)?', dice_str.lower())
            if not match:
                return 0

            num_dice = int(match.group(1))
            die_size = int(match.group(2))
            modifier = int(match.group(3)) if match.group(3) else 0

            total = sum(random.randint(1, die_size) for _ in range(num_dice)) + modifier
            return max(1, total)
        except:
            return 0

    def _get_modifier(self, ability_score: int) -> int:
        """Calculate ability modifier"""
        return (ability_score - 10) // 2

    def _format_modifier(self, ability_score: int) -> str:
        """Format modifier with + or - sign"""
        mod = self._get_modifier(ability_score)
        return f"+{mod}" if mod >= 0 else str(mod)

    def _get_attack_bonus(self, character: Dict) -> int:
        """Calculate attack bonus"""
        primary_stat = self.classes[character['class']]['primary']
        return self._get_modifier(character['abilities'][primary_stat]) + character['proficiency_bonus']

    def _get_starting_equipment(self, class_name: str) -> List[str]:
        """Get starting equipment for a class"""
        equipment = {
            'Fighter': ['Longsword', 'Shield', 'Chain mail', 'Backpack', 'Rope (50 ft)', 'Rations (10 days)'],
            'Wizard': ['Spellbook', 'Component pouch', 'Quarterstaff', 'Robes', 'Backpack', 'Ink and quill'],
            'Rogue': ['Rapier', 'Shortbow', 'Arrows (20)', 'Leather armor', "Thieves' tools", 'Backpack'],
            'Cleric': ['Mace', 'Shield', 'Scale mail', 'Holy symbol', 'Prayer book', 'Backpack'],
            'Ranger': ['Longbow', 'Arrows (20)', 'Shortsword', 'Leather armor', 'Backpack', 'Rope (50 ft)'],
            'Paladin': ['Longsword', 'Shield', 'Chain mail', 'Holy symbol', 'Backpack', 'Rations (10 days)']
        }
        return equipment.get(class_name, ['Dagger', 'Backpack', 'Rope (50 ft)', 'Rations (10 days)'])

    def _get_spell_slots(self, class_name: str, level: int) -> Dict:
        """Get spell slots for a spellcasting class"""
        if level == 1:
            return {
                '1': {'max': 2, 'used': 0}
            }
        return {}

    def _generate_narrative(self, game_state: Dict, action: str) -> str:
        """Generate narrative response using AI"""
        if not self.client:
            return f"You {action}. The DM nods thoughtfully at your action."

        character = game_state['character']
        location = game_state.get('location', 'unknown location')

        prompt = f"""You are an expert Dungeon Master running a D&D 5e campaign.

CHARACTER: {character['name']}, Level {character['level']} {character['race']} {character['class']}
LOCATION: {location}
PLAYER ACTION: {action}

Generate a vivid, engaging narrative response (2-3 sentences) that:
1. Describes what happens when the character performs this action
2. Includes sensory details (sights, sounds, smells)
3. Advances the story or reveals information
4. Maintains a BG3-level of storytelling quality

Be dramatic, immersive, and compelling!"""

        try:
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.85,
                max_tokens=200
            )
            return response.choices[0].message.content.strip()
        except:
            return f"You {action}. The world responds to your actions..."

    def _should_trigger_combat(self, action: str, game_state: Dict) -> bool:
        """Determine if action should trigger combat"""
        combat_keywords = ['attack', 'fight', 'strike', 'charge', 'ambush']
        return any(keyword in action.lower() for keyword in combat_keywords)

    def _initiate_combat(self, game_state: Dict, trigger_action: str) -> str:
        """Start a combat encounter"""
        # Generate enemies based on character level
        character = game_state['character']
        level = character['level']

        # Sample enemies
        enemy_types = [
            {'name': 'Goblin', 'hp': 7, 'max_hp': 7, 'ac': 15, 'attack_bonus': 4, 'damage_die': '1d6', 'damage_bonus': 2, 'xp': 50},
            {'name': 'Orc', 'hp': 15, 'max_hp': 15, 'ac': 13, 'attack_bonus': 5, 'damage_die': '1d12', 'damage_bonus': 3, 'xp': 100},
            {'name': 'Skeleton', 'hp': 13, 'max_hp': 13, 'ac': 13, 'attack_bonus': 4, 'damage_die': '1d6', 'damage_bonus': 2, 'xp': 50}
        ]

        num_enemies = min(level, 3)
        enemies = random.choices(enemy_types, k=num_enemies)

        game_state['combat'] = {
            'round': 1,
            'enemies': enemies,
            'initiative': self._roll_dice('1d20') + self._get_modifier(character['abilities']['DEX'])
        }

        self._save_game_state('current', game_state)

        output = f"""⚔️ COMBAT INITIATED! ⚔️

{', '.join([e['name'] for e in enemies])} appear before you!

🎲 Roll for initiative: {game_state['combat']['initiative']}

💡 COMBAT OPTIONS:
• Use 'combat_action' with target: "attack the goblin"
• Cast spells: "cast magic missile at the orc"
• Dodge, Disengage, or take other actions

--- YOUR TURN ---"""

        return output

    def _check_for_skill_requirement(self, action: str) -> Optional[str]:
        """Check if action requires a skill check"""
        skill_keywords = {
            'search': 'Perception',
            'sneak': 'Stealth',
            'persuade': 'Persuasion',
            'deceive': 'Deception',
            'intimidate': 'Intimidation',
            'climb': 'Athletics',
            'jump': 'Athletics',
            'investigate': 'Investigation'
        }

        for keyword, skill in skill_keywords.items():
            if keyword in action.lower():
                return skill
        return None

    def _perform_skill_check(self, character: Dict, skill: str) -> str:
        """Perform a skill check"""
        # Map skills to abilities
        skill_abilities = {
            'Perception': 'WIS',
            'Stealth': 'DEX',
            'Persuasion': 'CHA',
            'Deception': 'CHA',
            'Intimidation': 'CHA',
            'Athletics': 'STR',
            'Investigation': 'INT',
            'Insight': 'WIS',
            'Arcana': 'INT'
        }

        ability = skill_abilities.get(skill, 'DEX')
        modifier = self._get_modifier(character['abilities'][ability])
        roll = self._roll_dice('1d20')
        total = roll + modifier + character['proficiency_bonus']

        dc = 15  # Default difficulty

        if total >= dc:
            return f"🎲 {skill} check: {total} (d20: {roll} + {modifier + character['proficiency_bonus']}) - SUCCESS!"
        else:
            return f"🎲 {skill} check: {total} (d20: {roll} + {modifier + character['proficiency_bonus']}) - FAILURE!"

    def _xp_for_level(self, level: int) -> int:
        """XP required for a level"""
        xp_table = [0, 300, 900, 2700, 6500, 14000, 23000, 34000, 48000, 64000, 85000]
        return xp_table[min(level, len(xp_table) - 1)]

    def _save_game_state(self, save_name: str, game_state: Dict):
        """Save game state to storage"""
        try:
            saves_data = self.storage_manager.read_file('dnd_saves', 'saves.json')
            saves = json.loads(saves_data) if saves_data else {}

            saves[save_name] = game_state

            self.storage_manager.write_file(
                'dnd_saves',
                'saves.json',
                json.dumps(saves, indent=2)
            )
        except Exception as e:
            pass

    def _load_game_state(self, save_name: str) -> Optional[Dict]:
        """Load game state from storage"""
        try:
            saves_data = self.storage_manager.read_file('dnd_saves', 'saves.json')
            if not saves_data:
                return None

            saves = json.loads(saves_data)
            return saves.get(save_name)
        except:
            return None

    def _save_game(self, kwargs: Dict[str, Any]) -> str:
        """Save current game"""
        save_name = kwargs.get('save_name', f"save_{datetime.now().strftime('%Y%m%d_%H%M%S')}")

        game_state = self._load_game_state('current')
        if not game_state:
            return "❌ No active game to save!"

        self._save_game_state(save_name, game_state)

        return f"💾 Game saved as '{save_name}'! Use 'load_game' with save_name='{save_name}' to restore."

    def _load_game(self, kwargs: Dict[str, Any]) -> str:
        """Load a saved game"""
        save_name = kwargs.get('save_name', 'current')

        game_state = self._load_game_state(save_name)
        if not game_state:
            return f"❌ Save file '{save_name}' not found!"

        self._save_game_state('current', game_state)

        char = game_state['character']
        return f"""💾 Game loaded!

Welcome back, {char['name']}!
Location: {game_state.get('location', 'Unknown')}
HP: {char['hp']}/{char['max_hp']}

Your adventure continues..."""

    def _continue_game(self, kwargs: Dict[str, Any]) -> str:
        """Continue the current game"""
        game_state = self._load_game_state('current')
        if not game_state:
            return "❌ No active game found! Start a new campaign or create a character."

        char = game_state['character']
        location = game_state.get('location', 'Unknown')

        # Generate continuation narrative
        if self.client:
            prompt = f"""Generate a brief (2 sentences) reminder of where {char['name']} (Level {char['level']} {char['race']} {char['class']}) is and what they were doing.
Location: {location}
Make it atmospheric and engaging!"""

            try:
                response = self.client.chat.completions.create(
                    model=self.deployment_name,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.8,
                    max_tokens=100
                )
                narrative = response.choices[0].message.content.strip()
            except:
                narrative = f"You find yourself in {location}, ready to continue your adventure."
        else:
            narrative = f"You find yourself in {location}, ready to continue your adventure."

        output = f"""🗺️ WELCOME BACK, {char['name'].upper()}! 🗺️

{narrative}

📊 STATUS:
  HP: {char['hp']}/{char['max_hp']}
  Level: {char['level']}
  Gold: {char['gold']} gp

{f"⚔️ You are in COMBAT!" if game_state.get('combat') else ''}

💡 What do you do? Use 'take_action' to continue your adventure!"""

        return output

    def _talk_to_npc(self, kwargs: Dict[str, Any]) -> str:
        """Talk to an NPC"""
        description = kwargs.get('description', '')
        target = kwargs.get('target', 'stranger')

        game_state = self._load_game_state('current')
        if not game_state:
            return "❌ No active game found!"

        if not self.client:
            return f"You speak with {target}. They respond thoughtfully to your words."

        character = game_state['character']
        location = game_state.get('location', 'unknown')

        prompt = f"""You are a D&D NPC in {location}. The player ({character['name']}, a {character['race']} {character['class']}) wants to talk.

Player says: "{description}"
NPC ({target}):

Generate a 2-3 sentence response that is:
1. In-character and immersive
2. Advances the story or provides useful information
3. Reflects the NPC's personality

Be vivid and engaging!"""

        try:
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.9,
                max_tokens=150
            )
            npc_response = response.choices[0].message.content.strip()

            return f"""💬 Conversation with {target}

You: "{description}"

{target}: "{npc_response}"

💡 Continue the conversation or use 'take_action' to do something else."""
        except:
            return f"{target} listens to your words and nods thoughtfully."

    def _check_quests(self, kwargs: Dict[str, Any]) -> str:
        """Display active quests"""
        game_state = self._load_game_state('current')
        if not game_state:
            return "❌ No active game found!"

        quests = game_state.get('quests', [])

        if not quests:
            return "📜 No active quests. Explore and talk to NPCs to find adventures!"

        output = "📜 ACTIVE QUESTS:\n\n"
        for i, quest in enumerate(quests, 1):
            status_icon = "✅" if quest.get('status') == 'completed' else "🔄"
            output += f"{status_icon} {quest['name']}\n"
            output += f"   {quest.get('description', 'No description')}\n\n"

        return output

    def _combat_dodge(self, character: Dict, combat: Dict, game_state: Dict) -> str:
        """Dodge action in combat"""
        output = f"🛡️ {character['name']} takes the Dodge action!\n"
        output += "Attacks against you have disadvantage until your next turn.\n\n"

        # Enemy turn
        output += "--- Enemy Turn ---\n"
        for enemy in combat['enemies']:
            if enemy['hp'] > 0:
                output += f"{enemy['name']} attacks but you're dodging! (Disadvantage)\n"
                # Roll twice, take lower
                roll1 = self._roll_dice('1d20') + enemy.get('attack_bonus', 3)
                roll2 = self._roll_dice('1d20') + enemy.get('attack_bonus', 3)
                attack_roll = min(roll1, roll2)

                if attack_roll >= character['ac']:
                    damage = self._roll_dice(enemy.get('damage_die', '1d6'))
                    character['hp'] -= damage
                    output += f"💥 Hit despite your dodge! {damage} damage!\n"
                else:
                    output += f"🛡️ Missed! Your dodge worked!\n"

        self._save_game_state('current', game_state)
        return output

    def _combat_disengage(self, character: Dict, combat: Dict, game_state: Dict) -> str:
        """Disengage action in combat"""
        return "🏃 You disengage from combat, avoiding opportunity attacks! You can move away safely.\nUse 'take_action' to describe where you go."

    def _general_combat_action(self, character: Dict, combat: Dict, description: str, game_state: Dict) -> str:
        """Handle general combat actions"""
        return f"You attempt to {description} in combat. The DM considers your action...\n(Use specific combat actions like 'attack', 'dodge', or 'disengage' for mechanical effects)"

    def _cast_spell_in_combat(self, character: Dict, combat: Dict, spell_name: str, target: str, game_state: Dict) -> str:
        """Cast a spell in combat"""
        if not character.get('spells_known'):
            return "❌ You don't have spellcasting abilities!"

        # Simplified spell casting
        spell_slots = character.get('spell_slots', {})
        if not spell_slots.get('1', {}).get('max', 0):
            return "❌ No spell slots available!"

        used = spell_slots['1'].get('used', 0)
        max_slots = spell_slots['1'].get('max', 0)

        if used >= max_slots:
            return "❌ No spell slots remaining! Take a long rest to recover."

        # Use spell slot
        spell_slots['1']['used'] = used + 1

        # Find target
        enemy = None
        for e in combat['enemies']:
            if target.lower() in e['name'].lower() and e['hp'] > 0:
                enemy = e
                break

        if not enemy:
            return f"❌ Target not found!"

        # Cast spell (simplified)
        damage = self._roll_dice('3d4') + self._get_modifier(character['abilities']['INT'])
        enemy['hp'] -= damage

        output = f"✨ You cast {spell_name} at {enemy['name']}!\n"
        output += f"💥 {damage} magical damage!\n"
        output += f"{enemy['name']}: {max(0, enemy['hp'])}/{enemy['max_hp']} HP\n"

        if enemy['hp'] <= 0:
            output += f"💀 {enemy['name']} has been defeated!\n"

        self._save_game_state('current', game_state)
        return output

    def _level_up(self, kwargs: Dict[str, Any]) -> str:
        """Level up the character"""
        game_state = self._load_game_state('current')
        if not game_state:
            return "❌ No active game found!"

        char = game_state['character']
        next_level_xp = self._xp_for_level(char['level'] + 1)

        if char['xp'] < next_level_xp:
            return f"❌ Not enough XP! You need {next_level_xp - char['xp']} more XP to reach level {char['level'] + 1}."

        # Level up!
        char['level'] += 1

        # Increase HP
        hit_die = self.classes[char['class']]['hit_die']
        hp_increase = self._roll_dice(f"1d{hit_die}") + self._get_modifier(char['abilities']['CON'])
        char['max_hp'] += hp_increase
        char['hp'] = char['max_hp']

        # Increase proficiency at certain levels
        if char['level'] in [5, 9, 13, 17]:
            char['proficiency_bonus'] += 1

        # Add spell slot if spellcaster
        if char.get('spell_slots') and char['level'] in [2, 3]:
            if str(char['level'] - 1) not in char['spell_slots']:
                char['spell_slots'][str(char['level'] - 1)] = {'max': 2, 'used': 0}

        self._save_game_state('current', game_state)

        return f"""🎉 LEVEL UP! 🎉

{char['name']} has reached Level {char['level']}!

✨ Max HP increased by {hp_increase} (now {char['max_hp']})
✨ HP fully restored!
{f"✨ Proficiency bonus increased to +{char['proficiency_bonus']}" if char['level'] in [5, 9, 13, 17] else ''}
{f"✨ New spell slot unlocked!" if char.get('spell_slots') and char['level'] in [2, 3] else ''}

You feel more powerful and capable!"""
