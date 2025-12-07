# ConnectProBot 🤖

A production-grade Telegram SaaS bot system for connecting users with business/channel owners.

## Features

- **Main Bot**: ConnectProBot (@connectsprobot)
- **Mini-Bots**: Business owners can create their own branded bots
- **Two Usage Flows**:
  - Start With This Bot (Free with limits)
  - Start Your Own Bot (4 months free trial)
- **Admin Panel**: Full management and analytics
- **Global Broadcast**: Send announcements to owners/users
- **Privacy Protected**: No personal info shared

## Tech Stack

- Python 3.11+
- python-telegram-bot v21+ (async)
- PostgreSQL (Railway)
- APScheduler for scheduled tasks

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/connectprobot.git
cd connectprobot
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

Create a `.env` file based on `.env.example`:

```bash
cp .env.example .env
```

Edit `.env` with your values:
- `BOT_TOKEN`: Get from @BotFather
- `ADMIN_IDS`: Your Telegram user ID
- `DATABASE_URL`: PostgreSQL connection string

### 4. Run Locally

```bash
python main.py
```

## Deploy to Railway

### 1. Create Railway Account
Go to [railway.app](https://railway.app) and sign up.

### 2. Create New Project
- Click "New Project"
- Select "Deploy from GitHub repo"
- Connect your repository

### 3. Add PostgreSQL
- Click "New" → "Database" → "PostgreSQL"
- Railway will auto-set DATABASE_URL

### 4. Set Environment Variables
In your Railway project settings, add:
- `BOT_TOKEN`
- `ADMIN_IDS`

### 5. Deploy
Railway will automatically deploy when you push to main branch.

## Project Structure

```
connectprobot/
├── main.py              # Entry point
├── config.py            # Configuration
├── database.py          # Database operations
├── requirements.txt     # Dependencies
├── .env.example         # Env template
├── services/
│   ├── bot_factory.py   # Mini bot management
│   ├── trial_service.py # Trial management
│   ├── message_router.py# Message routing
│   └── cleanup_service.py# Data cleanup
├── handlers/
│   ├── start.py         # /start command
│   ├── registration.py  # Registration flow
│   ├── owner_onboarding.py # Owner setup
│   ├── user_chat.py     # User messaging
│   └── admin_panel.py   # Admin commands
└── templates/
    ├── intro_text.py    # Message templates
    └── footer.py        # Footer template
```

## Commands

### User Commands
- `/start` - Start the bot

### Owner Commands
- `/dashboard` - Access owner dashboard

### Admin Commands
- `/admin` - Access admin panel

## Database Schema

### Tables
- `users` - All bot users
- `owners` - Business/channel owners
- `conversations` - User-owner conversations
- `messages` - Chat messages (auto-deleted after 72 days)

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| FREE_MODE_MESSAGE_LIMIT | 2 | Messages per user per day (free mode) |
| FREE_MODE_START_HOUR | 9 | Free mode start time (9 AM) |
| FREE_MODE_END_HOUR | 23 | Free mode end time |
| TRIAL_DAYS | 120 | Mini bot trial period (4 months) |
| MESSAGE_RETENTION_DAYS | 72 | Message auto-delete after days |

## License

MIT License

## Support

For issues and feature requests, please open an issue on GitHub.

---

**This Bot was made using @Connectsprobot**
