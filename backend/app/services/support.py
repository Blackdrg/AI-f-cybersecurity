import tarfile
import os
import json
import io
from datetime import datetime

class SupportToolkit:
    """
    Generates diagnostic debug bundles for enterprise support.
    """
    def __init__(self, logs_dir: str = "logs"):
        self.logs_dir = logs_dir

    def generate_debug_bundle(self) -> io.BytesIO:
        """
        Creates a .tar.gz bundle containing logs, system info, and config (sanitized).
        """
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tar:
            # 1. System Info
            sys_info = {
                "timestamp": datetime.utcnow().isoformat(),
                "os": os.name,
                "cpu_count": os.cpu_count(),
                "version": "2.0.0"
            }
            info_data = json.dumps(sys_info, indent=2).encode()
            info_file = tarfile.TarInfo(name="debug/system_info.json")
            info_file.size = len(info_data)
            tar.addfile(info_file, io.BytesIO(info_data))
            
            # 2. Logs (if directory exists)
            if os.path.exists(self.logs_dir):
                for root, dirs, files in os.walk(self.logs_dir):
                    for file in files:
                        if file.endswith(".log"):
                            tar.add(os.path.join(root, file), arcname=f"debug/logs/{file}")
            
            # 3. Health Check result
            # (In a real app, you'd call your internal health check)
            
        buf.seek(0)
        return buf

support_toolkit = SupportToolkit()
