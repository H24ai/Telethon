import asyncio
import json
import os
from telegram import Update, BotCommand, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    CallbackQueryHandler
)
from telegram.constants import ParseMode

import config
from typing import Callable, Awaitable, List

class TelegramBot:
    def __init__(self, userbot):
        """Initialize the official Telegram bot with python-telegram-bot."""
        self.application = None
        self.userbot = userbot  # Reference to the UserBot instance
        
    async def start(self):
        """Start the bot and set up command handlers."""
        try:
            # Create the Application with proper polling configuration
            self.application = (
                Application.builder()
                .token(config.BOT_TOKEN)
                .build()
            )
            
            # Add command handlers
            self.application.add_handler(CommandHandler("start", self.cmd_start))
            self.application.add_handler(CommandHandler("help", self.cmd_help))
            self.application.add_handler(CommandHandler("status", self.cmd_status))
            self.application.add_handler(CommandHandler("send", self.cmd_send_message))
            self.application.add_handler(CommandHandler("broadcast", self.cmd_broadcast))
            self.application.add_handler(CommandHandler("join", self.cmd_join))
            self.application.add_handler(CommandHandler("leave", self.cmd_leave))
            self.application.add_handler(CommandHandler("info", self.cmd_info))
            
            # Add new command for keywords management
            self.application.add_handler(CommandHandler("addkeyword", self.cmd_add_keyword))
            self.application.add_handler(CommandHandler("listkeywords", self.cmd_list_keywords))
            self.application.add_handler(CommandHandler("deletekeyword", self.cmd_delete_keyword))

            # Add admin management commands
            self.application.add_handler(CommandHandler("admins", self.cmd_admin_panel))
            self.application.add_handler(CommandHandler("addadmin", self.cmd_add_admin))
            self.application.add_handler(CommandHandler("removeadmin", self.cmd_remove_admin))
            self.application.add_handler(CommandHandler("listadmins", self.cmd_list_admins))
            
            # Add callback handler for inline buttons
            self.application.add_handler(CallbackQueryHandler(self.button_callback))
            
            # Add a handler for ANY message - this helps debug issues
            self.application.add_handler(MessageHandler(filters.ALL, self.handle_message))
            
            # Set up commands for the bot
            await self.setup_commands()
            
            # Just initialize the bot (actual polling will be done in the main.py)
            await self.application.initialize()
            
            # Log startup message with bot username
            me = await self.application.bot.get_me()
            print(f"🟢 Bot @{me.username} has been initialized successfully")
            
            return self.application
            
        except Exception as e:
            print(f"❌ Error starting bot: {str(e)}")
            raise e
    
    async def stop(self):
        """Stop the bot."""
        if self.application:
            await self.application.stop()
            print("🔴 Bot has been stopped.")
    
    async def setup_commands(self):
        """Set up bot commands in the menu."""
        commands = [
            BotCommand("start", "بدء استخدام البوت"),
            BotCommand("help", "عرض المساعدة وقائمة الأوامر"),
            BotCommand("status", "التحقق من حالة اتصال الحساب الشخصي"),
            BotCommand("send", "إرسال رسالة (المعرف/الآيدي الرسالة)"),
            BotCommand("broadcast", "إرسال رسالة لكل المجموعات"),
            BotCommand("join", "الانضمام إلى مجموعة أو قناة"),
            BotCommand("leave", "مغادرة مجموعة أو قناة"),
            BotCommand("info", "عرض معلومات المستخدم"),
            BotCommand("addkeyword", "إضافة كلمة مفتاحية جديدة"),
            BotCommand("listkeywords", "عرض قائمة الكلمات المفتاحية الحالية"),
            BotCommand("deletekeyword", "حذف كلمة مفتاحية"),
            BotCommand("admins", "إدارة المشرفين")
        ]
        
        await self.application.bot.set_my_commands(commands)
        print("✅ Bot commands have been set up")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle all messages. Only respond to admins."""
        if not update.effective_message:
            return

        # Get user ID
        user_id = update.effective_user.id
        
        # Log the message for debugging
        print(f"📨 Received message from {user_id}: {update.effective_message.text}")
        
        # If user is not an admin, ignore the message
        if user_id not in config.ADMIN_IDS and 0 not in config.ADMIN_IDS:
            # Only respond to the /start command from non-admins for initial usage instructions
            if update.effective_message.text and update.effective_message.text.startswith('/start'):
                await update.effective_message.reply_text("⛔ هذا البوت للمسؤولين فقط. لا يمكنك استخدامه.")
            return
            
        # Only handle non-command messages here (commands are handled by their specific handlers)
        if update.effective_message.text and not update.effective_message.text.startswith('/'):
            await update.effective_message.reply_text(f"تم استلام رسالتك: {update.effective_message.text}\nاستخدم /help للحصول على قائمة الأوامر")
    
    async def owner_required(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Check if the user is the owner."""
        user_id = update.effective_user.id
        
        # If OWNER_ID is 0, check if user is in admin list and this is initial setup
        if config.OWNER_ID == 0 and (user_id in config.ADMIN_IDS or 0 in config.ADMIN_IDS):
            # First admin becomes owner
            config.OWNER_ID = user_id
            await update.message.reply_text(f"⚠️ لم يتم تعيين مالك للبوت من قبل. تم تعيينك كمالك (معرف: {user_id}).")
            return True
            
        if user_id != config.OWNER_ID:
            await update.message.reply_text("⛔ هذا الأمر متاح فقط لمالك البوت.")
            return False
            
        return True
    
    async def admin_required(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Check if the user is an admin."""
        user_id = update.effective_user.id
        # For debugging
        print(f"👤 User ID: {user_id} | Admin IDs: {config.ADMIN_IDS} | Match: {user_id in config.ADMIN_IDS}")
        
        # If ADMIN_IDS contains 0, accept any user (for initial setup)
        if 0 in config.ADMIN_IDS:
            await update.message.reply_text("⚠️ لم يتم تكوين معرفات المسؤولين بعد. تم قبولك كمسؤول.")
            return True
            
        if user_id not in config.ADMIN_IDS:
            await update.message.reply_text("⛔ أنت لست مسؤولًا. هذا الأمر متاح فقط للمسؤولين.")
            return False
        return True
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /start command."""
        user_id = update.effective_user.id
        print(f"🚀 Start command received from user {user_id}")
        
        # Check if user is an admin
        if user_id not in config.ADMIN_IDS and 0 not in config.ADMIN_IDS:
            await update.message.reply_text("⛔ هذا البوت للمسؤولين فقط. لا يمكنك استخدامه.")
            return
        
        await update.message.reply_text(
            "👋 مرحبًا بك في بوت التحكم بالحساب الشخصي!\n\n"
            "استخدم /help للحصول على قائمة الأوامر المتاحة."
        )
        
        # For first-time setup, offer to set admin ID
        if 0 in config.ADMIN_IDS and len(config.ADMIN_IDS) == 1:
            # Setup first admin and owner
            config.ADMIN_IDS.remove(0)
            config.ADMIN_IDS.append(user_id)
            config.OWNER_ID = user_id
            config.save_admins()
            
            await update.message.reply_text(
                f"🔧 تم تعيينك كمسؤول أول ومالك للبوت.\n"
                f"معرف حسابك هو: {user_id}\n\n"
                f"يمكنك استخدام الأمر /admins لإدارة المشرفين."
            )
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /help command."""
        # Check if user is an admin
        if not await self.admin_required(update, context):
            return
            
        help_text = (
            "📋 قائمة الأوامر المتاحة:\n\n"
            "/status - التحقق من حالة اتصال الحساب الشخصي\n"
            "/send <username_or_id> <message> - إرسال رسالة لأي مستخدم أو مجموعة\n"
            "/broadcast <message> - إرسال رسالة لكل المجموعات المشترك بها الحساب\n"
            "/join <group_link> - الانضمام إلى مجموعة أو قناة\n"
            "/leave <chat_id> - مغادرة مجموعة أو قناة\n"
            "/info <username_or_id> - عرض معلومات المستخدم\n\n"
            "🔑 إدارة الكلمات المفتاحية:\n"
            "/addkeyword <keyword> - إضافة كلمة مفتاحية جديدة\n"
            "/listkeywords - عرض قائمة الكلمات المفتاحية الحالية\n"
            "/deletekeyword <keyword> - حذف كلمة مفتاحية\n\n"
            "👥 إدارة المشرفين (للمالك فقط):\n"
            "/admins - فتح لوحة إدارة المشرفين\n"
            "/addadmin <user_id> - إضافة مشرف جديد\n"
            "/removeadmin <user_id> - حذف مشرف\n"
            "/listadmins - عرض قائمة المشرفين\n\n"
            "🔍 البوت يراقب الكلمات المفتاحية في جميع المجموعات ويعيد توجيه الرسائل المطابقة."
        )
        
        await update.message.reply_text(help_text)
        
    async def cmd_admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /admins command to manage admins."""
        if not await self.admin_required(update, context):
            return
            
        # Only the owner can manage admins
        if update.effective_user.id != config.OWNER_ID:
            await update.message.reply_text("⛔ فقط مالك البوت يمكنه إدارة المشرفين.")
            return
            
        keyboard = [
            [InlineKeyboardButton("إضافة مشرف", callback_data="admin_add")],
            [InlineKeyboardButton("حذف مشرف", callback_data="admin_remove")],
            [InlineKeyboardButton("عرض قائمة المشرفين", callback_data="admin_list")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "👥 لوحة إدارة المشرفين\n\n"
            "يمكنك إضافة أو حذف المشرفين من هنا.\n"
            "معرف المالك الحالي: " + str(config.OWNER_ID),
            reply_markup=reply_markup
        )
        
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks."""
        query = update.callback_query
        await query.answer()  # Acknowledge the button press
        
        # Check if user is the owner for admin management actions
        if query.from_user.id != config.OWNER_ID:
            await query.edit_message_text(text="⛔ فقط مالك البوت يمكنه إدارة المشرفين.")
            return
            
        if query.data == "admin_add":
            await query.edit_message_text(
                text="لإضافة مشرف جديد، استخدم الأمر:\n"
                "/addadmin <user_id>\n\n"
                "مثال: /addadmin 123456789"
            )
        elif query.data == "admin_remove":
            await query.edit_message_text(
                text="لحذف مشرف، استخدم الأمر:\n"
                "/removeadmin <user_id>\n\n"
                "مثال: /removeadmin 123456789\n\n"
                "لعرض قائمة المشرفين الحاليين، استخدم /listadmins"
            )
        elif query.data == "admin_list":
            admins_text = "👥 قائمة المشرفين الحاليين:\n\n"
            for i, admin_id in enumerate(config.ADMIN_IDS, 1):
                owner_mark = "👑 " if admin_id == config.OWNER_ID else ""
                admins_text += f"{i}. {owner_mark}{admin_id}\n"
                
            await query.edit_message_text(text=admins_text)
    
    async def cmd_add_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /addadmin command to add a new admin."""
        # Check if user is the owner
        if not await self.owner_required(update, context):
            return
            
        # Check arguments
        if len(context.args) != 1:
            await update.message.reply_text("❌ الاستخدام الصحيح: /addadmin <user_id>")
            return
            
        try:
            new_admin_id = int(context.args[0])
            
            if new_admin_id in config.ADMIN_IDS:
                await update.message.reply_text(f"⚠️ المستخدم {new_admin_id} مشرف بالفعل.")
                return
                
            config.add_admin(new_admin_id)
            await update.message.reply_text(f"✅ تمت إضافة المستخدم {new_admin_id} كمشرف بنجاح.")
            
        except ValueError:
            await update.message.reply_text("❌ يجب أن يكون معرف المستخدم رقمًا صحيحًا.")
    
    async def cmd_remove_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /removeadmin command to remove an admin."""
        # Check if user is the owner
        if not await self.owner_required(update, context):
            return
            
        # Check arguments
        if len(context.args) != 1:
            await update.message.reply_text("❌ الاستخدام الصحيح: /removeadmin <user_id>")
            return
            
        try:
            admin_id = int(context.args[0])
            
            if admin_id == config.OWNER_ID:
                await update.message.reply_text("⚠️ لا يمكن حذف مالك البوت من قائمة المشرفين.")
                return
                
            if admin_id not in config.ADMIN_IDS:
                await update.message.reply_text(f"⚠️ المستخدم {admin_id} ليس مشرفًا.")
                return
                
            config.remove_admin(admin_id)
            await update.message.reply_text(f"✅ تم حذف المستخدم {admin_id} من قائمة المشرفين بنجاح.")
            
        except ValueError:
            await update.message.reply_text("❌ يجب أن يكون معرف المستخدم رقمًا صحيحًا.")
    
    async def cmd_list_admins(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /listadmins command to list all admins."""
        # Check if user is an admin
        if not await self.admin_required(update, context):
            return
            
        if not config.ADMIN_IDS:
            await update.message.reply_text("⚠️ لا يوجد مشرفين حاليًا.")
            return
            
        admins_text = "👥 قائمة المشرفين الحاليين:\n\n"
        for i, admin_id in enumerate(config.ADMIN_IDS, 1):
            owner_mark = "👑 " if admin_id == config.OWNER_ID else ""
            admins_text += f"{i}. {owner_mark}{admin_id}\n"
            
        owner_note = f"\n👑 مالك البوت: {config.OWNER_ID}"
        await update.message.reply_text(admins_text + owner_note)
    
    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /status command to check UserBot status."""
        if not await self.admin_required(update, context):
            return
            
        await update.message.reply_text("⏳ جاري التحقق من الحالة...")
        status_message = await self.userbot.status()
        await update.message.reply_text(status_message)
    
    async def cmd_send_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /send command to send a message to a user or group."""
        if not await self.admin_required(update, context):
            return
            
        # Check arguments
        if len(context.args) < 2:
            await update.message.reply_text("❌ الاستخدام الصحيح: /send <username_or_id> <message>")
            return
            
        target = context.args[0]
        message = " ".join(context.args[1:])
        
        await update.message.reply_text(f"⏳ جاري إرسال الرسالة إلى {target}...")
        result = await self.userbot.send_message(target, message)
        await update.message.reply_text(result)
    
    async def cmd_broadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /broadcast command to send a message to all groups."""
        if not await self.admin_required(update, context):
            return
            
        # Check arguments
        if len(context.args) < 1:
            await update.message.reply_text("❌ الاستخدام الصحيح: /broadcast <message>")
            return
            
        message = " ".join(context.args)
        
        await update.message.reply_text("⏳ جاري إرسال الرسالة لكل المجموعات...")
        result = await self.userbot.broadcast(message)
        await update.message.reply_text(result)
    
    async def cmd_join(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /join command to join a group or channel."""
        if not await self.admin_required(update, context):
            return
            
        # Check arguments
        if len(context.args) != 1:
            await update.message.reply_text("❌ الاستخدام الصحيح: /join <group_link>")
            return
            
        link = context.args[0]
        
        await update.message.reply_text("⏳ جاري الانضمام...")
        result = await self.userbot.join_group(link)
        await update.message.reply_text(result)
    
    async def cmd_leave(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /leave command to leave a group or channel."""
        if not await self.admin_required(update, context):
            return
            
        # Check arguments
        if len(context.args) != 1:
            await update.message.reply_text("❌ الاستخدام الصحيح: /leave <chat_id>")
            return
            
        chat_id = context.args[0]
        
        await update.message.reply_text("⏳ جاري مغادرة المجموعة...")
        result = await self.userbot.leave_chat(chat_id)
        await update.message.reply_text(result)
    
    async def cmd_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /info command to get user information."""
        if not await self.admin_required(update, context):
            return
            
        # Check arguments
        if len(context.args) != 1:
            await update.message.reply_text("❌ الاستخدام الصحيح: /info <username_or_id>")
            return
            
        user = context.args[0]
        
        await update.message.reply_text("⏳ جاري جلب المعلومات...")
        result = await self.userbot.get_user_info(user)
        await update.message.reply_text(result)
        
    async def cmd_add_keyword(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /addkeyword command to add a new keyword to monitor."""
        if not await self.admin_required(update, context):
            return
        
        # Check arguments
        if len(context.args) != 1:
            await update.message.reply_text("❌ الاستخدام الصحيح: /addkeyword <keyword>")
            return
            
        keyword = context.args[0].strip()
        
        # Check if keyword already exists
        if keyword in config.KEYWORDS:
            await update.message.reply_text(f"⚠️ الكلمة المفتاحية '{keyword}' موجودة بالفعل.")
            return
        
        # Add keyword to config
        config.KEYWORDS.append(keyword)
        
        # Save to keywords file for persistence
        try:
            self._save_keywords_to_file()
            await update.message.reply_text(f"✅ تمت إضافة الكلمة المفتاحية '{keyword}' بنجاح.")
        except Exception as e:
            await update.message.reply_text(f"❌ حدث خطأ أثناء حفظ الكلمة المفتاحية: {str(e)}")
    
    async def cmd_list_keywords(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /listkeywords command to list all monitored keywords."""
        if not await self.admin_required(update, context):
            return
        
        if not config.KEYWORDS:
            await update.message.reply_text("⚠️ لا توجد كلمات مفتاحية محددة حاليًا.")
            return
            
        keywords_text = "🔑 الكلمات المفتاحية الحالية:\n\n"
        for i, keyword in enumerate(config.KEYWORDS, 1):
            keywords_text += f"{i}. {keyword}\n"
            
        await update.message.reply_text(keywords_text)
        
    async def cmd_delete_keyword(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /deletekeyword command to remove a keyword."""
        if not await self.admin_required(update, context):
            return
        
        # Check arguments
        if len(context.args) != 1:
            await update.message.reply_text("❌ الاستخدام الصحيح: /deletekeyword <keyword>")
            return
            
        keyword = context.args[0].strip()
        
        # Check if keyword exists
        if keyword not in config.KEYWORDS:
            await update.message.reply_text(f"⚠️ الكلمة المفتاحية '{keyword}' غير موجودة.")
            return
        
        # Remove keyword from config
        config.KEYWORDS.remove(keyword)
        
        # Save to keywords file for persistence
        try:
            self._save_keywords_to_file()
            await update.message.reply_text(f"✅ تم حذف الكلمة المفتاحية '{keyword}' بنجاح.")
        except Exception as e:
            await update.message.reply_text(f"❌ حدث خطأ أثناء حذف الكلمة المفتاحية: {str(e)}")
            
    def _save_keywords_to_file(self):
        """Save keywords to a file for persistence."""
        keywords_file = "keywords.json"
        with open(keywords_file, 'w', encoding='utf-8') as f:
            json.dump(config.KEYWORDS, f, ensure_ascii=False, indent=2) 