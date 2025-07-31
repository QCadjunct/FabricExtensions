#!/usr/bin/env python3
"""
Enhanced textfile_converter: A robust script to convert various file formats to text.
Supports PDF, Microsoft Office files, structured data formats (JSON, XML, YAML, CSV, Parquet),
SQL files, images via OCR, and more. Enhanced for Fabric integration with better error handling,
logging, and streaming capabilities.
"""

import os
import sys
import importlib
import logging
from pathlib import Path
import urllib.request
import urllib.error
import tempfile
import json
import subprocess
from typing import Optional, Union, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger(__name__)

class TextFileConverter:
    """Enhanced text file converter with better error handling and extensibility."""
    
    def __init__(self):
        self.temp_files = []
        self.supported_formats = {
            'pdf': self._convert_pdf,
            'docx': lambda fp: self._convert_office(fp, 'docx'),
            'xlsx': lambda fp: self._convert_office(fp, 'xlsx'), 
            'pptx': lambda fp: self._convert_office(fp, 'pptx'),
            'json': lambda fp: self._convert_structured(fp, 'json'),
            'xml': lambda fp: self._convert_structured(fp, 'xml'),
            'yaml': lambda fp: self._convert_structured(fp, 'yaml'),
            'yml': lambda fp: self._convert_structured(fp, 'yaml'),
            'csv': lambda fp: self._convert_structured(fp, 'csv'),
            'parquet': lambda fp: self._convert_structured(fp, 'parquet'),
            'sql': self._convert_sql,
            'jpg': self._convert_ocr,
            'jpeg': self._convert_ocr,
            'png': self._convert_ocr,
            'gif': self._convert_ocr,
            'bmp': self._convert_ocr,
            'tiff': self._convert_ocr,
            'webp': self._convert_ocr,
            'md': self._convert_text,
            'txt': self._convert_text,
            'rtf': self._convert_rtf,
            'epub': self._convert_epub,
            'html': self._convert_html,
            'htm': self._convert_html,
        }
    
    def __del__(self):
        """Clean up temporary files."""
        self._cleanup_temp_files()
    
    def _cleanup_temp_files(self):
        """Remove temporary files created during processing."""
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception as e:
                logger.warning(f"Failed to remove temp file {temp_file}: {e}")
        self.temp_files.clear()

    def _load_module(self, module_name: str, package_name: str = None):
        """
        Dynamically load a module and install it if not present.
        
        Args:
            module_name (str): Name of the module to load.
            package_name (str): Name of the package to install (if different from module).
            
        Returns:
            module: The loaded module.
        """
        if package_name is None:
            package_name = module_name
            
        try:
            return importlib.import_module(module_name)
        except ImportError:
            logger.info(f"Installing {package_name}...")
            try:
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", package_name],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                return importlib.import_module(module_name)
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to install {package_name}: {e}")
                raise ImportError(f"Could not install required package: {package_name}")

    def _detect_encoding(self, file_path: str) -> Optional[str]:
        """
        Detect the encoding of a text file using the chardet library.
        
        Args:
            file_path (str): Path to the text file.
            
        Returns:
            str: Detected encoding or None if detection fails.
        """
        try:
            chardet = self._load_module('chardet')
            with open(file_path, 'rb') as f:
                # Read more data for better detection
                rawdata = f.read(50000)
            result = chardet.detect(rawdata)
            confidence = result.get('confidence', 0)
            if confidence > 0.7:  # Only use if confidence is high
                return result['encoding']
        except Exception as e:
            logger.warning(f"Encoding detection failed for {file_path}: {e}")
        return None

    def _convert_pdf(self, file_path: str) -> str:
        """Convert PDF file to text with enhanced error handling."""
        try:
            # Try PyPDF2 first
            PyPDF2 = self._load_module('PyPDF2')
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                for page_num, page in enumerate(reader.pages):
                    try:
                        page_text = page.extract_text()
                        if page_text.strip():
                            text += f"\n--- Page {page_num + 1} ---\n{page_text}\n"
                    except Exception as e:
                        logger.warning(f"Failed to extract text from page {page_num + 1}: {e}")
                        continue
                return text
        except Exception as e:
            logger.error(f"PyPDF2 failed: {e}")
            
        # Fallback to pdfplumber if available
        try:
            pdfplumber = self._load_module('pdfplumber')
            with pdfplumber.open(file_path) as pdf:
                text = ""
                for page_num, page in enumerate(pdf.pages):
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text += f"\n--- Page {page_num + 1} ---\n{page_text}\n"
                    except Exception as e:
                        logger.warning(f"Failed to extract text from page {page_num + 1}: {e}")
                        continue
                return text
        except Exception as e:
            logger.error(f"PDF conversion failed: {e}")
            raise

    def _convert_office(self, file_path: str, format_type: str) -> str:
        """Convert Microsoft Office files with better error handling."""
        try:
            if format_type == 'docx':
                docx = self._load_module('docx', 'python-docx')
                doc = docx.Document(file_path)
                text_parts = []
                
                # Extract paragraphs
                for para in doc.paragraphs:
                    if para.text.strip():
                        text_parts.append(para.text)
                
                # Extract tables
                for table in doc.tables:
                    for row in table.rows:
                        row_text = []
                        for cell in row.cells:
                            if cell.text.strip():
                                row_text.append(cell.text.strip())
                        if row_text:
                            text_parts.append(" | ".join(row_text))
                
                return "\n".join(text_parts)
                
            elif format_type == 'xlsx':
                openpyxl = self._load_module('openpyxl')
                wb = openpyxl.load_workbook(file_path, data_only=True)
                text_parts = []
                
                for sheet_name in wb.sheetnames:
                    sheet = wb[sheet_name]
                    text_parts.append(f"\n--- Sheet: {sheet_name} ---")
                    
                    for row in sheet.iter_rows(values_only=True):
                        row_data = [str(cell) if cell is not None else "" for cell in row]
                        if any(cell.strip() for cell in row_data):
                            text_parts.append("\t".join(row_data))
                
                return "\n".join(text_parts)
                
            elif format_type == 'pptx':
                pptx = self._load_module('pptx', 'python-pptx')
                prs = pptx.Presentation(file_path)
                text_parts = []
                
                for slide_num, slide in enumerate(prs.slides, 1):
                    text_parts.append(f"\n--- Slide {slide_num} ---")
                    for shape in slide.shapes:
                        if hasattr(shape, 'text') and shape.text.strip():
                            text_parts.append(shape.text)
                
                return "\n".join(text_parts)
                
        except Exception as e:
            logger.error(f"Office file conversion failed for {file_path}: {e}")
            raise

    def _convert_structured(self, file_path: str, format_type: str) -> str:
        """Convert structured data files with enhanced formatting."""
        encoding = self._detect_encoding(file_path) or 'utf-8'
        
        try:
            if format_type == 'json':
                with open(file_path, 'r', encoding=encoding) as file:
                    data = json.load(file)
                return json.dumps(data, indent=2, ensure_ascii=False)
                
            elif format_type == 'xml':
                ET = self._load_module('xml.etree.ElementTree')
                try:
                    tree = ET.parse(file_path)
                    return ET.tostring(tree.getroot(), encoding='unicode', method='xml')
                except ET.ParseError:
                    # Fallback to reading as text if XML is malformed
                    return self._convert_text(file_path)
                    
            elif format_type == 'yaml':
                yaml = self._load_module('yaml', 'PyYAML')
                with open(file_path, 'r', encoding=encoding) as file:
                    data = yaml.safe_load(file)
                return yaml.dump(data, default_flow_style=False, allow_unicode=True)
                
            elif format_type == 'csv':
                pandas = self._load_module('pandas')
                try:
                    df = pandas.read_csv(file_path, encoding=encoding)
                    return df.to_string(index=False, max_rows=10000)
                except Exception:
                    # Fallback to basic CSV reading
                    csv = self._load_module('csv')
                    with open(file_path, 'r', encoding=encoding) as file:
                        reader = csv.reader(file)
                        return "\n".join(["\t".join(row) for row in reader])
                        
            elif format_type == 'parquet':
                pandas = self._load_module('pandas')
                df = pandas.read_parquet(file_path)
                return df.to_string(index=False, max_rows=10000)
                
        except Exception as e:
            logger.error(f"Structured data conversion failed for {file_path}: {e}")
            raise

    def _convert_sql(self, file_path: str) -> str:
        """Parse and format SQL file."""
        encoding = self._detect_encoding(file_path) or 'utf-8'
        
        try:
            with open(file_path, 'r', encoding=encoding) as file:
                sql_content = file.read()
            
            try:
                sqlparse = self._load_module('sqlparse')
                parsed = sqlparse.parse(sql_content)
                formatted_statements = []
                for stmt in parsed:
                    if str(stmt).strip():
                        formatted = sqlparse.format(
                            str(stmt), 
                            reindent=True, 
                            keyword_case='upper',
                            strip_comments=False
                        )
                        formatted_statements.append(formatted)
                return "\n\n".join(formatted_statements)
            except:
                # Fallback to raw SQL if parsing fails
                return sql_content
                
        except Exception as e:
            logger.error(f"SQL conversion failed for {file_path}: {e}")
            raise

    def _convert_ocr(self, file_path: str) -> str:
        """Perform OCR on image files with enhanced options."""
        try:
            pytesseract = self._load_module('pytesseract')
            PIL = self._load_module('PIL', 'Pillow')
            
            image = PIL.Image.open(file_path)
            
            # Enhance image for better OCR if needed
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Use multiple OCR configurations for better results
            configs = [
                '--psm 3',  # Default
                '--psm 6',  # Single uniform block
                '--psm 4',  # Single column of text
            ]
            
            best_text = ""
            for config in configs:
                try:
                    text = pytesseract.image_to_string(image, config=config)
                    if len(text.strip()) > len(best_text.strip()):
                        best_text = text
                except:
                    continue
            
            return best_text or pytesseract.image_to_string(image)
            
        except Exception as e:
            logger.error(f"OCR conversion failed for {file_path}: {e}")
            raise

    def _convert_text(self, file_path: str) -> str:
        """Convert plain text files with encoding detection."""
        encodings_to_try = []
        detected_encoding = self._detect_encoding(file_path)
        if detected_encoding:
            encodings_to_try.append(detected_encoding)
        
        encodings_to_try.extend([
            'utf-8', 'utf-16', 'utf-16le', 'utf-16be', 'utf-32',
            'iso-8859-1', 'windows-1252', 'cp1252', 'latin1'
        ])

        for encoding in encodings_to_try:
            try:
                with open(file_path, 'r', encoding=encoding) as file:
                    return file.read()
            except (UnicodeDecodeError, LookupError):
                continue

        raise UnicodeDecodeError(
            "utf-8", b"", 0, 1, 
            f"All encoding attempts failed for {file_path}. Please check the file."
        )

    def _convert_rtf(self, file_path: str) -> str:
        """Convert RTF files to text."""
        try:
            striprtf = self._load_module('striprtf')
            with open(file_path, 'r', encoding='utf-8') as file:
                rtf_content = file.read()
            return striprtf.rtf_to_text(rtf_content)
        except Exception as e:
            logger.warning(f"RTF conversion failed, falling back to text: {e}")
            return self._convert_text(file_path)

    def _convert_epub(self, file_path: str) -> str:
        """Convert EPUB files to text."""
        try:
            ebooklib = self._load_module('ebooklib')
            bs4 = self._load_module('bs4', 'beautifulsoup4')
            
            book = ebooklib.epub.read_epub(file_path)
            text_parts = []
            
            for item in book.get_items():
                if item.get_type() == ebooklib.ITEM_DOCUMENT:
                    soup = bs4.BeautifulSoup(item.get_content(), 'html.parser')
                    text_parts.append(soup.get_text())
            
            return "\n\n".join(text_parts)
        except Exception as e:
            logger.error(f"EPUB conversion failed for {file_path}: {e}")
            raise

    def _convert_html(self, file_path: str) -> str:
        """Convert HTML files to text."""
        try:
            bs4 = self._load_module('bs4', 'beautifulsoup4')
            encoding = self._detect_encoding(file_path) or 'utf-8'
            
            with open(file_path, 'r', encoding=encoding) as file:
                content = file.read()
            
            soup = bs4.BeautifulSoup(content, 'html.parser')
            return soup.get_text()
        except Exception as e:
            logger.warning(f"HTML conversion failed, falling back to text: {e}")
            return self._convert_text(file_path)

    def _download_file(self, url: str) -> str:
        """Download a file from URL with better error handling."""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        req = urllib.request.Request(url, headers=headers)

        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                suffix = Path(url).suffix or '.tmp'
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
                    tmp_file.write(response.read())
                    self.temp_files.append(tmp_file.name)
                    return tmp_file.name
        except urllib.error.HTTPError as e:
            logger.error(f"HTTP Error {e.code}: {e.reason} for URL: {url}")
            raise
        except urllib.error.URLError as e:
            logger.error(f"URL Error: {e.reason} for URL: {url}")
            raise
        except Exception as e:
            logger.error(f"Download failed for {url}: {e}")
            raise

    def convert_file(self, input_file: str) -> str:
        """
        Convert various file formats to text.
        
        Args:
            input_file (str): Path or URL to the input file.
            
        Returns:
            str: Extracted text content.
        """
        try:
            # Handle URLs
            if input_file.startswith(('http://', 'https://')):
                file_path = self._download_file(input_file)
            else:
                file_path = input_file
                if not os.path.exists(file_path):
                    raise FileNotFoundError(f"File not found: {file_path}")

            file_extension = Path(file_path).suffix.lower()[1:]  # Remove the leading dot
            
            # Check if format is supported
            if file_extension in self.supported_formats:
                logger.info(f"Converting {file_extension.upper()} file: {Path(file_path).name}")
                return self.supported_formats[file_extension](file_path)
            else:
                logger.info(f"Unknown extension '{file_extension}', treating as text file")
                return self._convert_text(file_path)
                
        except Exception as e:
            logger.error(f"Conversion failed for {input_file}: {e}")
            raise
        finally:
            self._cleanup_temp_files()


def convert_file(input_file: str) -> str:
    """Backward compatibility function."""
    converter = TextFileConverter()
    return converter.convert_file(input_file)


def main():
    """Main function to handle command-line arguments and process the file."""
    if len(sys.argv) < 2:
        print("Usage: python textfile_converter.py <input_file> [output_file]")
        print("\nSupported formats:")
        converter = TextFileConverter()
        formats = list(converter.supported_formats.keys())
        print(", ".join(sorted(formats)))
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    try:
        converter = TextFileConverter()
        converted_text = converter.convert_file(input_file)
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as file:
                file.write(converted_text)
            print(f"Converted text saved to {output_file}")
        else:
            print(converted_text)
            
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
