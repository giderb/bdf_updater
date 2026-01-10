"""
Design Constraint management for SOL200 optimization.

Handles DCONSTR cards for defining optimization constraints.

DCONSTR Format:
    DCONSTR, DCID, RID, LALLOW, UALLOW, LOWFQ, HIGHFQ

Constraints apply bounds to design responses:
    LALLOW <= Response <= UALLOW

For frequency-dependent constraints, LOWFQ and HIGHFQ specify
the frequency range where the constraint is active.
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple, Union
import uuid


class ConstraintType(Enum):
    """Types of optimization constraints."""
    UPPER_BOUND = auto()      # Response <= UALLOW
    LOWER_BOUND = auto()      # Response >= LALLOW
    DOUBLE_BOUND = auto()     # LALLOW <= Response <= UALLOW
    EQUALITY = auto()         # Response = Target (very tight bounds)


class ConstraintStatus(Enum):
    """Status of a constraint during/after optimization."""
    INACTIVE = auto()         # Not near bounds
    ACTIVE_LOWER = auto()     # At lower bound
    ACTIVE_UPPER = auto()     # At upper bound
    VIOLATED_LOWER = auto()   # Below lower bound
    VIOLATED_UPPER = auto()   # Above upper bound
    SATISFIED = auto()        # Within bounds


@dataclass
class DesignConstraint:
    """
    Design constraint definition (DCONSTR card).

    Attributes:
        id: Constraint set ID (DCID)
        response_id: Response ID to constrain (RID)
        lower_bound: Lower allowable value (LALLOW)
        upper_bound: Upper allowable value (UALLOW)
        low_frequency: Low frequency bound for freq-dependent (LOWFQ)
        high_frequency: High frequency bound for freq-dependent (HIGHFQ)
        label: Human-readable label
        description: Description of the constraint
        constraint_type: Type of constraint
        is_active: Whether constraint is currently active
        current_value: Current response value (for monitoring)
    """
    response_id: int
    id: Optional[int] = None
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None
    low_frequency: Optional[float] = None
    high_frequency: Optional[float] = None
    label: str = ""
    description: str = ""
    constraint_type: ConstraintType = ConstraintType.DOUBLE_BOUND
    is_active: bool = True
    current_value: Optional[float] = None
    _uuid: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    def __post_init__(self):
        """Validate and determine constraint type."""
        self._validate()
        self._determine_type()

    def _validate(self):
        """Validate constraint parameters."""
        # At least one bound must be specified
        if self.lower_bound is None and self.upper_bound is None:
            raise ValueError("At least one bound (lower or upper) must be specified")

        # If both bounds exist, lower must be <= upper
        if self.lower_bound is not None and self.upper_bound is not None:
            if self.lower_bound > self.upper_bound:
                raise ValueError(
                    f"Lower bound ({self.lower_bound}) cannot exceed "
                    f"upper bound ({self.upper_bound})"
                )

        # Frequency range validation
        if self.low_frequency is not None and self.high_frequency is not None:
            if self.low_frequency > self.high_frequency:
                raise ValueError(
                    f"Low frequency ({self.low_frequency}) cannot exceed "
                    f"high frequency ({self.high_frequency})"
                )

        # Label length
        if self.label and len(self.label) > 8:
            raise ValueError(f"Constraint label must be <= 8 characters: '{self.label}'")

    def _determine_type(self):
        """Determine constraint type based on bounds."""
        if self.lower_bound is not None and self.upper_bound is not None:
            # Check for equality constraint (very tight bounds)
            if abs(self.upper_bound - self.lower_bound) < 1e-10:
                self.constraint_type = ConstraintType.EQUALITY
            else:
                self.constraint_type = ConstraintType.DOUBLE_BOUND
        elif self.lower_bound is not None:
            self.constraint_type = ConstraintType.LOWER_BOUND
        else:
            self.constraint_type = ConstraintType.UPPER_BOUND

    def to_nastran(self) -> str:
        """Generate DCONSTR card string."""
        # DCONSTR, DCID, RID, LALLOW, UALLOW, LOWFQ, HIGHFQ
        lallow = f"{self.lower_bound:.6g}" if self.lower_bound is not None else ""
        uallow = f"{self.upper_bound:.6g}" if self.upper_bound is not None else ""
        lowfq = f"{self.low_frequency:.6g}" if self.low_frequency is not None else ""
        highfq = f"{self.high_frequency:.6g}" if self.high_frequency is not None else ""

        parts = [
            "DCONSTR",
            str(self.id),
            str(self.response_id),
            lallow,
            uallow,
            lowfq,
            highfq,
        ]

        return ",".join(parts)

    def get_status(self, value: Optional[float] = None) -> ConstraintStatus:
        """
        Get the status of this constraint given a response value.

        Args:
            value: Response value to check (uses current_value if None)

        Returns:
            ConstraintStatus indicating if constraint is satisfied, active, or violated
        """
        if value is None:
            value = self.current_value

        if value is None:
            return ConstraintStatus.INACTIVE

        tolerance = 1e-6

        # Check lower bound
        if self.lower_bound is not None:
            if value < self.lower_bound - tolerance:
                return ConstraintStatus.VIOLATED_LOWER
            elif abs(value - self.lower_bound) < tolerance:
                return ConstraintStatus.ACTIVE_LOWER

        # Check upper bound
        if self.upper_bound is not None:
            if value > self.upper_bound + tolerance:
                return ConstraintStatus.VIOLATED_UPPER
            elif abs(value - self.upper_bound) < tolerance:
                return ConstraintStatus.ACTIVE_UPPER

        return ConstraintStatus.SATISFIED

    def get_margin(self, value: Optional[float] = None) -> Dict[str, Optional[float]]:
        """
        Get margin to bounds.

        Args:
            value: Response value (uses current_value if None)

        Returns:
            Dictionary with 'lower_margin' and 'upper_margin'
        """
        if value is None:
            value = self.current_value

        result = {'lower_margin': None, 'upper_margin': None}

        if value is not None:
            if self.lower_bound is not None:
                result['lower_margin'] = value - self.lower_bound
            if self.upper_bound is not None:
                result['upper_margin'] = self.upper_bound - value

        return result

    def get_normalized_value(self, value: Optional[float] = None) -> Optional[float]:
        """
        Get normalized constraint value.

        For g(x) <= 0 formulation:
        - Upper bound: g = (value - upper) / |upper|
        - Lower bound: g = (lower - value) / |lower|

        Returns:
            Normalized value where negative means satisfied, positive means violated
        """
        if value is None:
            value = self.current_value

        if value is None:
            return None

        if self.constraint_type == ConstraintType.UPPER_BOUND and self.upper_bound:
            return (value - self.upper_bound) / max(abs(self.upper_bound), 1e-10)
        elif self.constraint_type == ConstraintType.LOWER_BOUND and self.lower_bound:
            return (self.lower_bound - value) / max(abs(self.lower_bound), 1e-10)
        elif self.constraint_type == ConstraintType.DOUBLE_BOUND:
            # Return the more critical one
            upper_norm = None
            lower_norm = None
            if self.upper_bound:
                upper_norm = (value - self.upper_bound) / max(abs(self.upper_bound), 1e-10)
            if self.lower_bound:
                lower_norm = (self.lower_bound - value) / max(abs(self.lower_bound), 1e-10)

            if upper_norm is not None and lower_norm is not None:
                return max(upper_norm, lower_norm)
            return upper_norm or lower_norm

        return None

    def is_satisfied(self, value: Optional[float] = None) -> bool:
        """Check if constraint is satisfied."""
        status = self.get_status(value)
        return status in [ConstraintStatus.SATISFIED,
                         ConstraintStatus.ACTIVE_LOWER,
                         ConstraintStatus.ACTIVE_UPPER]


@dataclass
class ConstraintSet:
    """
    Set of related constraints (maps to DCONADD).

    Attributes:
        id: Constraint set ID
        name: Name for the set
        constraints: List of constraints in this set
        description: Description of the constraint set
    """
    id: int
    name: str
    constraints: List[DesignConstraint] = field(default_factory=list)
    description: str = ""

    def add_constraint(self, constraint: DesignConstraint):
        """Add a constraint to the set."""
        self.constraints.append(constraint)

    def remove_constraint(self, constraint: DesignConstraint):
        """Remove a constraint from the set."""
        self.constraints.remove(constraint)

    def get_constraint_ids(self) -> List[int]:
        """Get all constraint IDs in this set."""
        return [c.id for c in self.constraints if c.id is not None]

    def to_nastran(self) -> str:
        """Generate DCONADD card if multiple constraints."""
        if len(self.constraints) <= 1:
            return ""

        # DCONADD, DCID, DC1, DC2, DC3, ...
        parts = ["DCONADD", str(self.id)]
        parts.extend([str(c.id) for c in self.constraints if c.id])

        return ",".join(parts)

    def get_all_violations(self) -> List[DesignConstraint]:
        """Get all violated constraints."""
        return [c for c in self.constraints
                if c.get_status() in [ConstraintStatus.VIOLATED_LOWER,
                                       ConstraintStatus.VIOLATED_UPPER]]

    def get_summary(self) -> Dict[str, int]:
        """Get summary of constraint statuses."""
        summary = {
            'total': len(self.constraints),
            'satisfied': 0,
            'active': 0,
            'violated': 0,
            'unknown': 0,
        }

        for c in self.constraints:
            status = c.get_status()
            if status == ConstraintStatus.SATISFIED:
                summary['satisfied'] += 1
            elif status in [ConstraintStatus.ACTIVE_LOWER, ConstraintStatus.ACTIVE_UPPER]:
                summary['active'] += 1
            elif status in [ConstraintStatus.VIOLATED_LOWER, ConstraintStatus.VIOLATED_UPPER]:
                summary['violated'] += 1
            else:
                summary['unknown'] += 1

        return summary


class ConstraintBuilder:
    """Builder class for creating common constraint configurations."""

    def __init__(self, start_id: int = 1):
        """Initialize with starting ID."""
        self._next_id = start_id
        self._constraints: List[DesignConstraint] = []

    def _get_next_id(self) -> int:
        """Get next available ID."""
        id = self._next_id
        self._next_id += 1
        return id

    def add_upper_bound(
        self,
        response_id: int,
        upper_bound: float,
        label: str = "",
        description: str = "",
    ) -> DesignConstraint:
        """Add upper bound constraint."""
        constraint = DesignConstraint(
            id=self._get_next_id(),
            response_id=response_id,
            upper_bound=upper_bound,
            label=label,
            description=description,
        )
        self._constraints.append(constraint)
        return constraint

    def add_lower_bound(
        self,
        response_id: int,
        lower_bound: float,
        label: str = "",
        description: str = "",
    ) -> DesignConstraint:
        """Add lower bound constraint."""
        constraint = DesignConstraint(
            id=self._get_next_id(),
            response_id=response_id,
            lower_bound=lower_bound,
            label=label,
            description=description,
        )
        self._constraints.append(constraint)
        return constraint

    def add_range_constraint(
        self,
        response_id: int,
        lower_bound: float,
        upper_bound: float,
        label: str = "",
        description: str = "",
    ) -> DesignConstraint:
        """Add double-sided constraint."""
        constraint = DesignConstraint(
            id=self._get_next_id(),
            response_id=response_id,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            label=label,
            description=description,
        )
        self._constraints.append(constraint)
        return constraint

    def add_rms_acceleration_constraint(
        self,
        response_id: int,
        max_rms: float,
        label: str = "RMSACC",
        low_frequency: Optional[float] = None,
        high_frequency: Optional[float] = None,
    ) -> DesignConstraint:
        """Add RMS acceleration constraint (common in vibration optimization)."""
        constraint = DesignConstraint(
            id=self._get_next_id(),
            response_id=response_id,
            upper_bound=max_rms,
            low_frequency=low_frequency,
            high_frequency=high_frequency,
            label=label,
            description=f"RMS acceleration limit: {max_rms} m/s²",
        )
        self._constraints.append(constraint)
        return constraint

    def add_weight_constraint(
        self,
        response_id: int,
        max_weight: float,
        min_weight: Optional[float] = None,
        label: str = "WEIGHT",
    ) -> DesignConstraint:
        """Add weight constraint."""
        constraint = DesignConstraint(
            id=self._get_next_id(),
            response_id=response_id,
            lower_bound=min_weight,
            upper_bound=max_weight,
            label=label,
            description=f"Weight constraint: {min_weight or 0} - {max_weight} kg",
        )
        self._constraints.append(constraint)
        return constraint

    def get_all_constraints(self) -> List[DesignConstraint]:
        """Get all created constraints."""
        return self._constraints.copy()
