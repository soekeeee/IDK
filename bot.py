import discord
from discord import app_commands
import json

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class MiddlemanBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.load_config()
        
    def load_config(self):
        try:
            with open('config.json', 'r') as f:
                self.config = json.load(f)
        except FileNotFoundError:
            self.config = {}
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
    
    # --- +mminfosab command ---
    if message.content.lower().startswith("+mminfosab"):
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

TOKEN = os.getenv('DISCORD_TOKEN')
if not TOKEN:
    print("ERROR: DISCORD_TOKEN not found in environment variables!")
    print("Please add your Discord bot token to the Secrets tab.")
else:
    bot.run(TOKEN)
