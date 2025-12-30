"""
Comprehensive unit tests for the BDF Processor module.

Tests cover:
- BDF file loading
- Property retrieval
- Property updates (PSHELL and PBARL)
- File saving with write_bdfs
- Error handling
"""

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from bdf_processor import (
    BDFProcessor, ShellPropertyUpdate, BarPropertyUpdate,
    PropertyUpdateResult, CSVParseError, BDFProcessorError
)


class TestBDFProcessorInit:
    """Tests for BDFProcessor initialization."""

    def test_init_creates_empty_processor(self, processor):
        """Test that a new processor has no BDF loaded."""
        assert processor.bdf is None
        assert processor.bdf_path is None
        assert processor.update_results == []

    def test_init_multiple_instances_independent(self):
        """Test that multiple processor instances are independent."""
        p1 = BDFProcessor()
        p2 = BDFProcessor()
        p1.update_results.append("test")
        assert len(p2.update_results) == 0


class TestBDFLoading:
    """Tests for BDF file loading."""

    def test_load_valid_bdf(self, processor, sample_bdf_path):
        """Test loading a valid BDF file."""
        processor.load_bdf(sample_bdf_path)
        assert processor.bdf is not None
        assert processor.bdf_path == sample_bdf_path

    def test_load_nonexistent_file(self, processor):
        """Test loading a file that doesn't exist."""
        with pytest.raises(BDFProcessorError) as exc_info:
            processor.load_bdf("/nonexistent/path/file.bdf")
        assert "not found" in str(exc_info.value).lower()

    def test_load_bdf_with_include(self, processor, temp_include_copy):
        """Test loading a BDF file with INCLUDE statement."""
        processor.load_bdf(temp_include_copy)
        assert processor.bdf is not None
        # Properties from included file should be loaded
        shell_props = processor.get_shell_properties()
        assert 101 in shell_props or len(shell_props) > 0

    def test_load_replaces_previous(self, processor, sample_bdf_path, temp_bdf_copy):
        """Test that loading a new file replaces the previous one."""
        processor.load_bdf(sample_bdf_path)
        first_path = processor.bdf_path
        processor.load_bdf(temp_bdf_copy)
        assert processor.bdf_path != first_path
        assert processor.bdf_path == temp_bdf_copy


class TestShellProperties:
    """Tests for PSHELL property operations."""

    def test_get_shell_properties(self, loaded_processor):
        """Test retrieving shell properties from BDF."""
        shell_props = loaded_processor.get_shell_properties()
        assert len(shell_props) == 3
        assert 101 in shell_props
        assert 102 in shell_props
        assert 103 in shell_props

    def test_shell_property_values(self, loaded_processor):
        """Test that shell property values are correct."""
        shell_props = loaded_processor.get_shell_properties()
        assert shell_props[101]['thickness'] == pytest.approx(0.005)
        assert shell_props[102]['thickness'] == pytest.approx(0.010)
        assert shell_props[103]['thickness'] == pytest.approx(0.003)

    def test_shell_property_has_type(self, loaded_processor):
        """Test that shell properties have correct type."""
        shell_props = loaded_processor.get_shell_properties()
        for pid, props in shell_props.items():
            assert props['type'] == 'PSHELL'

    def test_get_shell_properties_no_bdf_loaded(self, processor):
        """Test getting shell properties without loading BDF first."""
        with pytest.raises(BDFProcessorError) as exc_info:
            processor.get_shell_properties()
        assert "No BDF file loaded" in str(exc_info.value)

    def test_update_shell_property_success(self, loaded_processor):
        """Test updating a shell property successfully."""
        update = ShellPropertyUpdate(property_id=101, thickness=0.008)
        result = loaded_processor.update_shell_property(update)

        assert result.success is True
        assert result.property_id == 101
        assert result.property_type == 'PSHELL'
        assert result.old_values['thickness'] == pytest.approx(0.005)
        assert result.new_values['thickness'] == pytest.approx(0.008)

    def test_update_shell_property_changes_value(self, loaded_processor):
        """Test that updating actually changes the property value."""
        update = ShellPropertyUpdate(property_id=101, thickness=0.015)
        loaded_processor.update_shell_property(update)

        shell_props = loaded_processor.get_shell_properties()
        assert shell_props[101]['thickness'] == pytest.approx(0.015)

    def test_update_shell_property_not_found(self, loaded_processor):
        """Test updating a property that doesn't exist."""
        update = ShellPropertyUpdate(property_id=999, thickness=0.010)
        result = loaded_processor.update_shell_property(update)

        assert result.success is False
        assert "not found" in result.error_message.lower()

    def test_update_shell_property_wrong_type(self, loaded_processor):
        """Test updating a property that is not PSHELL."""
        # Property 201 is PBARL, not PSHELL
        update = ShellPropertyUpdate(property_id=201, thickness=0.010)
        result = loaded_processor.update_shell_property(update)

        assert result.success is False
        assert "PBARL" in result.error_message

    def test_update_shell_no_bdf_loaded(self, processor):
        """Test updating shell property without BDF loaded."""
        update = ShellPropertyUpdate(property_id=101, thickness=0.010)
        result = processor.update_shell_property(update)

        assert result.success is False
        assert "No BDF file loaded" in result.error_message


