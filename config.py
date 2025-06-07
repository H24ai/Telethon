import os
import json
from dotenv import load_dotenv
from typing import List, Dict, Any

# Load environment variables from .env file
load_dotenv()

# Telethon (UserBot) credentials
API_ID = int(os.getenv('API_ID', 0))
API_HASH = os.getenv('API_HASH', '')

# Official Bot credentials
# Hardcoded token as fallback
BOT_TOKEN = os.getenv('BOT_TOKEN', '') or '7365699658:AAEWrOYPJ8cUXevK69YUjCit3OrN95ixlfM'

# Target channel for forwarding messages
# The format for channels must start with "-100" followed by the actual ID
target_channel_str = os.getenv('TARGET_CHANNEL', '')
if target_channel_str:
    if target_channel_str.startswith('-') and not target_channel_str.startswith('-100'):
        # Add -100 prefix for channels if not already present
        TARGET_CHANNEL = int("-100" + target_channel_str[1:])
    else:
        TARGET_CHANNEL = int(target_channel_str)
else:
    TARGET_CHANNEL = 0

# Owner ID - the main admin who can add/remove other admins
owner_id_str = os.getenv('OWNER_ID', '0')
try:
    OWNER_ID = int(owner_id_str)
except ValueError:
    print(f"Warning: Invalid owner ID format: {owner_id_str}")
    OWNER_ID = 0

# Admin IDs list file path
ADMINS_FILE = "admins.json"

# Admin user IDs who can control the bot
# Support for multiple admins
ADMIN_IDS = []

# Load admins from file if it exists
def load_admins():
    global ADMIN_IDS
    try:
        if os.path.exists(ADMINS_FILE):
            with open(ADMINS_FILE, 'r', encoding='utf-8') as f:
                admins = json.load(f)
                # Ensure all admins are integers
                ADMIN_IDS = [int(admin_id) for admin_id in admins]
                return
    except Exception as e:
        print(f"Error loading admin IDs: {str(e)}")
    
    # If file doesn't exist or error loading, check environment variables
    admin_ids_str = os.getenv('ADMIN_IDS', '')
    if admin_ids_str:
        # Split by commas if multiple IDs are provided
        for admin_id in admin_ids_str.split(','):
            try:
                ADMIN_IDS.append(int(admin_id.strip()))
            except ValueError:
                print(f"Warning: Invalid admin ID format: {admin_id}")

    # For backward compatibility - also check the single ADMIN_ID
    single_admin_id = os.getenv('ADMIN_ID', '0')
    if single_admin_id and single_admin_id.strip() != '0':
        try:
            single_id = int(single_admin_id.strip())
            if single_id not in ADMIN_IDS:
                ADMIN_IDS.append(single_id)
        except ValueError:
            print(f"Warning: Invalid admin ID format: {single_admin_id}")

    # Always include the owner in admin list if specified
    if OWNER_ID != 0 and OWNER_ID not in ADMIN_IDS:
        ADMIN_IDS.append(OWNER_ID)

    # If no admin IDs are specified, default to 0 (allows initial setup)
    if not ADMIN_IDS:
        ADMIN_IDS = [0]
    
    # Save initial admin list to file
    save_admins()

# Save admin IDs to file
def save_admins():
    try:
        with open(ADMINS_FILE, 'w', encoding='utf-8') as f:
            json.dump(ADMIN_IDS, f, ensure_ascii=False, indent=2)
        print(f"✅ Admin IDs saved to {ADMINS_FILE}")
    except Exception as e:
        print(f"❌ Error saving admin IDs: {str(e)}")

# Add a new admin
def add_admin(user_id: int) -> bool:
    if user_id in ADMIN_IDS:
        return False  # Already an admin
    ADMIN_IDS.append(user_id)
    save_admins()
    return True

# Remove an admin
def remove_admin(user_id: int) -> bool:
    if user_id == OWNER_ID:
        return False  # Cannot remove owner
    if user_id not in ADMIN_IDS:
        return False  # Not an admin
    ADMIN_IDS.remove(user_id)
    save_admins()
    return True

# Initialize admin IDs
load_admins()

# Keywords to monitor in groups
# Default keywords that are always included
DEFAULT_KEYWORDS = [
    'عاجل',
    'خصم',
    'هام',
    'حصري',
]

# Load keywords from file if it exists
def load_keywords():
    keywords_file = "keywords.json"
    try:
        if os.path.exists(keywords_file):
            with open(keywords_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # If file doesn't exist, use default keywords and create the file
            with open(keywords_file, 'w', encoding='utf-8') as f:
                json.dump(DEFAULT_KEYWORDS, f, ensure_ascii=False, indent=2)
            return DEFAULT_KEYWORDS
    except Exception as e:
        print(f"Error loading keywords: {str(e)}")
        return DEFAULT_KEYWORDS

# Initialize keywords from file or defaults
KEYWORDS = load_keywords()

# Advanced settings
MESSAGE_FORWARD_FORMAT = """
📬 رسالة جديدة تحتوي على كلمة مفتاحية:

📝 الرسالة: {message}

👤 المرسل: {sender_name}
🔖 المعرف: {username}
🆔 الآيدي: {user_id}
🔗 رابط الرسالة: {message_link}

📅 {date}
"""

# Validation function to ensure all required environment variables are set
def validate_config() -> Dict[str, Any]:
    """Validate that all required configuration variables are set properly."""
    issues = {}
    
    if API_ID == 0:
        issues['API_ID'] = "API_ID is not set or invalid"
    
    if not API_HASH:
        issues['API_HASH'] = "API_HASH is not set"
    
    if not BOT_TOKEN:
        issues['BOT_TOKEN'] = "BOT_TOKEN is not set"
    
    if TARGET_CHANNEL == 0:
        issues['TARGET_CHANNEL'] = "TARGET_CHANNEL is not set or invalid"
    
    # Admin IDs are optional for initial setup
    
    return issues 
