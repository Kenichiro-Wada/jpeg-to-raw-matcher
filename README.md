# RAW-JPEG Matcher Tool

A Python command-line tool that efficiently finds and copies RAW camera files corresponding to JPEG files. Designed for photographers who need to collect RAW files that match their selected JPEG images.

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://python.org)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

## Features

- **Accurate Matching**: Matches files by both filename and EXIF capture datetime for precision
- **High Performance**: Pre-indexes RAW files for fast matching operations on large collections
- **Cross-Platform**: Works seamlessly on macOS and Windows
- **Comprehensive Format Support**: Supports all major camera RAW formats (Canon, Nikon, Sony, Fujifilm, etc.)
- **Robust Error Handling**: Continues processing even when individual files fail
- **Detailed Logging**: Provides comprehensive progress reports and error summaries

## Installation

### Prerequisites

This tool requires **ExifTool** to be installed on your system for reading EXIF metadata from RAW files.

#### Installing ExifTool

**macOS (using Homebrew):**
```bash
brew install exiftool
```

**Windows:**
1. Download ExifTool from [https://exiftool.org/](https://exiftool.org/)
2. Extract `exiftool.exe` to a directory in your PATH (e.g., `C:\Windows\System32`)

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get install libimage-exiftool-perl
```

### Installing RAW-JPEG Matcher Tool

#### From Source

1. Clone the repository:
```bash
git clone <repository-url>
cd raw-jpeg-matcher
```

2. Install the package:
```bash
pip install -e .
```

3. For development with testing dependencies:
```bash
pip install -e ".[test]"
```

#### Using pip (when published)

```bash
pip install raw-jpeg-matcher
```

## Usage

The tool provides four main commands: `index`, `match`, `list-index`, and `clear-cache`.

### Basic Workflow

1. **Index your RAW files** (one-time setup per directory):
```bash
raw-jpeg-matcher index /path/to/your/raw/files
```

2. **Match and copy RAW files** for your selected JPEGs:
```bash
raw-jpeg-matcher match /path/to/your/jpeg/files
```

### Command Reference

#### `index` - Create RAW File Index

Creates or updates an index of RAW files in the specified directory.

```bash
# Basic usage
raw-jpeg-matcher index /path/to/raw/files

# Don't search subdirectories
raw-jpeg-matcher index /path/to/raw/files --no-recursive

# Show detailed progress
raw-jpeg-matcher index /path/to/raw/files --verbose

# Force complete rebuild of index
raw-jpeg-matcher index /path/to/raw/files --force-rebuild
```

**Options:**
- `--no-recursive, -nr`: Don't search subdirectories (default: recursive)
- `--verbose, -v`: Show detailed logging
- `--force-rebuild, -f`: Force complete rebuild of the index

#### `match` - Find and Copy Matching RAW Files

Finds RAW files that match JPEG files and copies them to the same directory.

```bash
# Basic usage
raw-jpeg-matcher match /path/to/jpeg/files

# Don't search subdirectories
raw-jpeg-matcher match /path/to/jpeg/files --no-recursive

# Show detailed progress
raw-jpeg-matcher match /path/to/jpeg/files --verbose

# Only use RAW files from specific source
raw-jpeg-matcher match /path/to/jpeg/files --source-filter /path/to/specific/raw/source
```

**Options:**
- `--no-recursive, -nr`: Don't search subdirectories (default: recursive)
- `--verbose, -v`: Show detailed logging
- `--source-filter, -s`: Only use RAW files from specified source directory

#### `list-index` - Show Indexed Directories

Displays information about currently indexed directories.

```bash
# Basic listing
raw-jpeg-matcher list-index

# Show detailed information
raw-jpeg-matcher list-index --verbose
```

#### `clear-cache` - Clear Index Cache

Removes cached index data.

```bash
# Clear all cached indexes
raw-jpeg-matcher clear-cache

# Clear cache for specific directory only
raw-jpeg-matcher clear-cache --source /path/to/raw/files
```

### Examples

#### Example 1: Basic Usage

```bash
# Step 1: Index your RAW files (do this once per RAW directory)
raw-jpeg-matcher index ~/Photos/2024/RAW_Files

# Step 2: Copy RAW files for selected JPEGs
raw-jpeg-matcher match ~/Photos/2024/Selected_JPEGs
```

#### Example 2: Multiple RAW Sources

```bash
# Index multiple RAW directories
raw-jpeg-matcher index ~/Photos/2024/Camera1_RAW
raw-jpeg-matcher index ~/Photos/2024/Camera2_RAW

# Match will search all indexed directories
raw-jpeg-matcher match ~/Photos/2024/Selected_JPEGs
```

#### Example 3: Specific Source Filtering

```bash
# Only use RAW files from Camera1 for matching
raw-jpeg-matcher match ~/Photos/2024/Selected_JPEGs --source-filter ~/Photos/2024/Camera1_RAW
```

## Supported File Formats

### RAW Formats
- **Canon**: .CR2, .CR3
- **Nikon**: .NEF
- **Sony**: .ARW
- **Fujifilm**: .RAF
- **Olympus**: .ORF
- **Panasonic**: .RW2
- **Pentax**: .PEF
- **Leica**: .DNG, .RWL
- **Hasselblad**: .3FR
- **Phase One**: .IIQ
- **Adobe**: .DNG

### JPEG Formats
- .jpg, .jpeg (case-insensitive)

## How It Works

1. **Indexing Phase**: The tool scans RAW directories and creates an index containing:
   - Base filename (without extension)
   - Full file path
   - EXIF capture datetime
   - File metadata

2. **Matching Phase**: For each JPEG file:
   - Extracts base filename and EXIF capture datetime
   - Searches the index for RAW files with matching base filename
   - Verifies the match using EXIF capture datetime
   - Only files with identical capture times are considered matches

3. **Copying Phase**: Matched RAW files are copied to the JPEG directory with:
   - Original filename preserved
   - Existing files skipped (no overwrite)
   - Detailed progress reporting

## Configuration

The tool stores index cache files in `~/.raw_jpeg_matcher/cache/`. This directory is created automatically and can be safely deleted to clear all cached data.

## Troubleshooting

### ExifTool Not Found
```
❌ 処理エラー: ExifTool not found. Please install ExifTool first.
```
**Solution**: Install ExifTool following the installation instructions above.

### No Index Found
```
⚠️  Warning: No index found for matching. Please run 'index' command first.
```
**Solution**: Run the `index` command on your RAW directories before matching.

### Permission Errors
```
❌ 処理エラー: Permission denied accessing directory
```
**Solution**: Ensure you have read permissions for source directories and write permissions for target directories.

## Development

### Running Tests

```bash
# Install test dependencies
pip install -e ".[test]"

# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run property-based tests
pytest tests/test_*_properties.py -v
```

### Project Structure

```
raw-jpeg-matcher/
├── src/                    # Main source code
│   ├── cli.py             # Command-line interface
│   ├── index_manager.py   # Index management
│   ├── match_manager.py   # Matching workflow
│   ├── indexer.py         # RAW file indexing
│   ├── matcher.py         # File matching logic
│   ├── copier.py          # File copying operations
│   ├── exif_reader.py     # EXIF metadata reading
│   ├── file_scanner.py    # Directory scanning
│   └── path_validator.py  # Path validation
├── tests/                 # Test suite
└── pyproject.toml         # Project configuration
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Run the test suite (`pytest`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [ExifTool](https://exiftool.org/) by Phil Harvey for comprehensive EXIF metadata support
- The Python community for excellent libraries and tools
