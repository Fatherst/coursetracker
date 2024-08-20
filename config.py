from dotenv import load_dotenv
import os

load_dotenv()

BOT_TOKEN = os.environ.get("BOT_TOKEN")
COINMARKETCAP_API_KEY = os.environ.get("COINMARKETCAP_API_KEY")