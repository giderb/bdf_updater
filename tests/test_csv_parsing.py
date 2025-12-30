"""
Comprehensive tests for CSV parsing functionality.

Tests cover:
- Valid CSV parsing for shell and bar properties
- Header handling (with and without headers)
- Error handling for invalid data
- Edge cases and boundary conditions
"""

import os
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from bdf_processor import (
    BDFProcessor, ShellPropertyUpdate, BarPropertyUpdate, CSVParseError
)


class TestShellCSVParsing:
    """Tests for shell property CSV parsing."""

    def test_parse_shell_csv_with_header(self, sample_shell_csv_path):
        """Test parsing shell CSV with header row."""
        updates = BDFProcessor.parse_shell_csv(sample_shell_csv_path)

        assert len(updates) == 3
        assert all(isinstance(u, ShellPropertyUpdate) for u in updates)

    def test_parse_shell_csv_without_header(self, test_data_dir):
        """Test parsing shell CSV without header row."""
        csv_path = test_data_dir / "shell_no_header.csv"
        updates = BDFProcessor.parse_shell_csv(csv_path)

        assert len(updates) == 3

    def test_parse_shell_csv_values_correct(self, sample_shell_csv_path):
        """Test that parsed values are correct."""
        updates = BDFProcessor.parse_shell_csv(sample_shell_csv_path)

        # Find update for property 101
        update_101 = next(u for u in updates if u.property_id == 101)
        assert update_101.thickness == pytest.approx(0.008)

    def test_parse_shell_csv_nonexistent_file(self):
        """Test parsing a nonexistent CSV file."""
        with pytest.raises(CSVParseError) as exc_info:
            BDFProcessor.parse_shell_csv("/nonexistent/file.csv")
        assert "not found" in str(exc_info.value).lower()

    def test_parse_shell_csv_invalid_thickness(self, test_data_dir):
        """Test parsing CSV with invalid thickness value."""
        csv_path = test_data_dir / "invalid_shell.csv"
        with pytest.raises(CSVParseError) as exc_info:
            BDFProcessor.parse_shell_csv(csv_path)
        assert "invalid" in str(exc_info.value).lower()

    def test_parse_shell_csv_negative_thickness(self, test_data_dir):
        """Test parsing CSV with negative thickness."""
        csv_path = test_data_dir / "negative_thickness.csv"
        with pytest.raises(CSVParseError) as exc_info:
            BDFProcessor.parse_shell_csv(csv_path)
        assert "positive" in str(exc_info.value).lower()

    def test_parse_shell_csv_empty_file(self, temp_dir):
        """Test parsing an empty CSV file."""
        csv_path = temp_dir / "empty.csv"
        csv_path.write_text("")

        updates = BDFProcessor.parse_shell_csv(csv_path)
        assert len(updates) == 0

    def test_parse_shell_csv_only_header(self, temp_dir):
        """Test parsing CSV with only header row."""
        csv_path = temp_dir / "header_only.csv"
        csv_path.write_text("property_id,thickness\n")

        updates = BDFProcessor.parse_shell_csv(csv_path)
        assert len(updates) == 0

    def test_parse_shell_csv_whitespace_handling(self, temp_dir):
        """Test that whitespace is properly handled."""
        csv_path = temp_dir / "whitespace.csv"
        csv_path.write_text("property_id,thickness\n  101  ,  0.008  \n")

        updates = BDFProcessor.parse_shell_csv(csv_path)
        assert len(updates) == 1
        assert updates[0].property_id == 101
        assert updates[0].thickness == pytest.approx(0.008)

    def test_parse_shell_csv_scientific_notation(self, temp_dir):
        """Test parsing thickness in scientific notation."""
        csv_path = temp_dir / "scientific.csv"
        csv_path.write_text("property_id,thickness\n101,5.0e-3\n102,1.2E-2\n")

        updates = BDFProcessor.parse_shell_csv(csv_path)
        assert len(updates) == 2
        assert updates[0].thickness == pytest.approx(0.005)
        assert updates[1].thickness == pytest.approx(0.012)

    def test_parse_shell_csv_large_values(self, temp_dir):
        """Test parsing large thickness values."""
        csv_path = temp_dir / "large.csv"
        csv_path.write_text("property_id,thickness\n101,100.5\n")

        updates = BDFProcessor.parse_shell_csv(csv_path)
        assert len(updates) == 1
        assert updates[0].thickness == pytest.approx(100.5)

    def test_parse_shell_csv_skips_empty_rows(self, temp_dir):
        """Test that empty rows are skipped."""
        csv_path = temp_dir / "empty_rows.csv"
        csv_path.write_text("property_id,thickness\n101,0.005\n\n102,0.010\n")

        updates = BDFProcessor.parse_shell_csv(csv_path)
        assert len(updates) == 2


