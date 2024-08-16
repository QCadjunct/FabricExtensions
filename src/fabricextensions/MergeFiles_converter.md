# MergeFiles_converter

## Overview

`MergeFiles_converter` is a versatile Python script designed to merge multiple files of various formats into a single text output. It leverages the functionality of `textfile_converter.py` to handle different file types, making it a powerful tool for file merging and conversion tasks.

## Key Features

1. **Variable Parameter List**
   - Accepts multiple file paths as command-line arguments
   - Optional output file can be specified as the last argument

2. **Directory Processing**
   - Can process all files within a specified directory
   - Automatically numbers files in the output, handling existing "1-" or "01-" prefixes

3. **Integration with textfile_converter**
   - Uses the `convert_file` function from `textfile_converter.py`
   - Supports various file formats including PDF, Office documents, images, and more

4. **Flexible Output Handling**
   - Writes merged content to a specified output file
   - Prints to standard output if no output file is specified

5. **Robust Error Handling**
   - Catches and reports errors for individual file processing
   - Continues merging even if some files fail to process

## Usage

### Processing Individual Files

To merge specific files, use the following command structure:

`python MergeFiles_converter.py <file1> <file2> ... [output_file]`

#### Example 1

`python MergeFiles_converter.py file1.pdf file2.docx file3.txt output.txt`

### Processing a Directory

- To process all files within a directory:

`python MergeFiles_converter.py <input_directory> [output_file]`

#### Example 2

`python MergeFiles_converter.py /path/to/directory output.txt`

- Note: If you omit the output file, the merged content will be printed to the console.

## Output Format

The merged output follows this structure:

`01-filename1
[Content of file 1]

02-filename2
[Content of file 2]
...
`

## Dependencies

- Python 3.x
- `textfile_converter.py` (ensure this file is in the same directory or in the Python path)

## Error Handling

If an error occurs while processing a file, the script will:

1. Print an error message to stderr
2. Continue processing the remaining files
3. Include successfully processed files in the final output

## Conclusion

`MergeFiles_converter` provides a flexible and efficient way to merge multiple files of various formats into a single text output. Whether you need to combine individual files or process an entire directory, this script offers a straightforward solution while handling a wide range of file types.
