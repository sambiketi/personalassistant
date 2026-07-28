import redis
import json
import os
from datetime import datetime

class RedisClient:
    def __init__(self):
        self.client = None
        self.fallback_data = {}
        
        try:
            self.client = redis.Redis(
                host=os.getenv("REDIS_HOST", "localhost"),
                port=int(os.getenv("REDIS_PORT", 6379)),
                decode_responses=True,
                db=0,
                socket_connect_timeout=5
            )
            self.client.ping()
            print("✅ Connected to Redis")
        except Exception as e:
            print(f"⚠️ Redis not available: {e}")
            print("   📁 Running in fallback mode (in-memory only)")
            self.client = None
    
    def ping(self):
        try:
            if self.client:
                return self.client.ping()
            return False
        except:
            return False
    
    # ===== USER METHODS =====
    def save_user(self, user_id: str, data: dict):
        print(f"   💾 Saving user: {user_id}")
        if self.client:
            key = f"user:{user_id}"
            for field, value in data.items():
                if value:
                    self.client.hset(key, field, str(value))
            self.client.expire(key, 86400 * 365)
        else:
            if user_id not in self.fallback_data:
                self.fallback_data[user_id] = {}
            self.fallback_data[user_id].update(data)
            print(f"   📁 User saved to fallback")
        print(f"   ✅ User saved: {user_id}")
    
    def get_user(self, user_id: str):
        print(f"   🔍 Getting user: {user_id}")
        if self.client:
            key = f"user:{user_id}"
            data = self.client.hgetall(key)
            return data if data else None
        else:
            return self.fallback_data.get(user_id)
    
    # ===== USER CONFIG =====
    def save_user_config(self, user_id: str, config: dict):
        print(f"   💾 Saving config for user: {user_id}")
        print(f"   Config: {config}")
        
        if self.client:
            key = f"user:{user_id}:config"
            for field, value in config.items():
                if value:
                    self.client.hset(key, field, str(value))
            saved = self.client.hgetall(key)
            print(f"   ✅ Config saved to Redis: {saved}")
        else:
            if user_id not in self.fallback_data:
                self.fallback_data[user_id] = {}
            self.fallback_data[user_id]['config'] = config
            print(f"   📁 Config saved to fallback: {config}")
            print(f"   📁 Fallback data: {self.fallback_data}")
    
    def get_user_config(self, user_id: str):
        print(f"   🔍 Getting config for user: {user_id}")
        if self.client:
            key = f"user:{user_id}:config"
            data = self.client.hgetall(key)
            print(f"   Config from Redis: {data}")
            return data if data else None
        else:
            data = self.fallback_data.get(user_id, {}).get('config')
            print(f"   📁 Config from fallback: {data}")
            return data
    
    # ===== TELEGRAM =====
    def set_pending_connect(self, user_id: str, ttl: int = 600):
        if self.client:
            self.client.setex(f"pending_connect:{user_id}", ttl, "waiting")
        else:
            self.fallback_data[f"pending_{user_id}"] = "waiting"
    
    def is_pending_connect(self, user_id: str):
        if self.client:
            return bool(self.client.get(f"pending_connect:{user_id}"))
        else:
            return self.fallback_data.get(f"pending_{user_id}") == "waiting"
    
    def bind_telegram(self, user_id: str, chat_id: str):
        if self.client:
            key = f"user:{user_id}"
            self.client.hset(key, "telegram_chat_id", chat_id)
            self.client.hset(key, "telegram_connected_at", datetime.now().isoformat())
            self.client.delete(f"pending_connect:{user_id}")
        else:
            if user_id not in self.fallback_data:
                self.fallback_data[user_id] = {}
            self.fallback_data[user_id]['telegram_chat_id'] = chat_id
    
    def is_telegram_connected(self, user_id: str):
        if self.client:
            key = f"user:{user_id}"
            return bool(self.client.hget(key, "telegram_chat_id"))
        else:
            return bool(self.fallback_data.get(user_id, {}).get('telegram_chat_id'))
    
    def get_telegram_chat_id(self, user_id: str):
        if self.client:
            key = f"user:{user_id}"
            return self.client.hget(key, "telegram_chat_id")
        else:
            return self.fallback_data.get(user_id, {}).get('telegram_chat_id')
    
    # ===== SCHEDULE =====
    def save_schedule(self, user_id: str, schedule: dict):
        data = {
            "schedule": schedule,
            "created_at": datetime.now().isoformat()
        }
        if self.client:
            key = f"schedule:{user_id}"
            self.client.set(key, json.dumps(data))
            self.client.expire(key, 86400 * 7)
        else:
            if user_id not in self.fallback_data:
                self.fallback_data[user_id] = {}
            self.fallback_data[user_id]['schedule'] = data
    
    def get_schedule(self, user_id: str):
        if self.client:
            key = f"schedule:{user_id}"
            data = self.client.get(key)
            if data:
                return json.loads(data)
            return None
        else:
            return self.fallback_data.get(user_id, {}).get('schedule')

# Singleton instance
redis_client = RedisClient()
print(f"📁 Redis client initialized - Mode: {'Redis' if redis_client.client else 'Fallback (in-memory)'}")
