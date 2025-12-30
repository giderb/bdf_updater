"""
Integration tests for the BDF Property Updater.

Tests cover complete workflows:
- Load BDF -> Parse CSV -> Update properties -> Save
- Multiple update scenarios
- INCLUDE file handling
- Error recovery
"""

import os
import sys
import shutil
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from bdf_processor import (
    BDFProcessor, ShellPropertyUpdate, BarPropertyUpdate,
    CSVParseError, BDFProcessorError
)


class TestCompleteWorkflow:
    """Integration tests for complete update workflow."""

    def test_full_shell_update_workflow(self, temp_bdf_copy, sample_shell_csv_path, temp_dir):
        """Test complete shell property update workflow."""
        # 1. Create processor and load BDF
        processor = BDFProcessor()
        processor.load_bdf(temp_bdf_copy)

        # 2. Verify initial properties
        initial_props = processor.get_shell_properties()
        assert 101 in initial_props
        initial_thickness_101 = initial_props[101]['thickness']

        # 3. Parse CSV updates
        updates = BDFProcessor.parse_shell_csv(sample_shell_csv_path)
        assert len(updates) == 3

        # 4. Apply updates
        results = processor.apply_shell_updates(updates)
        assert all(r.success for r in results)

        # 5. Verify changes in memory
        updated_props = processor.get_shell_properties()
        assert updated_props[101]['thickness'] != initial_thickness_101

        # 6. Save to new file
        output_path = temp_dir / "output.bdf"
        processor.save_bdf(output_path, use_write_bdfs=False)
        assert output_path.exists()

        # 7. Reload and verify persistence
        processor2 = BDFProcessor()
        processor2.load_bdf(output_path)
        final_props = processor2.get_shell_properties()
        assert final_props[101]['thickness'] == pytest.approx(0.008)

    def test_full_bar_update_workflow(self, temp_bdf_copy, sample_bar_csv_path, temp_dir):
        """Test complete bar property update workflow."""
        # 1. Create processor and load BDF
        processor = BDFProcessor()
        processor.load_bdf(temp_bdf_copy)

        # 2. Verify initial properties
        initial_props = processor.get_bar_properties()
        assert 201 in initial_props

        # 3. Parse CSV updates
        updates = BDFProcessor.parse_bar_csv(sample_bar_csv_path)
        assert len(updates) == 3

        # 4. Apply updates
        results = processor.apply_bar_updates(updates)
        assert all(r.success for r in results)

        # 5. Save to new file
        output_path = temp_dir / "output.bdf"
        processor.save_bdf(output_path, use_write_bdfs=False)

        # 6. Reload and verify persistence
        processor2 = BDFProcessor()
        processor2.load_bdf(output_path)
        final_props = processor2.get_bar_properties()

        # For BAR type, dim = [width, height]
        # CSV has: 201,0.15,0.08 (height, width)
        # So dim should be [0.08, 0.15]
        assert final_props[201]['dimensions'][0] == pytest.approx(0.08)  # width
        assert final_props[201]['dimensions'][1] == pytest.approx(0.15)  # height

    def test_mixed_update_workflow(self, temp_bdf_copy, sample_shell_csv_path,
                                   sample_bar_csv_path, temp_dir):
        """Test workflow with both shell and bar updates."""
        processor = BDFProcessor()
        processor.load_bdf(temp_bdf_copy)

        # Apply shell updates
        shell_updates = BDFProcessor.parse_shell_csv(sample_shell_csv_path)
        processor.apply_shell_updates(shell_updates)

        # Apply bar updates
        bar_updates = BDFProcessor.parse_bar_csv(sample_bar_csv_path)
        processor.apply_bar_updates(bar_updates)

        # Check summary
        summary = processor.get_update_summary()
        assert summary['total_updates'] == 6
        assert summary['successful'] == 6
        assert summary['shell_updates']['total'] == 3
        assert summary['bar_updates']['total'] == 3

        # Save and verify
        output_path = temp_dir / "output.bdf"
        processor.save_bdf(output_path, use_write_bdfs=False)

        processor2 = BDFProcessor()
        processor2.load_bdf(output_path)

        shell_props = processor2.get_shell_properties()
        bar_props = processor2.get_bar_properties()

        assert shell_props[101]['thickness'] == pytest.approx(0.008)
        assert bar_props[201]['dimensions'][0] == pytest.approx(0.08)