class TestBarProperties:
    """Tests for PBARL property operations."""

    def test_get_bar_properties(self, loaded_processor):
        """Test retrieving bar properties from BDF."""
        bar_props = loaded_processor.get_bar_properties()
        assert len(bar_props) == 3
        assert 201 in bar_props
        assert 202 in bar_props
        assert 203 in bar_props

    def test_bar_property_values(self, loaded_processor):
        """Test that bar property values are correct."""
        bar_props = loaded_processor.get_bar_properties()
        # For BAR type, dim = [width, height]
        assert bar_props[201]['dimensions'][0] == pytest.approx(0.05)  # width
        assert bar_props[201]['dimensions'][1] == pytest.approx(0.10)  # height

    def test_bar_property_type(self, loaded_processor):
        """Test that bar properties have correct bar type."""
        bar_props = loaded_processor.get_bar_properties()
        for pid, props in bar_props.items():
            assert props['type'] == 'PBARL'
            assert props['bar_type'] == 'BAR'

    def test_get_bar_properties_no_bdf_loaded(self, processor):
        """Test getting bar properties without loading BDF first."""
        with pytest.raises(BDFProcessorError) as exc_info:
            processor.get_bar_properties()
        assert "No BDF file loaded" in str(exc_info.value)

    def test_update_bar_property_success(self, loaded_processor):
        """Test updating a bar property successfully."""
        update = BarPropertyUpdate(property_id=201, height=0.15, width=0.08)
        result = loaded_processor.update_bar_property(update)

        assert result.success is True
        assert result.property_id == 201
        assert result.property_type == 'PBARL'

    def test_update_bar_property_changes_value(self, loaded_processor):
        """Test that updating actually changes the property value."""
        update = BarPropertyUpdate(property_id=201, height=0.20, width=0.12)
        loaded_processor.update_bar_property(update)

        bar_props = loaded_processor.get_bar_properties()
        # For BAR type, dim = [width, height]
        assert bar_props[201]['dimensions'][0] == pytest.approx(0.12)  # width
        assert bar_props[201]['dimensions'][1] == pytest.approx(0.20)  # height

    def test_update_bar_property_not_found(self, loaded_processor):
        """Test updating a bar property that doesn't exist."""
        update = BarPropertyUpdate(property_id=999, height=0.10, width=0.05)
        result = loaded_processor.update_bar_property(update)

        assert result.success is False
        assert "not found" in result.error_message.lower()

    def test_update_bar_property_wrong_type(self, loaded_processor):
        """Test updating a property that is not PBARL."""
        # Property 101 is PSHELL, not PBARL
        update = BarPropertyUpdate(property_id=101, height=0.10, width=0.05)
        result = loaded_processor.update_bar_property(update)

        assert result.success is False
        assert "PSHELL" in result.error_message

    def test_update_bar_no_bdf_loaded(self, processor):
        """Test updating bar property without BDF loaded."""
        update = BarPropertyUpdate(property_id=201, height=0.10, width=0.05)
        result = processor.update_bar_property(update)

        assert result.success is False
        assert "No BDF file loaded" in result.error_message


