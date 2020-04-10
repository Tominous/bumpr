"""
Core cog provides stuff for actually bumping your server.
"""
import asyncio
import datetime
import discord
import json
import traceback
from discord.ext import commands, tasks

from .utils import checks
from .utils.config import read, write, get_guild_data
from .utils.converters import get_rank, fix_time

started = datetime.datetime(2019, 9, 4, 3, 7, 41, 301689)


# noinspection PyCallingNonCallable
class Core(commands.Cog):
	"""Core cog, provides bump and basic configuration commands"""

	def __init__(self, bot):
		self.bot = bot
		self.bot.speakers = {
			"no_lines": "\U0001f508",
			"one_line": "\U0001f509",
			"full": "\U0001f50a",
			"mute": "\U0001f507",
			"loop": "\U0001f501",
			"stop": "\U000026d4"
		}
		self.do_autobump.start()
		self.cooling = False
		self.error_responses = {
			commands.CommandOnCooldown: "You are on a cooldown to prevent abuse. try again in a few seconds.",
			commands.BotMissingPermissions: "Im missing some permissions. try running `{ctx.prefix}debug` to see if i "
			                                "have all REQUIRED set to tick.",
			commands.MissingPermissions: "You are missing the following permissions:\n```md\n{resolved_missing)\n```"
		}
		self.bot.reminding = {}

	def cog_unload(self):
		self.cooling = True
		asyncio.run_coroutine_threadsafe(asyncio.sleep(10), self.bot.loop)
		try:
			self.do_autobump.stop()
		except:
			pass

	async def get_bump_channel(self, guild: discord.Guild):
		with open('./data/bumpchannels.json', 'r') as a:
			data = json.load(a)
			if str(guild.id) in data.keys():
				channel = self.bot.get_channel(data[str(guild.id)])
				if not channel:
					for c in guild.text_channels:
						if c.name.endswith('bump'):
							p = c.permissions_for(guild.me)
							if not p.embed_links or not p.send_messages or not p.read_messages or not p.read_message_history:
								continue
							else:
								return c
					else:
						return None
				else:
					return channel
			else:
				for c in guild.text_channels:
					if c.name.endswith('bump'):
						p = c.permissions_for(guild.me)
						if not p.embed_links or not p.send_messages or not p.read_messages or not p.read_message_history:
							continue
						else:
							return c
				else:
					return None

	@tasks.loop(minutes=40)
	async def do_autobump(self):
		for guild in self.bot.guilds:
			_s = self.bot.autobumping.keys()

			if guild.id in self.bot.autobumping.keys():
				a = self.bot.autobumping[guild.id]
				ctx = a[0]
				msg = a[1]
				rank = a[2]
				autobump = a[3]
				invite = a[4]
				anon = a[5]

				await self.do_bump(ctx, message=msg, rank=rank, autobumped=autobump, invite=invite, anon=anon)

	async def do_cd(self, ctx, forlen: float = 3600):
		self.bot.on_cooldown[ctx.guild.id] = forlen
		while forlen > 0 and self.cooling is False:
			await asyncio.sleep(1)
			self.bot.on_cooldown[ctx.guild.id] -= 1
			forlen -= 1
		if self.cooling:
			self.bot.on_cooldown = {}  # reset cooldowns
		else:
			del self.bot.on_cooldown[ctx.guild.id]

	async def do_bump(self, ctx = None, *, guild: discord.Guild = None, message: str, rank: int = 0,
	                  autobumped: bool = True,
	                  invite: discord.Invite = None, sandbox: bool = False, anon: bool = False):
		"""Rank table:
		0 = regular (default)
		1 = Member
		2 = premium"""
		sent = []
		if ctx is None and guild is None:
			raise NameError("neither ctx nor guild were passed.")
		_guild = guild if guild else ctx.guild
		if len(message) > 600 and rank <= 0:
			raise ValueError("Regular users have a capped message size at 600 characters. Join my support "
			                 "server to get a cap of 700. (https://beta.dragdev.xyz/redirects/server.html)")
		elif len(message) > 700 and rank <= 1:
			raise ValueError("Members have a capped message size at 700 characters. Buy premium to get a cap of 1024!")
		else:  # we gucci
			try:
				_color, *content = message.split()
				color = await commands.ColourConverter().convert(ctx, _color)
				message = message.replace(_color, '')
			except (commands.BadArgument, ValueError):
				color = discord.Color.blurple()
			data = read('./data/leaderboard.json')
			if not anon and not autobumped:
				if str(ctx.guild.id) not in data.keys():
					data[str(ctx.guild.id)] = {}
				if str(ctx.author.id) not in data[str(ctx.guild.id)].keys():
					data[str(ctx.guild.id)][str(ctx.author.id)] = 0
				data[str(ctx.guild.id)][str(ctx.author.id)] += 1
				write('./data/leaderboard.json', data)
			for guild in self.bot.guilds:
				channel = await self.get_bump_channel(guild)
				if channel is None:
					continue
				else:
					_ = {True: "autobumped", False: "bumped"}
					e = discord.Embed(
						title=f"Join '{_guild.name}' now!",
						url=invite.url,
						color=color,
						timestamp=datetime.datetime.utcnow(),
						description=message
					)
					if not anon:
						e.set_author(name=f'{_[autobumped]} by ' + ctx.author.display_name,
						             icon_url=ctx.author.avatar_url_as(static_format='png'))
					if _guild.icon_url:
						e.set_thumbnail(url=str(_guild.icon_url_as(static_format='png')))
					if sandbox:
						return [e, color, message, len(message)]
					try:
						messagethingy = await channel.send(embed=e)
						sent.append(messagethingy)
					except:
						continue
		if not anon and not autobumped:
			try:
				self.bot.dispatch("bump_done", ctx, ctx.author)
			except TypeError:
				pass
		self.bot.bumps_since_reboot += 1
		return len(sent)

	async def do_reminding(self, ctx):
		orig = self.bot.reminding[ctx.author][ctx.guild]
		while ctx.guild in self.bot.reminding[ctx.author].keys():
			self.bot.reminding[ctx.author][ctx.guild] -= 1
			if self.bot.reminding[ctx.author][ctx.guild] <= 0:
				if self.bot.on_cooldown.get(ctx.guild.id):
					await asyncio.sleep(self.bot.on_cooldown[ctx.guild.id] - 2)
				await ctx.send(f"{ctx.author.mention} Bump reminder! You can now bump.")

				def waitcheck(_ctx):
					return _ctx.command.name == "bump" and _ctx.guild == ctx.guild

				await self.bot.wait_for("command", check=waitcheck)
				self.bot.reminding[ctx.author][ctx.guild] = orig
			await asyncio.sleep(1)

	@commands.command()
	async def remind(self, ctx):
		"""A toggle command for bump reminders.

		This command is per-guild, meaning you can have many reminders per guild"""
		if self.bot.reminding.get(ctx.author) is None:
			self.bot.reminding[ctx.author] = {}
		if ctx.guild in self.bot.reminding.get(ctx.author):
			await ctx.send(self.bot.speakers["stop"] + " Disabled reminders")
			del self.bot.reminding[ctx.author][ctx.guild]
			if len(self.bot.reminding[ctx.author].keys()) == 0:
				del self.bot.reminding[ctx.author]
		else:
			cooldowns = {
				0: 60,
				1: 30,
				2: 10,
				5: 3600,
				6: 1080,
				7: 600
			}
			cooldown = cooldowns[get_rank(ctx.bot, ctx.author) + 5]
			now = datetime.datetime.utcnow()
			if all([now.day == 25, now.month == 12]):
				cooldown /= 5
			strcooldown = fix_time(cooldown)
			await ctx.send(self.bot.speakers["loop"] + " Enabled reminders. I will @ you every {} here.".format(
				strcooldown
			))
			if ctx.author not in self.bot.reminding.keys():
				self.bot.reminding[ctx.author] = {}
			self.bot.reminding[ctx.author][ctx.guild] = cooldown
			await self.do_reminding(ctx)

	@commands.command(aliases=['bp', 'p', 'preview', 'sandbox'])
	@commands.bot_has_permissions(embed_links=True, send_messages=True, create_instant_invite=True,
	                              manage_messages=True)
	async def bumppreview(self, ctx):
		"""Previews your bump message."""
		msg = await ctx.send(f"{self.bot.speakers['no_lines']} gathering statistics...")
		rank = get_rank(ctx.bot, ctx.author)
		bump_channel = await self.get_bump_channel(ctx.guild)
		if ctx.guild.system_channel is None:
			return await msg.edit(
				content=f"{self.bot.speakers['mute']} I was unable to find your guild's system channel."
				        f" Set one and try again.")
		elif not ctx.guild.system_channel.permissions_for(ctx.me).create_instant_invite:
			return await msg.edit(content=f"{self.bot.speakers['mute']} I was unable to create/restore the invite for"
			                              f" {ctx.guild.system_channel.mention} because of a lack of permissions!")
		if bump_channel is None:
			return await msg.edit(
				content=f"{self.bot.speakers['mute']} No channel named 'bump' or custom channel found.")
		tpic_len = len(str(bump_channel.topic))
		if tpic_len <= 100:
			return await msg.edit(content=f"{self.bot.speakers['mute']} Your ad is not longer then **100** characters!")
		i = await ctx.guild.system_channel.create_invite(unique=False, reason=f"Bumped by {ctx.author}")
		await msg.edit(content=f"{self.bot.speakers['one_line']} bumping your server...")
		sentto = await self.do_bump(ctx, message=bump_channel.topic, rank=rank, autobumped=False, invite=i,
		                            sandbox=True)
		e, color, message, _ = tuple(sentto)
		await msg.edit(content=f"{self.bot.speakers['full']} Here is your preview:", embed=e)

	@commands.command(aliases=['b', 'ad', 'partner'])
	@commands.bot_has_permissions(embed_links=True, send_messages=True, create_instant_invite=True,
	                              manage_messages=True)
	@commands.cooldown(1, 10, commands.BucketType.user)
	@commands.guild_only()
	async def bump(self, ctx, anonymous: bool = False):
		"""Bumps your server to other servers!
		set "Anonymous" to "true" to make it seem like i bumped it. this does not go into your lead count.
		Your partner message and basic statistics will be send to every guild the bot is in, assuming it has either a custom bump channel, or a channel named `bump`."""
		msg = None
		try:
			if ctx.guild.id in self.bot.on_cooldown.keys():
				ft = fix_time(self.bot.on_cooldown[ctx.guild.id])
				return await ctx.send(f"{self.bot.speakers['no_lines']} You are on cooldown! bump again in **{ft}!**")
			msg = await ctx.send(f"{self.bot.speakers['no_lines']} gathering statistics...")
			rank = get_rank(ctx.bot, ctx.author)
			bump_channel = await self.get_bump_channel(ctx.guild)
			if ctx.guild.system_channel is None:
				return await msg.edit(
					content=f"{self.bot.speakers['mute']} I was unable to find your guild's system channel."
					        f" Set one and try again.")
			elif not ctx.guild.system_channel.permissions_for(ctx.me).create_instant_invite:
				return await msg.edit(
					content=f"{self.bot.speakers['mute']} I was unable to create/restore the invite for"
					        f" {ctx.guild.system_channel.mention} because of a lack of permissions!")
			if bump_channel is None:
				return await msg.edit(
					content=f"{self.bot.speakers['mute']} No channel named 'bump' or custom channel found.")
			tpic_len = len(str(bump_channel.topic))
			if tpic_len <= 100:
				return await msg.edit(
					content=f"{self.bot.speakers['mute']} Your ad is not longer then **100** characters!")
			i = await ctx.guild.system_channel.create_invite(unique=False, reason=f"Bumped by {ctx.author}")
			await msg.edit(content=f"{self.bot.speakers['one_line']} bumping your server...")
			sentto = await self.do_bump(ctx, message=bump_channel.topic, rank=rank, autobumped=False, invite=i,
			                            anon=anonymous)
			okso = f"Bumped your server to **{sentto}** servers!"
			cooldowns = {
				0: 60,
				1: 30,
				2: 10,
				5: 3600,
				6: 1080,
				7: 600
			}
			cooldown = cooldowns[rank + 5]
			now = datetime.datetime.utcnow()
			if all([now.day == 25, now.month == 12]):
				cooldown /= 5
			strcooldown = fix_time(cooldown)
			okso += f"\n\nYou may bump again in **{strcooldown}**!"
			await msg.edit(content=okso)
			return await self.do_cd(ctx, cooldown)
		except (Exception, discord.HTTPException) as e:
			if msg:
				await msg.edit(
					content=f"{self.bot.speakers['mute']} An error occurred while bumping. Details will raise in 5 seconds.")
			else:
				pass
			raise

	@commands.group(aliases=['ab', 'aad', 'apartner', 'autopartner'], invoke_without_command=True, enabled=False)
	@commands.bot_has_permissions(embed_links=True, send_messages=True, create_instant_invite=True,
	                              manage_messages=True)
	@checks.is_premium()
	async def autobump(self, ctx, anonymous: bool = False):
		"""Makes your server automatically bump every 30 minutes.

		This command is premium only"""
		if ctx.guild.id in self.bot.autobumping.keys():
			return await ctx.send("You are already autobumping!\n\n*did you mean: `{}{} cancel`?*".format(
				ctx.prefix, ctx.command.qualified_name
			))
		msg = await ctx.send(f"{self.bot.speakers['no_lines']} gathering statistics...")
		rank = get_rank(ctx.bot, ctx.author)
		bump_channel = await self.get_bump_channel(ctx.guild)
		if ctx.guild.system_channel is None:
			return await msg.edit(
				content=f"{self.bot.speakers['mute']} I was unable to find your guild's system channel."
				        f" Set one and try again.")
		elif not ctx.guild.system_channel.permissions_for(ctx.me).create_instant_invite:
			return await msg.edit(content=f"{self.bot.speakers['mute']} I was unable to create/restore the invite for"
			                              f" {ctx.guild.system_channel.mention} because of a lack of permissions!")
		if bump_channel is None:
			return await msg.edit(
				content=f"{self.bot.speakers['mute']} No channel named 'bump' or custom channel found.")
		tpic_len = len(str(bump_channel.topic))
		if tpic_len <= 100:
			return await msg.edit(content=f"{self.bot.speakers['mute']} Your ad is not longer then **100** characters!")
		i = await ctx.guild.system_channel.create_invite(unique=False, reason=f"Bumped by {ctx.author}")
		await msg.edit(content=f"{self.bot.speakers['one_line']} sandboxing...")
		try:
			await self.do_bump(ctx, message=bump_channel.topic, rank=rank, autobumped=False, invite=i, sandbox=True,
			                   anon=anonymous)
		except ValueError as rest:
			return await msg.edit(content=f"{self.bot.speakers['mute']} A restriction was exceeded:\n`{str(rest)}`")
		except discord.Forbidden as f:
			return await msg.edit(
				content=f"{self.bot.speakers['mute']} A permissions error prevented me from bumping:\n`{str(f)}`")
		self.bot.autobumping[ctx.guild.id] = [ctx, bump_channel.topic, rank, True, i, anonymous]
		await msg.edit(
			content=f"{self.bot.speakers['full']} started autobumping your server. it will be bumped every 30"
			        f" minutes.")

	@autobump.command(name="cancel", aliases=['stop', 'quit'])
	async def autobump_cancel(self, ctx):
		"""Stops autobumping."""
		if ctx.guild.id not in self.bot.autobumping.keys():
			return await ctx.send("You aren't already autobumping!\n\n*did you mean: `{}{}`?*".format(
				ctx.prefix, ctx.command.parents[0].qualified_name
			))
		else:
			if not ctx.author.guild_permissions.manage_server and not get_rank(ctx.bot, ctx.author) == 2:
				return await ctx.send("You can't cancel autobumping.")
			del self.bot.autobumping[ctx.guild.id]
			return await ctx.send("Stopped autobumping.")

	@commands.command()
	async def invite(self, ctx):
		"""Get invite links for the bot."""
		return await ctx.send(discord.utils.oauth_url(ctx.bot.user.id, None, None, 'https://discord.gg/z2YArks'))

	@staticmethod
	def validate_message(message, *, rank: int):
		limits = {
			0: 450,
			1: 700,
			2: 1024  # discord limit
		}
		l = len(message)
		if l <= 100:
			raise ValueError("Bottom limit - ad not longer then 100 chars.")
		else:
			if l > limits[rank]:
				raise ValueError(f"Rank limit reached - {l}/{limits[rank]}")
		return True

	@commands.command(name="setup")
	@commands.has_permissions(manage_guild=True)
	@commands.bot_has_permissions(embed_links=True, manage_messages=True, manage_channels=True, manage_guild=True)
	async def setup(self, ctx):
		"""Sets up basic stuff."""
		colour = ''
		data = read('./data/bumpchannels.json')
		data[str(ctx.guild.id)] = None

		def ir(m):
			return m.author == ctx.author and m.channel == ctx.channel

		msg = await ctx.send("Welcome to setup! say `--exit` to stop the setup."
		                     f"\n\nFirst step: Setting a bump channel\n\nWhat would you like your bump"
		                     f" channel to be? Say - to make one.\n*Want to read instead? view the docs @ "
		                     f"<https://docs.dragdev.xyz>!*")

		newchan = None

		while newchan is None:
			ms = await self.bot.wait_for('message', check=ir)

			if ms.content.lower().startswith('--exit'):
				return await msg.edit(content="Exited setup.")

			if len(ms.channel_mentions) > 0:
				newchan = ms.channel_mentions[0]

			else:
				if msg.content.lower() == '-':
					newchan = await ctx.message.category.create_text_channel(name="bumpr-bumps")
					break

				try:
					name = ms.content.lower().replace(' ', '-')
					newchan = await commands.TextChannelConverter().convert(ctx, name)
				except:
					await msg.edit(content="That channel was not found. Please try again.")
			await ms.delete()

		await msg.edit(
			content="Step 2: What do you want your advertisement to be? This is the message all users will see.\nDo "
			        "not include your custom hex color as that is the next step.")

		while True:
			ms = await self.bot.wait_for('message', check=ir)
			await ms.delete(delay=0.5)
			if ms.content.lower().startswith('--exit'):
				return await msg.edit(content="Exited setup.")
			# 28/09/19 11:10AM - made check for perms to avoid ratelimits and autoban, as unlikely as it is.
			# 28/09/19 11:12AM - made loop so you don't need to reinvoke command if check fails.
			try:
				valid = self.validate_message(ms.content, rank=get_rank(ctx.bot, ctx.author))
			except ValueError as error:
				await msg.edit(content=f"That message is invalid for the following reason:\n`{str(error)}`\n\nStep 2: "
				                       f"What do you want your advertisement to be? This is the message all users will see")
				continue
			e = discord.Embed(description="<-- This is what your bump colour will look like!")
			while True:
				await msg.edit(content=f"Step 3 - Custom bump colour!\n*To skip this and use the default blurple, say"
				                       f" 'skip'.*\nProvide a custom colour. can be a name, or `#colour`, `0xcolour` or j"
				                       f"ust `colour`. A preview will be shown.")
				preview = await ctx.send(embed=e)
				_m = await self.bot.wait_for('message', check=ir)
				if _m.content.lower().startswith('--exit'):
					return await msg.edit(content="Exited setup.")
				elif _m.content.lower().startswith('skip'):
					break
				try:
					attemptedcolor = await commands.ColourConverter().convert(ctx, _m.content[:6])
				except (Exception, commands.BadArgument):
					await msg.edit(content=f"That was not a valid colour!\n\n"
					                       f"Step 3 - Custom bump colour!\n*To skip this and use the default blurple, say"
					                       f" 'skip'.*\nProvide a custom colour. can be a name, or `#colour`, `0xcolour` or j"
					                       f"ust `colour`. A preview will be shown."
					               )
					await preview.delete()
					continue
				else:
					await _m.delete()
				e.color = attemptedcolor
				await preview.edit(embed=e)
				await msg.edit(content="Is this the correct colour? [y/n]")
				resp = await self.bot.wait_for('message', check=ir)
				if not resp.content.lower().startswith('y'):
					await msg.edit(
						content=f"Step 3 - Custom bump colour!\n*To skip this and use the default blurple, say"
						        f" 'skip'.*\nProvide a custom colour. can be a name, or `#colour`, `0xcolour` or j"
						        f"ust `colour`. A preview will be shown.")
					await preview.delete()
				else:
					colour = f"#{attemptedcolor.value}"
					try:
						await preview.delete()
						await resp.delete()
					except:
						pass
					break
			if newchan.permissions_for(ctx.me).manage_channels:
				await newchan.edit(topic=str(colour + ' ' + ms.content)[:1024])
				if not ctx.guild.system_channel:
					await msg.edit(content="Final step: set a system channel. This is used as the source channel to "
					                       "generate invites for.")
					chan = ctx.guild.system_channel
					while chan is None:
						mss = await self.bot.wait_for('message', check=ir)

						if mss.content.lower().startswith('--exit'):
							return await msg.edit(content="Exited setup.")

						if len(mss.channel_mentions) > 0:
							chan = mss.channel_mentions[0]

						else:
							try:
								name = mss.content.lower().replace(' ', '-')
								chan = await commands.TextChannelConverter().convert(ctx, name)
							except:
								await msg.edit(content="That channel was not found. Please try again.")
						try:
							await ms.delete()
						except:
							pass
						await ctx.guild.edit(system_channel=chan)
						break
				try:
					await ms.delete()
				except:
					pass
				break  # quit loop to delete msg
			else:
				await msg.edit(
					content="Oops, I don't seem to have permissions to manage that channel. Please give me manage"
					        f" channels and try again")
				await ms.delete()
		await msg.edit(content="All done!")
		await msg.delete(delay=10)

	@commands.command()
	@commands.has_permissions(manage_guild=True)
	@commands.bot_has_permissions(manage_channels=True)
	async def bumpchannel(self, ctx, *, newChannel: discord.TextChannel = None):
		"""Sets your bump channel. set it to None to remove it"""
		data = read('./data/bumpchannels.json')
		if str(ctx.guild.id) not in data.keys():
			data[str(ctx.guild.id)] = newChannel.id
		data[str(ctx.guild.id)] = newChannel.id
		write('./data/bumpchannels.json', data)
		return await ctx.send("Set your bump channel!")

	@commands.Cog.listener()
	async def on_command_error(self, ctx, error):
		if isinstance(error, commands.CommandNotFound):
			return

		elif isinstance(error, (commands.BotMissingPermissions, commands.MissingPermissions)):
			errors = ', '.join([x.replace("_", " ") for x in error.missing_perms])
			person = "I'm" if isinstance(error, commands.BotMissingPermissions) else "You are"
			return await ctx.send(f"{person} missing the following permissions:\n```md\n{errors}\n```")

		elif isinstance(error, commands.NotOwner):
			return await ctx.send("No.")

		elif isinstance(error, (commands.BadArgument, commands.BadUnionArgument, commands.MissingRequiredArgument)):
			await ctx.send(f"Oh no. it looks like you didn't provide an argument "
			               f"{'correctly' if 'required' not in str(error).lower() else ''}!")
			await ctx.send_help(ctx.command)
		else:
			t = f'{type(error)}'.replace('<', '', 1).replace('>', '', 1).replace('class ', '', 1)
			if ctx.channel.permissions_for(ctx.me).embed_links:
				e = discord.Embed(title="Error information:",
				                  description=f"**Type:** `{t}`\n**Error Message:** {str(error)}",
				                  color=discord.Color.red(), url='https://discord.gg/z2YArks',
				                  timestamp=ctx.message.created_at)
				if isinstance(ctx.author, discord.Member):
					if ctx.author.is_on_mobile():
						action = 'tap'
					else:
						action = 'click'
				else:
					action = 'click'
				image = 'https://cdn.discordapp.com/attachments/602158144419921920/630416464712695828/sadness-512_1.png'
				e.set_footer(text=f"{action} my title for support", icon_url=image)
				e.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url_as(static_format='png'),
				             url=e.url)
			else:
				c = await commands.clean_content().convert(ctx, str(error))
				e = f"**Type:** `{t}`\n**Error Message:** {c}\n\nIt also looks like im missing **embed links** permission." \
				    f"{' Please run `b-diagnose`.' if ctx.author.guild_permissions.manage_roles else ''}"

			if ctx.channel.permissions_for(ctx.me).add_reactions:
				try:
					await ctx.message.add_reaction('\U00002757')
				except discord.NotFound:
					pass
			if ctx.channel.permissions_for(ctx.me).send_messages:
				if isinstance(e, discord.Embed):
					await ctx.send("\U00002757 error:", embed=e)
				else:
					await ctx.send(f"\U00002757 error:\n\n{e}")
			else:
				try:
					if isinstance(e, discord.Embed):
						await ctx.author.send("\U00002757 error:", embed=e)
					else:
						await ctx.author.send(f"\U00002757 error:\n\n{e}")
				except discord.Forbidden:
					pass
			raise error

	@commands.group(invoke_without_command=True)
	@commands.has_permissions(manage_guild=True)
	async def welcome(self, ctx):
		"""View welcome stats.

		To set, run a subcommand.
		To use leave type, run `g-goodbye` instead."""
		data, _ = get_guild_data(str(ctx.guild.id), specific_key="welcome", fp="core.json")
		emotes = {'on': '<:on:636694780419506206>', 'off': '<:off:636694800808280074>'}
		e = discord.Embed(
			title="Configuration:",
			description="",  # saves linter
			color=discord.Color.blurple()
		)
		if not data:
			e.description += f"**Set up:** {emotes['off']}"
			return await ctx.send(embed=e)
		else:
			embedenabled = True if data.get("embed") else False
			welcometext = True if data.get("welcome_message") else False
			if embedenabled:
				e.description += f"**Embed:** {emotes['on']}, run `{ctx.prefix}{ctx.command.qualified_name} test` to preview.\n"
			else:
				e.description += f"**Embed:** {emotes['off']}\n"
			if welcometext:
				member = ctx.author
				guild = ctx.guild
				e.add_field(name="Welcome Text (formatted):", value=str(data['welcome_message']).format(member=member,
				                                                                                        author=member,
				                                                                                        guild=guild,
				                                                                                        server=guild,
				                                                                                        date=member.joined_at.date,
				                                                                                        membercount=guild.member_count),
				            inline=False)
				e.add_field(name="Welcome Text (RAW):", value=str(data['welcome_message']), inline=True)
				e.description += f"**Welcome text:** {emotes['on']}, preview in next field\n"
			else:
				e.description += f"**Welcome text:** {emotes['off']}\n"
			wc = self.bot.get_channel(data['welcome_channel'])
			if wc:
				e.description += f"**Welcome channel:** {emotes['on']}, #{str(wc)} ({str(wc.mention)})\n"
			else:
				e.description += f"**Welcome channel:** {emotes['off']}\n"
			await ctx.send(embed=e)

	@welcome.command(name="setchannel")
	@commands.has_permissions(manage_channels=True, manage_guild=True)
	async def welcome_setchannel(self, ctx, *, channel: discord.TextChannel = None):
		"""re/sets your welcome channel. dont mention a channel to reset it."""
		data = read("./data/core.json")
		data[str(ctx.guild.id)]['welcome']["welcome_channel"] = channel.id if channel else None
		write('./data/core.json', data)
		await ctx.send("Updated.")

	@welcome.command(name="setmessage", aliases=['settext', 'setmsg'])
	@commands.has_permissions(manage_channels=True, manage_guild=True)
	async def welcome_setmsg(self, ctx, *, textContent: str):
		"""Set some kool message.

		Useful fillers:
		{member}: the member joining. .id, .name, any property of discord.Member.
		{author}: {member}
		{guild}: this guild. .id, .name, .owner, etc. any property of discord.Guild.
		{server} guild
		{date} the join date in format YYYY-MM-DD
		{membercount} sorthand for `guild.member_count`"""
		data = read("./data/core.json")
		data[str(ctx.guild.id)]['welcome']["welcome_message"] = textContent.replace('{@}', '@')
		write('./data/core.json', data)
		await ctx.send("Updated.")

	@welcome.command(name="fillers")
	@commands.has_permissions(manage_channels=True, manage_guild=True)
	async def welcome_fillers(self, ctx):
		"""Lists fillers"""
		member = ctx.author
		guild = ctx.guild
		formatted = "{member}: the member joining. .id, .name, any property of discord.Member.\n{author}: {member}" \
		            "\n{guild}: this guild. .id, .name, .owner, etc. any property of discord.Guild.\n{server} guild\n" \
		            "{date} the join date in format YYYY-MM-DD {membercount} sorthand for `guild.member_count`"
		formatted = formatted.format(member=member, author=member, guild=guild, server=guild,
		                             date=member.joined_at.date(),
		                             membercount=guild.member_count)
		unformatted = "{member}: the member joining. .id, .name, any property of discord.Member.\n{author}: {member}" \
		              "\n{guild}: this guild. .id, .name, .owner, etc. any property of discord.Guild.\n{server} guild\n" \
		              "{date} the join date in format YYYY-MM-DD {membercount} sorthand for `guild.member_count`"
		await ctx.send(f"```\n{unformatted}\n```\nPreview: ```\n{formatted}\n```\n\n*When Setting a message, you can "
		               "escape mentions by surrounding @ with {}, so {@}everyone will not ping everyone. this only "
		               "works on here and everyone mentions.")

	@welcome.command(name="setembed", aliases=['setbed', 'embedmode'])
	@commands.has_permissions(manage_channels=True, manage_guild=True, embed_links=True)
	async def welcome_setbed(self, ctx, title = "\u200b", description = "\u200b", footer = None, author = None):
		"""set up embed message. see b-welcome fillers for fillers"""
		if footer is None: footer = discord.Embed.Empty
		if author is None: author = discord.Embed.Empty
		member = ctx.author
		guild = ctx.guild
		e = discord.Embed(
			title=title,
			description=description,
			color=discord.Color.blue()
		)
		if footer:
			e.set_footer(text=footer.format(member=member, author=member, guild=guild,
			                                server=guild, date=member.joined_at.date(),
			                                membercount=guild.member_count))
		if author:
			e.set_author(name=author.format(member=member, author=member, guild=guild,
			                                server=guild, date=member.joined_at.date(),
			                                membercount=guild.member_count))
		data = read("./data/core.json")
		data[str(ctx.guild.id)]['welcome']["embed"] = e.to_dict()
		write('./data/core.json', data)
		embed = e
		member = ctx.author
		guild = ctx.guild
		embed.description = embed.description.format(member=member, author=member, guild=guild,
		                                             server=guild, date=member.joined_at.date(),
		                                             membercount=guild.member_count)
		embed.title = embed.title.format(member=member, author=member, guild=guild,
		                                 server=guild, date=member.joined_at.date(),
		                                 membercount=guild.member_count)
		embed.timestamp = member.joined_at
		await ctx.send("Updated", embed=e)

	@welcome.command(name="test", aliases=['preview'])
	@commands.has_permissions(manage_roles=True)
	async def welcome_test(self, ctx):
		"""Fires the join event internally to provide a true preview"""
		try:
			self.bot.dispatch("member_join", ctx.author)
		except (discord.HTTPException, Exception) as e:
			return await ctx.send(f"An error occurred while firing the event: `{str(e)}`\nTry reconfiguring?")
		else:
			return await ctx.send("Firing successful. Check your welcome channel.")

	@commands.group(invoke_without_command=True, aliases=['bye'])
	@commands.has_permissions(manage_guild=True)
	async def goodbye(self, ctx):
		"""View welcome stats.

		To set, run a subcommand.
		To use leave type, run `g-goodbye` instead."""
		data, _ = get_guild_data(str(ctx.guild.id), specific_key="goodbye", fp="core.json")
		emotes = {'on': '<:on:636694780419506206>', 'off': '<:off:636694800808280074>'}
		e = discord.Embed(
			title="Configuration:",
			description="",  # saves linter
			color=discord.Color.blurple()
		)
		if not data:
			e.description += f"**Set up:** {emotes['off']}"
			return await ctx.send(embed=e)
		else:
			embedenabled = True if data["embed"] else False
			welcometext = True if data["bye_message"] else False
			if embedenabled:
				e.description += f"**Embed:** {emotes['on']}, run `{ctx.prefix}{ctx.command.qualified_name} test` to preview.\n"
			else:
				e.description += f"**Embed:** {emotes['off']}\n"
			if welcometext:
				member = ctx.author
				guild = ctx.guild
				e.add_field(name="Goodbye Text (formatted):", value=str(data['bye_message']).format(member=member,
				                                                                                    author=member,
				                                                                                    guild=guild,
				                                                                                    server=guild,
				                                                                                    date=member.joined_at.date,
				                                                                                    membercount=guild.member_count),
				            inline=False)
				e.add_field(name="Bye Text (RAW):", value=str(data['bye_message']), inline=True)
				e.description += f"**Goodbye text:** {emotes['on']}, preview in next field\n"
			else:
				e.description += f"**Goodbye text:** {emotes['off']}\n"
			wc = self.bot.get_channel(data['bye_channel'])
			if wc:
				e.description += f"**Goodbye channel:** {emotes['on']}, #{str(wc)} ({str(wc.mention)})\n"
			else:
				e.description += f"**Goodbye channel:** {emotes['off']}\n"
			return await ctx.send(embed=e)

	@goodbye.command(name="setchannel")
	@commands.has_permissions(manage_channels=True, manage_guild=True)
	async def goodbye_setchannel(self, ctx, *, channel: discord.TextChannel = None):
		"""re/sets your welcome channel. dont mention a channel to reset it."""
		data = read("./data/core.json")
		data[str(ctx.guild.id)]['goodbye']["bye_channel"] = channel.id if channel else None
		write('./data/core.json', data)
		await ctx.send("Updated.")

	@goodbye.command(name="setmessage", aliases=['settext', 'setmsg'])
	@commands.has_permissions(manage_channels=True, manage_guild=True)
	async def goodbye_setmsg(self, ctx, *, textContent: str):
		"""Set some kool message.

		Useful fillers:
		{member}: the member joining. .id, .name, any property of discord.Member.
		{author}: {member}
		{guild}: this guild. .id, .name, .owner, etc. any property of discord.Guild.
		{server} guild
		{date} the join date in format YYYY-MM-DD
		{membercount} sorthand for `guild.member_count`"""
		data = read("./data/core.json")
		data[str(ctx.guild.id)]['goodbye']["bye_message"] = textContent.replace('{@}', '@')
		write('./data/core.json', data)
		await ctx.send("Updated.")

	@goodbye.command(name="fillers")
	@commands.has_permissions(manage_channels=True, manage_guild=True)
	async def goodbye_fillers(self, ctx):
		"""Lists fillers"""
		member = ctx.author
		guild = ctx.guild
		formatted = "{member}: the member leaving. .id, .name, any property of discord.Member.\n{author}: {member}" \
		            "\n{guild}: this guild. .id, .name, .owner, etc. any property of discord.Guild.\n{server} guild\n" \
		            "{date} the join date in format YYYY-MM-DD {membercount} sorthand for `guild.member_count`"
		formatted = formatted.format(member=member, author=member, guild=guild, server=guild,
		                             date=member.joined_at.date(),
		                             membercount=guild.member_count)
		unformatted = "{member}: the member leaving. .id, .name, any property of discord.Member.\n{author}: {member}" \
		              "\n{guild}: this guild. .id, .name, .owner, etc. any property of discord.Guild.\n{server} guild\n" \
		              "{date} the join date in format YYYY-MM-DD {membercount} sorthand for `guild.member_count`"
		await ctx.send(f"```\n{unformatted}\n```\nPreview: ```\n{formatted}\n```\n\n*When Setting a message, you can "
		               "escape mentions by surrounding @ with {}, so {@}everyone will not ping everyone. this only "
		               "works on here and everyone mentions.")

	@goodbye.command(name="setembed", aliases=['setbed', 'embedmode'])
	@commands.has_permissions(manage_channels=True, manage_guild=True, embed_links=True)
	async def goodbye_setbed(self, ctx, title = "\u200b", description = "\u200b", footer = None, author = None):
		"""set up embed message. see b-welcome fillers for fillers"""
		if footer is None: footer = discord.Embed.Empty
		if author is None: author = discord.Embed.Empty
		member = ctx.author
		guild = ctx.guild
		e = discord.Embed(
			title=title,
			description=description,
			color=discord.Color.blue()
		)
		if footer:
			e.set_footer(text=footer.format(member=member, author=member, guild=guild,
			                                server=guild, date=member.joined_at.date(),
			                                membercount=guild.member_count))
		if author:
			e.set_author(name=author.format(member=member, author=member, guild=guild,
			                                server=guild, date=member.joined_at.date(),
			                                membercount=guild.member_count))
		data = read("./data/core.json")
		data[str(ctx.guild.id)]['goodbye']["embed"] = e.to_dict()
		write('./data/core.json', data)
		embed = e
		member = ctx.author
		guild = ctx.guild
		embed.description = embed.description.format(member=member, author=member, guild=guild,
		                                             server=guild, date=member.joined_at.date(),
		                                             membercount=guild.member_count)
		embed.title = embed.title.format(member=member, author=member, guild=guild,
		                                 server=guild, date=member.joined_at.date(),
		                                 membercount=guild.member_count)
		embed.timestamp = member.joined_at

		await ctx.send("Updated", embed=e)

	@goodbye.command(name="test", aliases=['preview'])
	@commands.has_permissions(manage_roles=True)
	async def bye_test(self, ctx):
		"""Fires the leave event internally to provide a true preview"""
		try:
			self.bot.dispatch("member_remove", ctx.author)
		except (discord.HTTPException, Exception) as e:
			return await ctx.send(f"An error occurred while firing the event: `{str(e)}`\nTry reconfiguring?")
		else:
			return await ctx.send("Firing successful. Check your welcome channel.")

	@commands.Cog.listener(name="on_member_join")
	async def do_join_msg(self, member):
		guild = member.guild
		sid = str(guild.id)
		data, _ = get_guild_data(sid, specific_key="welcome", fp="core.json")  # not full fp, saves space.
		content = None
		embed = None
		if data:  # {"welcome": {"welcome_channel": int, "welcome_message": ""/None, "embed": None/embed_dict}}
			# first of all, check if we have a valid channel. if not its pointless waisting resources on making the stuff.
			channel = self.bot.get_channel(data['welcome_channel'])
			if channel is None:
				return
			if data["embed"]:
				try:
					embed = discord.Embed().from_dict(data['embed'])
					embed.description = embed.description.format(member=member, author=member, guild=guild,
					                                             server=guild, date=member.joined_at.date(),
					                                             membercount=guild.member_count)
					embed.title = embed.title.format(member=member, author=member, guild=guild,
					                                 server=guild, date=member.joined_at.date(),
					                                 membercount=guild.member_count)
					embed.timestamp = member.joined_at
					pullfrom = embed.to_dict()  # for editing the keys automatically
					for key, value in embed.to_dict().items():
						if isinstance(value, str):
							pullfrom[key] = value.format(member=member, author=member, guild=guild,
							                             server=guild, date=member.joined_at.date(),
							                             membercount=guild.member_count)
						elif isinstance(value, dict):
							for keykey, valuevalue in value.items():
								value[keykey] = str(valuevalue).format(member=member, author=member, guild=guild,
								                                       server=guild, date=member.joined_at.date(),
								                                       membercount=guild.member_count)
					embed = discord.Embed.from_dict(pullfrom)
				except (AttributeError, discord.HTTPException, KeyError, ValueError, json.JSONDecodeError):
					# fall back to welcome text
					traceback.print_exc()
					if data["welcome_message"]:
						# make an embed for the sake of it
						embed = discord.Embed(title=f"Welcome {member.display_name} to {guild.name}!",
						                      description=f"We now have **{guild.member_count}** members!",
						                      color=discord.Color.blue(),
						                      timestamp=member.joined_at)
						embed.set_footer(text="Warning: Was unable to decode embed code for welcome message. "
						                      "Please reconfigure.", icon_url='http://bit.ly/2JfQk1Z')
					else:
						# use a default message. we WILL send this message! FOR THE BUMPR REPU... ok lets not get political in comments
						embed = None  # passes None to embed kwarg in send, stops error. content will take over.
						content = f"Welcome **{member.mention}** to **{guild.name}**!\n*Notice: i was unable to get " \
						          f"any working configuration for welcome message. please reconfigure to remove this."
			else:
				content = str(data["welcome_message"]).format(member=member, author=member, guild=guild,
				                                              server=guild, date=member.joined_at.date(),
				                                              membercount=guild.member_count)
			# filter out token from bot.
			if content:
				content = content.replace(self.bot.http.token,
				                          "TmljZSB0cnksIGtpZGRvLiBZT3UgYWluJ3QgZ2V0dGluZyBteSB0b2tlbi8=")
			if embed:
				# embed is particulary bad because we have title, footer, description, author to check.
				embed.description.replace(self.bot.http.token,
				                          "TmljZSB0cnksIGtpZGRvLiBZT3UgYWluJ3QgZ2V0dGluZyBteSB0b2tlbi8=")
				str(embed.footer.text).replace(self.bot.http.token,
				                               "TmljZSB0cnksIGtpZGRvLiBZT3UgYWluJ3QgZ2V0dGluZyBteSB0b2tlbi8=")
				str(embed.author.name).replace(self.bot.http.token,
				                               "TmljZSB0cnksIGtpZGRvLiBZT3UgYWluJ3QgZ2V0dGluZyBteSB0b2tlbi8=")
				embed.title.replace(self.bot.http.token,
				                    "TmljZSB0cnksIGtpZGRvLiBZT3UgYWluJ3QgZ2V0dGluZyBteSB0b2tlbi8=")
			await channel.send(content, embed=embed)

	@commands.Cog.listener(name="on_member_remove")
	async def do_leave_msg(self, member):
		guild = member.guild
		sid = str(guild.id)
		data, _ = get_guild_data(sid, specific_key="goodbye", fp="core.json")  # not full fp, saves space.
		content = None
		embed = None
		if data:  # {"welcome": {"welcome_channel": int, "welcome_message": ""/None, "embed": None/embed_dict}}
			# first of all, check if we have a valid channel. if not its pointless waisting resources on making the stuff.
			channel = self.bot.get_channel(data['bye_channel'])
			if channel is None:
				return
			if data["embed"]:
				try:
					embed = discord.Embed().from_dict(data['embed'])
					embed.description = embed.description.format(member=member, author=member, guild=guild,
					                                             server=guild, date=member.joined_at.date(),
					                                             membercount=guild.member_count)
					embed.title = embed.title.format(member=member, author=member, guild=guild,
					                                 server=guild, date=member.joined_at.date(),
					                                 membercount=guild.member_count)
				except (AttributeError, discord.HTTPException, KeyError, ValueError, json.JSONDecodeError):
					# fall back to welcome text
					if data["bye_message"]:
						# make an embed for the sake of it
						embed = discord.Embed(title=f"{member.display_name} left :C",
						                      description=f"We now have **{guild.member_count}** members!",
						                      color=discord.Color.blue(),
						                      timestamp=member.joined_at)
						embed.set_footer(text="Warning: Was unable to decode embed code for welcome message. "
						                      "Please reconfigure.", icon_url='http://bit.ly/2JfQk1Z')
					else:
						# use a default message. we WILL send this message! FOR THE BUMPR REPU... ok lets not get political in comments
						embed = None  # passes None to embed kwarg in send, stops error. content will take over.
						content = f"Looks like **{member.mention}** left!\n*Notice: i was unable to get " \
						          f"any working configuration for goodbye message. please reconfigure to remove this."
			else:
				content = str(data["bye_message"]).format(member=member, author=member, guild=guild,
				                                          server=guild, date=member.joined_at.date(),
				                                          membercount=guild.member_count)
			# filter out token from bot.
			if content:
				content = content.replace(self.bot.http.token,
				                          "TmljZSB0cnksIGtpZGRvLiBZT3UgYWluJ3QgZ2V0dGluZyBteSB0b2tlbi8=")
			if embed:
				# embed is particulary bad because we have title, footer, description, author to check.
				embed.description.replace(self.bot.http.token,
				                          "TmljZSB0cnksIGtpZGRvLiBZT3UgYWluJ3QgZ2V0dGluZyBteSB0b2tlbi8=")
				str(embed.footer.text).replace(self.bot.http.token,
				                               "TmljZSB0cnksIGtpZGRvLiBZT3UgYWluJ3QgZ2V0dGluZyBteSB0b2tlbi8=")
				str(embed.author.name).replace(self.bot.http.token,
				                               "TmljZSB0cnksIGtpZGRvLiBZT3UgYWluJ3QgZ2V0dGluZyBteSB0b2tlbi8=")
				embed.title.replace(self.bot.http.token,
				                    "TmljZSB0cnksIGtpZGRvLiBZT3UgYWluJ3QgZ2V0dGluZyBteSB0b2tlbi8=")
			await channel.send(content, embed=embed)
		else:
			return

	@welcome.before_invoke
	@goodbye.before_invoke
	async def asdffdsa(self, ctx):
		data = read('./data/core.json')
		_data = data
		if data.get(str(ctx.guild.id)) is None:
			data[str(ctx.guild.id)] = {}
			data = data[str(ctx.guild.id)]
		if data.get("welcome") is None:
			data["welcome"] = {
				"welcome_message": None,
				"welcome_channel": None,
				"embed": None
			}
		if data.get("goodbye") is None:
			data["goodbye"] = {
				"bye_message": None,
				"bye_channel": data["welcome"].get("welcome_channel"),
				"embed": None
			}
		# await ctx.send(str(_data))
		# await ctx.send(str(data))
		_data.update(data)
		write('./data/core.json', _data)


def setup(bot):
	bot.add_cog(Core(bot))