class TestWriteBDFsWorkflow:
    """Tests for write_bdfs functionality with INCLUDE files."""

    def test_write_bdfs_creates_output(self, temp_include_copy, temp_dir):
        """Test that write_bdfs creates output file."""
        processor = BDFProcessor()
        processor.load_bdf(temp_include_copy)

        output_path = temp_dir / "output_main.bdf"
        processor.save_bdf(output_path, use_write_bdfs=True)

        assert output_path.exists()

    def test_write_bdfs_preserves_structure(self, temp_include_copy, temp_dir):
        """Test that write_bdfs preserves the file structure."""
        processor = BDFProcessor()
        processor.load_bdf(temp_include_copy)

        # Make a change
        update = ShellPropertyUpdate(property_id=101, thickness=0.099)
        processor.update_shell_property(update)

        output_path = temp_dir / "output_main.bdf"
        processor.save_bdf(output_path, use_write_bdfs=True)

        # Verify the main file was created
        assert output_path.exists()


class TestPartialFailureHandling:
    """Tests for handling partial failures in update workflow."""

    def test_partial_shell_update_failure(self, loaded_processor, temp_dir):
        """Test workflow when some shell updates fail."""
        updates = [
            ShellPropertyUpdate(property_id=101, thickness=0.008),  # Valid
            ShellPropertyUpdate(property_id=999, thickness=0.010),  # Invalid - doesn't exist
            ShellPropertyUpdate(property_id=102, thickness=0.012),  # Valid
        ]

        results = loaded_processor.apply_shell_updates(updates)

        assert len(results) == 3
        assert results[0].success is True
        assert results[1].success is False
        assert results[2].success is True

        summary = loaded_processor.get_update_summary()
        assert summary['successful'] == 2
        assert summary['failed'] == 1

    def test_partial_bar_update_failure(self, loaded_processor, temp_dir):
        """Test workflow when some bar updates fail."""
        updates = [
            BarPropertyUpdate(property_id=201, height=0.15, width=0.08),  # Valid
            BarPropertyUpdate(property_id=999, height=0.10, width=0.05),  # Invalid
        ]

        results = loaded_processor.apply_bar_updates(updates)

        assert results[0].success is True
        assert results[1].success is False

    def test_wrong_property_type_update(self, loaded_processor):
        """Test updating property with wrong type."""
        # Try to update PBARL as if it were PSHELL
        shell_update = ShellPropertyUpdate(property_id=201, thickness=0.010)
        result = loaded_processor.update_shell_property(shell_update)

        assert result.success is False
        assert "PBARL" in result.error_message


class TestPreviewAndApplyConsistency:
    """Tests to ensure preview and apply produce consistent results."""

    def test_preview_matches_apply(self, loaded_processor, sample_shell_csv_path):
        """Test that preview accurately predicts apply results."""
        updates = BDFProcessor.parse_shell_csv(sample_shell_csv_path)

        # Get preview
        preview = loaded_processor.preview_changes(shell_updates=updates)

        # Apply updates
        results = loaded_processor.apply_shell_updates(updates)

        # Compare
        for p, r in zip(preview, results):
            if p['status'] == 'valid':
                assert r.success is True
            else:
                assert r.success is False

    def test_preview_shows_correct_changes(self, loaded_processor):
        """Test that preview shows correct before/after values."""
        initial_props = loaded_processor.get_shell_properties()
        initial_thickness = initial_props[101]['thickness']

        updates = [ShellPropertyUpdate(property_id=101, thickness=0.099)]
        preview = loaded_processor.preview_changes(shell_updates=updates)

        assert preview[0]['current_thickness'] == pytest.approx(initial_thickness)
        assert preview[0]['new_thickness'] == pytest.approx(0.099)
        assert preview[0]['change'] == pytest.approx(0.099 - initial_thickness)


