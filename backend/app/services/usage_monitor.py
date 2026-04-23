from datetime import datetime, timedelta
from typing import Dict, List
import logging
from backend.app.db.db_client import DBClient

class UsageMonitor:
    """
    SaaS Usage Monitoring & Alerting.
    Triggers alerts when users approach their tier limits.
    """
    def __init__(self, alert_threshold=0.8):
        self.alert_threshold = alert_threshold
        self.db = DBClient()

    async def check_all_users(self):
        """Audits all users and sends alerts if needed."""
        # Simulated logic: in reality, fetch users and their limits
        print(f"--- Usage Audit [{datetime.now()}] ---")
        
        users_to_check = [
            {"user_id": "user123", "limit": 1000, "used": 850},
            {"user_id": "user456", "limit": 5000, "used": 1200}
        ]
        
        for user in users_to_check:
            usage_ratio = user["used"] / user["limit"]
            if usage_ratio >= self.alert_threshold:
                print(f"🚨 ALERT: User {user['user_id']} at {usage_ratio:.1%} usage!")
                await self.send_usage_alert(user['user_id'], user['used'], user['limit'])

    async def send_usage_alert(self, user_id, used, limit):
        """Sends an email/slack alert to the user."""
        # Placeholder for notification service
        print(f"Notification sent to {user_id}: 'You have used {used}/{limit} of your monthly recognitions.'")

if __name__ == "__main__":
    import asyncio
    monitor = UsageMonitor()
    asyncio.run(monitor.check_all_users())
