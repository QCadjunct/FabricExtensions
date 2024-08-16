#!/usr/bin/env python3
"""
A versatile script to convert various file formats to text. Supports formats like PDF, Microsoft Office files,
structured data formats (JSON, XML, YAML, CSV, Parquet), SQL files, and images via OCR. The script can handle
files from local paths or URLs and intelligently manages file encodings to prevent decoding errors.
"""

import os
import sys
import importlib
from pathlib import Path
import urllib.request
import urllib.error
import tempfile


def load_module(module_name):
    """
    Dynamically load a module and install it if not present.

    Args:
        module_name (str): Name of the module to load.

    Returns:
        module: The loaded module.
    """
    try:
        return importlib.import_module(module_name)
    except ImportError:
        print(f"Installing {module_name}...")
        import subprocess
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", module_name])
        return importlib.import_module(module_name)


def detect_encoding(file_path):
    """
    Detect the encoding of a text file using the chardet library.

    Args:
        file_path (str): Path to the text file.

    Returns:
        str: Detected encoding or None if detection fails.
    """
    chardet = load_module('chardet')
    with open(file_path, 'rb') as f:
        rawdata = f.read(10000)
    result = chardet.detect(rawdata)
    return result['encoding']


def convert_pdf(file_path):
    """
    Convert PDF file to text.

    Args:
        file_path (str): Path to the PDF file.

    Returns:
        str: Extracted text from the PDF.
    """
    PyPDF2 = load_module('PyPDF2')
    with open(file_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
    return text


def convert_office(file_path, format_type):
    """
    Convert Microsoft Office files (docx, xlsx, pptx) to text.

    Args:
        file_path (str): Path to the Office file.
        format_type (str): Type of the Office file ('docx', 'xlsx', or 'pptx').

    Returns:
        str: Extracted text from the Office file.
    """
    if format_type == 'docx':
        docx = load_module('docx')
        doc = docx.Document(file_path)
        return "\n".join([para.text for para in doc.paragraphs])
    elif format_type == 'xlsx':
        openpyxl = load_module('openpyxl')
        wb = openpyxl.load_workbook(file_path)
        text = ""
        for sheet in wb:
            for row in sheet.iter_rows(values_only=True):
                text += "\t".join([str(cell) for cell in row if cell]) + "\n"
        return text
    elif format_type == 'pptx':
        pptx = load_module('pptx')
        prs = pptx.Presentation(file_path)
        text = ""
        for slide in prs.slides:
            for shape in slide.shapes:
                if hasattr(shape, 'text'):
                    text += shape.text + "\n"
        return text


def convert_structured(file_path, format_type):
    """
    Convert structured data files (json, xml, yaml, csv, parquet) to text.

    Args:
        file_path (str): Path to the structured data file.
        format_type (str): Type of the structured data file.

    Returns:
        str: Extracted text from the structured data file.
    """
    if format_type == 'json':
        json = load_module('json')
        encoding = detect_encoding(file_path) or 'utf-8'
        with open(file_path, 'r', encoding=encoding) as file:
            return json.dumps(json.load(file), indent=2)
    elif format_type == 'xml':
        ET = load_module('xml.etree.ElementTree')
        encoding = detect_encoding(file_path) or 'utf-8'
        tree = ET.parse(file_path)
        return ET.tostring(tree.getroot(), encoding='unicode', method='xml')
    elif format_type == 'yaml':
        yaml = load_module('yaml')
        encoding = detect_encoding(file_path) or 'utf-8'
        with open(file_path, 'r', encoding=encoding) as file:
            return yaml.dump(yaml.safe_load(file))
    elif format_type == 'csv':
        pandas = load_module('pandas')
        encoding = detect_encoding(file_path) or 'utf-8'
        df = pandas.read_csv(file_path, encoding=encoding)
        return df.to_string(index=False)
    elif format_type == 'parquet':
        pandas = load_module('pandas')
        df = pandas.read_parquet(file_path)
        return df.to_string(index=False)


def convert_sql(file_path):
    """
    Parse and format SQL file.

    Args:
        file_path (str): Path to the SQL file.

    Returns:
        str: Formatted SQL content.
    """
    sqlparse = load_module('sqlparse')
    encoding = detect_encoding(file_path) or 'utf-8'
    with open(file_path, 'r', encoding=encoding) as file:
        sql_content = file.read()
    parsed = sqlparse.parse(sql_content)
    return "\n\n".join([sqlparse.format(str(stmt), reindent=True, keyword_case='upper') for stmt in parsed])


def convert_ocr(file_path):
    """
    Perform OCR on image files.

    Args:
        file_path (str): Path to the image file.

    Returns:
        str: Extracted text from the image.
    """
    pytesseract = load_module('pytesseract')
    PIL = load_module('PIL')
    image = PIL.Image.open(file_path)
    return pytesseract.image_to_string(image)


def download_file(url):
    """
    Download a file from a given URL.

    Args:
        url (str): URL of the file to download.

    Returns:
        str: Path to the downloaded file.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
    req = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(req) as response:
            suffix = Path(url).suffix
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
                tmp_file.write(response.read())
                return tmp_file.name
    except urllib.error.HTTPError as e:
        if e.code == 403:
            print(
                f"Error 403: Access Forbidden. The server denied access to the resource: {url}")
            print(
                "This might be due to server restrictions. Try downloading the file manually and provide the local file path.")
        else:
            print(f"HTTP Error {e.code}: {e.reason}")
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"URL Error: {e.reason}")
        sys.exit(1)


def convert_file(input_file):
    """
    Convert various file formats to text.

    Args:
        input_file (str): Path or URL to the input file.

    Returns:
        str: Extracted text content.
    """
    if input_file.startswith(('http://', 'https://')):
        file_path = download_file(input_file)
    else:
        file_path = input_file

    file_extension = Path(file_path).suffix.lower()[1:]  # Remove the leading dot

    if file_extension == 'pdf':
        return convert_pdf(file_path)
    elif file_extension in ['docx', 'xlsx', 'pptx']:
        return convert_office(file_path, file_extension)
    elif file_extension in ['json', 'xml', 'yaml', 'csv', 'parquet']:
        return convert_structured(file_path, file_extension)
    elif file_extension == 'sql':
        return convert_sql(file_path)
    elif file_extension in ['jpg', 'jpeg', 'png', 'gif', 'bmp']:
        return convert_ocr(file_path)
    else:
        encodings_to_try = []
        detected_encoding = detect_encoding(file_path)
        if detected_encoding:
            encodings_to_try.append(detected_encoding)
        encodings_to_try.extend(['utf-8', 'utf-16', 'utf-16le',
                                'utf-16be', 'utf-32', 'iso-8859-1', 'windows-1252'])

        for encoding in encodings_to_try:
            try:
                with open(file_path, 'r', encoding=encoding) as file:
                    return file.read()
            except (UnicodeDecodeError, LookupError):
                continue

        raise UnicodeDecodeError(
            "All attempts to decode the file have failed. Please check the file encoding.")


def main():
    """
    Main function to handle command-line arguments and process the file.
    """
    if len(sys.argv) < 2:
        print("Usage: python textfile_converter.py <input_file> [output_file]")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    try:
        converted_text = convert_file(input_file)
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as file:
                file.write(converted_text)
            print(f"Converted text saved to {output_file}")
        else:
            print(converted_text)
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