class TestReloadAfterModification:
    """Tests for reloading BDF after modifications."""

    def test_reload_preserves_original(self, temp_bdf_copy):
        """Test that reloading the original file restores original values."""
        processor = BDFProcessor()
        processor.load_bdf(temp_bdf_copy)

        initial_thickness = processor.get_shell_properties()[101]['thickness']

        # Modify
        update = ShellPropertyUpdate(property_id=101, thickness=0.999)
        processor.update_shell_property(update)

        # Reload original (without saving)
        processor.load_bdf(temp_bdf_copy)

        # Should have original value again
        assert processor.get_shell_properties()[101]['thickness'] == pytest.approx(initial_thickness)

    def test_reload_after_save(self, temp_bdf_copy, temp_dir):
        """Test reloading after saving shows saved values."""
        processor = BDFProcessor()
        processor.load_bdf(temp_bdf_copy)

        # Modify and save
        update = ShellPropertyUpdate(property_id=101, thickness=0.999)
        processor.update_shell_property(update)

        output_path = temp_dir / "saved.bdf"
        processor.save_bdf(output_path, use_write_bdfs=False)

        # Reload saved file
        processor.load_bdf(output_path)

        assert processor.get_shell_properties()[101]['thickness'] == pytest.approx(0.999)


class TestLargeScaleUpdates:
    """Tests for handling larger numbers of updates."""

    def test_many_shell_updates(self, processor, temp_dir):
        """Test applying many shell updates."""
        # Create a BDF with many shell properties
        bdf_content = """$ Test BDF with many properties
SOL 101
BEGIN BULK
GRID    1       0       0.0     0.0     0.0
MAT1    1       2.1+11  0.3     7850.0
"""
        for i in range(1, 101):
            bdf_content += f"PSHELL  {i}       1       0.00{i:03d}                   1\n"

        bdf_content += "ENDDATA\n"

        bdf_path = temp_dir / "many_props.bdf"
        bdf_path.write_text(bdf_content)

        # Create CSV with updates for all properties
        csv_content = "property_id,thickness\n"
        for i in range(1, 101):
            csv_content += f"{i},0.{i:03d}\n"

        csv_path = temp_dir / "many_updates.csv"
        csv_path.write_text(csv_content)

        # Load and apply
        processor.load_bdf(bdf_path)
        updates = BDFProcessor.parse_shell_csv(csv_path)
        results = processor.apply_shell_updates(updates)

        # All should succeed
        assert len(results) == 100
        assert all(r.success for r in results)

        # Verify random sample
        props = processor.get_shell_properties()
        assert props[50]['thickness'] == pytest.approx(0.050)


class TestConcurrentProcessors:
    """Tests for multiple processor instances."""

    def test_multiple_processors_independent(self, sample_bdf_path):
        """Test that multiple processor instances are independent."""
        p1 = BDFProcessor()
        p2 = BDFProcessor()

        p1.load_bdf(sample_bdf_path)
        p2.load_bdf(sample_bdf_path)

        # Modify p1
        p1.update_shell_property(ShellPropertyUpdate(property_id=101, thickness=0.999))

        # p2 should be unchanged
        assert p2.get_shell_properties()[101]['thickness'] != pytest.approx(0.999)

    def test_multiple_processors_same_file(self, temp_bdf_copy, temp_dir):
        """Test multiple processors working with copies of same file."""
        p1 = BDFProcessor()
        p2 = BDFProcessor()

        p1.load_bdf(temp_bdf_copy)

        # Make a copy for p2
        copy2 = temp_dir / "copy2.bdf"
        shutil.copy(temp_bdf_copy, copy2)
        p2.load_bdf(copy2)

        # Different updates
        p1.update_shell_property(ShellPropertyUpdate(property_id=101, thickness=0.111))
        p2.update_shell_property(ShellPropertyUpdate(property_id=101, thickness=0.222))

        # Both have their own values
        assert p1.get_shell_properties()[101]['thickness'] == pytest.approx(0.111)
        assert p2.get_shell_properties()[101]['thickness'] == pytest.approx(0.222)
