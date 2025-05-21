import asyncio
import logging
import sys
import os
from typing import Dict, Any

# Configure logging - make it more verbose for debugging
logging.basicConfig(
    level=logging.DEBUG,  # Changed from INFO to DEBUG
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("telegram_bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configure python-telegram-bot and httpx libraries for more verbose logging
logging.getLogger('telegram').setLevel(logging.DEBUG)
logging.getLogger('httpx').setLevel(logging.DEBUG)

# Import our modules
import config
from userbot import UserBot
from bot import TelegramBot

async def setup_and_run():
    """Set up and run both clients."""
    # Print config values for debugging
    print("=== Configuration ===")
    print(f"API_ID: {config.API_ID}")
    print(f"API_HASH: {'Set' if config.API_HASH else 'Not set'}")
    print(f"BOT_TOKEN: {'Set' if config.BOT_TOKEN else 'Not set'}")
    print(f"TARGET_CHANNEL: {config.TARGET_CHANNEL}")
    print(f"OWNER_ID: {config.OWNER_ID}")
    print(f"ADMIN_IDS: {config.ADMIN_IDS}")
    print(f"KEYWORDS: {config.KEYWORDS}")
    print("====================")
    
    # Validate configuration first
    config_issues = config.validate_config()
    if config_issues:
        for key, issue in config_issues.items():
            logger.error(f"Configuration error: {issue}")
        logger.error("Please check your .env file and fix the above issues.")
        return  # Changed from sys.exit(1) to allow for more graceful termination
    
    try:
        # Create UserBot instance
        userbot = UserBot()
        
        # Create Bot instance with reference to UserBot
        bot = TelegramBot(userbot)
        
        # Set bot client reference in userbot
        userbot.set_bot_client(bot)
        
        # Start both clients
        logger.info("Starting UserBot client...")
        await userbot.start()
        
        logger.info("Starting Bot client...")
        try:
            # Initialize the bot application
            application = await bot.start()
            
            # Show information about how to use the bot
            logger.info("=========== HOW TO USE ============")
            bot_info = await bot.application.bot.get_me()
            logger.info(f"Bot username: @{bot_info.username}")
            logger.info("Send /start to the bot to begin using it.")
            logger.info("==================================")
            
            # Start bot - the correct way in PTB v20+ is to use application.run_polling()
            # BUT we need to handle it differently since we're already in an async context
            logger.info("Starting bot polling...")
            
            # For v20+, we need to just call start() to initialize the bot's API connection
            # and then we manually create and run updater in the background
            await application.initialize()
            
            # Actually start the bot to receive updates
            await application.start()
            
            # Create update tasks in a non-blocking way
            application.create_task(
                application.updater.start_polling(
                    poll_interval=1.0,
                    timeout=30,
                    drop_pending_updates=True,
                    allowed_updates=["message", "callback_query", "inline_query", "chat_member"]
                )
            )
            
            logger.info("Both clients are now running!")
            
            # Keep the application alive
            while True:
                await asyncio.sleep(10)
                
        except Exception as bot_error:
            logger.error(f"Failed to start bot: {str(bot_error)}")
            logger.error("This might be due to an invalid BOT_TOKEN or network issues.")
            raise bot_error
            
    except KeyboardInterrupt:
        logger.info("Received stop signal, shutting down...")
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        logger.exception("Detailed error information:")
    finally:
        # Stop both clients
        logger.info("Stopping clients...")
        
        # Stop UserBot
        try:
            if 'userbot' in locals() and userbot.running:
                await userbot.stop()
        except Exception as e:
            logger.error(f"Error stopping UserBot: {str(e)}")
        
        # Stop official Bot
        try:
            if 'bot' in locals() and hasattr(bot, 'application') and bot.application:
                await bot.stop()
        except Exception as e:
            logger.error(f"Error stopping Bot: {str(e)}")
        
        logger.info("Both clients have been stopped.")

def main():
    """Main entry point."""
    try:
        # Handle Windows-specific asyncio settings
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        # Print Python version for debugging
        print(f"Python version: {sys.version}")
        
        # Run the bot
        asyncio.run(setup_and_run())
    except KeyboardInterrupt:
        print("Bot stopped by user!")
    except Exception as e:
        print(f"Error: {str(e)}")
        logger.exception("Unhandled exception:")

if __name__ == "__main__":
    main() 