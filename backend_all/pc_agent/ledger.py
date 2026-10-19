import sqlite3
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

logger = logging.getLogger("PrintXAgent.Ledger")


class AgentLedger:
    """
    Local persistent SQLite ledger:
    Prevents duplicate prints and enables safe crash-recovery across PC reboots.
    """

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        conn = self._get_connection()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS job_ledger (
                    job_id TEXT PRIMARY KEY,
                    job_number TEXT NOT NULL,
                    local_pdf_path TEXT,
                    target_printer TEXT,
                    copies INTEGER DEFAULT 1,
                    paper_size TEXT,
                    colour_mode TEXT,
                    local_status TEXT NOT NULL,
                    claimed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    submitted_to_spooler_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    last_error TEXT
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def record_claim(self, job_data: Dict[str, Any], local_pdf_path: str = ""):
        conn = self._get_connection()
        try:
            conn.execute("""
                INSERT OR REPLACE INTO job_ledger (
                    job_id, job_number, local_pdf_path, target_printer,
                    copies, paper_size, colour_mode, local_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job_data['id'],
                job_data['job_number'],
                local_pdf_path,
                job_data.get('target_printer', ''),
                job_data.get('copies', 1),
                job_data.get('paper_size', 'A4'),
                job_data.get('colour_mode', 'bw'),
                'claimed'
            ))
            conn.commit()
        finally:
            conn.close()

    def update_status(self, job_id: str, status: str, local_pdf_path: str = None, error: str = None):
        conn = self._get_connection()
        try:
            updates = ["local_status = ?"]
            params = [status]

            if local_pdf_path:
                updates.append("local_pdf_path = ?")
                params.append(local_pdf_path)
            if error:
                updates.append("last_error = ?")
                params.append(error)
            if status == 'submitted_to_printer':
                updates.append("submitted_to_spooler_at = CURRENT_TIMESTAMP")
            elif status == 'completed':
                updates.append("completed_at = CURRENT_TIMESTAMP")

            params.append(job_id)
            query = f"UPDATE job_ledger SET {', '.join(updates)} WHERE job_id = ?"
            conn.execute(query, params)
            conn.commit()
        finally:
            conn.close()

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        try:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM job_ledger WHERE job_id = ?", (job_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_unresolved_jobs(self) -> List[Dict[str, Any]]:
        """
        Retrieves jobs that were claimed or downloading or submitting when a crash occurred.
        """
        conn = self._get_connection()
        try:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM job_ledger 
                WHERE local_status IN ('claimed', 'downloading', 'ready_to_print', 'submitting_to_printer', 'submitted_to_printer')
            """)
            return [dict(r) for r in cursor.fetchall()]
        finally:
            conn.close()

