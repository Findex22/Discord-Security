import discord
from discord.ext import commands
import datetime
import re
import os
from collections import defaultdict

TOKEN = 'MTM2MzAzNjgxMDc0OTY3MzU2Nw.GHjDmg.0mswrV-NouD-9dTB4oGFZGoXsqw8IL5N4orz3U' 
ADMIN_ROLE_ID = 1279892066318684231
PREFIX = '#'

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

user_strikes = defaultdict(list)
message_history = defaultdict(list) 

def load_bad_words():
    try:
        with open('bad_words.lng', 'r', encoding='utf-8') as f:
            content = f.read()
            return [word.strip().lower() for word in content.split(',') if word.strip()]
    except FileNotFoundError:
        return []

def parse_time(time_str):
    time_dict = {'s': 'seconds', 'm': 'minutes', 'h': 'hours', 'd': 'days'}
    unit = time_str[-1]
    if unit in time_dict and time_str[:-1].isdigit():
        val = int(time_str[:-1])
        return datetime.timedelta(**{time_dict[unit]: val})
    return None

def is_elite_admin():
    async def predicate(ctx):
        return any(role.id == ADMIN_ROLE_ID for role in ctx.author.roles)
    return commands.check(predicate)


@bot.event
async def on_ready():
    print(f'FINDEX SECURITY++is online! Logged in as {bot.user.name}')

@bot.event
async def on_message(message):
    if message.author.bot or message.guild is None:
        return

    is_admin = any(role.id == ADMIN_ROLE_ID for role in message.author.roles)
    if is_admin:
        await bot.process_commands(message)
        return

    now = datetime.datetime.now()
    user_id = message.author.id

    message_history[user_id] = [t for t in message_history[user_id] if (now - t).total_seconds() < 5]
    message_history[user_id].append(now)

    if len(message_history[user_id]) >= 5:
        await message.channel.purge(limit=10, check=lambda m: m.author.id == user_id)
        try:
            timeout_7d = datetime.timedelta(days=7)
            await message.author.timeout(timeout_7d, reason="FINDEX PRO: Automated Spam Detection")
            await message.author.send(f"🚨 You have been timed out for 7 days in {message.guild.name} due to heavy spamming.")
        except: pass
        await message.channel.send(f"🚨 {message.author.mention} was auto-muted for 7 days for Spamming.")
        return

    violation = False
    v_reason = ""
    bad_words_list = load_bad_words()

    if re.search(r'(https?://\S+)', message.content):
        violation = True
        v_reason = "URL Sending"
    elif len(message.attachments) > 0:
        violation = True
        v_reason = "Attachment/Image Sending"
    elif any(word in message.content.lower() for word in bad_words_list):
        violation = True
        v_reason = "Bad Language"

    if violation:
        await message.delete()
        user_strikes[user_id] = [t for t in user_strikes[user_id] if (now - t).total_seconds() < 86400]
        user_strikes[user_id].append(now)
        
        strike_count = len(user_strikes[user_id])
        if strike_count >= 3:
            try:
                await message.author.timeout(datetime.timedelta(hours=24), reason="3 Strikes in 24h")
                await message.author.send(f"⚠️ You reached 3 strikes in {message.guild.name}. 24h timeout applied.")
            except: pass
        else:
            try:
                await message.author.send(f"⚠️ Warning ({strike_count}/3): {v_reason} is restricted.")
            except: pass

    await bot.process_commands(message)

# --- Admin Commands ---

@bot.command(name='timeout', aliases=['mute'])
@is_elite_admin()
async def timeout_cmd(ctx, duration: str, member: discord.Member, *, reason="No reason"):
    delta = parse_time(duration)
    if not delta:
        await ctx.send("❌ Format: `#timeout 10m @user reason` (s/m/h/d)")
        return
    await member.timeout(delta, reason=reason)
    try: await member.send(f"🔇 Muted in {ctx.guild.name} for {duration}. Reason: {reason}")
    except: pass
    await ctx.send(f"✅ {member.mention} muted for {duration}.")

@bot.command()
@is_elite_admin()
async def kick(ctx, member: discord.Member, *, reason="No reason"):
    try: await member.send(f"👢 Kicked from {ctx.guild.name}. Reason: {reason}")
    except: pass
    await member.kick(reason=reason)
    await ctx.send(f"✅ {member.mention} kicked.")

@bot.command()
@is_elite_admin()
async def ban(ctx, member: discord.Member, *, reason="No reason"):
    try: await member.send(f"🔨 Banned from {ctx.guild.name}. Reason: {reason}")
    except: pass
    await member.ban(reason=reason)
    await ctx.send(f"✅ {member.mention} banned.")

@bot.command()
@is_elite_admin()
async def lock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send(f"🔒 **{ctx.channel.name}** locked by Admin.")

@bot.command()
@is_elite_admin()
async def unlock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send(f"🔓 **{ctx.channel.name}** is now open.")

@bot.command(name='sta')
@is_elite_admin()
async def status(ctx):
    guild = ctx.guild
    embed = discord.Embed(title=f"📊 {guild.name} Status", color=0x2f3136)
    embed.add_field(name="Members", value=guild.member_count)
    embed.add_field(name="Protection", value="🛡️ Maximum")
    embed.set_footer(text="FINDEX SECURITY++ | Developed by - FINDEX")
    await ctx.send(embed=embed)

bot.run(TOKEN)
