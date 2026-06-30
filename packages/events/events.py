import redis
import json
import asyncio
from typing import Callable, Dict, List

class EventBus:
    def __init__(self):
        self.redis_client = None
        self.pubsub = None
        self.listeners: Dict[str, List[Callable]] = {}
        try:
            self.redis_client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)
            self.redis_client.ping()
            print("[EventBus] Connected to Redis Pub/Sub successfully.")
        except Exception as e:
            print(f"[EventBus] Redis not available: {e}. Falling back to in-memory event bus.")
            self.redis_client = None

    async def publish(self, topic: str, data: dict):
        print(f"[EventBus] Publishing to {topic}: {data}")
        if self.redis_client:
            try:
                self.redis_client.publish(topic, json.dumps(data))
                # Also trigger local in-memory listeners if any
                await self._trigger_local(topic, data)
                return
            except Exception as e:
                print(f"[EventBus] Redis publish failed: {e}")
        
        await self._trigger_local(topic, data)

    async def _trigger_local(self, topic: str, data: dict):
        if topic in self.listeners:
            for listener in self.listeners[topic]:
                try:
                    if asyncio.iscoroutinefunction(listener):
                        asyncio.create_task(listener(data))
                    else:
                        listener(data)
                except Exception as e:
                    print(f"[EventBus] Error executing local listener for {topic}: {e}")

    def subscribe(self, topic: str, handler: Callable):
        if topic not in self.listeners:
            self.listeners[topic] = []
        self.listeners[topic].append(handler)
        print(f"[EventBus] Subscribed to {topic}")

    async def start_listening(self):
        if not self.redis_client:
            print("[EventBus] Not listening on Redis (using in-memory fallback).")
            return
        
        try:
            self.pubsub = self.redis_client.pubsub(ignore_subscribe_messages=True)
            for topic in self.listeners.keys():
                self.pubsub.subscribe(topic)
            
            print(f"[EventBus] Active Redis subscription loop started for topics: {list(self.listeners.keys())}")
            
            while True:
                # Retrieve messages periodically without blocking
                msg = self.pubsub.get_message(timeout=0.2)
                if msg and msg['type'] == 'message':
                    topic = msg['channel']
                    try:
                        data = json.loads(msg['data'])
                        # Execute subscribers
                        if topic in self.listeners:
                            for handler in self.listeners[topic]:
                                if asyncio.iscoroutinefunction(handler):
                                    asyncio.create_task(handler(data))
                                else:
                                    handler(data)
                    except Exception as e:
                        print(f"[EventBus] Error handling message on {topic}: {e}")
                await asyncio.sleep(0.05)
        except Exception as e:
            print(f"[EventBus] Exception in Redis listener loop: {e}")

event_bus = EventBus()
