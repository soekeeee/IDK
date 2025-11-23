import discord
from discord import app_commands
from discord.ui import Button, View, Modal, TextInput
import os
from datetime import datetime
import json
import asyncio

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class MiddlemanBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.load_config()
        self.active_tickets = {}
        
    def load_config(self):
        try:
            with open('config.json', 'r') as f:
                self.config = json.load(f)
        except FileNotFoundError:
            self.config = {
                "hub_channel_id": None,
                "ticket_category_id": None,
                "log_channel_id": None,
                "middleman_role_id": None,
                "override_role_ids": [],
                "joinus_message": "🎉 Join us today! We're building an awesome community!",
                "mminfo_message": "ℹ️ **Middleman System Info**\n\nOur middleman system helps facilitate safe trades between users. Click 'Request Middleman' to create a ticket!"
            }
            with open('config.json', 'w') as f:
                json.dump(self.config, f, indent=4)
        
    async def setup_hook(self):
        await self.tree.sync()

bot = MiddlemanBot()

class TradeModal(Modal, title="Request Middleman Service"):
    trade_description = TextInput(
        label="Trade Description",
        style=discord.TextStyle.paragraph,
        placeholder="Describe what you're trading...",
        required=True,
        max_length=1000
    )
    
    other_trader = TextInput(
        label="Other Trader's Discord ID or @mention",
        style=discord.TextStyle.short,
        placeholder="User ID or @username",
        required=True,
        max_length=100
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        guild = interaction.guild
        requester = interaction.user
        
        try:
            other_trader_input = self.other_trader.value.strip()
            
            if other_trader_input.startswith('<@') and other_trader_input.endswith('>'):
                user_id = int(other_trader_input.strip('<@!>'))
            else:
                user_id = int(other_trader_input)
            
            other_trader = await guild.fetch_member(user_id)
            
        except (ValueError, discord.NotFound, discord.HTTPException):
            await interaction.followup.send(
                "❌ Could not find the user you mentioned. Please use a valid Discord ID or @mention.",
                ephemeral=True
            )
            return
        
        category = None
        if bot.config.get('ticket_category_id'):
            category = guild.get_channel(bot.config['ticket_category_id'])
        
        ticket_name = f"mm-ticket-{requester.name.lower()}"
        
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            requester: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            other_trader: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        if bot.config.get('middleman_role_id'):
            mm_role = guild.get_role(bot.config['middleman_role_id'])
            if mm_role:
                overwrites[mm_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        
        try:
            ticket_channel = await guild.create_text_channel(
                name=ticket_name,
                category=category,
                overwrites=overwrites
            )
            
            embed = discord.Embed(
                title="🎫 Middleman Ticket",
                description=f"**Trade Description:**\n{self.trade_description.value}",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Requester", value=requester.mention, inline=True)
            embed.add_field(name="Other Trader", value=other_trader.mention, inline=True)
            embed.add_field(name="Status", value="⏳ Waiting for Middleman", inline=False)
            embed.set_footer(text=f"Ticket created by {requester.name}")
            
            claim_button = Button(label="Claim", style=discord.ButtonStyle.green, custom_id="claim_ticket")
            view = View(timeout=None)
            view.add_item(claim_button)
            
            claim_button.callback = claim_ticket_callback
            
            message = await ticket_channel.send(
                content=f"{requester.mention} {other_trader.mention}",
                embed=embed,
                view=view
            )
            
            bot.active_tickets[ticket_channel.id] = {
                'requester': requester.id,
                'other_trader': other_trader.id,
                'claimer': None,
                'message_id': message.id,
                'trade_description': self.trade_description.value,
                'created_at': datetime.utcnow().isoformat()
            }
            
            await interaction.followup.send(
                f"✅ Ticket created: {ticket_channel.mention}",
                ephemeral=True
            )
            
        except discord.Forbidden:
            await interaction.followup.send(
                "❌ I don't have permission to create channels. Please check my permissions.",
                ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(
                f"❌ An error occurred while creating the ticket: {str(e)}",
                ephemeral=True
            )

async def claim_ticket_callback(interaction: discord.Interaction):
    channel_id = interaction.channel.id
    
    if channel_id not in bot.active_tickets:
        await interaction.response.send_message(
            "❌ This ticket is not in the active tickets database.",
            ephemeral=True
        )
        return
    
    ticket_data = bot.active_tickets[channel_id]
    
    if not bot.config.get('middleman_role_id'):
        await interaction.response.send_message(
            "❌ Middleman role not configured. Please set up the bot configuration.",
            ephemeral=True
        )
        return
    
    mm_role = interaction.guild.get_role(bot.config['middleman_role_id'])
    if not mm_role or mm_role not in interaction.user.roles:
        await interaction.response.send_message(
            "❌ You must have the Middleman role to claim tickets.",
            ephemeral=True
        )
        return
    
    if ticket_data['claimer']:
        claimer = interaction.guild.get_member(ticket_data['claimer'])
        await interaction.response.send_message(
            f"❌ Already claimed by {claimer.mention if claimer else 'Unknown User'}",
            ephemeral=True
        )
        return
    
    ticket_data['claimer'] = interaction.user.id
    
    try:
        message = await interaction.channel.fetch_message(ticket_data['message_id'])
        embed = message.embeds[0]
        
        for i, field in enumerate(embed.fields):
            if field.name == "Status":
                embed.set_field_at(i, name="Status", value=f"✅ Claimed by {interaction.user.mention}", inline=False)
                break
        
        claim_button = Button(label="Claimed", style=discord.ButtonStyle.gray, custom_id="claim_ticket", disabled=True)
        view = View(timeout=None)
        view.add_item(claim_button)
        
        await message.edit(embed=embed, view=view)
        
        await interaction.response.send_message(
            f"✅ Claimed by {interaction.user.mention}",
            ephemeral=False
        )
        
    except Exception as e:
        await interaction.response.send_message(
            f"❌ Error updating ticket: {str(e)}",
            ephemeral=True
        )

async def joinus_accept_callback(interaction: discord.Interaction):
    user = interaction.user
    
    await interaction.response.send_message(
        f"✅ {user.mention} accepted!",
        ephemeral=False
    )
    
    if bot.config.get('joinus_role_id'):
        role = interaction.guild.get_role(bot.config['joinus_role_id'])
        if role:
            try:
                await user.add_roles(role)
            except discord.Forbidden:
                await interaction.followup.send(
                    "⚠️ I don't have permission to add roles.",
                    ephemeral=True
                )
        else:
            await interaction.followup.send(
                "⚠️ Join us role not found. Please configure it using `/config setting:joinus_role value:<role_id>`",
                ephemeral=True
            )
    else:
        await interaction.followup.send(
            "⚠️ Join us role not configured. Please set it using `/config setting:joinus_role value:<role_id>`",
            ephemeral=True
        )

async def joinus_decline_callback(interaction: discord.Interaction):
    user = interaction.user
    
    await interaction.response.send_message(
        f"❌ {user.mention} declined.",
        ephemeral=False
    )

class RequestMMButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="Request Middleman", style=discord.ButtonStyle.primary, custom_id="request_mm_button")
    async def request_mm(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = TradeModal()
        await interaction.response.send_modal(modal)

@bot.event
async def on_ready():
    print(f'{bot.user} is now online!')
    print(f'Bot ID: {bot.user.id}')
    bot.add_view(RequestMMButton())

def has_permission(user, channel_id):
    if channel_id not in bot.active_tickets:
        return False
    
    ticket_data = bot.active_tickets[channel_id]
    
    if ticket_data['claimer'] == user.id:
        return True
    
    override_roles = bot.config.get('override_role_ids', [])
    user_role_ids = [role.id for role in user.roles]
    
    for role_id in override_roles:
        if role_id in user_role_ids:
            return True
    
    return False

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    if not message.content.startswith('$'):
        return
    
    parts = message.content.split(maxsplit=1)
    command = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""
    
    if command == "$add":
        if not has_permission(message.author, message.channel.id):
            await message.channel.send("❌ Only the claiming middleman or authorized roles can use this command.")
            return
        
        if not message.mentions:
            await message.channel.send("❌ Please mention a user to add.")
            return
        
        user_to_add = message.mentions[0]
        try:
            await message.channel.set_permissions(user_to_add, read_messages=True, send_messages=True)
            await message.channel.send(f"✅ Added {user_to_add.mention} to the ticket.")
        except discord.Forbidden:
            await message.channel.send("❌ I don't have permission to modify channel permissions.")
    
    elif command == "$remove":
        if not has_permission(message.author, message.channel.id):
            await message.channel.send("❌ Only the claiming middleman or authorized roles can use this command.")
            return
        
        if not message.mentions:
            await message.channel.send("❌ Please mention a user to remove.")
            return
        
        user_to_remove = message.mentions[0]
        try:
            await message.channel.set_permissions(user_to_remove, overwrite=None)
            await message.channel.send(f"✅ Removed {user_to_remove.mention} from the ticket.")
        except discord.Forbidden:
            await message.channel.send("❌ I don't have permission to modify channel permissions.")
    
    elif command == "$unclaim":
        if message.channel.id not in bot.active_tickets:
            await message.channel.send("❌ This is not a ticket channel.")
            return
        
        if not has_permission(message.author, message.channel.id):
            await message.channel.send("❌ Only the claiming middleman or authorized roles can use this command.")
            return
        
        ticket_data = bot.active_tickets[message.channel.id]
        
        if not ticket_data['claimer']:
            await message.channel.send("❌ This ticket has not been claimed yet.")
            return
        
        ticket_data['claimer'] = None
        
        try:
            ticket_message = await message.channel.fetch_message(ticket_data['message_id'])
            embed = ticket_message.embeds[0]
            
            for i, field in enumerate(embed.fields):
                if field.name == "Status":
                    embed.set_field_at(i, name="Status", value="⏳ Waiting for Middleman", inline=False)
                    break
            
            claim_button = Button(label="Claim", style=discord.ButtonStyle.green, custom_id="claim_ticket")
            view = View(timeout=None)
            view.add_item(claim_button)
            claim_button.callback = claim_ticket_callback
            
            await ticket_message.edit(embed=embed, view=view)
            await message.channel.send("✅ Ticket has been unclaimed. The claim button is now active again.")
            
        except Exception as e:
            await message.channel.send(f"❌ Error unclaiming ticket: {str(e)}")
    
    elif command == "$rename":
        if not has_permission(message.author, message.channel.id):
            await message.channel.send("❌ Only the claiming middleman or authorized roles can use this command.")
            return
        
        if not args:
            await message.channel.send("❌ Please provide a new name. Usage: `$rename <name>`")
            return
        
        new_name = f"mm-{args.strip()}"
        
        try:
            await message.channel.edit(name=new_name)
            await message.channel.send(f"✅ Channel renamed to `{new_name}`")
        except discord.Forbidden:
            await message.channel.send("❌ I don't have permission to rename channels.")
    
    elif command == "$close":
        if message.channel.id not in bot.active_tickets:
            await message.channel.send("❌ This is not a ticket channel.")
            return
        
        ticket_data = bot.active_tickets[message.channel.id]
        
        if bot.config.get('log_channel_id'):
            log_channel = bot.get_channel(bot.config['log_channel_id'])
            if log_channel:
                requester = message.guild.get_member(ticket_data['requester'])
                other_trader = message.guild.get_member(ticket_data['other_trader'])
                claimer = message.guild.get_member(ticket_data['claimer']) if ticket_data['claimer'] else None
                
                log_embed = discord.Embed(
                    title="📋 Ticket Closed",
                    description=f"**Channel:** {message.channel.name}",
                    color=discord.Color.red(),
                    timestamp=datetime.utcnow()
                )
                log_embed.add_field(name="Requester", value=requester.mention if requester else "Unknown", inline=True)
                log_embed.add_field(name="Other Trader", value=other_trader.mention if other_trader else "Unknown", inline=True)
                log_embed.add_field(name="Claimed By", value=claimer.mention if claimer else "Not Claimed", inline=True)
                log_embed.add_field(name="Trade Description", value=ticket_data['trade_description'], inline=False)
                log_embed.add_field(name="Closed By", value=message.author.mention, inline=True)
                log_embed.add_field(name="Created At", value=ticket_data['created_at'], inline=True)
                
                try:
                    await log_channel.send(embed=log_embed)
                except:
                    pass
        
        del bot.active_tickets[message.channel.id]
        
        await message.channel.send("🔒 This ticket will be deleted in 5 seconds...")
        await asyncio.sleep(5)
        
        try:
            await message.channel.delete()
        except discord.Forbidden:
            await message.channel.send("❌ I don't have permission to delete channels.")
    
    elif command == "$joinus":
        joinus_msg = bot.config.get('joinus_message', '🎉 Join us today!')
        
        accept_button = Button(label="Accept", style=discord.ButtonStyle.green, custom_id="joinus_accept")
        decline_button = Button(label="Decline", style=discord.ButtonStyle.red, custom_id="joinus_decline")
        
        view = View(timeout=None)
        view.add_item(accept_button)
        view.add_item(decline_button)
        
        accept_button.callback = joinus_accept_callback
        decline_button.callback = joinus_decline_callback
        
        await message.channel.send(joinus_msg, view=view)
    
    elif command == "$mminfosab":
        embed = discord.Embed(
        title="Middleman Info & Explanation",
        description=(
            "ℹ️ **Middleman System Info**\n\n"
            "Our middleman system helps facilitate safe trades between users. Here's how it works:\n\n"
            "**Example:** Trade is a Brainrot for Brainrot (trade between Larry and Harry) .\n\n"
            "**Steps:**\n"
            "1. Log in with Account 1  → take Larry´s items.\n"
            "2. Log in with Account 2 → take Harry´s items.\n"
            "This part is called distribution and will only be done once I have the items from both players.\n"
            "3. Switch back to Account 1 but join Harry → give Harry the items from Larry.\n"
            "4. Remove player Harry from the server since he alr got his stuff.\n"
            "5. Join Player Larry again with Account 2 → give Larry the items taken from Harry.\n"
        ),
        color=0xFFA500
    )

    embed.set_image(url="https://cdn.discordapp.com/attachments/1292876935214534799/1442083659992797184/Middeman_sign.jpg?ex=69242491&is=6922d311&hm=57634a35322b38a76383361a7d6ab5b556a0fc97797a956195398045e99f54c7&")  # Replace with your actual image
    await message.channel.send(embed=embed)




@bot.tree.command(name="setup_hub", description="Set up the Request Middleman button in this channel")
@app_commands.checks.has_permissions(administrator=True)
async def setup_hub(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🛡️ Middleman Services",
        description="Need a middleman for your trade? Click the button below to create a ticket!",
        color=discord.Color.gold()
    )
    embed.add_field(
        name="How it works:",
        value="1️⃣ Click 'Request Middleman'\n2️⃣ Fill out the form\n3️⃣ Wait for a middleman to claim your ticket",
        inline=False
    )
    
    view = RequestMMButton()
    
    await interaction.channel.send(embed=embed, view=view)
    await interaction.response.send_message("✅ Hub button set up successfully!", ephemeral=True)

@bot.tree.command(name="config", description="Configure bot settings")
@app_commands.checks.has_permissions(administrator=True)
async def config_command(interaction: discord.Interaction, 
                         setting: str, 
                         value: str):
    await interaction.response.defer(ephemeral=True)
    
    if setting == "ticket_category":
        try:
            category_id = int(value)
            category = interaction.guild.get_channel(category_id)
            if category and isinstance(category, discord.CategoryChannel):
                bot.config['ticket_category_id'] = category_id
                await interaction.followup.send(f"✅ Ticket category set to: {category.name}")
            else:
                await interaction.followup.send("❌ Invalid category ID")
                return
        except ValueError:
            await interaction.followup.send("❌ Please provide a valid category ID")
            return
    
    elif setting == "log_channel":
        try:
            channel_id = int(value)
            channel = interaction.guild.get_channel(channel_id)
            if channel and isinstance(channel, discord.TextChannel):
                bot.config['log_channel_id'] = channel_id
                await interaction.followup.send(f"✅ Log channel set to: {channel.mention}")
            else:
                await interaction.followup.send("❌ Invalid channel ID")
                return
        except ValueError:
            await interaction.followup.send("❌ Please provide a valid channel ID")
            return
    
    elif setting == "middleman_role":
        try:
            role_id = int(value)
            role = interaction.guild.get_role(role_id)
            if role:
                bot.config['middleman_role_id'] = role_id
                await interaction.followup.send(f"✅ Middleman role set to: {role.name}")
            else:
                await interaction.followup.send("❌ Invalid role ID")
                return
        except ValueError:
            await interaction.followup.send("❌ Please provide a valid role ID")
            return
    
    elif setting == "joinus_role":
        try:
            role_id = int(value)
            role = interaction.guild.get_role(role_id)
            if role:
                bot.config['joinus_role_id'] = role_id
                await interaction.followup.send(f"✅ Join us role set to: {role.name}")
            else:
                await interaction.followup.send("❌ Invalid role ID")
                return
        except ValueError:
            await interaction.followup.send("❌ Please provide a valid role ID")
            return
    
    elif setting == "add_override_role":
        try:
            role_id = int(value)
            role = interaction.guild.get_role(role_id)
            if role:
                if 'override_role_ids' not in bot.config:
                    bot.config['override_role_ids'] = []
                if role_id not in bot.config['override_role_ids']:
                    bot.config['override_role_ids'].append(role_id)
                    await interaction.followup.send(f"✅ Added override role: {role.name}")
                else:
                    await interaction.followup.send(f"⚠️ {role.name} is already an override role")
                    return
            else:
                await interaction.followup.send("❌ Invalid role ID")
                return
        except ValueError:
            await interaction.followup.send("❌ Please provide a valid role ID")
            return
    
    elif setting == "joinus_message":
        bot.config['joinus_message'] = value
        await interaction.followup.send(f"✅ Join us message updated")
    
    else:
        await interaction.followup.send("❌ Unknown setting. Available: ticket_category, log_channel, middleman_role, joinus_role, add_override_role, joinus_message")
        return
    
    with open('config.json', 'w') as f:
        json.dump(bot.config, f, indent=4)

TOKEN = os.getenv('DISCORD_TOKEN')
if not TOKEN:
    print("ERROR: DISCORD_TOKEN not found in environment variables!")
    print("Please add your Discord bot token to the Secrets tab.")
else:
    bot.run(TOKEN)

