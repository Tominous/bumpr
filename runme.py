import datetime
import discord
import json
import logging
import os
import time
from discord.ext import commands
from jishaku import help_command

ran = {"time": time.time(), "datetime": datetime.datetime.utcnow()}


def get_prefix(_bot, message):
	prefixes = ['b-', 'B-']
	if message.guild:  # dm compat
		with open('./data/prefixes.json', 'r') as rprefixes:
			data = json.load(rprefixes)
			if str(message.guild.id) in data.keys():
				for prefix in data[str(message.guild.id)]:
					if prefix in prefixes:
						if prefix == str(_bot.user.mention) + ' ':
							continue
						else:
							prefixes.remove(prefix)
							continue
					prefixes.append(prefix)
	return commands.when_mentioned_or(*prefixes)(_bot, message)


bot = commands.Bot(command_prefix=get_prefix, help_command=help_command.MinimalEmbedPaginatorHelp(),
                   description="A Modern bumping/advertising bot that will grow your server quickly!",
                   case_insensitive=True, status=discord.Status.dnd, owner_ids=[421698654189912064, 317731855317336067])
bot.autobumping = {}
bot.on_cooldown = {}

exts = [
	'cogs.core',
	'cogs.misc',
	'cogs.newsletter',
	'cogs.owner',
	'jishaku'
]


@bot.event
async def on_ready():
	bot.ran = ran
	bot.logged_in_at = {"time": time.time(), "datetime": datetime.datetime.utcnow()}
	bot.bumps_since_reboot = 0
	print(f"Logged in as {bot.user.display_name}, {len(bot.guilds)} guilds.")
	for cog in exts:
		try:
			bot.load_extension(cog)
		except:
			continue


with open("./token.txt") as tokenfile:
	bot.run(tokenfile.readlines()[0])
