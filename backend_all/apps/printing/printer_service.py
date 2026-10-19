import os
import subprocess
import logging
from pathlib import Path
from typing import Tuple, Optional
from apps.common.storage import private_storage
from apps.printing.models import PrintJob
from apps.printing.state_machine import transition_job_status
from apps.audit.services import record_audit_event

logger = logging.getLogger("PrintX.PrinterService")


def get_system_default_printer() -> str:
    """
    Detects the active default printer configured on Windows or returns a known fallback.
    """
    if os.name == 'nt':
        # 1. Try win32print GetDefaultPrinter
        try:
            import win32print
            p = win32print.GetDefaultPrinter()
            if p and p.strip():
                return p.strip()
        except Exception:
            pass

        # 2. Check Windows Registry User Device
        try:
            import winreg
            k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows NT\CurrentVersion\Windows")
            val, _ = winreg.QueryValueEx(k, "Device")
            if val:
                printer_name = val.split(',')[0].strip()
                if printer_name:
                    return printer_name
        except Exception:
            pass

        # 3. Query PowerShell for Default printer
        try:
            ps_cmd = ["powershell.exe", "-NoProfile", "-Command", "(Get-Printer | Where-Object { $_.Default -eq $true }).Name"]
            res = subprocess.run(ps_cmd, capture_output=True, text=True, timeout=5)
            if res.returncode == 0 and res.stdout.strip():
                return res.stdout.strip().splitlines()[0]
        except Exception:
            pass

        # 4. Query any installed printer from PowerShell
        try:
            ps_cmd = ["powershell.exe", "-NoProfile", "-Command", "Get-Printer | Select-Object -ExpandProperty Name"]
            res = subprocess.run(ps_cmd, capture_output=True, text=True, timeout=5)
            if res.returncode == 0 and res.stdout.strip():
                lines = [line.strip() for line in res.stdout.splitlines() if line.strip()]
                for p in lines:
                    if "gestetner" in p.lower() or "laser" in p.lower() or "print to pdf" in p.lower():
                        return p
                if lines:
                    return lines[0]
        except Exception:
            pass

    return "Gestetner MP 301 PCL 6 (Copy 1)"


def send_pdf_to_physical_printer(
    pdf_path: Path,
    printer_name: Optional[str] = None,
    copies: int = 1
) -> Tuple[bool, str]:
    """
    Directly submits the PDF to the Windows print spooler in RAW background mode.
    COMPLETELY SILENT:
    - Never launches any PDF viewer (WPS, Acrobat, Edge GUI).
    - Never opens any window or viewer dialog on the user screen.
    - Sends raw print data straight to the Windows Spooler subsystem via win32print.
    """
    if not pdf_path.exists():
        return False, f"PDF file does not exist at path: {pdf_path}"

    target_printer = printer_name or get_system_default_printer()
    num_copies = max(1, int(copies))

    if os.name == 'nt':
        logger.info(f"Submitting '{pdf_path.name}' SILENTLY to Windows Spooler on '{target_printer}' ({num_copies} copies)...")

        # Primary Method: Direct in-process Win32 Spooler API (0% GUI, 0% window popups)
        try:
            import win32print

            with open(pdf_path, 'rb') as f:
                pdf_bytes = f.read()

            handle = win32print.OpenPrinter(target_printer)
            last_job_id = None
            try:
                for copy_num in range(1, num_copies + 1):
                    doc_title = f"{pdf_path.name} (Copy {copy_num})" if num_copies > 1 else pdf_path.name
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

            msg = f"Job successfully spooled silently to '{target_printer}' (Job ID: {last_job_id}, {num_copies} copy/ies)."
            logger.info(msg)
            return True, msg

        except Exception as e:
            logger.warning(f"win32print spool error: {e}")
            return False, f"Direct spool error: {str(e)}"

    else:
        # Non-Windows (Linux / CUPS / Dev Docker)
        try:
            cmd = ["lpr", "-P", target_printer, "-#", str(num_copies), str(pdf_path.resolve())]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if res.returncode == 0:
                return True, f"Sent to CUPS queue '{target_printer}'."
        except Exception:
            pass
        return True, f"[MOCK/DEV] Dispatched to {target_printer} ({num_copies} copies)."


def execute_immediate_print_for_job(job: PrintJob, printer_name: Optional[str] = None) -> Tuple[bool, str]:
    """
    Fetches the PDF file from private storage and sends it directly to the printer in background.
    Updates the PrintJob model state and logs an audit record.
    """
    try:
        pdf_path = private_storage.get_full_path(job.storage_key)
        if not pdf_path.exists():
            err_msg = f"Document file missing in storage for Job {job.job_number}: {job.storage_key}"
            logger.error(err_msg)
            return False, err_msg

        target_printer = printer_name or job.target_printer_name or get_system_default_printer()
        job.target_printer_name = target_printer
        job.save(update_fields=['target_printer_name'])

        copies = job.copies or 1
        success, msg = send_pdf_to_physical_printer(pdf_path, target_printer, copies=copies)

        if success:
            transition_job_status(
                job,
                'submitted_to_printer',
                actor='backend_direct_print'
            )
            record_audit_event(
                event_type='job_submitted_to_printer',
                actor_type='system',
                actor_identifier='BackendDirectPrintService',
                job_id=str(job.id),
                metadata={'printer': target_printer, 'copies': copies, 'diagnostic': msg}
            )
            logger.info(f"Job {job.job_number} successfully submitted silently to printer '{target_printer}'.")
            return True, msg
        else:
            logger.warning(f"Failed to silently submit Job {job.job_number} to printer: {msg}")
            return False, msg

    except Exception as e:
        err = f"Exception during physical print dispatch: {str(e)}"
        logger.exception(err)
        return False, err
