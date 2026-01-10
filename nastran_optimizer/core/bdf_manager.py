"""
BDF Manager for SOL200 optimization.

Handles loading, parsing, and modifying Nastran BDF files using pyNastran.

Features:
- Load BDF with INCLUDE support
- Extract properties (PSHELL, PBAR, PBARL, PROD)
- Add optimization cards (DESVAR, DVPREL, DRESP, DCONSTR, DEQATN)
- Validate model for SOL200
- Export modified BDF
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union, Any

from pyNastran.bdf.bdf import BDF


@dataclass
class PropertyInfo:
    """Information about a structural property."""
    id: int
    type: str  # PSHELL, PBAR, PBARL, PROD
    data: Dict[str, Any]
    element_count: int = 0
    element_ids: List[int] = field(default_factory=list)


@dataclass
class NodeInfo:
    """Information about a grid point."""
    id: int
    coordinates: Tuple[float, float, float]
    displacement_cs: int  # Displacement coordinate system
    analysis_cs: int  # Analysis coordinate system


@dataclass
class ModelSummary:
    """Summary of the BDF model."""
    filename: str
    num_nodes: int
    num_elements: int
    num_properties: int
    num_materials: int
    property_types: Dict[str, int]
    element_types: Dict[str, int]
    has_frequency_cards: bool
    has_spc: bool
    has_loads: bool
    solution_type: Optional[int] = None


class BDFManager:
    """
    Manager for BDF file operations.

    Handles loading, property extraction, and modification for SOL200.
    """

    # Supported property types for design variables
    SUPPORTED_PROPERTIES = {'PSHELL', 'PBAR', 'PBARL', 'PROD'}

    def __init__(self):
        """Initialize the BDF manager."""
        self.bdf: Optional[BDF] = None
        self.bdf_path: Optional[Path] = None
        self._properties: Dict[int, PropertyInfo] = {}
        self._nodes: Dict[int, NodeInfo] = {}
        self._element_to_property: Dict[int, int] = {}
        self._is_modified: bool = False

    def load(self, bdf_path: Union[str, Path]) -> ModelSummary:
        """
        Load a BDF file.

        Args:
            bdf_path: Path to the BDF file

        Returns:
            ModelSummary with model information

        Raises:
            FileNotFoundError: If file doesn't exist
            RuntimeError: If loading fails
        """
        self.bdf_path = Path(bdf_path)

        if not self.bdf_path.exists():
            raise FileNotFoundError(f"BDF file not found: {bdf_path}")

        try:
            self.bdf = BDF()
            self.bdf.read_bdf(str(self.bdf_path))
        except Exception as e:
            raise RuntimeError(f"Failed to load BDF: {e}")

        # Extract model information
        self._extract_properties()
        self._extract_nodes()
        self._build_element_property_map()
        self._is_modified = False

        return self.get_summary()

    def _extract_properties(self):
        """Extract all supported properties from the model."""
        self._properties.clear()

        if self.bdf is None:
            return

        for pid, prop in self.bdf.properties.items():
            if prop.type in self.SUPPORTED_PROPERTIES:
                prop_data = self._get_property_data(prop)
                self._properties[pid] = PropertyInfo(
                    id=pid,
                    type=prop.type,
                    data=prop_data,
                )

    def _get_property_data(self, prop) -> Dict[str, Any]:
        """Extract data from a property card."""
        data = {'type': prop.type}

        if prop.type == 'PSHELL':
            data.update({
                'thickness': prop.t,
                'mid1': prop.mid1,
                'mid2': prop.mid2 if hasattr(prop, 'mid2') else None,
                'mid3': prop.mid3 if hasattr(prop, 'mid3') else None,
                'nsm': prop.nsm if hasattr(prop, 'nsm') else 0.0,
                '12i_t3': prop.twelveIt3 if hasattr(prop, 'twelveIt3') else 1.0,
            })

        elif prop.type == 'PBAR':
            data.update({
                'mid': prop.mid,
                'A': prop.A,
                'i1': prop.i1,
                'i2': prop.i2,
                'j': prop.j if hasattr(prop, 'j') else 0.0,
                'nsm': prop.nsm if hasattr(prop, 'nsm') else 0.0,
            })

        elif prop.type == 'PBARL':
            data.update({
                'mid': prop.mid,
                'bar_type': getattr(prop, 'bar_type', None) or getattr(prop, 'Type', 'BAR'),
                'dim': list(prop.dim) if hasattr(prop, 'dim') else [],
                'group': prop.group if hasattr(prop, 'group') else 'MSCBML0',
                'nsm': prop.nsm if hasattr(prop, 'nsm') else 0.0,
            })

        elif prop.type == 'PROD':
            data.update({
                'mid': prop.mid,
                'A': prop.A,
                'j': prop.j if hasattr(prop, 'j') else 0.0,
                'c': prop.c if hasattr(prop, 'c') else 0.0,
                'nsm': prop.nsm if hasattr(prop, 'nsm') else 0.0,
            })

        return data

    def _extract_nodes(self):
        """Extract all grid points from the model."""
        self._nodes.clear()

        if self.bdf is None:
            return

        for nid, node in self.bdf.nodes.items():
            xyz = node.get_position()
            self._nodes[nid] = NodeInfo(
                id=nid,
                coordinates=(xyz[0], xyz[1], xyz[2]),
                displacement_cs=node.cd,
                analysis_cs=node.cp,
            )

    def _build_element_property_map(self):
        """Build mapping from element to property."""
        self._element_to_property.clear()

        if self.bdf is None:
            return

        for eid, elem in self.bdf.elements.items():
            if hasattr(elem, 'pid'):
                pid = elem.pid
                self._element_to_property[eid] = pid

                # Update property element count
                if pid in self._properties:
                    self._properties[pid].element_count += 1
                    self._properties[pid].element_ids.append(eid)

    def get_summary(self) -> ModelSummary:
        """Get a summary of the loaded model."""
        if self.bdf is None:
            return ModelSummary(
                filename="",
                num_nodes=0,
                num_elements=0,
                num_properties=0,
                num_materials=0,
                property_types={},
                element_types={},
                has_frequency_cards=False,
                has_spc=False,
                has_loads=False,
            )

        # Count property types
        prop_types = {}
        for prop in self._properties.values():
            prop_types[prop.type] = prop_types.get(prop.type, 0) + 1

        # Count element types
        elem_types = {}
        for elem in self.bdf.elements.values():
            elem_types[elem.type] = elem_types.get(elem.type, 0) + 1

        # Check for frequency analysis cards
        has_freq = bool(self.bdf.frequencies) or any(
            hasattr(self.bdf, attr) and getattr(self.bdf, attr)
            for attr in ['freq1', 'freq2', 'freq3', 'freq4', 'freq5']
        )

        # Check for constraints and loads
        has_spc = bool(self.bdf.spcs) or bool(self.bdf.spcadds)
        has_loads = bool(self.bdf.loads)

        # Get solution type from executive control
        sol_type = None
        if hasattr(self.bdf, 'sol'):
            sol_type = self.bdf.sol

        return ModelSummary(
            filename=str(self.bdf_path) if self.bdf_path else "",
            num_nodes=len(self.bdf.nodes),
            num_elements=len(self.bdf.elements),
            num_properties=len(self._properties),
            num_materials=len(self.bdf.materials),
            property_types=prop_types,
            element_types=elem_types,
            has_frequency_cards=has_freq,
            has_spc=has_spc,
            has_loads=has_loads,
            solution_type=sol_type,
        )

    def get_properties(
        self,
        prop_type: Optional[str] = None,
    ) -> Dict[int, PropertyInfo]:
        """
        Get properties from the model.

        Args:
            prop_type: Filter by property type (PSHELL, PBAR, etc.)

        Returns:
            Dictionary of PropertyInfo objects
        """
        if prop_type is None:
            return self._properties.copy()

        return {
            pid: prop for pid, prop in self._properties.items()
            if prop.type == prop_type
        }

    def get_property(self, pid: int) -> Optional[PropertyInfo]:
        """Get a specific property by ID."""
        return self._properties.get(pid)

    def get_nodes(self) -> Dict[int, NodeInfo]:
        """Get all nodes from the model."""
        return self._nodes.copy()

    def get_node(self, nid: int) -> Optional[NodeInfo]:
        """Get a specific node by ID."""
        return self._nodes.get(nid)

    def get_elements_for_property(self, pid: int) -> List[int]:
        """Get all element IDs using a property."""
        prop = self._properties.get(pid)
        if prop:
            return prop.element_ids.copy()
        return []

    def add_optimization_cards(
        self,
        desvar_cards: List[str],
        dvprel_cards: List[str],
        dresp_cards: List[str],
        dconstr_cards: List[str],
        deqatn_cards: List[str],
        doptprm_card: Optional[str] = None,
    ):
        """
        Add optimization cards to the model.

        Args:
            desvar_cards: DESVAR card strings
            dvprel_cards: DVPREL1/DVPREL2 card strings
            dresp_cards: DRESP1/DRESP2 card strings
            dconstr_cards: DCONSTR card strings
            deqatn_cards: DEQATN card strings
            doptprm_card: DOPTPRM card string (optional)
        """
        if self.bdf is None:
            raise RuntimeError("No BDF loaded")

        # Add cards using pyNastran's card parser
        all_cards = []
        all_cards.extend(desvar_cards)
        all_cards.extend(dvprel_cards)
        all_cards.extend(dresp_cards)
        all_cards.extend(dconstr_cards)
        all_cards.extend(deqatn_cards)

        if doptprm_card:
            all_cards.append(doptprm_card)

        for card_str in all_cards:
            if card_str.strip():
                try:
                    # Parse the card string
                    lines = card_str.strip().split('\n')
                    self.bdf.add_card_lines(lines, lines[0].split(',')[0].strip())
                except Exception as e:
                    # Store as reject card if parsing fails
                    self.bdf.reject_cards.append(card_str)

        self._is_modified = True

    def set_solution(self, sol: int = 200):
        """
        Set the solution sequence.

        Args:
            sol: Solution number (200 for optimization)
        """
        if self.bdf is None:
            raise RuntimeError("No BDF loaded")

        self.bdf.sol = sol
        self._is_modified = True

    def add_case_control(self, commands: List[str]):
        """
        Add case control commands.

        Args:
            commands: List of case control command strings
        """
        if self.bdf is None:
            raise RuntimeError("No BDF loaded")

        for cmd in commands:
            self.bdf.case_control_deck.add_parameter_to_global_subcase(cmd)

        self._is_modified = True

    def save(
        self,
        output_path: Optional[Union[str, Path]] = None,
        use_write_bdfs: bool = True,
    ) -> Path:
        """
        Save the BDF file.

        Args:
            output_path: Output path (uses original + "_opt" if None)
            use_write_bdfs: Use write_bdfs for INCLUDE support

        Returns:
            Path to saved file
        """
        if self.bdf is None:
            raise RuntimeError("No BDF loaded")

        if output_path is None:
            if self.bdf_path:
                stem = self.bdf_path.stem
                output_path = self.bdf_path.parent / f"{stem}_opt.bdf"
            else:
                raise ValueError("No output path specified")

        output_path = Path(output_path)

        if use_write_bdfs:
            self.bdf.write_bdfs(str(output_path))
        else:
            self.bdf.write_bdf(str(output_path))

        self._is_modified = False
        return output_path

    def validate_for_sol200(self) -> List[str]:
        """
        Validate model for SOL200 optimization.

        Returns:
            List of validation warnings/errors
        """
        issues = []

        if self.bdf is None:
            issues.append("ERROR: No BDF loaded")
            return issues

        # Check solution type
        if self.bdf.sol not in [200, None]:
            issues.append(f"WARNING: Solution type is {self.bdf.sol}, not 200")

        # Check for properties
        if not self._properties:
            issues.append("ERROR: No supported properties found (PSHELL, PBAR, PBARL, PROD)")

        # Check for constraints
        if not self.bdf.spcs and not self.bdf.spcadds:
            issues.append("WARNING: No SPC constraints found")

        # Check for loads
        if not self.bdf.loads:
            issues.append("WARNING: No loads found")

        # For frequency response (SOL111 within SOL200)
        # Check for frequency definitions
        has_freq = bool(self.bdf.frequencies)
        if not has_freq:
            issues.append("INFO: No FREQ cards found (required for frequency response)")

        return issues

    def get_designable_properties(self) -> List[Dict]:
        """
        Get list of properties that can be used as design variables.

        Returns:
            List of property information dictionaries
        """
        designable = []

        for pid, prop in self._properties.items():
            info = {
                'id': pid,
                'type': prop.type,
                'element_count': prop.element_count,
                'fields': [],
            }

            # Add designable fields based on property type
            if prop.type == 'PSHELL':
                info['fields'].append({
                    'name': 'T',
                    'description': 'Shell thickness',
                    'current_value': prop.data.get('thickness'),
                    'field_num': 4,
                })

            elif prop.type == 'PBAR':
                info['fields'].extend([
                    {'name': 'A', 'description': 'Cross-sectional area',
                     'current_value': prop.data.get('A'), 'field_num': 4},
                    {'name': 'I1', 'description': 'Moment of inertia 1',
                     'current_value': prop.data.get('i1'), 'field_num': 5},
                    {'name': 'I2', 'description': 'Moment of inertia 2',
                     'current_value': prop.data.get('i2'), 'field_num': 6},
                    {'name': 'J', 'description': 'Torsional constant',
                     'current_value': prop.data.get('j'), 'field_num': 7},
                ])

            elif prop.type == 'PBARL':
                bar_type = prop.data.get('bar_type', 'BAR')
                dims = prop.data.get('dim', [])
                for i, dim in enumerate(dims):
                    info['fields'].append({
                        'name': f'DIM{i+1}',
                        'description': f'{bar_type} dimension {i+1}',
                        'current_value': dim,
                        'field_num': 9 + i,
                    })

            elif prop.type == 'PROD':
                info['fields'].extend([
                    {'name': 'A', 'description': 'Cross-sectional area',
                     'current_value': prop.data.get('A'), 'field_num': 4},
                    {'name': 'J', 'description': 'Torsional constant',
                     'current_value': prop.data.get('j'), 'field_num': 5},
                ])

            designable.append(info)

        return designable

    @property
    def is_loaded(self) -> bool:
        """Check if a BDF is loaded."""
        return self.bdf is not None

    @property
    def is_modified(self) -> bool:
        """Check if the model has been modified."""
        return self._is_modified