class TestBatchUpdates:
    """Tests for batch update operations."""

    def test_apply_shell_updates(self, loaded_processor, sample_shell_csv_path):
        """Test applying multiple shell updates."""
        updates = BDFProcessor.parse_shell_csv(sample_shell_csv_path)
        results = loaded_processor.apply_shell_updates(updates)

        assert len(results) == 3
        assert all(r.success for r in results)

    def test_apply_bar_updates(self, loaded_processor, sample_bar_csv_path):
        """Test applying multiple bar updates."""
        updates = BDFProcessor.parse_bar_csv(sample_bar_csv_path)
        results = loaded_processor.apply_bar_updates(updates)

        assert len(results) == 3
        assert all(r.success for r in results)

    def test_apply_mixed_updates(self, loaded_processor, sample_shell_csv_path, sample_bar_csv_path):
        """Test applying both shell and bar updates."""
        shell_updates = BDFProcessor.parse_shell_csv(sample_shell_csv_path)
        bar_updates = BDFProcessor.parse_bar_csv(sample_bar_csv_path)

        shell_results = loaded_processor.apply_shell_updates(shell_updates)
        bar_results = loaded_processor.apply_bar_updates(bar_updates)

        assert len(shell_results) == 3
        assert len(bar_results) == 3

    def test_update_results_accumulated(self, loaded_processor, sample_shell_csv_path):
        """Test that update results are accumulated."""
        updates = BDFProcessor.parse_shell_csv(sample_shell_csv_path)
        loaded_processor.apply_shell_updates(updates)

        assert len(loaded_processor.update_results) == 3

    def test_clear_results(self, loaded_processor, sample_shell_csv_path):
        """Test clearing update results."""
        updates = BDFProcessor.parse_shell_csv(sample_shell_csv_path)
        loaded_processor.apply_shell_updates(updates)
        loaded_processor.clear_results()

        assert len(loaded_processor.update_results) == 0


class TestFileSaving:
    """Tests for BDF file saving operations."""

    def test_save_bdf_overwrites_original(self, processor, temp_bdf_copy):
        """Test saving BDF overwrites the original file."""
        processor.load_bdf(temp_bdf_copy)

        # Make a change
        update = ShellPropertyUpdate(property_id=101, thickness=0.099)
        processor.update_shell_property(update)

        # Save with write_bdf (not write_bdfs)
        saved_path = processor.save_bdf(use_write_bdfs=False)

        assert saved_path == temp_bdf_copy
        assert saved_path.exists()

    def test_save_bdf_to_new_path(self, processor, temp_bdf_copy, temp_dir):
        """Test saving BDF to a new path."""
        processor.load_bdf(temp_bdf_copy)

        new_path = temp_dir / "output.bdf"
        saved_path = processor.save_bdf(new_path, use_write_bdfs=False)

        assert saved_path == new_path
        assert new_path.exists()

    def test_save_bdf_preserves_changes(self, processor, temp_bdf_copy, temp_dir):
        """Test that saved BDF contains the changes."""
        processor.load_bdf(temp_bdf_copy)

        # Make a change
        update = ShellPropertyUpdate(property_id=101, thickness=0.099)
        processor.update_shell_property(update)

        # Save to new file
        new_path = temp_dir / "output.bdf"
        processor.save_bdf(new_path, use_write_bdfs=False)

        # Reload and verify
        processor2 = BDFProcessor()
        processor2.load_bdf(new_path)
        shell_props = processor2.get_shell_properties()

        assert shell_props[101]['thickness'] == pytest.approx(0.099)

    def test_save_no_bdf_loaded(self, processor, temp_dir):
        """Test saving without loading a BDF first."""
        with pytest.raises(BDFProcessorError) as exc_info:
            processor.save_bdf(temp_dir / "output.bdf")
        assert "No BDF file loaded" in str(exc_info.value)

    def test_save_with_write_bdfs(self, processor, temp_include_copy, temp_dir):
        """Test saving with write_bdfs preserves INCLUDE structure."""
        processor.load_bdf(temp_include_copy)

        # Make a change
        update = ShellPropertyUpdate(property_id=101, thickness=0.099)
        processor.update_shell_property(update)

        # Save using write_bdfs
        output_path = temp_dir / "output_main.bdf"
        processor.save_bdf(output_path, use_write_bdfs=True)

        assert output_path.exists()