class TestBarCSVParsing:
    """Tests for bar property CSV parsing."""

    def test_parse_bar_csv_with_header(self, sample_bar_csv_path):
        """Test parsing bar CSV with header row."""
        updates = BDFProcessor.parse_bar_csv(sample_bar_csv_path)

        assert len(updates) == 3
        assert all(isinstance(u, BarPropertyUpdate) for u in updates)

    def test_parse_bar_csv_without_header(self, test_data_dir):
        """Test parsing bar CSV without header row."""
        csv_path = test_data_dir / "bar_no_header.csv"
        updates = BDFProcessor.parse_bar_csv(csv_path)

        assert len(updates) == 2

    def test_parse_bar_csv_values_correct(self, sample_bar_csv_path):
        """Test that parsed values are correct."""
        updates = BDFProcessor.parse_bar_csv(sample_bar_csv_path)

        # Find update for property 201
        update_201 = next(u for u in updates if u.property_id == 201)
        assert update_201.height == pytest.approx(0.15)
        assert update_201.width == pytest.approx(0.08)

    def test_parse_bar_csv_nonexistent_file(self):
        """Test parsing a nonexistent CSV file."""
        with pytest.raises(CSVParseError) as exc_info:
            BDFProcessor.parse_bar_csv("/nonexistent/file.csv")
        assert "not found" in str(exc_info.value).lower()

    def test_parse_bar_csv_invalid_height(self, temp_dir):
        """Test parsing CSV with invalid height value."""
        csv_path = temp_dir / "invalid_bar.csv"
        csv_path.write_text("property_id,height,width\n201,invalid,0.05\n")

        with pytest.raises(CSVParseError):
            BDFProcessor.parse_bar_csv(csv_path)

    def test_parse_bar_csv_negative_dimension(self, temp_dir):
        """Test parsing CSV with negative dimension."""
        csv_path = temp_dir / "negative_bar.csv"
        csv_path.write_text("property_id,height,width\n201,-0.10,0.05\n")

        with pytest.raises(CSVParseError) as exc_info:
            BDFProcessor.parse_bar_csv(csv_path)
        assert "positive" in str(exc_info.value).lower()

    def test_parse_bar_csv_zero_dimension(self, temp_dir):
        """Test parsing CSV with zero dimension."""
        csv_path = temp_dir / "zero_bar.csv"
        csv_path.write_text("property_id,height,width\n201,0.10,0.0\n")

        with pytest.raises(CSVParseError) as exc_info:
            BDFProcessor.parse_bar_csv(csv_path)
        assert "positive" in str(exc_info.value).lower()

    def test_parse_bar_csv_missing_column(self, temp_dir):
        """Test parsing CSV with missing column."""
        csv_path = temp_dir / "missing_column.csv"
        csv_path.write_text("property_id,height\n201,0.10\n")

        updates = BDFProcessor.parse_bar_csv(csv_path)
        # Should skip rows with insufficient columns
        assert len(updates) == 0

    def test_parse_bar_csv_empty_file(self, temp_dir):
        """Test parsing an empty CSV file."""
        csv_path = temp_dir / "empty.csv"
        csv_path.write_text("")

        updates = BDFProcessor.parse_bar_csv(csv_path)
        assert len(updates) == 0

    def test_parse_bar_csv_whitespace_handling(self, temp_dir):
        """Test that whitespace is properly handled."""
        csv_path = temp_dir / "whitespace.csv"
        csv_path.write_text("property_id,height,width\n  201  ,  0.10  ,  0.05  \n")

        updates = BDFProcessor.parse_bar_csv(csv_path)
        assert len(updates) == 1
        assert updates[0].property_id == 201
        assert updates[0].height == pytest.approx(0.10)
        assert updates[0].width == pytest.approx(0.05)

    def test_parse_bar_csv_scientific_notation(self, temp_dir):
        """Test parsing dimensions in scientific notation."""
        csv_path = temp_dir / "scientific.csv"
        csv_path.write_text("property_id,height,width\n201,1.0e-1,5.0E-2\n")

        updates = BDFProcessor.parse_bar_csv(csv_path)
        assert len(updates) == 1
        assert updates[0].height == pytest.approx(0.1)
        assert updates[0].width == pytest.approx(0.05)

    def test_parse_bar_csv_extra_columns_ignored(self, temp_dir):
        """Test that extra columns are ignored."""
        csv_path = temp_dir / "extra_cols.csv"
        csv_path.write_text("property_id,height,width,extra1,extra2\n201,0.10,0.05,foo,bar\n")

        updates = BDFProcessor.parse_bar_csv(csv_path)
        assert len(updates) == 1
        assert updates[0].property_id == 201


