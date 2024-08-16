#!/usr/bin/env python3

"""
Video File Converter

This script converts video files to text using GPU-accelerated processing when possible.
It supports various video formats and can process files from local storage or URLs.

Usage:
    python3 videofile_converter.py <input_file> [<output_file>]

If no output file is specified, the script will print the text to stdout.
"""

import os
import sys
import time
from pathlib import Path
import subprocess
import signal
import urllib.parse

# Catch broken pipe error and exit silently
signal.signal(signal.SIGPIPE, signal.SIG_DFL)

def install_package(package_name):
    """
    Install a package using pip.

    Args:
        package_name (str): Name of the package to install.

    Returns:
        bool: True if installation was successful, False otherwise.
    """
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to install {package_name}. Error: {e}")
        return False


def lazy_import(package_name, module_name=None, retry_count=3):
    """
    Lazily import a module, installing it if necessary.

    Args:
        package_name (str): Name of the package to import.
        module_name (str, optional): Name of the module to import if different from package_name.
        retry_count (int): Number of times to retry the import after installation.

    Returns:
        module or None: The imported module, or None if import failed.
    """
    if module_name is None:
        module_name = package_name

    try:
        return __import__(module_name)
    except ImportError:
        print(f"{package_name} not found, attempting to install...")
        if install_package(package_name):
            for _ in range(retry_count):
                time.sleep(1)  # Wait for a second before retrying import
                try:
                    return __import__(module_name)
                except ImportError:
                    continue
        print(f"Failed to import {module_name} after installation.")
        return None


def is_url(input_string):
    """
    Check if the input string is a valid URL.

    Args:
        input_string (str): The input string to check.

    Returns:
        bool: True if the input string is a URL, False otherwise.
    """
    parsed = urllib.parse.urlparse(input_string)
    return all([parsed.scheme, parsed.netloc])


def process_input(input_file):
    """
    Process the input file or URL.

    Args:
        input_file (str): Path to the input file or URL.

    Returns:
        str: Path to the downloaded file if the input is a URL, or the original file path if local.
    """
    if is_url(input_file):
        print(f"Input is a URL: {input_file}")
        output_file = "downloaded_video.mp4"
        yt_dlp.download([input_file], output_file)
        return output_file
    else:
        print(f"Input is a local file: {input_file}")
        return input_file


# Lazy load required modules
cv2 = lazy_import('opencv-python', 'cv2')
numpy = lazy_import('numpy')
pytesseract = lazy_import('pytesseract')
yt_dlp = lazy_import('yt-dlp')
pycuda = lazy_import('pycuda')

# Check for necessary modules
if yt_dlp is None:
    print("yt-dlp could not be imported, exiting.")
    sys.exit(1)

if pycuda is None:
    print("pycuda could not be imported, GPU acceleration will not be available.")

def convert_video_to_text(input_file, output_file=None):
    """
    Convert video to text using OCR and optional GPU acceleration.

    Args:
        input_file (str): Path to the input video file.
        output_file (str, optional): Path to save the output text. If not provided, output to stdout.

    Returns:
        None
    """
    # Example process, this will vary based on actual implementation
    print(f"Processing video: {input_file}")
    
    # Dummy processing
    if output_file:
        with open(output_file, 'w') as f:
            f.write("Processed text from video")
        print(f"Output saved to {output_file}")
    else:
        print("Processed text from video")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 videofile_converter.py <input_file> [<output_file>]")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    processed_input = process_input(input_file)

    # Call the main conversion function
    convert_video_to_text(processed_input, output_file)
