# Discord Middleman Ticket Bot

A Discord bot that manages middleman tickets for safe trading between users.

## Features

- **Request Middleman Button**: Interactive button in hub channel to create tickets
- **Modal Form**: Collects trade description and other trader's information
- **Private Ticket Channels**: Automatically creates channels with proper permissions
- **Claim System**: Middlemen can claim tickets with a button
- **Ticket Management Commands**: Full suite of commands for managing tickets
- **Logging System**: Logs all closed tickets to a designated channel
- **Role-Based Permissions**: Override system for Staff/Admin roles

## Setup Instructions

### 1. Create a Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and give it a name
3. Go to the "Bot" tab and click "Add Bot"
4. Under "Privileged Gateway Intents", enable:
   - MESSAGE CONTENT INTENT
   - SERVER MEMBERS INTENT
5. Click "Reset Token" and copy your bot token

### 2. Add Bot Token to Replit

1. Click on the "Secrets" tab (🔒 icon) in the left sidebar
2. Add a new secret:
   - Key: `DISCORD_TOKEN`
   - Value: (paste your bot token)

### 3. Invite Bot to Your Server

1. In Discord Developer Portal, go to OAuth2 → URL Generator
2. Select scopes: `bot` and `applications.commands`
3. Select permissions:
   - Manage Channels
   - Manage Roles
   - Send Messages
   - Embed Links
   - Read Message History
   - Use Slash Commands
4. Copy the generated URL and open it to invite the bot

### 4. Configure the Bot

Use the `/config` command (requires Administrator permission):

```
/config setting:middleman_role value:<role_id>
/config setting:joinus_role value:<role_id>
/config setting:ticket_category value:<category_id>
/config setting:log_channel value:<channel_id>
/config setting:add_override_role value:<role_id>
```

**To get IDs**: Enable Developer Mode in Discord (Settings → Advanced → Developer Mode), then right-click on roles/channels and click "Copy ID"

### 5. Set Up Hub Channel

In the channel where you want the "Request Middleman" button:
```
/setup_hub
```

## Commands

### User Commands (anyone can use)
- `$joinus` - Posts preset promo/invite message with Accept/Decline buttons
  - When a user clicks "Accept": Bot sends acceptance message and assigns the configured role
  - When a user clicks "Decline": Bot sends declined message
- `$mminfo` - Posts MM system explanation (hardcoded message)
- `$close` - Closes the current ticket

### Middleman Commands (claimer or override roles only)
- `$add @user` - Adds a user to the ticket
- `$remove @user` - Removes a user from the ticket
- `$unclaim` - Releases the claim on the ticket
- `$rename <name>` - Renames the ticket channel to mm-<name>

### Admin Commands (slash commands)
- `/setup_hub` - Creates the Request Middleman button
- `/config` - Configure bot settings

## How It Works

1. User clicks "Request Middleman" button in hub channel
2. Modal form appears asking for:
   - Trade description
   - Other trader's Discord ID or @mention
3. Bot creates a private ticket channel with:
   - Requesting user
   - Other trader
   - Middlemen role
4. Ticket includes an embed with trade info and a "Claim" button
5. First middleman to click "Claim" is assigned to the ticket
6. Middleman manages the trade using ticket commands
7. Anyone can use `$close` to close the ticket
8. Closed tickets are logged to the log channel

## Customization

You can customize the following in `config.json` or via `/config`:
- `joinus_message` - Message for $joinus command
- `joinus_role_id` - Role that gets assigned when users accept the $joinus prompt
- `ticket_category_id` - Category where tickets are created
- `log_channel_id` - Channel where closed tickets are logged
- `middleman_role_id` - Role that can claim tickets
- `override_role_ids` - Roles that bypass permission checks (Staff, Head MM, etc.)

**Note:** The `$mminfo` command message is hardcoded in the bot and can only be changed by editing the bot.py file directly.

## Support

If you need help or encounter issues:
1. Make sure all required intents are enabled in Discord Developer Portal
2. Check that the bot has proper permissions in your server
3. Verify all IDs in config.json are correct
4. Check the console logs for error messages
