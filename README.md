# File Conversion Toolkit

This toolkit provides two powerful scripts for converting various file formats to text, including support for video files.

## 1. Text File Converter (textfile_converter.py)

A versatile script to convert various file formats to text.

### Supported Formats:
- PDF
- Microsoft Office files (DOCX, XLSX, PPTX)
- Structured data formats (JSON, XML, YAML, CSV, Parquet)
- SQL files
- Images (via OCR)
- Plain text files with various encodings

### Usage:
```
python textfile_converter.py <input_file> [output_file]
```

If no output file is specified, the script will print the converted text to stdout.

### Features:
- Handles local files and URLs
- Intelligent file encoding detection
- Dynamic module loading and installation

## 2. Video File Converter (videofile_converter.py)

This script converts video files to text using GPU-accelerated processing when possible.

### Supported Formats:
- Various video formats (processed using OpenCV)

### Usage:
```
python3 videofile_converter.py <input_file> [<output_file>]
```

If no output file is specified, the script will print the extracted text to stdout.

### Features:
- Supports local video files and URLs (including YouTube videos)
- GPU acceleration (when PyCUDA is available)
- Dynamic module loading and installation

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/file-conversion-toolkit.git
   cd file-conversion-toolkit
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

   Note: Some dependencies might require additional system-level installations, particularly for OCR and video processing.

## Dependencies

See the `requirements.txt` file for a full list of Python dependencies.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
