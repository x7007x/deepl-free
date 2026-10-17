# DeepL Free

[![PyPI version](https://badge.fury.io/py/deepl-free.svg)](https://pypi.org/project/deepl-free/)
[![GitHub stars](https://img.shields.io/github/stars/x7007x/deepl-free?style=social)](https://github.com/x7007x/deepl-free)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

Translate text and documents with DeepL — no login, no API key required.

## Features

- No authentication or API keys needed
- Automatic source language detection
- 39 languages supported
- Document translation (PDF, DOCX, PPTX)
- Lightweight: only depends on `requests`

## Installation

```bash
pip install deepl-free
```

## Usage

```python
from deepl_free import DeepL

d = DeepL()

d.translate("Hello world", target="es")
# Hola mundo

d.translate("مرحبا بالعالم", target="en")
# Hello world (source auto-detected)

d.translate("Good morning", target="ar", source="en")
# صباح الخير

d.detect("Bonjour le monde")
# FR

data = d.translate_file("report.pdf", target="ar")
open("report_ar.pdf", "wb").write(data)
```

### `translate(text, target="en", source="auto")`

| Argument | Description                              | Default  |
|----------|------------------------------------------|----------|
| `text`   | Text to translate                        | —        |
| `target` | Target language code or name (e.g. `es`) | `"en"`   |
| `source` | Source language code or name, or `"auto"`| `"auto"` |

### `translate_file(path, target="en", source="auto")`

Translates a document (PDF, DOCX, PPTX) and returns the translated file as bytes.

| Argument | Description                              | Default  |
|----------|------------------------------------------|----------|
| `path`   | Path to the document                     | —        |
| `target` | Target language code or name             | `"en"`   |
| `source` | Source language code or name, or `"auto"`| `"auto"` |

### `detect(text)`

Returns the detected source language code (e.g. `FR`).

### `languages()`

Returns a dict mapping language codes to language names.

## How it works

The library replicates DeepL's public web flows — language tables are
extracted at runtime and document uploads use the same endpoints as the
web translator — nothing for you to configure.

## License

MIT
