"""
Exhibit Processor - Core logic for processing exhibits
Ported from TypeScript exhibit-generator.ts
"""

from dataclasses import dataclass
from typing import List, Optional, Callable
from datetime import datetime
import os


@dataclass
class ExhibitSource:
    """Source information for an exhibit"""
    url: Optional[str] = None
    title: str = ""
    description: Optional[str] = None
    archived: bool = False
    archive_url: Optional[str] = None
    file_path: Optional[str] = None


@dataclass
class GeneratedExhibit:
    """Generated exhibit information"""
    exhibit_letter: str  # A, B, C, etc.
    original_url: Optional[str]
    archive_url: Optional[str]
    pdf_url: Optional[str]
    pdf_path: Optional[str]
    title: str
    success: bool
    error: Optional[str] = None


@dataclass
class ExhibitPackage:
    """Complete exhibit package"""
    case_id: str
    exhibits: List[GeneratedExhibit]
    table_of_contents_path: Optional[str]
    combined_pdf_path: Optional[str]
    total_exhibits: int
    successful_exhibits: int
    failed_exhibits: int
    generated_at: datetime


class ExhibitProcessor:
    """Main exhibit processor class"""

    def __init__(self):
        self.exhibits = []

    def add_exhibit_from_file(self, file_path: str, title: str = "") -> None:
        """Add an exhibit from a file"""
        if not title:
            title = os.path.basename(file_path)

        exhibit = ExhibitSource(
            file_path=file_path,
            title=title
        )
        self.exhibits.append(exhibit)

    def add_exhibit_from_url(self, url: str, title: str = "") -> None:
        """Add an exhibit from a URL"""
        if not title:
            title = url.split('/')[-1] or 'webpage'

        exhibit = ExhibitSource(
            url=url,
            title=title
        )
        self.exhibits.append(exhibit)

    def clear_exhibits(self) -> None:
        """Clear all exhibits"""
        self.exhibits = []

    def get_exhibit_count(self) -> int:
        """Get total number of exhibits"""
        return len(self.exhibits)

    def process_exhibits(
        self,
        case_id: str,
        on_progress: Optional[Callable[[str, int, int], None]] = None
    ) -> ExhibitPackage:
        """
        Process all exhibits and generate package

        Args:
            case_id: Unique case identifier
            on_progress: Callback for progress updates (stage, current, total)

        Returns:
            ExhibitPackage with results
        """
        generated_exhibits = []

        for idx, source in enumerate(self.exhibits):
            if on_progress:
                on_progress(f"Processing exhibit {idx + 1}", idx + 1, len(self.exhibits))

            # Generate exhibit letter (A, B, C...)
            exhibit_letter = chr(65 + idx)

            try:
                # Process the exhibit
                generated = GeneratedExhibit(
                    exhibit_letter=exhibit_letter,
                    original_url=source.url,
                    archive_url=source.archive_url,
                    pdf_url=None,
                    pdf_path=source.file_path,
                    title=source.title,
                    success=True
                )
                generated_exhibits.append(generated)

            except Exception as e:
                # Handle failures
                generated = GeneratedExhibit(
                    exhibit_letter=exhibit_letter,
                    original_url=source.url,
                    archive_url=source.archive_url,
                    pdf_url=None,
                    pdf_path=None,
                    title=source.title,
                    success=False,
                    error=str(e)
                )
                generated_exhibits.append(generated)

        # Calculate statistics
        successful = sum(1 for ex in generated_exhibits if ex.success)
        failed = sum(1 for ex in generated_exhibits if not ex.success)

        return ExhibitPackage(
            case_id=case_id,
            exhibits=generated_exhibits,
            table_of_contents_path=None,
            combined_pdf_path=None,
            total_exhibits=len(generated_exhibits),
            successful_exhibits=successful,
            failed_exhibits=failed,
            generated_at=datetime.now()
        )
