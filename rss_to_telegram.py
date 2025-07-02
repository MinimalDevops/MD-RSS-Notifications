import pandas as pd
import json
import requests
from dateutil import parser
from time import sleep
import feedparser
import os
import ssl
from dotenv import load_dotenv
import re
from html import unescape

# Load environment variables
load_dotenv()

# Get configuration from environment variables
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("Please set TELEGRAM_BOT_TOKEN in .env file")

# Directory where the last published dates will be stored
STORAGE_DIR = 'rss_parser_storage/'
if not os.path.exists(STORAGE_DIR):
    os.makedirs(STORAGE_DIR)

# Get Excel file path, defaulting to local directory
EXCEL_FILE_PATH = os.getenv('RSS_EXCEL_PATH', os.path.join(os.path.dirname(__file__), 'rss_channels.xlsx'))
if not os.path.exists(EXCEL_FILE_PATH):
    raise FileNotFoundError(f"Excel file not found at: {EXCEL_FILE_PATH}")

def get_entry_date(entry):
    """Extract publication date from an RSS entry handling different date field names."""
    date_fields = ['published', 'pubDate', 'updated', 'created', 'date']
    
    for field in date_fields:
        if hasattr(entry, field):
            try:
                return parser.parse(getattr(entry, field))
            except (ValueError, TypeError) as e:
                print(f"Error parsing date from field '{field}': {e}")
                continue
    
    # If no valid date field is found
    print(f"Warning: No valid date field found in entry: {entry.title if hasattr(entry, 'title') else 'Unknown title'}")
    return None

def clean_html_content(text):
    """Clean HTML content for Telegram compatibility."""
    if not text:
        return ""
    
    # Unescape HTML entities
    text = unescape(text)
    
    # Remove unsupported HTML tags but keep their content
    text = re.sub(r'<p.*?>', '\n\n', text)
    text = re.sub(r'</p>', '', text)
    text = re.sub(r'<br.*?>', '\n', text)
    text = re.sub(r'<.*?>', '', text)  # Remove any other HTML tags
    
    # Clean up multiple newlines
    text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)
    text = text.strip()
    
    return text

def format_telegram_message(entry):
    """Format the message for Telegram with proper HTML tags."""
    title = entry.title if hasattr(entry, 'title') else "No title"
    description = entry.description if hasattr(entry, 'description') else ""
    link = entry.link if hasattr(entry, 'link') else ""
    
    # Clean the content
    clean_description = clean_html_content(description)
    
    # Format message with only supported HTML tags
    msg = f"<b>{title}</b>\n\n{clean_description}"
    if link:
        msg += f"\n\n<a href=\"{link}\">Read more</a>"
    
    return msg

# Function to read the Excel file and return a dictionary mapping RSS links to channel IDs and last published dates
def load_feed_channel_map(excel_file):
    df = pd.read_excel(excel_file)
    print("Reading from Excel:")
    print(df)
    feed_channel_map = {}
    for _, row in df.iterrows():
        rss_link = row['rss_link']
        channel_id = str(row['channel_id'])
        last_published_date = row['last_published_date']
        feed_channel_map[rss_link] = {
            'channel_id': channel_id,
            'last_published_date': last_published_date,
            'file_path': os.path.join(STORAGE_DIR, f'{channel_id}.txt')
        }
    return feed_channel_map

# Function to update the last_published_date in the Excel file
def update_last_published_date(excel_file, rss_link, new_last_published_date):
    df = pd.read_excel(excel_file)
    df.loc[df['rss_link'] == rss_link, 'last_published_date'] = new_last_published_date
    df.to_excel(excel_file, index=False)
    print(f"Updated last_published_date for {rss_link} to {new_last_published_date}")

FEEDURL_CHANNEL_MAP = load_feed_channel_map(EXCEL_FILE_PATH)
TELEGRAM_TOO_MANY_REQUESTS_ERROR_CODE = 429
TELEGRAM_PHOTO_CAPTION_LENGTH_LIMIT = 1024

def send_message(channel_id, message, image_url=None):
    try:
        if image_url and len(message) <= TELEGRAM_PHOTO_CAPTION_LENGTH_LIMIT:
            response = requests.get(f'https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto?chat_id={channel_id}&photo={image_url}&caption={message}&parse_mode=html', verify=False)
        else:
            response = requests.get(f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage?chat_id={channel_id}&text={message}&parse_mode=html', verify=False)
        
        print(f"Response Status Code: {response.status_code}")
        print(f"Response Content: {response.content.decode('utf-8')}")

        response.raise_for_status()
    except requests.exceptions.HTTPError as http_err:
        if response.status_code == TELEGRAM_TOO_MANY_REQUESTS_ERROR_CODE:
            retry_in_seconds = int(response.headers.get('Retry-After', 1))
            print(f'Rate limit exceeded. Waiting {retry_in_seconds} seconds before retrying...')
            sleep(retry_in_seconds)
            send_message(channel_id, message, image_url)
        else:
            print(f"HTTP error occurred: {http_err}")
    except Exception as err:
        print(f"An error occurred while sending a message: {err}")


def main():
    for rss_link, details in FEEDURL_CHANNEL_MAP.items():
        try:
            ssl._create_default_https_context = ssl._create_unverified_context
            channel_id = details['channel_id']
            last_update_file = details['file_path']
            last_published_date_str = details['last_published_date']
            print(f"\nProcessing RSS feed: {rss_link}")
            print(f"Last published date from Excel: {last_published_date_str}")

            # Parse the last published date from the Excel file
            last_update = parser.parse(last_published_date_str)
            last_published_date = last_update

            # Parse RSS feed
            rss_feed = feedparser.parse(rss_link)

            # Iterate through entries in reverse order (most recent first)
            for entry in reversed(rss_feed.entries):
                try:
                    # Get entry published date
                    entry_published_date = get_entry_date(entry)
                    if not entry_published_date:
                        continue
                        
                    print(f"Entry published date: {entry_published_date}")

                    # Check if entry is newer than the last update date
                    if entry_published_date > last_update:
                        # Format message with proper HTML
                        msg = format_telegram_message(entry)

                        # Send message to each channel
                        try:
                            # Check if entry has an image and send image with caption if possible
                            if hasattr(entry, 'links') and len(entry.links) > 1 and entry.links[1].href:
                                send_message(channel_id, msg, entry.links[1].href)
                            else:
                                send_message(channel_id, msg)
                            print(f'Sent {entry.link if hasattr(entry, "link") else "Unknown link"}')
                        except Exception as err:
                            print(f"An error occurred while sending a message to {channel_id}: {err}")

                        # Update last published date
                        last_published_date = max(last_published_date, entry_published_date)
                except Exception as err:
                    print(f"An error occurred while processing an entry: {err}")

            # Update last update date in the file and Excel if necessary
            if last_published_date > last_update:
                update_last_published_date(EXCEL_FILE_PATH, rss_link, last_published_date.isoformat())
        except Exception as err:
            print(f"An error occurred while processing the feed '{rss_link}': {err}")

if __name__ == "__main__":
    main()
