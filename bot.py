import discord
from discord import app_commands
import os
import json
from collections import defaultdict

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class MiddlemanBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.load_config()
        self.message_counts = defaultdict(lambda: defaultdict(int))  # {channel_id: {user_id: count}}
        
    def load_config(self):
        try:
            with open('config.json', 'r') as f:
                self.config = json.load(f)
        except FileNotFoundError:
            self.config = {"leaderboard_channel_id": None}
            with open('config.json', 'w') as f:
                json.dump(self.config, f, indent=4)
        
    async def setup_hook(self):
        await self.tree.sync()

bot = MiddlemanBot()

@bot.event
async def on_ready():
    print(f'{bot.user} is now online!')

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    # Track messages only in the configured channel
    lb_channel_id = bot.config.get("leaderboard_channel_id")
    if lb_channel_id and message.channel.id == lb_channel_id:
        bot.message_counts[lb_channel_id][message.author.id] += 1
    
    # --- mminfosab command ---
    if message.content.lower().startswith("$mminfosab"):
        embed = discord.Embed(
            title="Middleman Info & Explanation",
            description=(
                "ℹ️ **Middleman System Info**\n\n"
                "Our middleman system helps facilitate safe trades between users. Here's how it works:\n\n"
                "**Example:** Trade is a Brainrot for Brainrot (trade between Larry and Harry).\n\n"
                "**Steps:**\n"
                "1. Log in with Account 1 → take Larry´s items.\n"
                "2. Log in with Account 2 → take Harry´s items.\n"
                "This part is called distribution and will only be done once I have the items from both players.\n"
                "3. Switch back to Account 1 but join Harry → give Harry the items from Larry.\n"
                "4. Remove player Harry from the server since he already got his stuff.\n"
                "5. Join Player Larry again with Account 2 → give Larry the items taken from Harry.\n"
            ),
            color=0xFFA500
        )
        embed.set_image(
            url="https://cdn.discordapp.com/attachments/1292876935214534799/1442083659992797184/Middeman_sign.jpg"
        )
        await message.channel.send(embed=embed)
    
    # --- Leaderboard command ---
    if message.content.lower().startswith("$leaderboard"):
        lb_channel_id = bot.config.get("leaderboard_channel_id")
        if not lb_channel_id:
            await message.channel.send("❌ Leaderboard channel not configured yet.")
            return
        
        counts = bot.message_counts[lb_channel_id]
        if not counts:
            await message.channel.send("📊 No messages tracked yet.")
            return
        
        # Sort users by message count
        sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        embed = discord.Embed(
            title="🏆 Message Leaderboard",
            description=f"Top message senders in <#{lb_channel_id}>",
            color=discord.Color.gold()
        )
        
        for rank, (user_id, count) in enumerate(sorted_counts, start=1):
            user = message.guild.get_member(user_id)
            name = user.display_name if user else f"User({user_id})"
            embed.add_field(name=f"{rank}. {name}", value=f"{count} messages", inline=False)
        
        await message.channel.send(embed=embed)

# Slash command to configure leaderboard channel
@bot.tree.command(name="config_leaderboard", description="Set the channel for message leaderboard tracking")
@app_commands.checks.has_permissions(administrator=True)
async def config_leaderboard(interaction: discord.Interaction, channel: discord.TextChannel):
    bot.config["leaderboard_channel_id"] = channel.id
    with open('config.json', 'w') as f:
        json.dump(bot.config, f, indent=4)
    await interaction.response.send_message(f"✅ Leaderboard channel set to {channel.mention}", ephemeral=True)

TOKEN = os.getenv('DISCORD_TOKEN')
if TOKEN:
    bot.run(TOKEN)
else:
    print("ERROR: DISCORD_TOKEN not found in environment variables!")

