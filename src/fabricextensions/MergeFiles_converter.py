#!/usr/bin/env python3
"""
MergeFiles_converter: A script to merge multiple files into a single text output.
This script can handle individual files specified as command-line arguments
or process all files within a specified directory.
It utilizes the textfile_converter to convert various file formats to text before merging.
"""

import os
import sys
from pathlib import Path
from textfile_converter import convert_file

def process_files(file_paths, output_file=None):
    """
    Process multiple files and merge their contents.

    Args:
        file_paths (list): List of file paths to process.
        output_file (str, optional): Path to the output file. If None, print to stdout.

    Returns:
        str: Merged content of all processed files.
    """
    merged_content = ""
    for i, file_path in enumerate(file_paths, start=1):
        try:
            content = convert_file(file_path)
            file_name = Path(file_path).name
            merged_content += f"{i:02d}-{file_name}\n{content}\n\n"
        except Exception as e:
            print(f"Error processing {file_path}: {str(e)}", file=sys.stderr)

    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(merged_content)
        print(f"Merged content saved to {output_file}")
    else:
        print(merged_content)

    return merged_content

def main():
    """
    Main function to handle command-line arguments and process files.
    """
    if len(sys.argv) < 2:
        print("Usage:")
        print("1. python MergeFiles_converter.py <file1> <file2> ... [output_file]")
        print("2. python MergeFiles_converter.py <input_directory> [output_file]")
        sys.exit(1)

    # Check if the first argument is a directory
    if os.path.isdir(sys.argv[1]):
        input_dir = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) > 2 else None
        file_paths = [os.path.join(input_dir, f) for f in os.listdir(input_dir) if os.path.isfile(os.path.join(input_dir, f))]
    else:
        file_paths = sys.argv[1:-1] if len(sys.argv) > 2 else sys.argv[1:]
        output_file = sys.argv[-1] if len(sys.argv) > 2 else None

    process_files(file_paths, output_file)

if __name__ == "__main__":
    main()