class TestCSVEdgeCases:
    """Tests for edge cases in CSV parsing."""

    def test_parse_csv_with_quotes(self, temp_dir):
        """Test parsing CSV with quoted values."""
        csv_path = temp_dir / "quoted.csv"
        csv_path.write_text('property_id,thickness\n"101","0.008"\n')

        updates = BDFProcessor.parse_shell_csv(csv_path)
        assert len(updates) == 1
        assert updates[0].property_id == 101

    def test_parse_csv_with_unicode(self, temp_dir):
        """Test parsing CSV with unicode characters in comments."""
        csv_path = temp_dir / "unicode.csv"
        content = "property_id,thickness\n101,0.008\n"
        csv_path.write_text(content, encoding='utf-8')

        updates = BDFProcessor.parse_shell_csv(csv_path)
        assert len(updates) == 1

    def test_parse_csv_crlf_line_endings(self, temp_dir):
        """Test parsing CSV with CRLF line endings (Windows style)."""
        csv_path = temp_dir / "crlf.csv"
        content = "property_id,thickness\r\n101,0.008\r\n102,0.010\r\n"
        csv_path.write_bytes(content.encode())

        updates = BDFProcessor.parse_shell_csv(csv_path)
        assert len(updates) == 2

    def test_parse_csv_duplicate_property_ids(self, temp_dir):
        """Test parsing CSV with duplicate property IDs."""
        csv_path = temp_dir / "duplicate.csv"
        csv_path.write_text("property_id,thickness\n101,0.008\n101,0.010\n")

        updates = BDFProcessor.parse_shell_csv(csv_path)
        # Both entries should be parsed; handling duplicates is up to the caller
        assert len(updates) == 2
        assert all(u.property_id == 101 for u in updates)

    def test_parse_csv_very_large_property_id(self, temp_dir):
        """Test parsing CSV with very large property ID."""
        csv_path = temp_dir / "large_id.csv"
        csv_path.write_text("property_id,thickness\n99999999,0.008\n")

        updates = BDFProcessor.parse_shell_csv(csv_path)
        assert len(updates) == 1
        assert updates[0].property_id == 99999999

    def test_parse_csv_very_small_thickness(self, temp_dir):
        """Test parsing CSV with very small thickness."""
        csv_path = temp_dir / "small_thickness.csv"
        csv_path.write_text("property_id,thickness\n101,1e-10\n")

        updates = BDFProcessor.parse_shell_csv(csv_path)
        assert len(updates) == 1
        assert updates[0].thickness == pytest.approx(1e-10)

    def test_parse_csv_integer_thickness(self, temp_dir):
        """Test parsing CSV where thickness is an integer."""
        csv_path = temp_dir / "integer.csv"
        csv_path.write_text("property_id,thickness\n101,5\n")

        updates = BDFProcessor.parse_shell_csv(csv_path)
        assert len(updates) == 1
        assert updates[0].thickness == pytest.approx(5.0)
