from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, CallbackQueryHandler, CommandHandler
from telegram.error import BadRequest
import asyncio
from config import config
from services import db_service

async def start_verification(update: Update, context: CallbackContext):
    """处理 /start 命令，开始验证流程"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # 如果是群组消息，可能不需要验证
    if update.effective_chat.type != 'private':
        # 在群组中，可以回复提示用户私聊机器人进行验证
        await update.message.reply_text("请私聊我进行验证。")
        return
        
    # 获取用户当前的加入状态
    user_status = await db_service.get_user_join_status(user_id)
    
    # 如果已经验证通过，则直接告知用户
    if user_status.get('verified'):
        await update.message.reply_text("✅ 您已经通过验证！可以使用其他功能了。")
        return
        
    # 创建内联键盘按钮
    keyboard = [
        [
            InlineKeyboardButton("加入频道", url=f"https://t.me/{config.REQUIRED_CHANNEL_USERNAME}"),
            InlineKeyboardButton("加入群组", url=f"https://t.me/{config.REQUIRED_GROUP_USERNAME}")
        ],
        [InlineKeyboardButton("✅ 我已加入", callback_data="check_join_status")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # 发送验证消息
    message = await update.message.reply_text(
        "⚠️ 请先加入我们的频道和群组以使用本机器人：\n\n"
        f"• 频道: @{config.REQUIRED_CHANNEL_USERNAME}\n"
        f"• 群组: @{config.REQUIRED_GROUP_USERNAME}\n\n"
        "加入后请点击下方的“✅ 我已加入”按钮进行验证。",
        reply_markup=reply_markup
    )
    
    # 存储发送的消息ID到数据库，以便后续更新消息
    await db_service.update_user_join_status(user_id, verification_message_id=message.message_id)

async def button_callback(update: Update, context: CallbackContext):
    """处理InlineKeyboard按钮的回调"""
    query = update.callback_query
    user_id = update.effective_user.id
    await query.answer()  # 回答回调查询，防止客户端显示“加载中”
    
    if query.data == "check_join_status":
        # 检查用户是否加入了指定的频道和群组
        has_joined_channel = False
        has_joined_group = False
        
        try:
            # 检查是否加入频道
            member_channel = await context.bot.get_chat_member(f"@{config.REQUIRED_CHANNEL_USERNAME}", user_id)
            if member_channel.status not in ['left', 'kicked']:
                has_joined_channel = True
        except BadRequest:
            # 如果无法获取成员信息（通常是因为用户未加入或频道不存在）
            has_joined_channel = False
            
        try:
            # 检查是否加入群组
            member_group = await context.bot.get_chat_member(f"@{config.REQUIRED_GROUP_USERNAME}", user_id)
            if member_group.status not in ['left', 'kicked']:
                has_joined_group = True
        except BadRequest:
            has_joined_group = False
            
        # 更新数据库中的状态
        await db_service.update_user_join_status(
            user_id, 
            has_joined_channel=has_joined_channel,
            has_joined_group=has_joined_group
        )
        
        # 根据检查结果回复用户
        if has_joined_channel and has_joined_group:
            # 用户都已加入，验证通过
            await db_service.update_user_join_status(user_id, verified=True)
            await query.edit_message_text(
                "🎉 验证成功！感谢您的加入。您现在可以使用机器人的所有功能了。\n\n"
                "试试这些命令：\n"
                "/bind <地址> - 绑定TRON钱包地址\n"
                "/balance - 查询余额\n"
                "/help - 获取帮助"
            )
        else:
            # 用户未全部加入，提示具体未加入的项目
            not_joined = []
            if not has_joined_channel:
                not_joined.append(f"频道 @{config.REQUIRED_CHANNEL_USERNAME}")
            if not has_joined_group:
                not_joined.append(f"群组 @{config.REQUIRED_GROUP_USERNAME}")
                
            await query.edit_message_text(
                f"❌ 验证失败。您尚未加入：{', '.join(not_joined)}\n\n"
                "请先点击下方按钮加入，然后再次点击“✅ 我已加入”进行验证。",
                reply_markup=query.message.reply_markup  # 保持按钮不变
            )

def setup_verification_handlers(application):
    """设置验证相关的处理器"""
    application.add_handler(CommandHandler("start", start_verification))
    application.add_handler(CallbackQueryHandler(button_callback))
