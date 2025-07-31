#!/usr/bin/env python3
"""
Enhanced Video File Converter

This script converts video files to text using multiple extraction methods:
- Audio transcription using Whisper (OpenAI's speech recognition)
- OCR on video frames for text overlays
- Subtitle extraction from embedded subtitles
- GPU acceleration when available

Enhanced for Fabric integration with better error handling, progress tracking,
and multiple output formats.

Usage:
    python3 videofile_converter.py <input_file> [<output_file>] [options]
"""

import os
import sys
import time
import logging
import argparse
import tempfile
import subprocess
import signal
import urllib.parse
from pathlib import Path
from typing import Optional, Dict, List, Tuple
import json
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Catch broken pipe error and exit silently
signal.signal(signal.SIGPIPE, signal.SIG_DFL)


class VideoFileConverter:
    """Enhanced video file converter with multiple extraction methods."""
    
    def __init__(self):
        self.temp_files = []
        self.supported_video_formats = {
            '.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', 
            '.m4v', '.3gp', '.ogv', '.ts', '.mts', '.m2ts'
        }
        self.extraction_methods = {
            'whisper': self._extract_audio_whisper,
            'ocr': self._extract_text_ocr,
            'subtitles': self._extract_subtitles,
            'combined': self._extract_combined
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

    def _install_package(self, package_name: str) -> bool:
        """Install a package using pip."""
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", package_name],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to install {package_name}: {e}")
            return False

    def _lazy_import(self, package_name: str, module_name: str = None, retry_count: int = 3):
        """Lazily import a module, installing it if necessary."""
        if module_name is None:
            module_name = package_name

        try:
            return __import__(module_name)
        except ImportError:
            logger.info(f"{package_name} not found, attempting to install...")
            if self._install_package(package_name):
                for _ in range(retry_count):
                    time.sleep(1)
                    try:
                        return __import__(module_name)
                    except ImportError:
                        continue
            logger.error(f"Failed to import {module_name} after installation.")
            return None

    def _is_url(self, input_string: str) -> bool:
        """Check if the input string is a valid URL."""
        parsed = urllib.parse.urlparse(input_string)
        return all([parsed.scheme, parsed.netloc])

    def _download_video(self, url: str) -> str:
        """Download video from URL using yt-dlp."""
        yt_dlp = self._lazy_import('yt-dlp')
        if not yt_dlp:
            raise ImportError("yt-dlp is required for URL downloads")

        try:
            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp_file:
                output_path = tmp_file.name
                self.temp_files.append(output_path)

            # Configure yt-dlp options
            ydl_opts = {
                'outtmpl': output_path,
                'format': 'best[ext=mp4]/best',
                'quiet': True,
                'no_warnings': True,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            return output_path

        except Exception as e:
            logger.error(f"Failed to download video from {url}: {e}")
            raise

    def _extract_audio(self, video_path: str, duration_limit: Optional[int] = None) -> str:
        """Extract audio from video file using ffmpeg."""
        try:
            # Check if ffmpeg is available
            subprocess.run(['ffmpeg', '-version'], 
                         stdout=subprocess.DEVNULL, 
                         stderr=subprocess.DEVNULL, 
                         check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise RuntimeError("ffmpeg is not installed or not in PATH")

        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
            audio_path = tmp_file.name
            self.temp_files.append(audio_path)

        # Build ffmpeg command
        cmd = ['ffmpeg', '-i', video_path]
        
        if duration_limit:
            cmd.extend(['-t', str(duration_limit)])
        
        cmd.extend([
            '-vn',  # No video
            '-acodec', 'pcm_s16le',  # 16-bit PCM
            '-ar', '16000',  # 16kHz sample rate for Whisper
            '-ac', '1',  # Mono
            '-y',  # Overwrite output file
            audio_path
        ])

        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return audio_path
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to extract audio: {e}")
            raise

    def _extract_audio_whisper(self, video_path: str, **kwargs) -> Dict:
        """Extract text from video using Whisper speech recognition."""
        whisper = self._lazy_import('openai-whisper', 'whisper')
        if not whisper:
            raise ImportError("openai-whisper is required for audio transcription")

        try:
            # Extract audio
            duration_limit = kwargs.get('duration_limit', None)
            audio_path = self._extract_audio(video_path, duration_limit)
            
            # Load Whisper model
            model_size = kwargs.get('whisper_model', 'base')
            logger.info(f"Loading Whisper model: {model_size}")
            model = whisper.load_model(model_size)
            
            # Transcribe audio
            logger.info("Transcribing audio...")
            result = model.transcribe(audio_path)
            
            return {
                'method': 'whisper',
                'text': result['text'],
                'segments': result.get('segments', []),
                'language': result.get('language', 'unknown')
            }
            
        except Exception as e:
            logger.error(f"Whisper transcription failed: {e}")
            raise

    def _extract_frames(self, video_path: str, interval: int = 30) -> List[str]:
        """Extract frames from video at specified intervals."""
        frame_paths = []
        
        try:
            # Get video duration
            cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json',
                '-show_format', video_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            duration = float(json.loads(result.stdout)['format']['duration'])
            
            # Extract frames at intervals
            for timestamp in range(0, int(duration), interval):
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                    frame_path = tmp_file.name
                    self.temp_files.append(frame_path)
                    frame_paths.append(frame_path)
                
                cmd = [
                    'ffmpeg', '-ss', str(timestamp), '-i', video_path,
                    '-frames:v', '1', '-y', frame_path
                ]
                subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            return frame_paths
            
        except Exception as e:
            logger.error(f"Frame extraction failed: {e}")
            return []

    def _extract_text_ocr(self, video_path: str, **kwargs) -> Dict:
        """Extract text from video frames using OCR."""
        pytesseract = self._lazy_import('pytesseract')
        PIL = self._lazy_import('Pillow', 'PIL')
        
        if not pytesseract or not PIL:
            raise ImportError("pytesseract and Pillow are required for OCR")

        try:
            interval = kwargs.get('frame_interval', 30)
            frame_paths = self._extract_frames(video_path, interval)
            
            if not frame_paths:
                return {'method': 'ocr', 'text': '', 'frames_processed': 0}
            
            extracted_text = []
            processed_frames = 0
            
            for i, frame_path in enumerate(frame_paths):
                try:
                    image = PIL.Image.open(frame_path)
                    text = pytesseract.image_to_string(image, config='--psm 6')
                    
                    if text.strip():
                        timestamp = i * interval
                        extracted_text.append(f"[Frame {timestamp}s]: {text.strip()}")
                    
                    processed_frames += 1
                    
                except Exception as e:
                    logger.warning(f"OCR failed for frame {frame_path}: {e}")
                    continue
            
            return {
                'method': 'ocr',
                'text': '\n\n'.join(extracted_text),
                'frames_processed': processed_frames
            }
            
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            raise

    def _extract_subtitles(self, video_path: str, **kwargs) -> Dict:
        """Extract embedded subtitles from video."""
        try:
            # Try to extract subtitles using ffmpeg
            with tempfile.NamedTemporaryFile(suffix='.srt', delete=False, mode='w') as tmp_file:
                subtitle_path = tmp_file.name
                self.temp_files.append(subtitle_path)
            
            cmd = ['ffmpeg', '-i', video_path, '-c:s', 'srt', '-y', subtitle_path]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0 and os.path.exists(subtitle_path):
                with open(subtitle_path, 'r', encoding='utf-8') as f:
                    subtitle_content = f.read()
                
                # Clean up SRT formatting
                lines = subtitle_content.split('\n')
                text_lines = []
                for line in lines:
                    line = line.strip()
                    if line and not line.isdigit() and '-->' not in line:
                        text_lines.append(line)
                
                return {
                    'method': 'subtitles',
                    'text': '\n'.join(text_lines),
                    'raw_subtitles': subtitle_content
                }
            else:
                return {'method': 'subtitles', 'text': '', 'error': 'No subtitles found'}
                
        except Exception as e:
            logger.error(f"Subtitle extraction failed: {e}")
            return {'method': 'subtitles', 'text': '', 'error': str(e)}

    def _extract_combined(self, video_path: str, **kwargs) -> Dict:
        """Extract text using all available methods and combine results."""
        results = {}
        combined_text = []
        
        # Try Whisper transcription
        try:
            whisper_result = self._extract_audio_whisper(video_path, **kwargs)
            results['whisper'] = whisper_result
            if whisper_result['text'].strip():
                combined_text.append("=== AUDIO TRANSCRIPTION (Whisper) ===")
                combined_text.append(whisper_result['text'])
                combined_text.append("")
        except Exception as e:
            logger.warning(f"Whisper extraction failed: {e}")
            results['whisper'] = {'error': str(e)}
        
        # Try subtitle extraction
        try:
            subtitle_result = self._extract_subtitles(video_path, **kwargs)
            results['subtitles'] = subtitle_result
            if subtitle_result['text'].strip():
                combined_text.append("=== EMBEDDED SUBTITLES ===")
                combined_text.append(subtitle_result['text'])
                combined_text.append("")
        except Exception as e:
            logger.warning(f"Subtitle extraction failed: {e}")
            results['subtitles'] = {'error': str(e)}
        
        # Try OCR extraction (only if other methods failed or produced little text)
        total_text_length = sum(len(results.get(method, {}).get('text', '')) 
                              for method in ['whisper', 'subtitles'])
        
        if total_text_length < 500:  # If we don't have much text, try OCR
            try:
                ocr_result = self._extract_text_ocr(video_path, **kwargs)
                results['ocr'] = ocr_result
                if ocr_result['text'].strip():
                    combined_text.append("=== VISUAL TEXT (OCR) ===")
                    combined_text.append(ocr_result['text'])
                    combined_text.append("")
            except Exception as e:
                logger.warning(f"OCR extraction failed: {e}")
                results['ocr'] = {'error': str(e)}
        
        return {
            'method': 'combined',
            'text': '\n'.join(combined_text),
            'individual_results': results
        }

    def convert_video_to_text(self, 
                            input_file: str, 
                            method: str = 'combined',
                            **kwargs) -> Dict:
        """
        Convert video to text using specified method.
        
        Args:
            input_file: Path to video file or URL
            method: Extraction method ('whisper', 'ocr', 'subtitles', 'combined')
            **kwargs: Additional options for extraction methods
            
        Returns:
            Dictionary with extracted text and metadata
        """
        try:
            # Handle URL downloads
            if self._is_url(input_file):
                logger.info(f"Downloading video from URL: {input_file}")
                video_path = self._download_video(input_file)
            else:
                video_path = input_file
                if not os.path.exists(video_path):
                    raise FileNotFoundError(f"Video file not found: {video_path}")
            
            # Check if file is a supported video format
            file_ext = Path(video_path).suffix.lower()
            if file_ext not in self.supported_video_formats:
                logger.warning(f"Unsupported video format: {file_ext}")
            
            # Extract text using specified method
            if method not in self.extraction_methods:
                raise ValueError(f"Unsupported extraction method: {method}")
            
            logger.info(f"Processing video with method: {method}")
            result = self.extraction_methods[method](video_path, **kwargs)
            
            # Add metadata
            result.update({
                'source_file': input_file,
                'processed_at': datetime.now().isoformat(),
                'file_size': os.path.getsize(video_path) if os.path.exists(video_path) else None
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Video conversion failed: {e}")
            raise
        finally:
            self._cleanup_temp_files()


def create_argument_parser():
    """Create argument parser for command line interface."""
    parser = argparse.ArgumentParser(
        description="Convert video files to text using multiple extraction methods",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic transcription using Whisper
  python videofile_converter.py video.mp4 output.txt
  
  # Use specific method
  python videofile_converter.py video.mp4 -m whisper -o output.txt
  
  # Extract from YouTube URL
  python videofile_converter.py "https://youtube.com/watch?v=..." -o transcript.txt
  
  # Use all methods combined
  python videofile_converter.py video.mp4 -m combined -o complete_output.txt
  
  # Limit duration and use larger Whisper model
  python videofile_converter.py video.mp4 --duration 300 --whisper-model medium
        """
    )
    
    parser.add_argument(
        'input_file',
        help='Video file path or URL'
    )
    
    parser.add_argument(
        'output_file',
        nargs='?',
        help='Output text file (optional, prints to stdout if not specified)'
    )
    
    parser.add_argument(
        '-m', '--method',
        choices=['whisper', 'ocr', 'subtitles', 'combined'],
        default='combined',
        help='Text extraction method (default: combined)'
    )
    
    parser.add_argument(
        '-o', '--output',
        help='Output file (alternative to positional argument)'
    )
    
    parser.add_argument(
        '--whisper-model',
        choices=['tiny', 'base', 'small', 'medium', 'large'],
        default='base',
        help='Whisper model size (default: base)'
    )
    
    parser.add_argument(
        '--duration',
        type=int,
        help='Limit processing to first N seconds of video'
    )
    
    parser.add_argument(
        '--frame-interval',
        type=int,
        default=30,
        help='Interval between frames for OCR (seconds, default: 30)'
    )
    
    parser.add_argument(
        '--format',
        choices=['text', 'json'],
        default='text',
        help='Output format (default: text)'
    )
    
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Set logging level (default: INFO)'
    )
    
    return parser


def main():
    """Main function for command line interface."""
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # Set logging level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # Determine output file
    output_file = args.output or args.output_file
    
    try:
        converter = VideoFileConverter()
        
        # Prepare extraction options
        extraction_options = {
            'whisper_model': args.whisper_model,
            'duration_limit': args.duration,
            'frame_interval': args.frame_interval
        }
        
        # Convert video to text
        start_time = time.time()
        result = converter.convert_video_to_text(
            args.input_file, 
            method=args.method,
            **extraction_options
        )
        processing_time = time.time() - start_time
        
        # Format output
        if args.format == 'json':
            output_content = json.dumps(result, indent=2, ensure_ascii=False)
        else:
            output_content = result.get('text', '')
            if args.method == 'combined' and args.log_level == 'INFO':
                # Add processing summary for combined method
                individual_results = result.get('individual_results', {})
                summary_lines = [
                    f"\n{'='*50}",
                    "PROCESSING SUMMARY",
                    f"{'='*50}",
                    f"Processing time: {processing_time:.2f} seconds",
                    f"Methods used: {', '.join(individual_results.keys())}",
                ]
                
                for method, method_result in individual_results.items():
                    if 'error' in method_result:
                        summary_lines.append(f"{method.capitalize()}: Failed ({method_result['error']})")
                    else:
                        text_length = len(method_result.get('text', ''))
                        summary_lines.append(f"{method.capitalize()}: {text_length} characters extracted")
                
                output_content += '\n'.join(summary_lines)
        
        # Save or print output
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(output_content)
            print(f"Text extracted and saved to {output_file}")
        else:
            print(output_content)
            
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()