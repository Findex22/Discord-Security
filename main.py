import discord
from discord.ext import commands
import datetime
import re
import os
from collections import defaultdict

# ================= CONFIG =================
TOKEN = os.getenv("TOKEN")  # IMPORTANT: Railway env variable
ADMIN_ROLE_ID = 1279892066318684231
PREFIX = '#'

if not TOKEN:
    raise ValueError("TOKEN not found! Set it in Railway Variables.")

# ================= INTENTS =================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents)

# ================= DATA =================
user_strikes = defaultdict(list)
message_history = defaultdict(list)

# ================= UTIL =================
def load_bad_words():
    try:
        with open('bad_words.lng', 'r', encoding='utf-8') as f:
            return [w.strip().lower() for w in f.read().split(',') if w.strip()]
    except:
        return []

def parse_time(time_str):
    time_dict = {'s': 'seconds', 'm': 'minutes', 'h': 'hours', 'd': 'days'}
    if len(time_str) < 2:
        return None
    unit = time_str[-1]
    if unit in time_dict and time_str[:-1].isdigit():
        return datetime.timedelta(**{time_dict[unit]: int(time_str[:-1])})
    return None

def is_elite_admin():
    async def predicate(ctx):
        return any(role.id == ADMIN_ROLE_ID for role in ctx.author.roles)
    return commands.check(predicate)

# ================= EVENTS =================
@bot.event
async def on_ready():
    print(f'✅ Bot is ONLINE as {bot.user} (ID: {bot.user.id})')

@bot.event
async def on_message(message):
    if message.author.bot or message.guild is None:
        return

    try:
        is_admin = any(role.id == ADMIN_ROLE_ID for role in message.author.roles)
        if is_admin:
            await bot.process_commands(message)
            return

        now = datetime.datetime.utcnow()
        user_id = message.author.id

        # ===== SPAM DETECTION =====
        message_history[user_id] = [
            t for t in message_history[user_id]
            if (now - t).total_seconds() < 5
        ]
        message_history[user_id].append(now)

        if len(message_history[user_id]) >= 5:
            await message.channel.purge(limit=10, check=lambda m: m.author.id == user_id)
            try:
                await message.author.timeout(datetime.timedelta(days=7), reason="Spam Detection")
                await message.author.send("🚨 You have been muted for 7 days due to spamming.")
            except:
                pass

            await message.channel.send(f"🚨 {message.author.mention} auto-muted for spam.")
            return

        # ===== FILTER SYSTEM =====
        violation = False
        v_reason = ""
        bad_words = load_bad_words()

        if re.search(r'(https?://\S+)', message.content):
            violation = True
            v_reason = "Links not allowed"
        elif message.attachments:
            violation = True
            v_reason = "Attachments not allowed"
        elif any(word in message.content.lower() for word in bad_words):
            violation = True
            v_reason = "Bad language"

        if violation:
            await message.delete()

            user_strikes[user_id] = [
                t for t in user_strikes[user_id]
                if (now - t).total_seconds() < 86400
            ]
            user_strikes[user_id].append(now)

            strikes = len(user_strikes[user_id])

            if strikes >= 3:
                try:
                    await message.author.timeout(datetime.timedelta(hours=24), reason="3 strikes")
                    await message.author.send("⚠️ 3 strikes reached → 24h mute.")
                except:
                    pass
            else:
                try:
                    await message.author.send(f"⚠️ Warning {strikes}/3: {v_reason}")
                except:
                    pass

        await bot.process_commands(message)

    except Exception as e:
        print(f"❌ ERROR in on_message: {e}")

# ================= COMMANDS =================
@bot.command()
@is_elite_admin()
async def timeout(ctx, duration: str, member: discord.Member, *, reason="No reason"):
    delta = parse_time(duration)
    if not delta:
        await ctx.send("❌ Use: #timeout 10m @user reason")
        return
    await member.timeout(delta, reason=reason)
    await ctx.send(f"✅ {member.mention} muted for {duration}")

@bot.command()
@is_elite_admin()
async def kick(ctx, member: discord.Member, *, reason="No reason"):
    await member.kick(reason=reason)
    await ctx.send(f"✅ {member.mention} kicked")

@bot.command()
@is_elite_admin()
async def ban(ctx, member: discord.Member, *, reason="No reason"):
    await member.ban(reason=reason)
    await ctx.send(f"✅ {member.mention} banned")

@bot.command()
@is_elite_admin()
async def lock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send("🔒 Channel locked")

@bot.command()
@is_elite_admin()
async def unlock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send("🔓 Channel unlocked")

@bot.command()
@is_elite_admin()
async def sta(ctx):
    embed = discord.Embed(title="📊 Server Status", color=0x2f3136)
    embed.add_field(name="Members", value=ctx.guild.member_count)
    embed.add_field(name="Protection", value="🛡️ Active")
    await ctx.send(embed=embed)

# ================= START =================
bot.run(TOKEN)
