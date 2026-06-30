import redis
import json
from typing import Optional, List, Dict

class RuleCache:
    def __init__(self):
        self.redis_client = None
        try:
            self.redis_client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)
            self.redis_client.ping()
            print("[RuleCache] Connected to Redis successfully.")
        except Exception as e:
            print(f"[RuleCache] Redis not available: {e}. Falling back to in-memory cache.")
            self.redis_client = None
        
        self._memory_cache: Dict[str, Dict] = {}

    def get(self, org_id: str) -> Optional[Dict]:
        if self.redis_client:
            try:
                data = self.redis_client.get(f"rules:{org_id}")
                if data:
                    return json.loads(data)
            except Exception as e:
                print(f"[RuleCache] Redis get failed: {e}")
        
        return self._memory_cache.get(org_id)

    def set(self, org_id: str, version: int, rules: List[Dict]):
        payload = {
            "version": version,
            "rules": rules
        }
        if self.redis_client:
            try:
                # Cache for 1 day
                self.redis_client.setex(f"rules:{org_id}", 86400, json.dumps(payload))
                return
            except Exception as e:
                print(f"[RuleCache] Redis set failed: {e}")
        
        self._memory_cache[org_id] = payload

    def invalidate(self, org_id: str):
        if self.redis_client:
            try:
                self.redis_client.delete(f"rules:{org_id}")
            except Exception as e:
                print(f"[RuleCache] Redis delete failed: {e}")
        
        if org_id in self._memory_cache:
            del self._memory_cache[org_id]

    def get_mapping(self, org_id: str, entity_hash: str) -> Optional[str]:
        if self.redis_client:
            try:
                return self.redis_client.get(f"org_map:{org_id}:{entity_hash}")
            except Exception:
                pass
        return self._memory_cache.get(f"org_map:{org_id}:{entity_hash}")

    def set_mapping(self, org_id: str, entity_hash: str, replacement: str):
        if self.redis_client:
            try:
                self.redis_client.set(f"org_map:{org_id}:{entity_hash}", replacement)
                return
            except Exception:
                pass
        self._memory_cache[f"org_map:{org_id}:{entity_hash}"] = replacement

rule_cache = RuleCache()
