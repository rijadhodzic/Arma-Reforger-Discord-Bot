# Arma Reforger Discord Bot

A Discord bot for managing your Arma Reforger dedicated server directly from Discord — kick players, ban/unban, and view online players, all via slash commands.

## Features

- `/players` — list all online players with their UIDs
- `/kick <player> [reason]` — kick a player by name or UID
- `/ban <player> [reason] [duration]` — ban a player (temporary or permanent)
- `/bans` — list all active bans with their IDs
- `/unban <ban_id>` — remove a ban by ID
- Role-based access control — only Discord members with the configured admin role can use commands
- Partial name matching — no need to type exact player names
- Rich embeds for all responses

## Requirements

- Python 3.10+
- Arma Reforger dedicated server with REST API enabled (port 8080)
- A Discord bot token

## Installation

```bash
git clone https://github.com/YOUR_USERNAME/arma-reforger-discord-bot
cd arma-reforger-discord-bot

python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

## Configuration

Copy the example env file and fill in your values:

```bash
cp .env.example .env
nano .env
```

| Variable | Description | Default |
|---|---|---|
| `DISCORD_TOKEN` | Your Discord bot token | — |
| `ARMA_API_HOST` | Base URL of your server's REST API | `http://localhost:8080` |
| `ARMA_API_USER` | REST API username | `admin` |
| `ARMA_API_PASS` | Your server's `adminPassword` from `serverHosting.json` | — |
| `ADMIN_ROLE_NAME` | Discord role name allowed to use commands | `Admin` |

## Enabling the Arma Reforger REST API

In your `serverHosting.json`, make sure `adminPassword` is set:

```json
{
  "adminPassword": "YOUR_STRONG_PASSWORD",
  ...
}
```

Then launch the server with the `-restApiPort` flag:

```bash
./ArmaReforgerServer -config serverHosting.json -restApiPort 8080
```

Test it:

```bash
curl -u admin:YOUR_PASSWORD http://localhost:8080/api/v1/session/players
```

> **Security:** Do not expose port 8080 publicly. Run the bot on the same machine as the server and connect via `localhost`. If the bot is on a separate machine, use an SSH tunnel.

## Running

```bash
source venv/bin/activate
python bot.py
```

## Running as a systemd service (Linux)

Edit `arma-bot.service` — replace `YOUR_LINUX_USER` with your actual username — then:

```bash
sudo cp arma-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now arma-bot

# Check status
sudo systemctl status arma-bot

# View logs
sudo journalctl -u arma-bot -f
```

## Usage

All commands are Discord slash commands and require the configured admin role.

**List online players:**
```
/players
```

**Kick a player** (by name or UID):
```
/kick player:Rijad reason:Teamkilling
```

**Ban a player** (duration in minutes, 0 = permanent):
```
/ban player:Rijad reason:Cheating duration:0
/ban player:Rijad reason:Abusive language duration:60
```

**List active bans:**
```
/bans
```

**Remove a ban:**
```
/unban ban_id:abc123
```

> Tip: Player names support partial matching. `/kick player:rij` will match `Rijad` as long as no other online player has "rij" in their name. If the name is ambiguous, the bot will ask you to use the UID instead.

## Project Structure

```
arma-reforger-discord-bot/
├── bot.py               # Main bot — slash commands + Arma REST client
├── .env.example         # Environment variable template
├── requirements.txt     # Python dependencies
├── arma-bot.service     # systemd unit file
└── README.md
```
