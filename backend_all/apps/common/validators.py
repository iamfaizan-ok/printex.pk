import io
import re
from typing import List, Tuple
from pypdf import PdfReader
from pypdf.errors import PdfReadError, FileNotDecryptedError
from rest_framework.exceptions import ValidationError

ALLOWED_PAPER_SIZES = ['A4', 'A3', 'Letter', 'Legal']
ALLOWED_COLOUR_MODES = ['colour', 'bw']
ALLOWED_ORIENTATIONS = ['portrait', 'landscape']
ALLOWED_SIDES = ['single', 'double']
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB
MAX_COPIES_PER_DOCUMENT = 100
MIN_COPIES_PER_DOCUMENT = 1


def validate_pdf_file(file_obj) -> Tuple[int, bytes]:
    """
    Validates uploaded file:
    - Size check
    - PDF magic bytes check (%PDF-)
    - pypdf parsing check (detect malformed or password-protected PDFs)
    Returns: (page_count, file_content_bytes)
    """
    file_bytes = file_obj.read()
    file_size = len(file_bytes)

    if file_size == 0:
        raise ValidationError({"file": "The uploaded file is empty."})

    if file_size > MAX_FILE_SIZE_BYTES:
        raise ValidationError({
            "file": f"File size exceeds maximum allowed limit of {MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB."
        })

    # Validate PDF signature magic bytes (%PDF-)
    if not file_bytes.startswith(b'%PDF-'):
        raise ValidationError({
            "file": "Invalid file format. The uploaded document is not a valid PDF file."
        })

    # Safe PDF parsing with pypdf
    try:
        stream = io.BytesIO(file_bytes)
        reader = PdfReader(stream, strict=False)

        if reader.is_encrypted:
            # Check if decryptable with empty password
            try:
                decrypted = reader.decrypt('')
                if decrypted == 0:
                    raise ValidationError({
                        "file": "Password-protected PDFs cannot be printed. Please remove the password and try again."
                    })
            except Exception:
                raise ValidationError({
                    "file": "Password-protected PDFs cannot be printed. Please remove the password and try again."
                })

        page_count = len(reader.pages)
        if page_count < 1:
            raise ValidationError({"file": "The PDF does not contain any printable pages."})

        return page_count, file_bytes

    except (PdfReadError, FileNotDecryptedError) as e:
        raise ValidationError({"file": f"Corrupt or unreadable PDF: {str(e)}"})
    except Exception as e:
        if isinstance(e, ValidationError):
            raise e
        raise ValidationError({"file": f"Unable to parse PDF document: {str(e)}"})


def parse_page_range(page_range_str: str, total_pages: int) -> List[int]:
    """
    Parses and validates page range string (e.g. 'all', '1-5', '1, 3, 5-7').
    Returns a sorted list of unique 1-indexed page numbers.
    """
    cleaned = (page_range_str or 'all').strip().lower()

    if cleaned == 'all' or cleaned == '':
        return list(range(1, total_pages + 1))

    # Allow only digits, hyphens, commas, and spaces
    if not re.match(r'^[0-9\s,\-]+$', cleaned):
        raise ValidationError({
            "page_range": "Invalid page range format. Use formats like 'all', '1-5', or '1, 3, 5-8'."
        })

    selected_pages = set()
    parts = cleaned.split(',')

    for part in parts:
        part = part.strip()
        if not part:
            continue

        if '-' in part:
            bounds = part.split('-')
            if len(bounds) != 2:
                raise ValidationError({"page_range": f"Invalid range expression: '{part}'."})
            try:
                start, end = int(bounds[0].strip()), int(bounds[1].strip())
            except ValueError:
                raise ValidationError({"page_range": f"Invalid page numbers in range: '{part}'."})

            if start > end:
                raise ValidationError({"page_range": f"Range start ({start}) cannot be greater than end ({end})."})
            if start < 1 or end > total_pages:
                raise ValidationError({
                    "page_range": f"Range {start}-{end} exceeds document page bounds (1 to {total_pages})."
                })

            for p in range(start, end + 1):
                selected_pages.add(p)
        else:
            try:
                page_num = int(part)
            except ValueError:
                raise ValidationError({"page_range": f"Invalid page number: '{part}'."})

            if page_num < 1 or page_num > total_pages:
                raise ValidationError({
                    "page_range": f"Page {page_num} exceeds document page bounds (1 to {total_pages})."
                })

            selected_pages.add(page_num)

    if not selected_pages:
        raise ValidationError({"page_range": "No pages selected in specified range."})

    return sorted(list(selected_pages))


def validate_print_settings(data: dict, total_pages: int = 1) -> dict:
    """
    Validates print settings dictionary.
    """
    paper_size = data.get('paper_size', 'A4')
    if paper_size not in ALLOWED_PAPER_SIZES:
        raise ValidationError({"paper_size": f"Invalid paper size. Must be one of: {ALLOWED_PAPER_SIZES}."})

    colour_mode = data.get('colour_mode', 'bw')
    if colour_mode not in ALLOWED_COLOUR_MODES:
        raise ValidationError({"colour_mode": f"Invalid colour mode. Must be one of: {ALLOWED_COLOUR_MODES}."})

    orientation = data.get('orientation', 'portrait')
    if orientation not in ALLOWED_ORIENTATIONS:
        raise ValidationError({"orientation": f"Invalid orientation. Must be one of: {ALLOWED_ORIENTATIONS}."})

    sides = data.get('sides', 'single')
    if sides not in ALLOWED_SIDES:
        raise ValidationError({"sides": f"Invalid sides selection. Must be one of: {ALLOWED_SIDES}."})

    copies = data.get('copies', 1)
    try:
        copies = int(copies)
    except (ValueError, TypeError):
        raise ValidationError({"copies": "Copies count must be an integer."})

    if copies < MIN_COPIES_PER_DOCUMENT or copies > MAX_COPIES_PER_DOCUMENT:
        raise ValidationError({
            "copies": f"Copies must be between {MIN_COPIES_PER_DOCUMENT} and {MAX_COPIES_PER_DOCUMENT}."
        })

    page_range = data.get('page_range', 'all')
    selected_pages = parse_page_range(page_range, total_pages)

    return {
        "paper_size": paper_size,
        "colour_mode": colour_mode,
        "orientation": orientation,
        "sides": sides,
        "copies": copies,
        "page_range": page_range,
        "selected_pages_count": len(selected_pages),
    }
