import logging
from typing import Optional, Dict, Any, List
from pathlib import Path
import requests

logger = logging.getLogger("PrintXAgent.Client")


class AgentApiClient:
    """
    Handles authenticated outbound HTTPS communication with the Django backend.
    """

    def __init__(self, base_url: str, station_code: str, agent_secret: str, agent_version: str = "1.0.0"):
        self.base_url = base_url.rstrip('/')
        self.station_code = station_code
        self.agent_secret = agent_secret
        self.agent_version = agent_version
        self.session = requests.Session()
        self.session.headers.update({
            "X-Station-Code": self.station_code,
            "X-Agent-Secret": self.agent_secret,
            "X-Agent-Version": self.agent_version,
            "Accept": "application/json",
        })

    def send_heartbeat(self, local_printers: List[str]) -> bool:
        url = f"{self.base_url}/agent/heartbeat/"
        try:
            resp = self.session.post(
                url,
                json={"agent_version": self.agent_version, "local_printers": local_printers},
                timeout=10
            )
            return resp.status_code == 200
        except Exception as e:
            logger.warning(f"Heartbeat failed: {e}")
            return False

    def claim_job(self) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}/agent/claim-job/"
        try:
            resp = self.session.post(url, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                return data.get('job')
            elif resp.status_code == 204:
                return None  # Queue empty
            else:
                logger.warning(f"Claim job returned HTTP {resp.status_code}: {resp.text}")
                return None
        except Exception as e:
            logger.error(f"Error querying claim-job: {e}")
            return None

    def download_pdf(self, download_url: str, destination_path: Path) -> bool:
        """
        Streams PDF file into local destination path.
        """
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        # Ensure full URL if relative returned
        if not download_url.startswith('http'):
            download_url = f"{self.base_url.split('/api')[0]}{download_url}"

        try:
            with self.session.get(download_url, stream=True, timeout=60) as resp:
                resp.raise_for_status()
                with open(destination_path, 'wb') as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        f.write(chunk)
            return True
        except Exception as e:
            logger.error(f"Failed to download PDF from {download_url}: {e}")
            return False

    def update_job_status(
        self,
        job_id: str,
        status: str,
        error_code: str = '',
        error_message: str = '',
        diagnostic_details: str = ''
    ) -> bool:
        url = f"{self.base_url}/agent/jobs/{job_id}/status/"
        payload = {
            "status": status,
            "error_code": error_code,
            "error_message": error_message,
            "diagnostic_details": diagnostic_details,
        }
        try:
            resp = self.session.post(url, json=payload, timeout=15)
            return resp.status_code == 200
        except Exception as e:
            logger.error(f"Failed to update status for job {job_id} to '{status}': {e}")
            return False