class TestUpdateSummary:
    """Tests for update summary functionality."""

    def test_get_summary_empty(self, loaded_processor):
        """Test summary with no updates."""
        summary = loaded_processor.get_update_summary()

        assert summary['total_updates'] == 0
        assert summary['successful'] == 0
        assert summary['failed'] == 0

    def test_get_summary_with_updates(self, loaded_processor, sample_shell_csv_path):
        """Test summary after applying updates."""
        updates = BDFProcessor.parse_shell_csv(sample_shell_csv_path)
        loaded_processor.apply_shell_updates(updates)

        summary = loaded_processor.get_update_summary()

        assert summary['total_updates'] == 3
        assert summary['successful'] == 3
        assert summary['failed'] == 0
        assert summary['shell_updates']['total'] == 3

    def test_get_summary_with_failures(self, loaded_processor, test_data_dir):
        """Test summary when some updates fail."""
        updates = BDFProcessor.parse_shell_csv(test_data_dir / "missing_property.csv")
        loaded_processor.apply_shell_updates(updates)

        summary = loaded_processor.get_update_summary()

        assert summary['failed'] == 1  # Property 999 doesn't exist
        assert len(summary['failed_details']) == 1
        assert summary['failed_details'][0]['property_id'] == 999


class TestPreviewChanges:
    """Tests for preview functionality."""

    def test_preview_shell_changes(self, loaded_processor, sample_shell_csv_path):
        """Test previewing shell changes."""
        updates = BDFProcessor.parse_shell_csv(sample_shell_csv_path)
        preview = loaded_processor.preview_changes(shell_updates=updates)

        assert len(preview) == 3
        for p in preview:
            assert p['status'] == 'valid'
            assert 'current_thickness' in p
            assert 'new_thickness' in p

    def test_preview_bar_changes(self, loaded_processor, sample_bar_csv_path):
        """Test previewing bar changes."""
        updates = BDFProcessor.parse_bar_csv(sample_bar_csv_path)
        preview = loaded_processor.preview_changes(bar_updates=updates)

        assert len(preview) == 3
        for p in preview:
            assert p['status'] == 'valid'

    def test_preview_invalid_property(self, loaded_processor):
        """Test previewing with non-existent property."""
        updates = [ShellPropertyUpdate(property_id=999, thickness=0.01)]
        preview = loaded_processor.preview_changes(shell_updates=updates)

        assert len(preview) == 1
        assert preview[0]['status'] == 'error'
        assert 'not found' in preview[0]['error'].lower()

    def test_preview_wrong_property_type(self, loaded_processor):
        """Test previewing with wrong property type."""
        # Try to update PBARL as PSHELL
        updates = [ShellPropertyUpdate(property_id=201, thickness=0.01)]
        preview = loaded_processor.preview_changes(shell_updates=updates)

        assert len(preview) == 1
        assert preview[0]['status'] == 'error'

    def test_preview_no_bdf_loaded(self, processor):
        """Test preview without loading BDF first."""
        updates = [ShellPropertyUpdate(property_id=101, thickness=0.01)]
        with pytest.raises(BDFProcessorError):
            processor.preview_changes(shell_updates=updates)


class TestDataClasses:
    """Tests for data class objects."""

    def test_shell_property_update_creation(self):
        """Test creating ShellPropertyUpdate."""
        update = ShellPropertyUpdate(property_id=101, thickness=0.005)
        assert update.property_id == 101
        assert update.thickness == 0.005

    def test_bar_property_update_creation(self):
        """Test creating BarPropertyUpdate."""
        update = BarPropertyUpdate(property_id=201, height=0.10, width=0.05)
        assert update.property_id == 201
        assert update.height == 0.10
        assert update.width == 0.05

    def test_property_update_result_success(self):
        """Test PropertyUpdateResult for successful update."""
        result = PropertyUpdateResult(
            property_id=101,
            property_type='PSHELL',
            success=True,
            old_values={'thickness': 0.005},
            new_values={'thickness': 0.010}
        )
        assert result.success is True
        assert result.error_message is None

    def test_property_update_result_failure(self):
        """Test PropertyUpdateResult for failed update."""
        result = PropertyUpdateResult(
            property_id=999,
            property_type='PSHELL',
            success=False,
            error_message="Property not found"
        )
        assert result.success is False
        assert result.error_message == "Property not found"
