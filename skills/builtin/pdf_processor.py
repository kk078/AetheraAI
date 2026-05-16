"""
Aethera AI - PDF Processor Skill

Read PDFs, extract text, detect form fields, count pages, find tables.
Uses PyPDF2 for structure and pdfplumber (when available) for richer extraction.
"""

import io
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from skills.skill_base import AetheraSkill, SkillResult, skill


@skill(name="pdf_processor", category="data")
class PdfProcessorSkill(AetheraSkill):
    """
    Process PDF files: extract text, get metadata, find form fields,
    extract tables, and split/merge pages.
    """

    @property
    def name(self) -> str:
        return "pdf_processor"

    @property
    def description(self) -> str:
        return (
            "Read and process PDF files: extract text, metadata, form fields, "
            "tables, page count, and split/merge page stubs"
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "extract_text",
                        "page_count",
                        "metadata",
                        "find_form_fields",
                        "extract_tables",
                        "split_pages",
                        "merge_pdfs",
                    ],
                    "description": "Action to perform on the PDF",
                },
                "file_path": {
                    "type": "string",
                    "description": "Path to the PDF file",
                },
                "file_content_b64": {
                    "type": "string",
                    "description": "Base64-encoded PDF content (alternative to file_path)",
                },
                "page_start": {
                    "type": "integer",
                    "description": "Start page (0-indexed) for text extraction or splitting",
                    "default": 0,
                },
                "page_end": {
                    "type": "integer",
                    "description": "End page (exclusive) for text extraction or splitting",
                },
                "pages": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "Specific page indices to extract (0-indexed)",
                },
                "file_paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of PDF file paths for merging",
                },
                "output_dir": {
                    "type": "string",
                    "description": "Directory for split page output files",
                },
            },
            "required": ["action"],
        }

    @property
    def examples(self) -> list:
        return [
            {"input": {"action": "extract_text", "file_path": "report.pdf"}},
            {"input": {"action": "page_count", "file_path": "report.pdf"}},
            {"input": {"action": "find_form_fields", "file_path": "form.pdf"}},
            {"input": {"action": "extract_tables", "file_path": "data.pdf", "page_start": 0, "page_end": 3}},
        ]

    async def execute(self, **kwargs) -> SkillResult:
        action = kwargs.get("action", "")
        if not action:
            return SkillResult(success=False, error="Action is required")

        try:
            if action == "extract_text":
                return self._extract_text(kwargs)
            elif action == "page_count":
                return self._page_count(kwargs)
            elif action == "metadata":
                return self._metadata(kwargs)
            elif action == "find_form_fields":
                return self._find_form_fields(kwargs)
            elif action == "extract_tables":
                return self._extract_tables(kwargs)
            elif action == "split_pages":
                return self._split_pages(kwargs)
            elif action == "merge_pdfs":
                return self._merge_pdfs(kwargs)
            else:
                return SkillResult(success=False, error=f"Unknown action: {action}")
        except Exception as e:
            return SkillResult(success=False, error=f"PDF processing failed: {e}")

    # ------------------------------------------------------------------
    # PDF reader helpers
    # ------------------------------------------------------------------

    def _get_pdf_bytes(self, kwargs: dict) -> bytes:
        """Resolve PDF bytes from file_path or base64 content."""
        import base64

        file_path = kwargs.get("file_path")
        b64 = kwargs.get("file_content_b64")

        if file_path:
            if not os.path.isfile(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")
            with open(file_path, "rb") as f:
                return f.read()
        elif b64:
            return base64.b64decode(b64)
        else:
            raise ValueError("Either file_path or file_content_b64 is required")

    def _open_pypdf2(self, pdf_bytes: bytes):
        """Open PDF with PyPDF2, returning the reader object."""
        try:
            from PyPDF2 import PdfReader
        except ImportError:
            try:
                from pypdf import PdfReader  # type: ignore[no-redef]
            except ImportError:
                raise ImportError("PyPDF2 or pypdf is required for PDF processing")
        return PdfReader(io.BytesIO(pdf_bytes))

    def _page_range(self, kwargs: dict, total_pages: int) -> List[int]:
        """Resolve which pages to process from kwargs."""
        specific_pages = kwargs.get("pages")
        if specific_pages is not None:
            return [p for p in specific_pages if 0 <= p < total_pages]

        start = kwargs.get("page_start", 0)
        end = kwargs.get("page_end", total_pages)
        return list(range(max(0, start), min(end, total_pages)))

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _extract_text(self, kwargs: dict) -> SkillResult:
        """Extract text from PDF pages."""
        pdf_bytes = self._get_pdf_bytes(kwargs)
        reader = self._open_pypdf2(pdf_bytes)
        total_pages = len(reader.pages)
        page_indices = self._page_range(kwargs, total_pages)

        pages_text: List[Dict[str, Any]] = []
        for idx in page_indices:
            page = reader.pages[idx]
            text = page.extract_text() or ""
            pages_text.append({
                "page": idx,
                "text": text,
                "char_count": len(text),
            })

        all_text = "\n\n".join(p["text"] for p in pages_text)

        return SkillResult(
            success=True,
            data={
                "total_pages": total_pages,
                "pages_extracted": len(pages_text),
                "full_text": all_text,
                "pages": pages_text,
                "total_char_count": len(all_text),
            },
        )

    def _page_count(self, kwargs: dict) -> SkillResult:
        """Return the number of pages in the PDF."""
        pdf_bytes = self._get_pdf_bytes(kwargs)
        reader = self._open_pypdf2(pdf_bytes)
        count = len(reader.pages)

        return SkillResult(
            success=True,
            data={
                "page_count": count,
            },
        )

    def _metadata(self, kwargs: dict) -> SkillResult:
        """Extract PDF metadata."""
        pdf_bytes = self._get_pdf_bytes(kwargs)
        reader = self._open_pypdf2(pdf_bytes)
        meta = reader.metadata or {}

        metadata: Dict[str, Any] = {
            "page_count": len(reader.pages),
        }

        # Map standard metadata fields
        field_map = {
            "/Title": "title",
            "/Author": "author",
            "/Subject": "subject",
            "/Creator": "creator",
            "/Producer": "producer",
            "/CreationDate": "creation_date",
            "/ModDate": "modification_date",
            "/Keywords": "keywords",
        }

        for pdf_key, friendly_name in field_map.items():
            value = meta.get(pdf_key)
            if value:
                metadata[friendly_name] = str(value)

        # Collect any additional custom metadata
        extra = {}
        for k, v in meta.items():
            friendly = field_map.get(k)
            if friendly is None:
                extra[k] = str(v)
        if extra:
            metadata["extra"] = extra

        # Check if the PDF is encrypted
        metadata["is_encrypted"] = reader.is_encrypted

        return SkillResult(
            success=True,
            data=metadata,
        )

    def _find_form_fields(self, kwargs: dict) -> SkillResult:
        """Detect and list form fields (AcroForm) in a PDF."""
        pdf_bytes = self._get_pdf_bytes(kwargs)
        reader = self._open_pypdf2(pdf_bytes)

        fields: List[Dict[str, Any]] = []

        # PyPDF2 exposes form fields via get_form_text_fields or get_fields
        try:
            # get_fields returns a dict mapping name -> FieldObject
            raw_fields = reader.get_fields()
        except Exception:
            raw_fields = None

        if raw_fields:
            for name, field_obj in raw_fields.items():
                field_info: Dict[str, Any] = {
                    "name": name,
                }

                # Field type mapping
                if hasattr(field_obj, "field_type"):
                    ft = field_obj.field_type
                    type_map = {
                        "/Btn": "button",
                        "/Tx": "text",
                        "/Ch": "choice",
                        "/Sig": "signature",
                    }
                    field_info["type"] = type_map.get(str(ft), str(ft) if ft else "unknown")

                if hasattr(field_obj, "value") and field_obj.value is not None:
                    field_info["value"] = str(field_obj.value)

                if hasattr(field_obj, "default_value") and field_obj.default_value is not None:
                    field_info["default_value"] = str(field_obj.default_value)

                if hasattr(field_obj, "field_flags"):
                    field_info["flags"] = field_obj.field_flags

                if hasattr(field_obj, "indirect_reference") and field_obj.indirect_reference:
                    field_info["page"] = self._find_field_page(reader, field_obj.indirect_reference)

                fields.append(field_info)

        return SkillResult(
            success=True,
            data={
                "total_fields": len(fields),
                "fields": fields,
                "has_forms": len(fields) > 0,
            },
        )

    @staticmethod
    def _find_field_page(reader, ref) -> Optional[int]:
        """Attempt to find which page a form field lives on."""
        try:
            ref_id = ref.idnum if hasattr(ref, "idnum") else id(ref)
            for i, page in enumerate(reader.pages):
                annots = page.get("/Annots")
                if annots:
                    for annot in annots:
                        annot_obj = annot.get_object() if hasattr(annot, "get_object") else annot
                        if hasattr(annot_obj, "indirect_reference"):
                            annot_ref = annot_obj.indirect_reference
                            if hasattr(annot_ref, "idnum") and annot_ref.idnum == ref_id:
                                return i
            return None
        except Exception:
            return None

    def _extract_tables(self, kwargs: dict) -> SkillResult:
        """Extract tables from PDF pages using pdfplumber if available, else heuristic."""
        pdf_bytes = self._get_pdf_bytes(kwargs)

        # Try pdfplumber first for rich table extraction
        tables = self._extract_tables_pdfplumber(pdf_bytes, kwargs)
        if tables is not None:
            return SkillResult(
                success=True,
                data={
                    "source": "pdfplumber",
                    "total_tables": len(tables),
                    "tables": tables,
                },
            )

        # Fallback: use PyPDF2 text extraction and parse heuristically
        tables = self._extract_tables_heuristic(pdf_bytes, kwargs)
        return SkillResult(
            success=True,
            data={
                "source": "heuristic",
                "total_tables": len(tables),
                "tables": tables,
            },
        )

    def _extract_tables_pdfplumber(self, pdf_bytes: bytes, kwargs: dict) -> Optional[List[Dict]]:
        """Attempt table extraction with pdfplumber."""
        try:
            import pdfplumber  # type: ignore[import-untyped]
        except ImportError:
            return None

        reader = self._open_pypdf2(pdf_bytes)
        total_pages = len(reader.pages)
        page_indices = self._page_range(kwargs, total_pages)

        all_tables: List[Dict[str, Any]] = []

        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for idx in page_indices:
                if idx >= len(pdf.pages):
                    continue
                page = pdf.pages[idx]
                page_tables = page.extract_tables()
                for t_idx, table in enumerate(page_tables):
                    if not table:
                        continue
                    # Clean up None cells
                    cleaned = [
                        [str(cell) if cell is not None else "" for cell in row]
                        for row in table
                    ]
                    headers_row = cleaned[0] if cleaned else []
                    rows = cleaned[1:] if len(cleaned) > 1 else []
                    all_tables.append({
                        "page": idx,
                        "table_index": t_idx,
                        "headers": headers_row,
                        "rows": rows,
                        "row_count": len(rows),
                    })

        return all_tables if all_tables else None

    def _extract_tables_heuristic(self, pdf_bytes: bytes, kwargs: dict) -> List[Dict]:
        """Heuristic table extraction from text: look for repeated delimiter patterns."""
        reader = self._open_pypdf2(pdf_bytes)
        total_pages = len(reader.pages)
        page_indices = self._page_range(kwargs, total_pages)

        all_tables: List[Dict[str, Any]] = []

        for idx in page_indices:
            page = reader.pages[idx]
            text = page.extract_text() or ""
            if not text:
                continue

            lines = text.split("\n")
            # Heuristic: lines with multiple separators (spaces, pipes, tabs) suggest a table
            table_lines: List[List[str]] = []
            separator_threshold = 3  # Minimum column-like splits

            for line in lines:
                # Try pipe-separated
                if "|" in line:
                    cells = [c.strip() for c in line.split("|") if c.strip()]
                    if len(cells) >= separator_threshold:
                        table_lines.append(cells)
                        continue
                # Try tab-separated
                if "\t" in line:
                    cells = [c.strip() for c in line.split("\t") if c.strip()]
                    if len(cells) >= separator_threshold:
                        table_lines.append(cells)
                        continue
                # Try multi-space separated
                import re
                cells = re.split(r"\s{2,}", line.strip())
                if len(cells) >= separator_threshold:
                    table_lines.append(cells)

            if table_lines:
                headers = table_lines[0]
                rows = table_lines[1:]
                all_tables.append({
                    "page": idx,
                    "table_index": len(all_tables),
                    "headers": headers,
                    "rows": rows,
                    "row_count": len(rows),
                })

        return all_tables

    def _split_pages(self, kwargs: dict) -> SkillResult:
        """Split PDF into individual page files."""
        pdf_bytes = self._get_pdf_bytes(kwargs)
        output_dir = kwargs.get("output_dir", os.path.dirname(kwargs.get("file_path", ".")) or ".")

        try:
            from PyPDF2 import PdfReader, PdfWriter
        except ImportError:
            try:
                from pypdf import PdfReader, PdfWriter  # type: ignore[no-redef]
            except ImportError:
                raise ImportError("PyPDF2 or pypdf is required for splitting PDFs")

        reader = PdfReader(io.BytesIO(pdf_bytes))
        total_pages = len(reader.pages)

        page_indices = self._page_range(kwargs, total_pages)
        if not page_indices:
            return SkillResult(success=False, error="No pages selected for splitting")

        base_name = Path(kwargs.get("file_path", "document")).stem
        os.makedirs(output_dir, exist_ok=True)

        output_files: List[str] = []
        for idx in page_indices:
            writer = PdfWriter()
            writer.add_page(reader.pages[idx])
            out_path = os.path.join(output_dir, f"{base_name}_page_{idx + 1}.pdf")
            with open(out_path, "wb") as f:
                writer.write(f)
            output_files.append(out_path)

        return SkillResult(
            success=True,
            data={
                "total_pages": total_pages,
                "pages_split": len(output_files),
                "output_files": output_files,
                "output_dir": output_dir,
            },
        )

    def _merge_pdfs(self, kwargs: dict) -> SkillResult:
        """Merge multiple PDF files into one."""
        file_paths = kwargs.get("file_paths", [])
        if len(file_paths) < 2:
            return SkillResult(success=False, error="At least two file_paths are required for merging")

        try:
            from PyPDF2 import PdfReader, PdfWriter
        except ImportError:
            try:
                from pypdf import PdfReader, PdfWriter  # type: ignore[no-redef]
            except ImportError:
                raise ImportError("PyPDF2 or pypdf is required for merging PDFs")

        writer = PdfWriter()
        source_info: List[Dict[str, Any]] = []

        for path in file_paths:
            if not os.path.isfile(path):
                return SkillResult(success=False, error=f"File not found: {path}")
            reader = PdfReader(path)
            page_count = len(reader.pages)
            for page in reader.pages:
                writer.add_page(page)
            source_info.append({
                "file": path,
                "pages": page_count,
            })

        # Write merged output next to first file
        output_dir = os.path.dirname(file_paths[0]) or "."
        base_name = Path(file_paths[0]).stem
        output_path = os.path.join(output_dir, f"{base_name}_merged.pdf")

        with open(output_path, "wb") as f:
            writer.write(f)

        total_pages = sum(s["pages"] for s in source_info)

        return SkillResult(
            success=True,
            data={
                "output_file": output_path,
                "total_pages": total_pages,
                "source_files": source_info,
            },
        )