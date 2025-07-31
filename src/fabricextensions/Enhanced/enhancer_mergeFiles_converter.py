#!/usr/bin/env python3
"""
Enhanced MergeFiles_converter: A robust script to merge multiple files into a single text output.
This enhanced version includes better error handling, progress tracking, filtering options,
and improved integration with Fabric workflows.
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from typing import List, Optional, Dict, Set
import fnmatch
import json
from datetime import datetime

try:
    from textfile_converter import TextFileConverter, convert_file
except ImportError:
    print("Error: textfile_converter.py not found. Please ensure it's in the same directory.")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EnhancedMergeFiles:
    """Enhanced file merger with filtering, progress tracking, and metadata support."""
    
    def __init__(self):
        self.converter = TextFileConverter()
        self.processed_files = []
        self.failed_files = []
        self.stats = {
            'total_files': 0,
            'processed': 0,
            'failed': 0,
            'skipped': 0,
            'start_time': None,
            'end_time': None
        }

    def _is_hidden_file(self, file_path: Path) -> bool:
        """Check if file is hidden (starts with dot)."""
        return file_path.name.startswith('.')

    def _matches_pattern(self, file_path: Path, patterns: List[str]) -> bool:
        """Check if file matches any of the given patterns."""
        if not patterns:
            return True
        
        file_name = file_path.name.lower()
        for pattern in patterns:
            if fnmatch.fnmatch(file_name, pattern.lower()):
                return True
        return False

    def _should_exclude_file(self, file_path: Path, exclude_patterns: List[str]) -> bool:
        """Check if file should be excluded based on patterns."""
        if not exclude_patterns:
            return False
        
        file_name = file_path.name.lower()
        for pattern in exclude_patterns:
            if fnmatch.fnmatch(file_name, pattern.lower()):
                return True
        return False

    def _get_file_metadata(self, file_path: Path) -> Dict:
        """Get metadata for a file."""
        try:
            stat = file_path.stat()
            return {
                'size': stat.st_size,
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'extension': file_path.suffix.lower()
            }
        except Exception as e:
            logger.warning(f"Could not get metadata for {file_path}: {e}")
            return {}

    def collect_files(self, 
                     paths: List[str], 
                     recursive: bool = False,
                     include_patterns: List[str] = None,
                     exclude_patterns: List[str] = None,
                     include_hidden: bool = False,
                     max_size_mb: Optional[float] = None) -> List[Path]:
        """
        Collect files from given paths with filtering options.
        
        Args:
            paths: List of file or directory paths
            recursive: Whether to search directories recursively
            include_patterns: List of patterns to include (e.g., ['*.txt', '*.md'])
            exclude_patterns: List of patterns to exclude
            include_hidden: Whether to include hidden files
            max_size_mb: Maximum file size in MB
            
        Returns:
            List of Path objects for files to process
        """
        collected_files = []
        
        for path_str in paths:
            path = Path(path_str)
            
            if path.is_file():
                if path.exists():
                    collected_files.append(path)
                else:
                    logger.warning(f"File not found: {path}")
                    
            elif path.is_dir():
                pattern = "**/*" if recursive else "*"
                for file_path in path.glob(pattern):
                    if file_path.is_file():
                        collected_files.append(file_path)
            else:
                logger.warning(f"Path not found: {path}")
        
        # Apply filters
        filtered_files = []
        for file_path in collected_files:
            # Skip hidden files if not included
            if not include_hidden and self._is_hidden_file(file_path):
                continue
            
            # Check include patterns
            if not self._matches_pattern(file_path, include_patterns):
                continue
            
            # Check exclude patterns
            if self._should_exclude_file(file_path, exclude_patterns):
                continue
            
            # Check file size
            if max_size_mb:
                try:
                    size_mb = file_path.stat().st_size / (1024 * 1024)
                    if size_mb > max_size_mb:
                        logger.info(f"Skipping large file ({size_mb:.1f}MB): {file_path}")
                        self.stats['skipped'] += 1
                        continue
                except Exception:
                    pass
            
            filtered_files.append(file_path)
        
        # Sort files for consistent output
        return sorted(set(filtered_files))

    def process_files(self, 
                     file_paths: List[Path],
                     output_file: Optional[str] = None,
                     include_metadata: bool = False,
                     add_separators: bool = True,
                     progress: bool = True) -> str:
        """
        Process multiple files and merge their contents.
        
        Args:
            file_paths: List of file paths to process
            output_file: Path to output file (optional)
            include_metadata: Whether to include file metadata
            add_separators: Whether to add separators between files
            progress: Whether to show progress
            
        Returns:
            Merged content of all processed files
        """
        self.stats['total_files'] = len(file_paths)
        self.stats['start_time'] = datetime.now()
        
        merged_content = ""
        
        if include_metadata:
            # Add header with processing info
            header = {
                'processed_at': self.stats['start_time'].isoformat(),
                'total_files': self.stats['total_files'],
                'merger_version': '2.0'
            }
            merged_content += f"<!-- Merge Metadata\n{json.dumps(header, indent=2)}\n-->\n\n"
        
        for i, file_path in enumerate(file_paths, start=1):
            if progress:
                print(f"Processing {i}/{len(file_paths)}: {file_path.name}", file=sys.stderr)
            
            try:
                content = self.converter.convert_file(str(file_path))
                
                if add_separators:
                    separator = f"\n{'='*60}\n"
                    file_header = f"FILE {i:02d}: {file_path.name}"
                    
                    if include_metadata:
                        metadata = self._get_file_metadata(file_path)
                        metadata_str = f" | Size: {metadata.get('size', 'unknown')} bytes | Modified: {metadata.get('modified', 'unknown')}"
                        file_header += metadata_str
                    
                    merged_content += f"{separator}{file_header}\n{separator}\n"
                
                merged_content += content
                
                if add_separators:
                    merged_content += "\n\n"
                
                self.processed_files.append(str(file_path))
                self.stats['processed'] += 1
                
            except Exception as e:
                error_msg = f"Error processing {file_path}: {str(e)}"
                logger.error(error_msg)
                self.failed_files.append((str(file_path), str(e)))
                self.stats['failed'] += 1
                
                if add_separators:
                    merged_content += f"\n{'='*60}\n"
                    merged_content += f"ERROR processing {file_path.name}: {str(e)}\n"
                    merged_content += f"{'='*60}\n\n"

        self.stats['end_time'] = datetime.now()
        
        # Add processing summary
        if include_metadata:
            summary = {
                'processing_completed': self.stats['end_time'].isoformat(),
                'duration_seconds': (self.stats['end_time'] - self.stats['start_time']).total_seconds(),
                'files_processed': self.stats['processed'],
                'files_failed': self.stats['failed'],
                'files_skipped': self.stats['skipped']
            }
            merged_content += f"\n\n<!-- Processing Summary\n{json.dumps(summary, indent=2)}\n-->\n"

        # Save to file if specified
        if output_file:
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(merged_content)
                print(f"Merged content saved to {output_file}")
            except Exception as e:
                logger.error(f"Failed to save to {output_file}: {e}")
                raise

        return merged_content

    def print_summary(self):
        """Print processing summary."""
        print(f"\n{'='*50}")
        print("PROCESSING SUMMARY")
        print(f"{'='*50}")
        print(f"Total files: {self.stats['total_files']}")
        print(f"Successfully processed: {self.stats['processed']}")
        print(f"Failed: {self.stats['failed']}")
        print(f"Skipped: {self.stats['skipped']}")
        
        if self.stats['start_time'] and self.stats['end_time']:
            duration = self.stats['end_time'] - self.stats['start_time']
            print(f"Processing time: {duration.total_seconds():.2f} seconds")
        
        if self.failed_files:
            print(f"\nFailed files:")
            for file_path, error in self.failed_files:
                print(f"  - {Path(file_path).name}: {error}")


def create_argument_parser():
    """Create and configure argument parser."""
    parser = argparse.ArgumentParser(
        description="Merge multiple files into a single text output with advanced filtering options.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Merge specific files
  python MergeFiles_converter.py file1.pdf file2.docx -o merged.txt
  
  # Process all files in a directory
  python MergeFiles_converter.py /path/to/docs/ -o merged.txt
  
  # Recursive processing with filters
  python MergeFiles_converter.py /path/to/docs/ -r --include "*.md" "*.txt" -o merged.txt
  
  # Exclude certain patterns
  python MergeFiles_converter.py /path/to/docs/ --exclude "*.log" "temp*" -o merged.txt
  
  # Include metadata and limit file size
  python MergeFiles_converter.py /path/to/docs/ --metadata --max-size 10 -o merged.txt
        """
    )
    
    parser.add_argument(
        'paths',
        nargs='+',
        help='File paths or directories to process'
    )
    
    parser.add_argument(
        '-o', '--output',
        help='Output file path (if not specified, prints to stdout)'
    )
    
    parser.add_argument(
        '-r', '--recursive',
        action='store_true',
        help='Process directories recursively'
    )
    
    parser.add_argument(
        '--include',
        nargs='*',
        default=[],
        help='Include only files matching these patterns (e.g., "*.txt" "*.md")'
    )
    
    parser.add_argument(
        '--exclude',
        nargs='*',
        default=[],
        help='Exclude files matching these patterns (e.g., "*.log" "temp*")'
    )
    
    parser.add_argument(
        '--hidden',
        action='store_true',
        help='Include hidden files (starting with .)'
    )
    
    parser.add_argument(
        '--max-size',
        type=float,
        help='Maximum file size in MB'
    )
    
    parser.add_argument(
        '--metadata',
        action='store_true',
        help='Include file metadata in output'
    )
    
    parser.add_argument(
        '--no-separators',
        action='store_true',
        help='Do not add separators between files'
    )
    
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Suppress progress output'
    )
    
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Set logging level'
    )
    
    return parser


