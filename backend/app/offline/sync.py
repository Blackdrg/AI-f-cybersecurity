import aiosqlite
import json
import os
import asyncio
from pathlib import Path
from typing import List, Dict, Any
import sqlite3
from datetime import datetime
import numpy as np
from ..db.db_client import DBClient
import logging
logger = logging.getLogger(__name__)

class OfflineSync:
    def __init__(self, cache_dir: str = "./offline_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.local_db = None
        self.online_db = None
        self.sync_lock = asyncio.Lock()
        self.pending_sync = []
    
    async def init_local_db(self):
        self.local_db_path = self.cache_dir / "local_face.db"
        self.local_db = await aiosqlite.connect(self.local_db_path)
        await self.local_db.execute("""
            CREATE TABLE IF NOT EXISTS local_embeddings (
                embedding_id TEXT PRIMARY KEY,
                person_id TEXT,
                embedding TEXT,  -- JSON serialized
                camera_id TEXT,
                created_at TEXT
            )
        """)
        await self.local_db.execute("""
            CREATE TABLE IF NOT EXISTS local_events (
                event_id TEXT PRIMARY KEY,
                org_id TEXT,
                person_id TEXT,
                camera_id TEXT,
                confidence REAL,
                metadata TEXT,
                timestamp TEXT
            )
        """)
        await self.local_db.commit()
    
    async def cache_embedding(self, embedding_id: str, person_id: str, embedding: np.ndarray, camera_id: str = None):
        """Cache embedding locally."""
        emb_json = embedding.tolist()  # JSON serializable
        await self.local_db.execute("""
            INSERT OR REPLACE INTO local_embeddings (embedding_id, person_id, embedding, camera_id, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (embedding_id, person_id, json.dumps(emb_json), camera_id, datetime.now().isoformat()))
        await self.local_db.commit()
        self.pending_sync.append(('enroll', embedding_id))
    
    async def cache_event(self, event_data: Dict[str, Any]):
        """Cache recognition event."""
        await self.local_db.execute("""
            INSERT INTO local_events (event_id, org_id, person_id, camera_id, confidence, metadata, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            event_data['event_id'],
            event_data['org_id'],
            event_data.get('person_id'),
            event_data['camera_id'],
            event_data['confidence'],
            json.dumps(event_data.get('metadata', {})),
            datetime.now().isoformat()
        ))
        await self.local_db.commit()
        self.pending_sync.append(('event', event_data['event_id']))
    
    async def sync_to_cloud(self, online_db: DBClient):
        """Sync pending data when online."""
        async with self.sync_lock:
            if not self.pending_sync:
                return
            
            logger.info(f"Syncing {len(self.pending_sync)} items")
            
            # Sync embeddings
            embeddings = await self.local_db.execute_fetchall("SELECT * FROM local_embeddings WHERE embedding_id IN (SELECT embedding_id FROM pending WHERE type='enroll')")
            for row in embeddings:
                emb_array = np.array(json.loads(row[2]))
                await online_db.enroll_person(  # Stub - match signature
                    row[1], '', [emb_array], {}, row[3])
            
            # Sync events
            events = await self.local_db.execute_fetchall("SELECT * FROM local_events WHERE event_id IN (SELECT event_id FROM pending WHERE type='event')")
            for row in events:
                await online_db.log_recognition_event(
                    row[1], row[2], row[3], row[4], json.loads(row[5]))
            
            # Clear pending
            self.pending_sync.clear()
            logger.info("Offline sync complete")
    
    async def recognize_local(self, query_embedding: np.ndarray, top_k: int = 1, threshold: float = 0.6) -> List[Dict]:
        """Recognize from local cache."""
        rows = await self.local_db.execute_fetchall("SELECT * FROM local_embeddings ORDER BY created_at DESC LIMIT ?", (top_k * 10,))
        matches = []
        for row in rows:
            emb_array = np.array(json.loads(row[2]))
            distance = 1 - np.dot(query_embedding, emb_array) / (np.linalg.norm(query_embedding) * np.linalg.norm(emb_array))
            if distance <= threshold:
                matches.append({
                    'person_id': row[1],
                    'distance': distance,
                    'camera_id': row[3]
                })
        return matches[:top_k]
    
    async def is_online(self) -> bool:
        """Check online status."""
        try:
            if self.online_db and self.online_db.pool:
                return True
        except:
            pass
        return False
    
    async def periodic_sync(self, interval: int = 60):
        """Background sync task."""
        while True:
            try:
                if self.is_online():
                    await self.sync_to_cloud(self.online_db)
                await asyncio.sleep(interval)
            except Exception as e:
                logger.error(f"Sync error: {e}")
                await asyncio.sleep(30)

# Global instance
offline_sync = OfflineSync()

async def get_offline_sync():
    if offline_sync.local_db is None:
        await offline_sync.init_local_db()
    return offline_sync

