# Type stubs for celery.schedules
# Minimal definitions needed for this project

from typing import Any

class crontab:
    def __init__(
        self,
        minute: str = "*",
        hour: str = "*",
        day_of_month: str = "*",
        month_of_year: str = "*",
        day_of_week: str = "*",
    ) -> None: ...
    
    @property
    def schedule(self) -> Any: ...
    
    def remaining_estimate(self, last_run_at: Any) -> float: ...

# Base schedule type
class schedule:
    def __init__(self, run_every: Any, relative: bool = False) -> None: ...
    def remaining_estimate(self, last_run_at: Any) -> float: ...
