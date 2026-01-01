# Video Editor - Unit Tests

This directory contains unit tests for the Video Editor application.

## Running Tests

### Run all tests:
```bash
python -m pytest tests/
```

Or from the project root:
```bash
cd tests
python -m pytest .
```

### Run specific test file:
```bash
python -m pytest tests/test_VideoInfo.py
```

### Run with verbose output:
```bash
python -m pytest tests/ -v
```

### Run with coverage:
```bash
python -m pytest tests/ --cov=src/models --cov-report=html
```

### Run individual test file directly:
```bash
python tests/test_VideoInfo.py
```

**Note:** The test files automatically add the project root to Python's path, so they can be run directly or via pytest.

## Test Structure

- `test_VideoInfo.py` - Tests for video metadata extraction
- `test_FFmpegCommandBuilder.py` - Tests for FFmpeg command construction
- `test_ConfigManager.py` - Tests for configuration management
- `test_constants.py` - Tests for constants validation

## Requirements

Install pytest for running tests:
```bash
pip install pytest pytest-cov
```

## Note

Some tests use mocking to avoid requiring actual video files or FFmpeg installation.
Tests that require FFmpeg should be marked as integration tests.

