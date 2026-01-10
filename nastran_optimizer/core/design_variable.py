"""
Design Variable management for SOL200 optimization.

Handles DESVAR cards and property relationships (DVPREL1/DVPREL2).

DESVAR Format:
    DESVAR, ID, LABEL, XINIT, XLB, XUB, DELXV, DDVAL

DVPREL1 Format (linear relationship):
    DVPREL1, ID, TYPE, PID, FID, PMIN, PMAX, C0,
            DVID1, COEF1, DVID2, COEF2, ...

Supported property types:
    - PSHELL: Shell element properties (T, MID1, etc.)
    - PBAR: Simple bar properties (A, I1, I2, J)
    - PBARL: Library bar properties (DIM1, DIM2, ...)
    - PROD: Rod properties (A, J)
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple, Union
import uuid


class PropertyType(Enum):
    """Supported property card types for design variables."""
    PSHELL = "PSHELL"
    PBAR = "PBAR"
    PBARL = "PBARL"
    PROD = "PROD"


class PropertyField(Enum):
    """Property fields that can be linked to design variables."""
    # PSHELL fields
    PSHELL_T = ("PSHELL", "T", 4)           # Shell thickness
    PSHELL_MID1 = ("PSHELL", "MID1", 3)     # Material for membrane
    PSHELL_MID2 = ("PSHELL", "MID2", 5)     # Material for bending
    PSHELL_12IT3 = ("PSHELL", "12I/T3", 6)  # Bending stiffness ratio
    PSHELL_NSM = ("PSHELL", "NSM", 8)       # Non-structural mass

    # PBAR fields
    PBAR_A = ("PBAR", "A", 4)               # Cross-sectional area
    PBAR_I1 = ("PBAR", "I1", 5)             # Moment of inertia 1
    PBAR_I2 = ("PBAR", "I2", 6)             # Moment of inertia 2
    PBAR_J = ("PBAR", "J", 7)               # Torsional constant

    # PBARL fields (library bar - dimensions depend on cross-section type)
    PBARL_DIM1 = ("PBARL", "DIM1", 9)       # First dimension
    PBARL_DIM2 = ("PBARL", "DIM2", 10)      # Second dimension
    PBARL_DIM3 = ("PBARL", "DIM3", 11)      # Third dimension
    PBARL_DIM4 = ("PBARL", "DIM4", 12)      # Fourth dimension

    # PROD fields
    PROD_A = ("PROD", "A", 4)               # Cross-sectional area
    PROD_J = ("PROD", "J", 5)               # Torsional constant

    def __init__(self, prop_type: str, field_name: str, field_num: int):
        self.prop_type = prop_type
        self.field_name = field_name
        self.field_num = field_num

    @classmethod
    def get_fields_for_property(cls, prop_type: PropertyType) -> List['PropertyField']:
        """Get all available fields for a property type."""
        return [f for f in cls if f.prop_type == prop_type.value]


class LinkType(Enum):
    """Type of design variable to property relationship."""
    DVPREL1 = auto()  # Linear relationship: P = C0 + sum(Ci * DVi)
    DVPREL2 = auto()  # Nonlinear relationship using DEQATN


@dataclass
class DesignVariable:
    """
    Design variable definition (DESVAR card).

    Attributes:
        id: Unique identifier (auto-generated if None)
        label: 8-character label for the design variable
        initial_value: Initial value (XINIT)
        lower_bound: Lower bound (XLB)
        upper_bound: Upper bound (XUB)
        delta: Move limit for optimization (DELXV, optional)
        discrete_values: List of discrete allowed values (DDVAL, optional)
        description: Human-readable description
        unit: Engineering unit for display
    """
    label: str
    initial_value: float
    lower_bound: float
    upper_bound: float
    id: Optional[int] = None
    delta: Optional[float] = None
    discrete_values: Optional[List[float]] = None
    description: str = ""
    unit: str = ""
    _uuid: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    def __post_init__(self):
        """Validate design variable parameters."""
        self._validate()

    def _validate(self):
        """Validate design variable bounds and values."""
        # Label validation (max 8 characters)
        if len(self.label) > 8:
            raise ValueError(f"DESVAR label must be <= 8 characters: '{self.label}'")

        if not self.label.replace('_', '').isalnum():
            raise ValueError(f"DESVAR label must be alphanumeric: '{self.label}'")

        # Bounds validation
        if self.lower_bound > self.upper_bound:
            raise ValueError(
                f"Lower bound ({self.lower_bound}) cannot exceed upper bound ({self.upper_bound})"
            )

        if not (self.lower_bound <= self.initial_value <= self.upper_bound):
            raise ValueError(
                f"Initial value ({self.initial_value}) must be within bounds "
                f"[{self.lower_bound}, {self.upper_bound}]"
            )

        # Positive bounds for physical properties
        if self.lower_bound < 0:
            raise ValueError(
                f"Lower bound ({self.lower_bound}) must be non-negative for physical properties"
            )

        # Delta validation
        if self.delta is not None and self.delta <= 0:
            raise ValueError(f"Delta move limit must be positive: {self.delta}")

    def to_nastran(self) -> str:
        """Generate DESVAR card string."""
        # DESVAR, ID, LABEL, XINIT, XLB, XUB, DELXV, DDVAL
        parts = [
            "DESVAR",
            str(self.id),
            self.label,
            f"{self.initial_value:.6g}",
            f"{self.lower_bound:.6g}",
            f"{self.upper_bound:.6g}",
        ]

        if self.delta is not None:
            parts.append(f"{self.delta:.6g}")
        else:
            parts.append("")

        # DDVAL would reference a separate DDVAL card
        if self.discrete_values:
            parts.append(str(self.id))  # Reference DDVAL with same ID

        return ",".join(parts)

    def get_range(self) -> Tuple[float, float]:
        """Get the allowable range as a tuple."""
        return (self.lower_bound, self.upper_bound)

    def is_at_bound(self, tolerance: float = 1e-6) -> Optional[str]:
        """Check if current value is at a bound."""
        if abs(self.initial_value - self.lower_bound) < tolerance:
            return "lower"
        if abs(self.initial_value - self.upper_bound) < tolerance:
            return "upper"
        return None


@dataclass
class DesignVariableLink:
    """
    Link between design variable(s) and a property field (DVPREL1/DVPREL2).

    For DVPREL1 (linear): Property = C0 + sum(Ci * DVi)
    For DVPREL2 (nonlinear): Property = f(DV1, DV2, ...) via DEQATN

    Attributes:
        id: Unique identifier for the DVPREL card
        property_type: Type of property card (PSHELL, PBAR, etc.)
        property_id: ID of the property card
        field: Property field being linked
        link_type: DVPREL1 (linear) or DVPREL2 (equation)
        design_variables: List of (DesignVariable, coefficient) tuples for DVPREL1
                         or just DesignVariable list for DVPREL2
        constant: C0 constant term for DVPREL1
        equation_id: DEQATN ID for DVPREL2
        p_min: Minimum property value constraint
        p_max: Maximum property value constraint
    """
    id: int
    property_type: PropertyType
    property_id: int
    field: PropertyField
    link_type: LinkType = LinkType.DVPREL1
    design_variables: List[Tuple['DesignVariable', float]] = field(default_factory=list)
    constant: float = 0.0
    equation_id: Optional[int] = None
    p_min: Optional[float] = None
    p_max: Optional[float] = None

    def __post_init__(self):
        """Validate the link configuration."""
        self._validate()

    def _validate(self):
        """Validate link parameters."""
        # Check field matches property type
        if self.field.prop_type != self.property_type.value:
            raise ValueError(
                f"Field {self.field.field_name} is not valid for {self.property_type.value}"
            )

        # DVPREL1 requires design variables with coefficients
        if self.link_type == LinkType.DVPREL1:
            if not self.design_variables:
                raise ValueError("DVPREL1 requires at least one design variable")

        # DVPREL2 requires equation reference
        if self.link_type == LinkType.DVPREL2:
            if self.equation_id is None:
                raise ValueError("DVPREL2 requires an equation ID (DEQATN)")

        # Property bounds validation
        if self.p_min is not None and self.p_max is not None:
            if self.p_min > self.p_max:
                raise ValueError(f"PMIN ({self.p_min}) cannot exceed PMAX ({self.p_max})")

    def to_nastran(self) -> str:
        """Generate DVPREL1 or DVPREL2 card string."""
        if self.link_type == LinkType.DVPREL1:
            return self._to_dvprel1()
        else:
            return self._to_dvprel2()

    def _to_dvprel1(self) -> str:
        """Generate DVPREL1 card."""
        # DVPREL1, ID, TYPE, PID, FID, PMIN, PMAX, C0,
        #         DVID1, COEF1, DVID2, COEF2, ...
        lines = []

        # First line
        pmin_str = f"{self.p_min:.6g}" if self.p_min is not None else ""
        pmax_str = f"{self.p_max:.6g}" if self.p_max is not None else ""

        line1 = (
            f"DVPREL1,{self.id},{self.property_type.value},{self.property_id},"
            f"{self.field.field_name},{pmin_str},{pmax_str},{self.constant:.6g}"
        )
        lines.append(line1)

        # Continuation lines with design variable IDs and coefficients
        dvs = list(self.design_variables)
        while dvs:
            batch = dvs[:4]  # 4 DV-coefficient pairs per continuation line
            dvs = dvs[4:]

            parts = ["+"]
            for dv, coef in batch:
                parts.extend([str(dv.id), f"{coef:.6g}"])

            lines.append(",".join(parts))

        return "\n".join(lines)

    def _to_dvprel2(self) -> str:
        """Generate DVPREL2 card."""
        # DVPREL2, ID, TYPE, PID, FID, PMIN, PMAX, EQID,
        #         DESVAR, DVID1, DVID2, ...
        pmin_str = f"{self.p_min:.6g}" if self.p_min is not None else ""
        pmax_str = f"{self.p_max:.6g}" if self.p_max is not None else ""

        lines = []

        line1 = (
            f"DVPREL2,{self.id},{self.property_type.value},{self.property_id},"
            f"{self.field.field_name},{pmin_str},{pmax_str},{self.equation_id}"
        )
        lines.append(line1)

        # Design variable references
        if self.design_variables:
            parts = ["+", "DESVAR"]
            for dv, _ in self.design_variables:
                parts.append(str(dv.id))
            lines.append(",".join(parts))

        return "\n".join(lines)

    def calculate_current_value(self) -> float:
        """Calculate the current property value based on design variable values."""
        if self.link_type == LinkType.DVPREL1:
            value = self.constant
            for dv, coef in self.design_variables:
                value += coef * dv.initial_value
            return value
        else:
            # For DVPREL2, would need equation evaluation
            raise NotImplementedError("DVPREL2 value calculation requires equation evaluation")


@dataclass
class DesignVariableGroup:
    """
    Group of related design variables for UI organization.

    Attributes:
        name: Group name
        description: Group description
        variables: List of design variables in this group
        color: Display color for UI
    """
    name: str
    description: str = ""
    variables: List[DesignVariable] = field(default_factory=list)
    color: str = "#4A90D9"

    def add_variable(self, variable: DesignVariable):
        """Add a design variable to the group."""
        self.variables.append(variable)

    def remove_variable(self, variable: DesignVariable):
        """Remove a design variable from the group."""
        self.variables.remove(variable)

    def get_total_range(self) -> Dict[str, Tuple[float, float]]:
        """Get ranges for all variables in the group."""
        return {dv.label: dv.get_range() for dv in self.variables}
