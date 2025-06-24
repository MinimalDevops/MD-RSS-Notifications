# RSS to Telegram Notifications

This Python script automatically fetches RSS feeds and forwards new posts to Telegram channels. It keeps track of the last published date for each feed to avoid duplicate posts.

For a detailed guide on setting up Telegram channels and using this project, check out my blog post:
[Automate RSS Feed Delivery to Telegram Channels Using Python](https://minimaldevops.com/automate-rss-feed-delivery-to-telegram-channels-using-python-d4e4a3175ed8)

## Features

- Supports multiple RSS feeds and Telegram channels
- Handles images in RSS posts
- Maintains last published dates in Excel
- Rate limiting handling for Telegram API
- HTML formatting support for messages

## Prerequisites

- Python 3.11 or higher
- A Telegram bot token (get it from [@BotFather](https://t.me/botfather))
- Telegram channel(s) where the bot is an administrator

## Installation

1. Clone the repository:
```bash
git clone <your-repo-url>
cd MD-RSS-Notifications
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

1. Create a `.env` file in the project root:
```
TELEGRAM_BOT_TOKEN=your_bot_token_here
```

2. Create your own `rss_channels.xlsx` file with your RSS feeds:
- Create a new Excel file named `rss_channels.xlsx`
- This file is gitignored by default as it contains your personal channel IDs
- Add the following columns:
  - `rss_link`: The URL of the RSS feed
  - `channel_id`: Your Telegram channel ID (must start with -100)
  - `last_published_date`: The date from which to start fetching updates (format: YYYY-MM-DDTHH:MM:SS+00:00)

Example Excel format:
| rss_link | channel_id | last_published_date |
|----------|------------|---------------------|
| https://example.com/feed | -100xxxxxxxxxxxx | 2024-01-01T00:00:00+00:00 |

## Usage

Run the script manually:
```bash
python rss_to_telegram.py
```

For automated running, set up a cron job (Linux/Mac) or Task Scheduler (Windows).

Example cron job (runs every hour):
```bash
0 * * * * cd /path/to/MD-RSS-Notifications && source venv/bin/activate && python rss_to_telegram.py >> rss_parser.log 2>&1
```

## Directory Structure

```
MD-RSS-Notifications/
├── rss_to_telegram.py    # Main script
├── requirements.txt      # Python dependencies
├── rss_channels.xlsx    # RSS feed configuration
├── .env                 # Environment variables
├── rss_parser_storage/  # Storage for tracking files
└── README.md           # This file
```

## Error Handling

The script includes handling for:
- Network connectivity issues
- Invalid RSS feeds
- Telegram API rate limits
- Missing or invalid configuration

## Contributing

Feel free to submit issues and enhancement requests!

## License

[Your chosen license] 