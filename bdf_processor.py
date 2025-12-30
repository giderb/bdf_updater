"""
BDF Processor Module for updating Nastran BDF shell and bar properties.

This module provides functionality to:
- Load Nastran BDF files using pyNastran
- Parse CSV files for property updates
- Update PSHELL properties (thickness)
- Update PBARL properties (rectangular section dimensions)
- Write BDF files with INCLUDE statement support
"""

import csv
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from pyNastran.bdf.bdf import BDF


@dataclass
class ShellPropertyUpdate:
    """Data class for shell property updates."""
    property_id: int
    thickness: float


@dataclass
class BarPropertyUpdate:
    """Data class for bar property updates (rectangular PBARL)."""
    property_id: int
    height: float
    width: float


@dataclass
class PropertyUpdateResult:
    """Result of a property update operation."""
    property_id: int
    property_type: str
    success: bool
    old_values: Optional[Dict] = None
    new_values: Optional[Dict] = None
    error_message: Optional[str] = None


class CSVParseError(Exception):
    """Exception raised when CSV parsing fails."""
    pass


class BDFProcessorError(Exception):
    """Exception raised when BDF processing fails."""
    pass


class BDFProcessor:
    """
    Processor for updating Nastran BDF file properties.

    Supports updating:
    - PSHELL properties (shell thickness)
    - PBARL properties (rectangular bar section dimensions)
    """

    SUPPORTED_PBARL_TYPES = ['BAR', 'ROD', 'TUBE', 'I', 'CHAN', 'T', 'BOX',
                             'BAR', 'CROSS', 'H', 'T1', 'I1', 'CHAN1', 'Z',
                             'CHAN2', 'T2', 'BOX1', 'HEXA', 'HAT', 'HAT1']

    def __init__(self):
        """Initialize the BDF processor."""
        self.bdf: Optional[BDF] = None
        self.bdf_path: Optional[Path] = None
        self.update_results: List[PropertyUpdateResult] = []

    def load_bdf(self, bdf_path: Union[str, Path]) -> None:
        """
        Load a Nastran BDF file.

        Args:
            bdf_path: Path to the BDF file

        Raises:
            BDFProcessorError: If the file cannot be loaded
        """
        self.bdf_path = Path(bdf_path)

        if not self.bdf_path.exists():
            raise BDFProcessorError(f"BDF file not found: {bdf_path}")

        try:
            self.bdf = BDF()
            self.bdf.read_bdf(str(self.bdf_path))
        except Exception as e:
            raise BDFProcessorError(f"Failed to load BDF file: {e}")

    def get_shell_properties(self) -> Dict[int, Dict]:
        """
        Get all PSHELL properties from the loaded BDF.

        Returns:
            Dictionary mapping property ID to property details
        """
        if self.bdf is None:
            raise BDFProcessorError("No BDF file loaded")

        shell_props = {}
        for pid, prop in self.bdf.properties.items():
            if prop.type == 'PSHELL':
                shell_props[pid] = {
                    'type': 'PSHELL',
                    'thickness': prop.t,
                    'material_id': prop.mid1,
                    'nsm': prop.nsm if hasattr(prop, 'nsm') else 0.0
                }
        return shell_props

    def get_bar_properties(self) -> Dict[int, Dict]:
        """
        Get all PBARL properties from the loaded BDF.

        Returns:
            Dictionary mapping property ID to property details
        """
        if self.bdf is None:
            raise BDFProcessorError("No BDF file loaded")

        bar_props = {}
        for pid, prop in self.bdf.properties.items():
            if prop.type == 'PBARL':
                dims = prop.dim if hasattr(prop, 'dim') else []
                bar_props[pid] = {
                    'type': 'PBARL',
                    'bar_type': prop.bar_type if hasattr(prop, 'bar_type') else prop.Type,
                    'dimensions': list(dims),
                    'material_id': prop.mid,
                    'group': prop.group if hasattr(prop, 'group') else 'MSCBML0'
                }
        return bar_props

    @staticmethod
    def parse_shell_csv(csv_path: Union[str, Path]) -> List[ShellPropertyUpdate]:
        """
        Parse a CSV file for shell property updates.

        Expected format: property_id, thickness

        Args:
            csv_path: Path to the CSV file

        Returns:
            List of ShellPropertyUpdate objects

        Raises:
            CSVParseError: If parsing fails
        """
        csv_path = Path(csv_path)
        if not csv_path.exists():
            raise CSVParseError(f"CSV file not found: {csv_path}")

        updates = []
        try:
            with open(csv_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.reader(f)
                line_num = 0
                for row in reader:
                    line_num += 1
                    # Skip empty rows and header rows
                    if not row or len(row) < 2:
                        continue

                    # Skip header if present
                    try:
                        pid = int(row[0].strip())
                        thickness = float(row[1].strip())
                    except ValueError:
                        # Likely a header row, skip it
                        if line_num == 1:
                            continue
                        raise CSVParseError(
                            f"Invalid data at line {line_num}: "
                            f"expected (int, float), got ({row[0]}, {row[1]})"
                        )

                    if thickness <= 0:
                        raise CSVParseError(
                            f"Invalid thickness at line {line_num}: "
                            f"thickness must be positive, got {thickness}"
                        )

                    updates.append(ShellPropertyUpdate(
                        property_id=pid,
                        thickness=thickness
                    ))
        except Exception as e:
            if isinstance(e, CSVParseError):
                raise
            raise CSVParseError(f"Failed to parse CSV file: {e}")

        return updates

    @staticmethod
    def parse_bar_csv(csv_path: Union[str, Path]) -> List[BarPropertyUpdate]:
        """
        Parse a CSV file for bar property updates.

        Expected format: property_id, height, width

        Args:
            csv_path: Path to the CSV file

        Returns:
            List of BarPropertyUpdate objects

        Raises:
            CSVParseError: If parsing fails
        """
        csv_path = Path(csv_path)
        if not csv_path.exists():
            raise CSVParseError(f"CSV file not found: {csv_path}")

        updates = []
        try:
            with open(csv_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.reader(f)
                line_num = 0
                for row in reader:
                    line_num += 1
                    # Skip empty rows
                    if not row or len(row) < 3:
                        continue

                    # Skip header if present
                    try:
                        pid = int(row[0].strip())
                        height = float(row[1].strip())
                        width = float(row[2].strip())
                    except ValueError:
                        # Likely a header row, skip it
                        if line_num == 1:
                            continue
                        raise CSVParseError(
                            f"Invalid data at line {line_num}: "
                            f"expected (int, float, float), got ({row[0]}, {row[1]}, {row[2]})"
                        )

                    if height <= 0 or width <= 0:
                        raise CSVParseError(
                            f"Invalid dimensions at line {line_num}: "
                            f"dimensions must be positive, got height={height}, width={width}"
                        )

                    updates.append(BarPropertyUpdate(
                        property_id=pid,
                        height=height,
                        width=width
                    ))
        except Exception as e:
            if isinstance(e, CSVParseError):
                raise
            raise CSVParseError(f"Failed to parse CSV file: {e}")

        return updates

    def update_shell_property(self, update: ShellPropertyUpdate) -> PropertyUpdateResult:
        """
        Update a single PSHELL property.

        Args:
            update: ShellPropertyUpdate with new thickness

        Returns:
            PropertyUpdateResult with operation status
        """
        if self.bdf is None:
            return PropertyUpdateResult(
                property_id=update.property_id,
                property_type='PSHELL',
                success=False,
                error_message="No BDF file loaded"
            )

        pid = update.property_id

        if pid not in self.bdf.properties:
            return PropertyUpdateResult(
                property_id=pid,
                property_type='PSHELL',
                success=False,
                error_message=f"Property ID {pid} not found in BDF"
            )

        prop = self.bdf.properties[pid]

        if prop.type != 'PSHELL':
            return PropertyUpdateResult(
                property_id=pid,
                property_type=prop.type,
                success=False,
                error_message=f"Property {pid} is {prop.type}, not PSHELL"
            )

        old_thickness = prop.t
        prop.t = update.thickness

        return PropertyUpdateResult(
            property_id=pid,
            property_type='PSHELL',
            success=True,
            old_values={'thickness': old_thickness},
            new_values={'thickness': update.thickness}
        )

    def update_bar_property(self, update: BarPropertyUpdate) -> PropertyUpdateResult:
        """
        Update a single PBARL property (rectangular section).

        For rectangular (BAR) sections, dimensions are [width, height] or [height, width]
        depending on the convention. This method sets dim[0]=height, dim[1]=width.

        Args:
            update: BarPropertyUpdate with new height and width

        Returns:
            PropertyUpdateResult with operation status
        """
        if self.bdf is None:
            return PropertyUpdateResult(
                property_id=update.property_id,
                property_type='PBARL',
                success=False,
                error_message="No BDF file loaded"
            )

        pid = update.property_id

        if pid not in self.bdf.properties:
            return PropertyUpdateResult(
                property_id=pid,
                property_type='PBARL',
                success=False,
                error_message=f"Property ID {pid} not found in BDF"
            )

        prop = self.bdf.properties[pid]

        if prop.type != 'PBARL':
            return PropertyUpdateResult(
                property_id=pid,
                property_type=prop.type,
                success=False,
                error_message=f"Property {pid} is {prop.type}, not PBARL"
            )

        # Get bar type (handle different pyNastran versions)
        bar_type = getattr(prop, 'bar_type', None) or getattr(prop, 'Type', None)

        if bar_type != 'BAR':
            return PropertyUpdateResult(
                property_id=pid,
                property_type='PBARL',
                success=False,
                error_message=f"Property {pid} is PBARL with type '{bar_type}', "
                             f"not rectangular (BAR) section"
            )

        old_dims = list(prop.dim) if hasattr(prop, 'dim') else []

        # For BAR (rectangular) section: dim = [width, height]
        # Per Nastran documentation: DIM1=width (horizontal), DIM2=height (vertical)
        prop.dim = [update.width, update.height]

        return PropertyUpdateResult(
            property_id=pid,
            property_type='PBARL',
            success=True,
            old_values={'dimensions': old_dims, 'height': old_dims[1] if len(old_dims) > 1 else None,
                       'width': old_dims[0] if len(old_dims) > 0 else None},
            new_values={'dimensions': [update.width, update.height],
                       'height': update.height, 'width': update.width}
        )

    def apply_shell_updates(self, updates: List[ShellPropertyUpdate]) -> List[PropertyUpdateResult]:
        """
        Apply multiple shell property updates.

        Args:
            updates: List of ShellPropertyUpdate objects

        Returns:
            List of PropertyUpdateResult objects
        """
        results = []
        for update in updates:
            result = self.update_shell_property(update)
            results.append(result)
            self.update_results.append(result)
        return results

    def apply_bar_updates(self, updates: List[BarPropertyUpdate]) -> List[PropertyUpdateResult]:
        """
        Apply multiple bar property updates.

        Args:
            updates: List of BarPropertyUpdate objects

        Returns:
            List of PropertyUpdateResult objects
        """
        results = []
        for update in updates:
            result = self.update_bar_property(update)
            results.append(result)
            self.update_results.append(result)
        return results

    def save_bdf(self, output_path: Optional[Union[str, Path]] = None,
                 use_write_bdfs: bool = True) -> Path:
        """
        Save the modified BDF file.

        Args:
            output_path: Optional output path. If None, overwrites the original.
            use_write_bdfs: If True, use write_bdfs() for INCLUDE support.
                           If False, use write_bdf() for single file output.

        Returns:
            Path to the saved file

        Raises:
            BDFProcessorError: If saving fails
        """
        if self.bdf is None:
            raise BDFProcessorError("No BDF file loaded")

        if output_path is None:
            output_path = self.bdf_path
        else:
            output_path = Path(output_path)

        try:
            if use_write_bdfs:
                # write_bdfs preserves INCLUDE structure and writes sub-BDFs
                self.bdf.write_bdfs(str(output_path))
            else:
                # write_bdf writes everything to a single file
                self.bdf.write_bdf(str(output_path))
            return output_path
        except Exception as e:
            raise BDFProcessorError(f"Failed to save BDF file: {e}")

    def get_update_summary(self) -> Dict:
        """
        Get a summary of all applied updates.

        Returns:
            Dictionary with update statistics
        """
        total = len(self.update_results)
        successful = sum(1 for r in self.update_results if r.success)
        failed = total - successful

        shell_updates = [r for r in self.update_results if r.property_type == 'PSHELL']
        bar_updates = [r for r in self.update_results if r.property_type == 'PBARL']

        return {
            'total_updates': total,
            'successful': successful,
            'failed': failed,
            'shell_updates': {
                'total': len(shell_updates),
                'successful': sum(1 for r in shell_updates if r.success),
                'failed': sum(1 for r in shell_updates if not r.success)
            },
            'bar_updates': {
                'total': len(bar_updates),
                'successful': sum(1 for r in bar_updates if r.success),
                'failed': sum(1 for r in bar_updates if not r.success)
            },
            'failed_details': [
                {'property_id': r.property_id, 'type': r.property_type, 'error': r.error_message}
                for r in self.update_results if not r.success
            ]
        }

    def clear_results(self) -> None:
        """Clear stored update results."""
        self.update_results.clear()

    def preview_changes(self, shell_updates: Optional[List[ShellPropertyUpdate]] = None,
                       bar_updates: Optional[List[BarPropertyUpdate]] = None) -> List[Dict]:
        """
        Preview changes without applying them.

        Args:
            shell_updates: List of shell property updates to preview
            bar_updates: List of bar property updates to preview

        Returns:
            List of dictionaries describing the proposed changes
        """
        if self.bdf is None:
            raise BDFProcessorError("No BDF file loaded")

        preview = []

        if shell_updates:
            for update in shell_updates:
                pid = update.property_id
                if pid in self.bdf.properties:
                    prop = self.bdf.properties[pid]
                    if prop.type == 'PSHELL':
                        preview.append({
                            'property_id': pid,
                            'property_type': 'PSHELL',
                            'current_thickness': prop.t,
                            'new_thickness': update.thickness,
                            'change': update.thickness - prop.t,
                            'status': 'valid'
                        })
                    else:
                        preview.append({
                            'property_id': pid,
                            'property_type': prop.type,
                            'status': 'error',
                            'error': f"Expected PSHELL, found {prop.type}"
                        })
                else:
                    preview.append({
                        'property_id': pid,
                        'property_type': 'PSHELL',
                        'status': 'error',
                        'error': 'Property ID not found'
                    })

        if bar_updates:
            for update in bar_updates:
                pid = update.property_id
                if pid in self.bdf.properties:
                    prop = self.bdf.properties[pid]
                    if prop.type == 'PBARL':
                        bar_type = getattr(prop, 'bar_type', None) or getattr(prop, 'Type', None)
                        if bar_type == 'BAR':
                            dims = list(prop.dim) if hasattr(prop, 'dim') else []
                            preview.append({
                                'property_id': pid,
                                'property_type': 'PBARL',
                                'bar_type': bar_type,
                                'current_width': dims[0] if len(dims) > 0 else None,
                                'current_height': dims[1] if len(dims) > 1 else None,
                                'new_width': update.width,
                                'new_height': update.height,
                                'status': 'valid'
                            })
                        else:
                            preview.append({
                                'property_id': pid,
                                'property_type': 'PBARL',
                                'bar_type': bar_type,
                                'status': 'error',
                                'error': f"Expected BAR type, found {bar_type}"
                            })
                    else:
                        preview.append({
                            'property_id': pid,
                            'property_type': prop.type,
                            'status': 'error',
                            'error': f"Expected PBARL, found {prop.type}"
                        })
                else:
                    preview.append({
                        'property_id': pid,
                        'property_type': 'PBARL',
                        'status': 'error',
                        'error': 'Property ID not found'
                    })

        return preview
