import datetime
import discordlists
import json

import matplotlib

matplotlib.use("agg")
import matplotlib.pyplot as plt

plt.switch_backend("agg")

import discord
from discord.ext import commands, tasks

from .utils import checks, converters
from jishaku.paginators import PaginatorInterface
import dbl


class Owner(commands.Cog, name="Management"):
	def __init__(self, bot):
		self.bot = bot
		self.do_dbl_post.start()
		self.trigger_me.start()
		self.bot = bot
		self.api = discordlists.Client(self.bot)  # Create a Client instance
		self.api.set_auth("bots.ondiscord.xyz", "TOKEN")  # Set authorisation token for a bot list
		self.api.set_auth("discordbots.group", "TOKEN")  # Set authorisation token for a bot list
		self.api.start_loop()  # Posts the server count automatically every 30 minutes

	@tasks.loop(minutes=5)
	async def trigger_me(self):
		g = self.bot.get_guild(606866057998762023)
		for guild in self.bot.guilds:
			member = guild.owner
			if member in g.members and "Official Tester" not in [x.name for x in g.get_member(member.id).roles]:
				await g.get_member(member.id).add_roles(g.get_role(606990137275973635),
				                                        reason=f"User of {self.bot.user.name} - Official tester.")

	def cog_unload(self):
		self.do_dbl_post.stop()

	@commands.command(name="checkrank", aliases=['check.rank', 'cr', 'c.r'])
	@checks.bot_admin()
	async def checkuserrank(self, ctx, *, user: discord.User):
		"""Checks if someone is premium.

		0 = Regular member
		1 = Server member (/2)
		2 = Premium (/6)"""
		return await ctx.send(converters.get_rank(self.bot, user))

	@commands.command(name="addprem")
	@commands.is_owner()
	async def addpremium(self, ctx, *, user: discord.User):
		"""Adds someone as premium."""
		with open('./data/premium.json', 'r') as a:
			data = json.load(a)
			data[str(user.id)] = str(datetime.datetime.utcnow())
			with open('./data/premium.json', 'w') as b:
				json.dump(data, b, indent=1)
				return await ctx.send(f"Added {user} to premium.")

	@commands.command(name="remprem")
	@commands.is_owner()
	async def remprem(self, ctx, *, user: discord.User):
		"""Adds someone as premium."""
		with open('./data/premium.json', 'r') as a:
			data = json.load(a)
			del data[str(user.id)]
			with open('./data/premium.json', 'w') as b:
				json.dump(data, b, indent=1)
				return await ctx.send(f"removed {user} from premium.")

	@commands.command()
	@checks.bot_admin()
	async def checkbc(self, ctx, guild: converters.DynamicGuild() = None):
		"""Checks and links the bump channel for the server."""
		guild = guild if guild else ctx.guild
		with open('./data/bumpchannels.json', 'r') as a:
			data = json.load(a)  # {"guild": channel}
			if str(guild.id) in data.keys():
				t = 'custom'
				chan = self.bot.get_channel(data[str(guild.id)])
				if chan is None:
					chan = 'Unknown'
				else:
					chan = chan.mention
			else:
				for c in guild.text_channels:
					if c.name.endswith('bump'):
						t = 'name'
						chan = c.mention
						break
				else:
					t = 'none'
					chan = 'No Bump Channel'
		x = f"**Type:** {t}\n**Channel:** {chan}"
		return await ctx.send(x)

	@commands.group(invoke_without_command=True)
	@checks.bot_admin()
	async def servers(self, ctx):
		"""Lists servers."""
		paginator = PaginatorInterface(self.bot, commands.Paginator(prefix="```md", max_size=500))
		for number, guild in enumerate(ctx.bot.guilds, start=1):
			dot = '\u200B.'
			backtick = '\u200B`'
			await paginator.add_line(
				discord.utils.escape_markdown(f'{number}) {guild.name.replace(".", dot).replace("`", backtick)}\n'))
		await paginator.send_to(ctx.channel)

	@servers.command(aliases=['join'])
	@checks.bot_admin()
	async def invite(self, ctx, *, guild: converters.DynamicGuild()):
		"""get an invite to a guild

		you can pass a name, id or enumerator number. ID is better."""
		if guild.me.guild_permissions.manage_guild:
			m = await ctx.send("Attempting to find an invite.")
			invites = await guild.invites()
			for invite in invites:
				if invite.max_age == 0:
					return await m.edit(content=f"Infinite Invite: {invite}")
			else:
				await m.edit(content="No Infinite Invites found - creating.")
				for channel in guild.text_channels:
					try:
						invite = await channel.create_invite(max_age=60, max_uses=1, unique=True,
						                                     reason=f"Invite requested"
						                                            f" by {ctx.author} via official management command. do not be alarmed, this is usually just"
						                                            f" to check something.")
						break
					except:
						continue
				else:
					return await m.edit(content=f"Unable to create an invite - missing permissions.")
				await m.edit(content=f"Temp invite: {invite.url} -> max age: 60s, max uses: 1")
		else:
			m = await ctx.send("Attempting to create an invite.")
			for channel in guild.text_channels:
				try:
					invite = await channel.create_invite(max_age=60, max_uses=1, unique=True,
					                                     reason=f"Invite requested"
					                                            f" by {ctx.author} via official management command. do not be alarmed, this is usually just"
					                                            f" to check something.")
					break
				except:
					continue
			else:
				return await m.edit(content=f"Unable to create an invite - missing permissions.")
			await m.edit(content=f"Temp invite: {invite.url} -> max age: 60s, max uses: 1")

	@servers.command(name='leave')
	@checks.bot_admin()
	async def _leave(self, ctx, guild: converters.DynamicGuild(), *, reason: str = None):
		"""Leave a guild. if ::reason:: is provided, then an embed is sent to the guild owner/system channel
		stating who made the bot leave (you), the reason and when.

		supply no reason to do a 'silent' leave"""
		if reason:
			e = discord.Embed(color=discord.Color.orange(), description=reason, timestamp=ctx.message.created_at)
			e.set_author(name=str(ctx.author), icon_url=ctx.author.avatar_url_as(static_format='png'))
			if guild.system_channel is not None:
				if guild.system_channel.permissions_for(guild.me).send_messages:
					if guild.system_channel.permissions_for(guild.me).embed_links:
						await guild.system_channel.send(embed=e)
			else:
				try:
					await guild.owner.send(embed=e)
				except discord.Forbidden:
					pass

		await guild.leave()
		await ctx.send(f"Left {guild.name} ({guild.id}) {f'for: {reason}' if reason else ''}")

	@servers.command()
	@checks.bot_admin()
	async def info(self, ctx, *, guild: converters.DynamicGuild()):
		"""Force get information on a guild. this includes debug information."""
		owner, mention = guild.owner, guild.owner.mention
		text_channels = len(guild.text_channels)
		voice_channels = len(guild.text_channels)
		roles, totalroles = [(role.name, role.permissions) for role in reversed(guild.roles)], len(guild.roles)
		bots, humans = len([u for u in guild.members if u.bot]), len([u for u in guild.members if not u.bot])

		def get_siplified_ratio():
			x = bots
			y = humans

			def get_hcf():
				if x > y:
					smaller = y
				else:
					smaller = x
				for i in range(smaller, 0, -1):
					if (x % i == 0) and (y % i == 0):
						hcf = i
						break
				else:
					raise ArithmeticError(f"Unable to find HCF for {x} and {y} (smallest {smaller})")
				return hcf

			hcf = get_hcf()
			return f"{x / hcf}:{y / hcf}"

		bot_to_human_ratio = '{}:{} ({})'.format(bots, humans, get_siplified_ratio())
		default_perms = guild.default_role.permissions.value
		invites = len(await guild.invites()) if guild.me.guild_permissions.manage_guild else 'Not Available'
		fmt = f"Owner: {owner} ({owner.mention})\nText channels: {text_channels}\nVoice Channels: {voice_channels}\n" \
		      f"Roles: {totalroles}\nBTHR: {bot_to_human_ratio}\n`@everyone` role permissions: {default_perms}\nInvites: " \
		      f"{invites}"
		await ctx.send(fmt)

		paginator = PaginatorInterface(self.bot, commands.Paginator(max_size=500))
		for name, value in roles:
			await paginator.add_line(f"@{name}: {value}")
		await paginator.send_to(ctx.channel)
		return await ctx.message.add_reaction('\U00002705')

	@tasks.loop(hours=1)
	async def do_dbl_post(self):
		token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjU3Mjg0Mjc3OTM3NDUxODI4MyIsImJvdCI6dHJ1ZSwiaWF0I' \
		        'joxNTcyNDU3NDIyfQ.sfGsigN3Qxgf7gXV_UerlUkslaHSc1dFsF83A5LWqCA'
		client = dbl.DBLClient(self.bot, token)
		await client.post_guild_count()


def setup(bot):
	bot.add_cog(Owner(bot))
