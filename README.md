# BDF Property Updater

A standalone PyQt5 GUI application for updating Nastran BDF shell (PSHELL) and bar (PBARL) properties from CSV files.

## Features

- **Load BDF Files**: Load Nastran BDF files with full INCLUDE statement support
- **Update Shell Properties**: Update PSHELL thickness values from CSV
- **Update Bar Properties**: Update PBARL rectangular section dimensions from CSV
- **Preview Changes**: Review proposed changes before applying
- **Write BDFs**: Preserve INCLUDE file structure with `write_bdfs()` method
- **Comprehensive Logging**: Track all operations with detailed log output

## Installation

### Requirements

- Python 3.8+
- pyNastran >= 1.3.4
- PyQt5 >= 5.15.0
- pandas >= 1.3.0

### Install from source

```bash
pip install -r requirements.txt
```

Or install as a package:

```bash
pip install .
```

## Usage

### Running the GUI

```bash
python bdf_updater_gui.py
```

Or if installed as a package:

```bash
bdf-updater
```

### CSV File Formats

#### Shell Properties CSV

Format: `property_id, thickness`

```csv
property_id,thickness
101,0.008
102,0.012
103,0.005
```

#### Bar Properties CSV (Rectangular PBARL only)

Format: `property_id, height, width`

```csv
property_id,height,width
201,0.15,0.08
202,0.07,0.035
203,0.09,0.045
```

**Note**: Headers are optional. The first row will be treated as data if it contains valid numeric values.

### Using the Application

1. **Load BDF File**: Click "Browse..." next to "BDF File" and select your Nastran BDF file
2. **Click "Load BDF"**: This loads the file and displays current properties
3. **Load CSV Files**: Select your shell and/or bar property CSV files
4. **Click "Load CSV Files"**: This parses the CSV files for updates
5. **Preview Changes**: Click "Preview Changes" to see what will be modified
6. **Apply & Save**: Click "Apply & Save" to apply changes and save the updated BDF

### Write BDFs Option

The "Use write_bdfs()" checkbox (checked by default) preserves the INCLUDE file structure when saving. If your BDF file uses INCLUDE statements to reference sub-BDF files, this option ensures the structure is maintained.

## Programmatic Usage

You can also use the processor module directly in Python:

```python
from bdf_processor import BDFProcessor, ShellPropertyUpdate, BarPropertyUpdate

# Create processor and load BDF
processor = BDFProcessor()
processor.load_bdf("model.bdf")

# View current properties
shell_props = processor.get_shell_properties()
bar_props = processor.get_bar_properties()

# Parse CSV files
shell_updates = BDFProcessor.parse_shell_csv("shell_updates.csv")
bar_updates = BDFProcessor.parse_bar_csv("bar_updates.csv")

# Preview changes
preview = processor.preview_changes(shell_updates=shell_updates, bar_updates=bar_updates)

# Apply updates
processor.apply_shell_updates(shell_updates)
processor.apply_bar_updates(bar_updates)

# Get summary
summary = processor.get_update_summary()
print(f"Updated {summary['successful']} properties")

# Save with INCLUDE support
processor.save_bdf("model_updated.bdf", use_write_bdfs=True)
```

## Testing

Run the test suite:

```bash
pytest
```

Run with coverage:

```bash
pytest --cov=. --cov-report=html
```

Run specific test categories:

```bash
# Only unit tests
pytest tests/test_bdf_processor.py tests/test_csv_parsing.py

# Only GUI tests
pytest tests/test_gui.py

# Only integration tests
pytest tests/test_integration.py
```

## Project Structure

```
bdf_updater/
├── __init__.py           # Package initialization
├── bdf_processor.py      # Core BDF processing logic
├── bdf_updater_gui.py    # PyQt5 GUI application
├── requirements.txt      # Dependencies
├── setup.py              # Package setup
├── pytest.ini            # Pytest configuration
├── README.md             # This file
├── tests/
│   ├── __init__.py
│   ├── conftest.py       # Pytest fixtures
│   ├── test_bdf_processor.py
│   ├── test_csv_parsing.py
│   ├── test_gui.py
│   └── test_integration.py
└── test_data/
    ├── sample.bdf
    ├── main_with_include.bdf
    ├── properties.bdf
    ├── shell_updates.csv
    ├── bar_updates.csv
    └── ... (other test files)
```

## License

MIT License