def main():
    """Main function with enhanced argument parsing."""
    parser = create_argument_parser()
    
    # Handle legacy usage (backward compatibility)
    if len(sys.argv) >= 2 and not any(arg.startswith('-') for arg in sys.argv[1:]):
        # Legacy mode: treat all args as file paths, last one might be output
        if len(sys.argv) > 2:
            # Check if last argument looks like an output file
            last_arg = sys.argv[-1]
            if not os.path.exists(last_arg) and not os.path.isdir(os.path.dirname(last_arg) if os.path.dirname(last_arg) else '.'):
                # Looks like output file
                file_paths = sys.argv[1:-1]
                output_file = last_arg
            else:
                file_paths = sys.argv[1:]
                output_file = None
        else:
            file_paths = sys.argv[1:]
            output_file = None
        
        # Convert to Path objects and process
        merger = EnhancedMergeFiles()
        try:
            paths = [Path(p) for p in file_paths]
            merged_content = merger.process_files(paths, output_file)
            
            if not output_file:
                print(merged_content)
                
        except Exception as e:
            logger.error(f"Processing failed: {e}")
            sys.exit(1)
        
        return

    # Modern argument parsing
    args = parser.parse_args()
    
    # Set logging level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    try:
        merger = EnhancedMergeFiles()
        
        # Collect files with filtering
        file_paths = merger.collect_files(
            paths=args.paths,
            recursive=args.recursive,
            include_patterns=args.include if args.include else None,
            exclude_patterns=args.exclude if args.exclude else None,
            include_hidden=args.hidden,
            max_size_mb=args.max_size
        )
        
        if not file_paths:
            print("No files found matching the criteria.")
            sys.exit(1)
        
        print(f"Found {len(file_paths)} files to process", file=sys.stderr)
        
        # Process files
        merged_content = merger.process_files(
            file_paths=file_paths,
            output_file=args.output,
            include_metadata=args.metadata,
            add_separators=not args.no_separators,
            progress=not args.quiet
        )
        
        # Print to stdout if no output file specified
        if not args.output:
            print(merged_content)
        
        # Print summary
        if not args.quiet:
            merger.print_summary()
            
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        sys.exit(1)


# Backward compatibility functions
def process_files(file_paths, output_file=None):
    """Legacy function for backward compatibility."""
    merger = EnhancedMergeFiles()
    paths = [Path(p) for p in file_paths]
    return merger.process_files(paths, output_file, add_separators=True, progress=False)


if __name__ == "__main__":
    main()