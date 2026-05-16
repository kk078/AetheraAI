"""
Aethera AI — Stage 2: Content Extractor

Extracts text, tables, and images from documents by delegating to
existing skills and type-specific extractors.
"""
import json
import logging
from typing import Dict, Any

from .stages import PipelineStage
from .context import PipelineContext
from .extractors.url_scraper import scrape_url
from .extractors.office_docs import extract_docx, extract_pptx, extract_xlsx
from .extractors.email_parser import extract_eml, extract_msg

logger = logging.getLogger("aethera.pipeline.extractor")


class ContentExtractor(PipelineStage):
    """Stage 2: Extract text, tables, and metadata from documents."""

    name = "extractor"

    @property
    def required_content(self) -> bool:
        return False

    async def execute(self, context: PipelineContext) -> PipelineContext:
        file_type = context.file_type

        if file_type == "url":
            result = await scrape_url(context.url)
            if result.get("success"):
                context.raw_text = result["text"]
                context.metadata = result.get("metadata", {})
                if result.get("title"):
                    context.metadata["title"] = result["title"]

        elif file_type == "pdf":
            await self._extract_pdf(context)

        elif file_type == "docx":
            self._extract_docx(context)

        elif file_type == "xlsx":
            self._extract_xlsx(context)

        elif file_type == "csv":
            await self._extract_csv(context)

        elif file_type == "pptx":
            self._extract_pptx(context)

        elif file_type == "image":
            await self._extract_image(context)

        elif file_type in ("txt", "unknown"):
            self._extract_text(context)

        elif file_type == "html":
            self._extract_html(context)

        elif file_type in ("json", "xml"):
            self._extract_structured(context, file_type)

        elif file_type == "email":
            self._extract_email(context)

        logger.info(
            f"Extracted {len(context.raw_text)} chars, "
            f"{len(context.tables)} tables from {file_type}"
        )
        return context

    async def _extract_pdf(self, context: PipelineContext) -> None:
        """Extract from PDF using PdfProcessorSkill."""
        try:
            from skills.skill_registry import get_skill
            skill = get_skill("pdf_processor")
            if skill:
                result = await skill.run(
                    action="extract_text",
                    file_path=context.file_path,
                    include_metadata=True,
                )
                if result.success and result.data:
                    context.raw_text = result.data.get("text", "")
                    context.metadata = result.data.get("metadata", {})
                    context.page_count = result.data.get("page_count", 0)

                # Try table extraction
                table_result = await skill.run(
                    action="extract_tables",
                    file_path=context.file_path,
                )
                if table_result.success and table_result.data:
                    context.tables = table_result.data.get("tables", [])
                return
        except Exception as e:
            logger.debug(f"PdfProcessorSkill unavailable: {e}")

        # Fallback: try pypdf directly
        try:
            from pypdf import PdfReader
            reader = PdfReader(context.file_path)
            pages = []
            for page in reader.pages:
                pages.append(page.extract_text() or "")
            context.raw_text = "\n\n".join(pages)
            context.page_count = len(reader.pages)
            context.metadata = {"page_count": len(reader.pages)}
        except Exception as e:
            logger.error(f"PDF extraction fallback failed: {e}")

    def _extract_docx(self, context: PipelineContext) -> None:
        result = extract_docx(context.file_path)
        if result.get("success"):
            context.raw_text = result["text"]
            context.tables = result.get("tables", [])
            context.metadata = result.get("metadata", {})

    def _extract_xlsx(self, context: PipelineContext) -> None:
        result = extract_xlsx(context.file_path)
        if result.get("success"):
            context.raw_text = result["text"]
            context.tables = result.get("tables", [])
            context.metadata = result.get("metadata", {})

    async def _extract_csv(self, context: PipelineContext) -> None:
        """Extract from CSV using SpreadsheetAnalyzerSkill."""
        try:
            from skills.skill_registry import get_skill
            skill = get_skill("spreadsheet_analyzer")
            if skill:
                result = await skill.run(action="load", file_path=context.file_path)
                if result.success and result.data:
                    context.raw_text = result.data.get("text", "") or str(result.data)
                    context.metadata = result.data.get("metadata", {})
                return
        except Exception:
            pass

        # Fallback: read CSV as text
        try:
            with open(context.file_path, "r", encoding="utf-8", errors="replace") as f:
                context.raw_text = f.read(500000)
        except Exception as e:
            logger.error(f"CSV extraction failed: {e}")

    def _extract_pptx(self, context: PipelineContext) -> None:
        result = extract_pptx(context.file_path)
        if result.get("success"):
            context.raw_text = result["text"]
            context.tables = result.get("tables", [])
            context.metadata = result.get("metadata", {})

    async def _extract_image(self, context: PipelineContext) -> None:
        """Extract from image using OCR via ImageAnalyzerSkill."""
        try:
            from skills.skill_registry import get_skill
            skill = get_skill("image_analyzer")
            if skill:
                result = await skill.run(action="ocr", file_path=context.file_path)
                if result.success and result.data:
                    context.raw_text = result.data.get("text", "")
                    context.metadata = result.data.get("metadata", {})
                return
        except Exception:
            pass

        # Fallback: try pytesseract directly
        try:
            import pytesseract
            from PIL import Image
            img = Image.open(context.file_path)
            context.raw_text = pytesseract.image_to_string(img)
        except Exception as e:
            logger.error(f"Image OCR failed: {e}")

    def _extract_text(self, context: PipelineContext) -> None:
        """Extract plain text files."""
        try:
            with open(context.file_path, "r", encoding="utf-8", errors="replace") as f:
                context.raw_text = f.read(500000)
        except Exception as e:
            logger.error(f"Text extraction failed: {e}")

    def _extract_html(self, context: PipelineContext) -> None:
        """Extract text from HTML."""
        try:
            with open(context.file_path, "r", encoding="utf-8", errors="replace") as f:
                html = f.read(500000)
        except Exception as e:
            logger.error(f"HTML read failed: {e}")
            return

        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")
            for tag in soup.find_all(["script", "style", "nav", "footer"]):
                tag.decompose()
            main = soup.find("main") or soup.find("article") or soup.find("body")
            context.raw_text = main.get_text(separator="\n", strip=True) if main else soup.get_text(strip=True)
            title = soup.find("title")
            if title:
                context.metadata["title"] = title.get_text(strip=True)
        except ImportError:
            # Fallback: regex strip tags
            import re
            text = re.sub(r"<[^>]+>", " ", html)
            context.raw_text = re.sub(r"\s+", " ", text).strip()

    def _extract_structured(self, context: PipelineContext, file_type: str) -> None:
        """Extract from JSON or XML files."""
        try:
            with open(context.file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read(500000)

            if file_type == "json":
                try:
                    data = json.loads(content)
                    context.raw_text = json.dumps(data, indent=2, ensure_ascii=False)
                    context.metadata["json_type"] = type(data).__name__
                except json.JSONDecodeError:
                    context.raw_text = content

            elif file_type == "xml":
                context.raw_text = content  # Store raw for entity extraction
                context.metadata["format"] = "xml"
        except Exception as e:
            logger.error(f"Structured extraction failed: {e}")

    def _extract_email(self, context: PipelineContext) -> None:
        """Extract from EML or MSG email files."""
        ext = (context.filename or context.file_path or "").rsplit(".", 1)[-1].lower()
        if ext == "msg":
            result = extract_msg(context.file_path)
        else:
            result = extract_eml(context.file_path)

        if result.get("success"):
            context.raw_text = result["text"]
            context.metadata = result.get("metadata", {})