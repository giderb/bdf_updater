"""
Objective Function management for SOL200 optimization.

Handles objective function definition for optimization.

The objective in SOL200 can be:
1. A single DRESP1/DRESP2 response (minimize or maximize)
2. A weighted combination via DRESP2

Common objectives for vibration optimization:
- Minimize RMS acceleration
- Minimize weight subject to response constraints
- Minimize peak acceleration
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple
import uuid


class ObjectiveType(Enum):
    """Type of optimization objective."""
    MINIMIZE = auto()
    MAXIMIZE = auto()


class ObjectiveSense(Enum):
    """
    Sense of the objective function.

    In SOL200, minimization is the default. For maximization,
    the objective is negated.
    """
    MINIMIZE = 1.0
    MAXIMIZE = -1.0


@dataclass
class ObjectiveFunction:
    """
    Objective function definition.

    In SOL200, the objective is defined via DESOBJ case control
    referencing a response (DRESP1 or DRESP2).

    For composite objectives (e.g., weighted sum), use DRESP2
    to combine multiple responses.

    Attributes:
        response_id: ID of the response to optimize (DRESP1 or DRESP2)
        objective_type: MINIMIZE or MAXIMIZE
        label: Human-readable label
        description: Description of the objective
        target_value: Target value for tracking (not used in optimization)
        weight: Weight factor (for reference only, actual weighting in DRESP2)
        is_composite: True if this uses a DRESP2 combining multiple responses
        component_responses: For composite, the component response IDs and weights
    """
    response_id: int
    objective_type: ObjectiveType = ObjectiveType.MINIMIZE
    label: str = "OBJECTIVE"
    description: str = ""
    target_value: Optional[float] = None
    weight: float = 1.0
    is_composite: bool = False
    component_responses: List[Tuple[int, float]] = field(default_factory=list)
    _uuid: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    def __post_init__(self):
        """Validate objective."""
        self._validate()

    def _validate(self):
        """Validate objective parameters."""
        if len(self.label) > 8:
            raise ValueError(f"Objective label must be <= 8 characters: '{self.label}'")

        if self.weight <= 0:
            raise ValueError(f"Weight must be positive: {self.weight}")

    def to_case_control(self) -> str:
        """Generate DESOBJ case control command."""
        # DESOBJ = RID or DESOBJ(MIN/MAX) = RID
        sense = "MIN" if self.objective_type == ObjectiveType.MINIMIZE else "MAX"
        return f"DESOBJ({sense}) = {self.response_id}"

    def get_sense_multiplier(self) -> float:
        """Get multiplier for objective sense (1.0 for min, -1.0 for max)."""
        return ObjectiveSense.MINIMIZE.value if self.objective_type == ObjectiveType.MINIMIZE else ObjectiveSense.MAXIMIZE.value


@dataclass
class ObjectiveConfiguration:
    """
    Complete objective configuration for the optimization.

    Supports single and multi-objective formulations.

    Attributes:
        primary_objective: Main objective function
        secondary_objectives: Additional objectives (for Pareto, etc.)
        normalization: Normalization values for objectives
    """
    primary_objective: ObjectiveFunction
    secondary_objectives: List[ObjectiveFunction] = field(default_factory=list)
    normalization: Dict[int, float] = field(default_factory=dict)

    def get_all_objectives(self) -> List[ObjectiveFunction]:
        """Get all objective functions."""
        return [self.primary_objective] + self.secondary_objectives

    def to_case_control(self) -> str:
        """Generate case control for primary objective."""
        return self.primary_objective.to_case_control()


class RMSObjectiveBuilder:
    """
    Builder for creating RMS acceleration objective.

    Creates the necessary DRESP1, DRESP2, and DEQATN cards for
    RMS calculation over a frequency range.
    """

    def __init__(self, base_id: int = 1000):
        """Initialize the builder."""
        self._next_dresp_id = base_id
        self._next_deqatn_id = base_id
        self.acceleration_responses: List[int] = []
        self.frequency_points: List[float] = []

    def add_acceleration_point(
        self,
        node_id: int,
        dof: int,
        frequency: float,
    ) -> int:
        """
        Add an acceleration response at a specific frequency.

        Returns the DRESP1 ID.
        """
        dresp_id = self._next_dresp_id
        self._next_dresp_id += 1
        self.acceleration_responses.append(dresp_id)
        self.frequency_points.append(frequency)
        return dresp_id

    def build_rms_equation(self) -> Tuple[int, str]:
        """
        Build DEQATN for RMS calculation.

        RMS = sqrt(sum(Ai^2) / N)

        Returns:
            Tuple of (equation_id, DEQATN card string)
        """
        n = len(self.acceleration_responses)
        if n == 0:
            raise ValueError("No acceleration responses defined")

        eq_id = self._next_deqatn_id
        self._next_deqatn_id += 1

        # Build RMS equation
        # For N responses: RMS = SQRT((R1^2 + R2^2 + ... + RN^2) / N)
        sum_terms = " + ".join([f"R{i+1}**2" for i in range(n)])
        equation = f"RMS(R1"
        for i in range(2, n + 1):
            equation += f",R{i}"
        equation += f") = SQRT(({sum_terms}) / {n})"

        # DEQATN card format
        deqatn = f"DEQATN  {eq_id}       {equation}"

        return eq_id, deqatn

    def build_rms_dresp2(self, label: str = "RMSACC") -> Tuple[int, str, str]:
        """
        Build complete RMS response.

        Returns:
            Tuple of (dresp2_id, DRESP2 card string, DEQATN card string)
        """
        eq_id, deqatn = self.build_rms_equation()

        dresp2_id = self._next_dresp_id
        self._next_dresp_id += 1

        # DRESP2 card
        dresp2_parts = [
            f"DRESP2,{dresp2_id},{label},{eq_id},,,,",
            "+,DRESP1," + ",".join(str(r) for r in self.acceleration_responses),
        ]
        dresp2 = "\n".join(dresp2_parts)

        return dresp2_id, dresp2, deqatn


class WeightedSumObjectiveBuilder:
    """
    Builder for weighted sum of multiple responses.

    Creates DRESP2 with DEQATN for: sum(wi * Ri)
    """

    def __init__(self, base_id: int = 2000):
        """Initialize the builder."""
        self._next_id = base_id
        self.responses: List[Tuple[int, float]] = []

    def add_response(self, response_id: int, weight: float = 1.0):
        """Add a response with its weight."""
        self.responses.append((response_id, weight))

    def build(self, label: str = "WSUM") -> Tuple[int, str, str]:
        """
        Build weighted sum response.

        Returns:
            Tuple of (dresp2_id, DRESP2 card, DEQATN card)
        """
        n = len(self.responses)
        if n == 0:
            raise ValueError("No responses defined")

        eq_id = self._next_id
        dresp2_id = self._next_id + 1
        self._next_id += 2

        # Build equation: WSUM = w1*R1 + w2*R2 + ...
        args = ",".join([f"R{i+1}" for i in range(n)])
        terms = " + ".join([f"{w:.6g}*R{i+1}" for i, (_, w) in enumerate(self.responses)])
        equation = f"WSUM({args}) = {terms}"

        deqatn = f"DEQATN  {eq_id}       {equation}"

        # DRESP2
        dresp2_parts = [
            f"DRESP2,{dresp2_id},{label},{eq_id},,,,",
            "+,DRESP1," + ",".join(str(r) for r, _ in self.responses),
        ]
        dresp2 = "\n".join(dresp2_parts)

        return dresp2_id, dresp2, deqatn


@dataclass
class OptimizationObjective:
    """
    High-level optimization objective specification.

    This is the user-facing class that describes what to optimize.
    """
    name: str
    description: str
    objective_type: ObjectiveType
    target_response: str  # Description like "RMS Acceleration at Node 100"
    response_id: Optional[int] = None

    # For RMS-type objectives
    node_ids: List[int] = field(default_factory=list)
    dof: int = 3  # Default to Z direction
    frequency_range: Optional[Tuple[float, float]] = None

    # For weight objectives
    include_weight: bool = False
    weight_factor: float = 0.0

    def get_objective_summary(self) -> str:
        """Get human-readable summary."""
        action = "Minimize" if self.objective_type == ObjectiveType.MINIMIZE else "Maximize"
        return f"{action} {self.name}: {self.target_response}"
