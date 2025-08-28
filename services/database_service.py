import sqlite3
from contextlib import contextmanager
from config import config

@contextmanager
def get_db_connection():
    """获取数据库连接的上下文管理器，确保连接正确关闭"""
    conn = sqlite3.connect(config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # 允许以字典形式访问列
    try:
        yield conn
    finally:
        conn.close()

def init_database():
    """初始化数据库，创建必要的表"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 创建钱包地址表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_wallets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                chat_id INTEGER NOT NULL,
                wallet_address TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, wallet_address)
            )
        ''')
        
        # 创建群组设置表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS group_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL UNIQUE,
                welcome_message TEXT,
                is_monitoring_enabled BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建用户加入状态表（用于验证用户是否加入了指定的频道和群组）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_join_status (
                user_id INTEGER PRIMARY KEY,
                has_joined_channel BOOLEAN DEFAULT 0,
                has_joined_group BOOLEAN DEFAULT 0,
                verified BOOLEAN DEFAULT 0,
                verification_message_id INTEGER, -- 存储发送的验证消息ID，便于更新
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建违规记录表（用于群管功能）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_violations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                chat_id INTEGER NOT NULL,
                reason TEXT,
                action_taken TEXT, -- 如 'mute', 'ban'
                duration INTEGER, -- 禁言时长（秒），封禁则为NULL
                admin_id INTEGER, -- 执行操作的管理员ID
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()

class DatabaseService:
    def __init__(self):
        init_database()
        
    async def add_wallet_address(self, user_id: int, chat_id: int, address: str):
        """添加用户绑定的钱包地址"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO user_wallets (user_id, chat_id, wallet_address) VALUES (?, ?, ?)",
                (user_id, chat_id, address)
            )
            conn.commit()
            
    async def get_user_wallets(self, user_id: int):
        """获取用户的所有钱包地址"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT wallet_address FROM user_wallets WHERE user_id = ?",
                (user_id,)
            )
            return [row['wallet_address'] for row in cursor.fetchall()]
            
    async def set_welcome_message(self, chat_id: int, message: str):
        """设置群组的欢迎消息"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO group_settings (chat_id, welcome_message) 
                   VALUES (?, ?) 
                   ON CONFLICT(chat_id) DO UPDATE SET welcome_message = ?""",
                (chat_id, message, message)
            )
            conn.commit()
            
    async def get_user_join_status(self, user_id: int):
        """获取用户的加入验证状态"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM user_join_status WHERE user_id = ?",
                (user_id,)
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
            else:
                # 如果用户不存在于表中，则初始化一条记录
                cursor.execute(
                    "INSERT INTO user_join_status (user_id) VALUES (?)",
                    (user_id,)
                )
                conn.commit()
                return {'user_id': user_id, 'has_joined_channel': False, 'has_joined_group': False, 'verified': False, 'verification_message_id': None}
                
    async def update_user_join_status(self, user_id: int, ​**kwargs):
        """更新用户的加入状态（例如 has_joined_channel, has_joined_group, verified）"""
        set_clause = ", ".join([f"{key} = ?" for key in kwargs.keys()])
        values = list(kwargs.values())
        values.append(user_id)  # 用于WHERE子句
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"UPDATE user_join_status SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
                values
            )
            conn.commit()
            
    async def record_violation(self, user_id: int, chat_id: int, reason: str, action_taken: str, duration: int = None, admin_id: int = None):
        """记录用户的违规行为和管理员采取的操作"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO user_violations (user_id, chat_id, reason, action_taken, duration, admin_id)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (user_id, chat_id, reason, action_taken, duration, admin_id)
            )
            conn.commit()

# 创建全局数据库服务实例
db_service = DatabaseService()
