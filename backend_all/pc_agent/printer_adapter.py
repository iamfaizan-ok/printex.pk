import os
import subprocess
import logging
from typing import List, Tuple
from pathlib import Path

logger = logging.getLogger("PrintXAgent.PrinterAdapter")


class WindowsPrinterAdapter:
    """
    Submits PDF print jobs safely to the local Windows operating system print spooler.
    Enforces strict printer allowlist verification.
    """

    def __init__(self, allowed_printers: List[str], default_printer: str, mode: str = 'windows_native'):
        self.allowed_printers = [p.lower() for p in allowed_printers]
        self.default_printer = default_printer
        self.mode = mode

    def get_installed_printers(self) -> List[str]:
        """
        Lists installed Windows printers using PowerShell or WMI.
        """
        if self.mode == 'mock' or os.name != 'nt':
            return ["Microsoft Print to PDF", "HP LaserJet Pro M404n"]

        try:
            cmd = ["powershell.exe", "-NoProfile", "-Command", "Get-Printer | Select-Object -ExpandProperty Name"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                printers = [line.strip() for line in result.stdout.splitlines() if line.strip()]
                return printers
        except Exception as e:
            logger.warning(f"Unable to query Windows printers via PowerShell: {e}")

        return [self.default_printer]

    def validate_printer(self, target_printer: str) -> str:
        """
        Validates target printer against explicit allowlist.
        Never silently falls back to an arbitrary default printer!
        """
        candidate = (target_printer or self.default_printer).strip()
        if candidate.lower() not in self.allowed_printers:
            raise ValueError(
                f"Unauthorized printer '{candidate}'. Must be one of allowlisted printers: {self.allowed_printers}"
            )
        return candidate

    def print_pdf(self, pdf_path: Path, printer_name: str, copies: int = 1) -> Tuple[bool, str]:
        """
        Submits PDF to physical Windows printer.
        Returns (success: bool, diagnostic_message: str)
        """
        clean_printer = self.validate_printer(printer_name)

        if not pdf_path.exists():
            return False, f"PDF file does not exist at path: {pdf_path}"

        if self.mode == 'mock':
            logger.info(f"[MOCK] Simulated successful print of {pdf_path.name} to '{clean_printer}' ({copies} copies).")
            return True, f"Mock print job spooled successfully to {clean_printer}."

        # Windows Native Printing via win32print (Silent in-process spooler, no GUI windows)
        try:
            logger.info(f"Submitting {pdf_path.name} silently to Windows Spooler on '{clean_printer}' ({copies} copies)...")
            import win32print

            with open(pdf_path, 'rb') as f:
                pdf_bytes = f.read()

            handle = win32print.OpenPrinter(clean_printer)
            last_job_id = None
            try:
                for i in range(1, int(copies) + 1):
                    doc_title = f"{pdf_path.name} (Copy {i})" if copies > 1 else pdf_path.name
                    job_id = win32print.StartDocPrinter(handle, 1, (doc_title, None, "RAW"))
                    last_job_id = job_id
                    try:
                        win32print.StartPagePrinter(handle)
                        win32print.WritePrinter(handle, pdf_bytes)
                        win32print.EndPagePrinter(handle)
                    finally:
                        win32print.EndDocPrinter(handle)
            finally:
                win32print.ClosePrinter(handle)

            return True, f"Job successfully accepted silently by Windows Spooler for '{clean_printer}' (Job ID: {last_job_id})."

        except Exception as e:
            return False, f"Printer submission error: {str(e)}"
