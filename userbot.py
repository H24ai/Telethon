import asyncio
import re
from datetime import datetime
from telethon import TelegramClient, events
from telethon.tl.types import User, Channel, Chat
from telethon.tl.functions.channels import JoinChannelRequest, LeaveChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest
from telethon.errors import ChatAdminRequiredError, ChannelPrivateError, UserNotParticipantError, FloodWaitError

import config

class UserBot:
    def __init__(self):
        """Initialize the UserBot with Telethon client."""
        self.client = None
        self.running = False
        self.bot_client = None  # Will be set later by main.py
    
    async def start(self):
        """Start the UserBot client."""
        self.client = TelegramClient('userbot_session', config.API_ID, config.API_HASH)
        await self.client.start()
        self.running = True
        
        # Register message handler for keyword monitoring
        self.client.add_event_handler(
            self.keyword_monitor,
            events.NewMessage(incoming=True, outgoing=False, chats=None)
        )
        
        print("🟢 UserBot has started successfully!")
        return self.client
    
    async def stop(self):
        """Stop the UserBot client."""
        if self.client:
            await self.client.disconnect()
            self.running = False
            print("🔴 UserBot has been stopped.")
    
    async def keyword_monitor(self, event):
        """Monitor messages for keywords and forward them if matched."""
        # Skip if message is from a private chat
        if event.is_private:
            return
        
        # Get the text message
        message_text = event.message.text or event.message.caption or ""
        if not message_text:
            return
            
        # Check if message contains any of the keywords
        for keyword in config.KEYWORDS:
            if re.search(rf'\b{re.escape(keyword)}\b', message_text, re.IGNORECASE):
                try:
                    # Get sender information
                    sender = await event.get_sender()
                    chat = await event.get_chat()
                    
                    # Prepare user information
                    sender_name = ""
                    username = "غير متوفر"
                    user_id = 0
                    
                    if isinstance(sender, User):
                        user_id = sender.id
                        sender_name = f"{sender.first_name} {sender.last_name if sender.last_name else ''}"
                        username = f"@{sender.username}" if sender.username else "غير متوفر"
                    
                    # Get message link
                    try:
                        message_link = f"https://t.me/c/{str(event.chat_id)[4:]}/{event.message.id}" if str(event.chat_id).startswith("-100") else "غير متوفر"
                    except:
                        message_link = "غير متوفر"
                    
                    # Format the forwarded message
                    formatted_message = config.MESSAGE_FORWARD_FORMAT.format(
                        message=message_text,
                        sender_name=sender_name.strip(),
                        username=username,
                        user_id=user_id,
                        message_link=message_link,
                        date=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    )
                    
                    # Send the formatted message to the target channel
                    try:
                        # Make sure the target channel ID has the correct format
                        target_channel = config.TARGET_CHANNEL
                        
                        # For channels/supergroups, IDs should start with -100
                        # Convert if needed
                        if target_channel < 0 and not str(target_channel).startswith('-100'):
                            # Remove negative sign and add -100 prefix
                            target_channel = int(f"-100{str(abs(target_channel))}")
                        
                        # Try to send the message using the entity object instead of direct ID
                        try:
                            # Get entity first
                            entity = await self.client.get_entity(target_channel)
                            await self.client.send_message(entity, formatted_message)
                            print(f"🔄 Forwarded message containing keyword '{keyword}' to target channel")
                        except Exception as e1:
                            # Fallback to direct ID
                            await self.client.send_message(target_channel, formatted_message)
                            print(f"🔄 Forwarded message containing keyword '{keyword}' to target channel")
                    except Exception as e:
                        print(f"❌ Error forwarding message: {str(e)}")
                    break
                    
                except Exception as e:
                    print(f"❌ Error forwarding message: {str(e)}")
                break
    
    async def status(self):
        """Check connection status of UserBot."""
        if not self.running or not self.client:
            return "UserBot is not running."
            
        try:
            me = await self.client.get_me()
            return f"✅ UserBot is running!\nConnected as: {me.first_name} (@{me.username if me.username else 'No username'}) - ID: {me.id}"
        except Exception as e:
            return f"❌ Error checking UserBot status: {str(e)}"
    
    async def send_message(self, target, message):
        """Send a message to a user or channel."""
        if not self.running:
            return "❌ UserBot is not running."
            
        try:
            # Check if target is a numeric ID or a username
            if target.isdigit() or (target.startswith("-") and target[1:].isdigit()):
                target_id = int(target)
                entity = await self.client.get_entity(target_id)
            else:
                # If not numeric, treat as username (with or without @)
                username = target[1:] if target.startswith("@") else target
                entity = await self.client.get_entity(username)
                
            # Send message
            await self.client.send_message(entity, message)
            return f"✅ Message sent successfully to {target}"
            
        except Exception as e:
            return f"❌ Error sending message: {str(e)}"
    
    async def broadcast(self, message):
        """Send a message to all groups the user is in."""
        if not self.running:
            return "❌ UserBot is not running."
            
        try:
            count = 0
            failed = 0
            
            # Get all dialogs (chats, groups, channels)
            async for dialog in self.client.iter_dialogs():
                # Check if it's a group or channel
                if dialog.is_group or dialog.is_channel:
                    try:
                        # Try to send message
                        await self.client.send_message(dialog.entity, message)
                        count += 1
                        await asyncio.sleep(0.5)  # Short delay to avoid flood limits
                    except Exception:
                        failed += 1
            
            return f"✅ Broadcast complete: Sent to {count} groups/channels, failed in {failed} groups/channels."
            
        except Exception as e:
            return f"❌ Error during broadcast: {str(e)}"
    
    async def join_group(self, link):
        """Join a group or channel using an invite link or username."""
        if not self.running:
            return "❌ UserBot is not running."
            
        try:
            # Check if it's an invite link with hash
            hash_match = re.search(r't\.me/\+([a-zA-Z0-9_-]+)', link)
            if hash_match:
                invite_hash = hash_match.group(1)
                await self.client(ImportChatInviteRequest(invite_hash))
                return f"✅ Successfully joined the group via invite link."
            
            # Check if it's a public username link or just username
            username_match = re.search(r't\.me/([a-zA-Z0-9_]+)', link)
            username = None
            
            if username_match:
                username = username_match.group(1)
            elif not link.startswith(("https:", "http:", "t.me")):
                # If it's just the username
                username = link[1:] if link.startswith("@") else link
            
            if username:
                entity = await self.client.get_entity(username)
                await self.client(JoinChannelRequest(entity))
                return f"✅ Successfully joined {username}."
            
            return "❌ Invalid link format. Please use a t.me link or a username."
            
        except Exception as e:
            return f"❌ Error joining group: {str(e)}"
    
    async def leave_chat(self, chat_id):
        """Leave a group or channel."""
        if not self.running:
            return "❌ UserBot is not running."
            
        try:
            # Convert string to integer if it's a numeric ID
            if chat_id.isdigit() or (chat_id.startswith("-") and chat_id[1:].isdigit()):
                chat_id = int(chat_id)
            else:
                # If not numeric, treat as username
                entity = await self.client.get_entity(chat_id)
                chat_id = entity.id
            
            # Get the entity
            entity = await self.client.get_entity(chat_id)
            
            # Leave the chat
            if isinstance(entity, (Channel, Chat)):
                await self.client(LeaveChannelRequest(entity))
                return f"✅ Successfully left the chat with ID {chat_id}"
            else:
                return "❌ This is not a group or channel."
                
        except Exception as e:
            return f"❌ Error leaving chat: {str(e)}"
    
    async def get_user_info(self, user_id_or_username):
        """Get information about a user."""
        if not self.running:
            return "❌ UserBot is not running."
            
        try:
            # Check if it's a user ID or username
            if user_id_or_username.isdigit():
                user_id = int(user_id_or_username)
                entity = await self.client.get_entity(user_id)
            else:
                # If not numeric, treat as username (with or without @)
                username = user_id_or_username[1:] if user_id_or_username.startswith("@") else user_id_or_username
                entity = await self.client.get_entity(username)
            
            # Get user information
            if isinstance(entity, User):
                first_name = entity.first_name or ""
                last_name = entity.last_name or ""
                user_id = entity.id
                username = f"@{entity.username}" if entity.username else "غير متوفر"
                
                info = f"👤 User Information:\n" \
                       f"Name: {first_name} {last_name}\n" \
                       f"Username: {username}\n" \
                       f"User ID: {user_id}"
                return info
            else:
                return "❌ This is not a user."
                
        except Exception as e:
            return f"❌ Error getting user info: {str(e)}"

    def set_bot_client(self, bot_client):
        """Set the bot client reference for communication."""
        self.bot_client = bot_client 