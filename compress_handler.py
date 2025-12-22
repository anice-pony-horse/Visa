"""
PDF Compression Handler for Visa Petition Exhibits
Implements 3-tier compression with USCIS-compliant quality settings

Tier 1: Ghostscript (60-90% compression, FREE)
Tier 2: PyMuPDF (30-60% compression, FREE)
Tier 3: SmallPDF API (40-80% compression, $12/month)

Maintains legal document quality:
- Text: 300 DPI (crystal clear)
- Images: 200 DPI (readable seals/signatures)
- JPEG Quality: 85% (no visible artifacts)
"""

import os
import subprocess
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Literal
import requests

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class USCISPDFCompressor:
    """
    Production-ready PDF compression for USCIS visa petition documents
    Maintains legal document quality while significantly reducing file size
    """

    QUALITY_PRESETS = {
        'high': {
            'name': 'High Quality (USCIS Recommended)',
            'description': '300 DPI text, 200 DPI images - Best for legal docs',
            'ghostscript_settings': '/printer',
            'color_dpi': 200,
            'gray_dpi': 200,
            'mono_dpi': 300,
            'jpeg_quality': 85
        },
        'balanced': {
            'name': 'Balanced',
            'description': '150 DPI images, 300 DPI text - Good compression',
            'ghostscript_settings': '/ebook',
            'color_dpi': 150,
            'gray_dpi': 150,
            'mono_dpi': 300,
            'jpeg_quality': 80
        },
        'maximum': {
            'name': 'Maximum Compression',
            'description': '100 DPI images - Smallest files (use with caution)',
            'ghostscript_settings': '/screen',
            'color_dpi': 100,
            'gray_dpi': 100,
            'mono_dpi': 200,
            'jpeg_quality': 75
        }
    }

    def __init__(
        self,
        quality_preset: Literal['high', 'balanced', 'maximum'] = 'high',
        smallpdf_api_key: Optional[str] = None
    ):
        """
        Initialize PDF compressor

        Args:
            quality_preset: Quality level ('high', 'balanced', 'maximum')
            smallpdf_api_key: Optional SmallPDF API key for Tier 3 fallback
        """
        self.quality_preset = quality_preset
        self.smallpdf_api_key = smallpdf_api_key
        self.preset_config = self.QUALITY_PRESETS[quality_preset]

    def compress(
        self,
        input_path: str,
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Compress PDF using intelligent 3-tier fallback system

        Args:
            input_path: Path to input PDF file
            output_path: Path for compressed output (optional)

        Returns:
            Dictionary with compression results including:
            - success: bool
            - output_path: str
            - original_size: int
            - compressed_size: int
            - reduction_percent: float
            - method: str ('ghostscript', 'pymupdf', 'smallpdf', 'none')
        """
        if not output_path:
            output_path = self._get_temp_path(input_path)

        logger.info(f"Compressing: {input_path}")
        logger.info(f"Quality preset: {self.preset_config['name']}")

        # Try compression methods in order of preference
        methods = [
            ('ghostscript', self._compress_ghostscript),
            ('pymupdf', self._compress_pymupdf),
        ]

        # Add SmallPDF if API key provided
        if self.smallpdf_api_key:
            methods.append(('smallpdf', self._compress_smallpdf))

        for method_name, method_func in methods:
            try:
                logger.info(f"Attempting compression with: {method_name}")
                result = method_func(input_path, output_path)

                if result['success']:
                    logger.info(
                        f"✓ Compression successful with {method_name}: "
                        f"{result['reduction_percent']:.1f}% reduction"
                    )
                    return result

            except Exception as e:
                logger.warning(f"✗ {method_name} compression failed: {e}")
                continue

        # All methods failed - return original file
        logger.warning("All compression methods failed - using original file")
        original_size = os.path.getsize(input_path)

        return {
            'success': False,
            'output_path': input_path,
            'original_size': original_size,
            'compressed_size': original_size,
            'reduction_percent': 0.0,
            'method': 'none',
            'error': 'All compression methods failed'
        }

    def _compress_ghostscript(
        self,
        input_path: str,
        output_path: str
    ) -> Dict[str, Any]:
        """
        Tier 1: Ghostscript compression (best compression ratio)
        """
        # Check if Ghostscript is available
        if not self._check_ghostscript():
            raise Exception("Ghostscript not available")

        config = self.preset_config

        # Build Ghostscript command with USCIS-optimized settings
        cmd = [
            'gs',
            '-sDEVICE=pdfwrite',
            '-dCompatibilityLevel=1.4',
            f'-dPDFSETTINGS={config["ghostscript_settings"]}',
            f'-dColorImageResolution={config["color_dpi"]}',
            f'-dGrayImageResolution={config["gray_dpi"]}',
            f'-dMonoImageResolution={config["mono_dpi"]}',
            '-dColorImageDownsampleType=/Bicubic',
            '-dGrayImageDownsampleType=/Bicubic',
            '-dDownsampleColorImages=true',
            '-dDownsampleGrayImages=true',
            '-dDownsampleMonoImages=false',  # Don't downsample text
            '-dCompressPages=true',
            '-dOptimize=true',
            '-dEmbedAllFonts=true',  # Always embed fonts
            '-dSubsetFonts=true',
            '-dNOPAUSE',
            '-dQUIET',
            '-dBATCH',
            f'-sOutputFile={output_path}',
            input_path
        ]

        original_size = os.path.getsize(input_path)

        # Run Ghostscript
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True
        )

        compressed_size = os.path.getsize(output_path)
        reduction = (1 - compressed_size / original_size) * 100

        return {
            'success': True,
            'output_path': output_path,
            'original_size': original_size,
            'compressed_size': compressed_size,
            'reduction_percent': round(reduction, 2),
            'method': 'ghostscript',
            'quality_preset': self.quality_preset
        }

    def _compress_pymupdf(
        self,
        input_path: str,
        output_path: str
    ) -> Dict[str, Any]:
        """
        Tier 2: PyMuPDF compression (good fallback)
        """
        try:
            import fitz  # PyMuPDF
        except ImportError:
            raise Exception("PyMuPDF not installed (pip install PyMuPDF)")

        config = self.preset_config
        doc = fitz.open(input_path)

        # USCIS-safe compression settings
        doc.save(
            output_path,
            garbage=4,  # Maximum garbage collection
            deflate=True,  # Maximum compression
            deflate_images=True,
            deflate_fonts=True,
            image_quality=config['jpeg_quality'],  # Maintain quality
            clean=True,  # Clean up redundant objects
            linear=True,  # Optimize for web viewing
        )

        original_size = os.path.getsize(input_path)
        compressed_size = os.path.getsize(output_path)
        reduction = (1 - compressed_size / original_size) * 100

        doc.close()

        return {
            'success': True,
            'output_path': output_path,
            'original_size': original_size,
            'compressed_size': compressed_size,
            'reduction_percent': round(reduction, 2),
            'method': 'pymupdf',
            'quality_preset': self.quality_preset
        }

    def _compress_smallpdf(
        self,
        input_path: str,
        output_path: str
    ) -> Dict[str, Any]:
        """
        Tier 3: SmallPDF API compression (premium quality)
        Requires API key: https://smallpdf.com/developers
        """
        if not self.smallpdf_api_key:
            raise Exception("SmallPDF API key not provided")

        base_url = "https://api.smallpdf.com/v2"
        headers = {"Authorization": f"Bearer {self.smallpdf_api_key}"}

        original_size = os.path.getsize(input_path)

        # Step 1: Upload file to SmallPDF
        with open(input_path, 'rb') as f:
            upload_response = requests.post(
                f"{base_url}/files",
                headers=headers,
                files={"file": f}
            )
            upload_response.raise_for_status()
            file_id = upload_response.json()["id"]

        # Step 2: Compress with recommended quality (best for legal docs)
        compress_data = {
            "files": [{"id": file_id}],
            "compression_level": "recommended"  # Maintains readability
        }

        compress_response = requests.post(
            f"{base_url}/compress",
            headers=headers,
            json=compress_data
        )
        compress_response.raise_for_status()

        # Step 3: Download compressed file
        download_url = compress_response.json()["files"][0]["url"]
        compressed_content = requests.get(download_url).content

        # Save compressed file
        with open(output_path, 'wb') as f:
            f.write(compressed_content)

        compressed_size = len(compressed_content)
        reduction = (1 - compressed_size / original_size) * 100

        return {
            'success': True,
            'output_path': output_path,
            'original_size': original_size,
            'compressed_size': compressed_size,
            'reduction_percent': round(reduction, 2),
            'method': 'smallpdf',
            'quality_preset': 'recommended'
        }

    def _check_ghostscript(self) -> bool:
        """Check if Ghostscript is installed and available"""
        try:
            result = subprocess.run(
                ['gs', '--version'],
                capture_output=True,
                check=True
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def _get_temp_path(self, input_path: str) -> str:
        """Generate temporary output path"""
        path = Path(input_path)
        return str(path.parent / f"compressed_{path.name}")

    @staticmethod
    def format_bytes(bytes_size: int) -> str:
        """Format bytes as human-readable string"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_size < 1024.0:
                return f"{bytes_size:.1f} {unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.1f} TB"


def compress_pdf_batch(
    file_paths: list[str],
    quality_preset: str = 'high',
    smallpdf_api_key: Optional[str] = None,
    on_progress: Optional[callable] = None
) -> list[Dict[str, Any]]:
    """
    Batch compress multiple PDF files

    Args:
        file_paths: List of PDF file paths to compress
        quality_preset: Quality level
        smallpdf_api_key: Optional SmallPDF API key
        on_progress: Optional callback(current, total, filename)

    Returns:
        List of compression results for each file
    """
    compressor = USCISPDFCompressor(quality_preset, smallpdf_api_key)
    results = []

    for i, file_path in enumerate(file_paths):
        if on_progress:
            on_progress(i + 1, len(file_paths), os.path.basename(file_path))

        result = compressor.compress(file_path)
        results.append(result)

    return results


# Example usage
if __name__ == "__main__":
    # Example: Compress a single file
    compressor = USCISPDFCompressor(quality_preset='high')

    test_file = "test.pdf"
    if os.path.exists(test_file):
        result = compressor.compress(test_file)

        print(f"\n{'='*60}")
        print(f"Compression Results")
        print(f"{'='*60}")
        print(f"Method: {result['method']}")
        print(f"Original Size: {USCISPDFCompressor.format_bytes(result['original_size'])}")
        print(f"Compressed Size: {USCISPDFCompressor.format_bytes(result['compressed_size'])}")
        print(f"Reduction: {result['reduction_percent']:.1f}%")
        print(f"Output: {result['output_path']}")
        print(f"{'='*60}\n")
