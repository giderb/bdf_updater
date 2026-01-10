"""
Design Response management for SOL200 optimization.

Handles DRESP1 and DRESP2 cards for defining responses.

DRESP1 Format (direct responses):
    DRESP1, ID, LABEL, RTYPE, PTYPE, REGION, ATTA, ATTB, ATTi

DRESP2 Format (synthetic responses using equations):
    DRESP2, ID, LABEL, EQID, REGION, METHOD,
            DESVAR, DVID1, DVID2, ...,
            DRESP1, RID1, RID2, ...

Key response types for SOL111 (frequency response):
    - FRACCL: Acceleration response (real/imag or magnitude/phase)
    - FRDISP: Displacement response
    - FRVEL: Velocity response
    - FRSTRE: Stress response
    - FRFORC: Force response
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Set, Tuple, Union
import uuid


class ResponseType(Enum):
    """Response types for DRESP1."""

    # Static responses (SOL101)
    WEIGHT = "WEIGHT"       # Total weight
    VOLUME = "VOLUME"       # Total volume
    DISP = "DISP"          # Static displacement
    STRESS = "STRESS"      # Static stress
    STRAIN = "STRAIN"      # Static strain
    FORCE = "FORCE"        # Element force
    CSTRESS = "CSTRESS"    # Composite stress
    CSTRAIN = "CSTRAIN"    # Composite strain

    # Frequency response (SOL111)
    FRACCL = "FRACCL"      # Frequency response acceleration
    FRDISP = "FRDISP"      # Frequency response displacement
    FRVEL = "FRVEL"        # Frequency response velocity
    FRSTRE = "FRSTRE"      # Frequency response stress
    FRFORC = "FRFORC"      # Frequency response force

    # Modal responses (SOL103)
    EIGN = "EIGN"          # Eigenvalue
    FREQ = "FREQ"          # Natural frequency
    LAMA = "LAMA"          # Eigenvalue (lambda)

    # Synthetic (DRESP2)
    EQUATION = "EQUATION"  # Equation-based response


class ResponseAttribute(Enum):
    """
    Attributes for frequency response components.

    For complex responses, ATTA specifies the component:
    - 1: Real part
    - 2: Imaginary part
    - 3: Magnitude
    - 4: Phase
    - 7: RMS (requires DRESP2)
    """
    REAL = 1
    IMAGINARY = 2
    MAGNITUDE = 3
    PHASE = 4
    RMS = 7  # Root Mean Square - typically computed via DRESP2

    @classmethod
    def get_description(cls, attr: 'ResponseAttribute') -> str:
        """Get human-readable description."""
        descriptions = {
            cls.REAL: "Real Part",
            cls.IMAGINARY: "Imaginary Part",
            cls.MAGNITUDE: "Magnitude",
            cls.PHASE: "Phase Angle",
            cls.RMS: "Root Mean Square",
        }
        return descriptions.get(attr, str(attr))


class DOFType(Enum):
    """Degrees of freedom for response extraction."""
    T1 = 1  # Translation X
    T2 = 2  # Translation Y
    T3 = 3  # Translation Z
    R1 = 4  # Rotation X
    R2 = 5  # Rotation Y
    R3 = 6  # Rotation Z

    @classmethod
    def get_translation_dofs(cls) -> List['DOFType']:
        """Get translational DOFs."""
        return [cls.T1, cls.T2, cls.T3]

    @classmethod
    def get_rotation_dofs(cls) -> List['DOFType']:
        """Get rotational DOFs."""
        return [cls.R1, cls.R2, cls.R3]


@dataclass
class DesignResponse:
    """
    Design response definition (DRESP1 or DRESP2).

    Attributes:
        id: Unique identifier
        label: 8-character label
        response_type: Type of response (FRACCL, DISP, etc.)
        property_type: Property type for element responses (optional)
        region: Region ID for screening (optional)
        atta: First attribute (component for complex, item code)
        attb: Second attribute (mode/frequency)
        atti: List of grid/element IDs
        is_synthetic: True if this is a DRESP2 (equation-based)
        equation_id: DEQATN ID for DRESP2
        referenced_responses: List of DRESP1 IDs for DRESP2
        referenced_desvars: List of DESVAR IDs for DRESP2
        description: Human-readable description
        unit: Engineering unit
    """
    label: str
    response_type: ResponseType
    id: Optional[int] = None
    property_type: Optional[str] = None
    region: Optional[int] = None
    atta: Optional[int] = None
    attb: Optional[Union[int, float]] = None
    atti: List[int] = field(default_factory=list)
    is_synthetic: bool = False
    equation_id: Optional[int] = None
    referenced_responses: List[int] = field(default_factory=list)
    referenced_desvars: List[int] = field(default_factory=list)
    description: str = ""
    unit: str = ""
    _uuid: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    def __post_init__(self):
        """Validate response parameters."""
        self._validate()

    def _validate(self):
        """Validate response configuration."""
        # Label validation
        if len(self.label) > 8:
            raise ValueError(f"Response label must be <= 8 characters: '{self.label}'")

        # Synthetic response validation
        if self.is_synthetic:
            if self.equation_id is None:
                raise ValueError("Synthetic response (DRESP2) requires equation_id")
        else:
            # DRESP1 requires atti for most response types
            if self.response_type not in [ResponseType.WEIGHT, ResponseType.VOLUME]:
                if not self.atti:
                    pass  # Some responses don't need atti

    def to_nastran(self) -> str:
        """Generate DRESP1 or DRESP2 card string."""
        if self.is_synthetic:
            return self._to_dresp2()
        else:
            return self._to_dresp1()

    def _to_dresp1(self) -> str:
        """Generate DRESP1 card."""
        # DRESP1, ID, LABEL, RTYPE, PTYPE, REGION, ATTA, ATTB, ATT1, ATT2, ...
        ptype = self.property_type if self.property_type else ""
        region = str(self.region) if self.region else ""
        atta = str(self.atta) if self.atta is not None else ""
        attb = str(self.attb) if self.attb is not None else ""

        parts = [
            "DRESP1",
            str(self.id),
            self.label,
            self.response_type.value,
            ptype,
            region,
            atta,
            attb,
        ]

        # Add ATTi (grid/element IDs)
        if self.atti:
            # First line can have some ATTi
            first_batch = self.atti[:1]
            remaining = self.atti[1:]

            for att in first_batch:
                parts.append(str(att))

            lines = [",".join(parts)]

            # Continuation lines for remaining ATTi
            while remaining:
                batch = remaining[:8]
                remaining = remaining[8:]
                cont_parts = ["+"] + [str(att) for att in batch]
                lines.append(",".join(cont_parts))

            return "\n".join(lines)
        else:
            return ",".join(parts)

    def _to_dresp2(self) -> str:
        """Generate DRESP2 card."""
        # DRESP2, ID, LABEL, EQID, REGION, METHOD, C1, C2, C3
        #         DESVAR, DVID1, DVID2, ...
        #         DRESP1, RID1, RID2, ...
        region = str(self.region) if self.region else ""

        lines = []

        line1 = f"DRESP2,{self.id},{self.label},{self.equation_id},{region},,"
        lines.append(line1)

        # Design variable references
        if self.referenced_desvars:
            parts = ["+", "DESVAR"]
            for dvid in self.referenced_desvars:
                parts.append(str(dvid))
            lines.append(",".join(parts))

        # DRESP1 references
        if self.referenced_responses:
            parts = ["+", "DRESP1"]
            for rid in self.referenced_responses:
                parts.append(str(rid))
            lines.append(",".join(parts))

        return "\n".join(lines)


@dataclass
class FrequencyResponseConfig:
    """
    Configuration for frequency response extraction.

    Attributes:
        node_ids: List of grid point IDs for response extraction
        dofs: Degrees of freedom to extract
        frequency_range: (min_freq, max_freq) in Hz
        frequency_values: Specific frequencies (alternative to range)
        response_attribute: Real, Imag, Magnitude, or Phase
        subcase_id: Subcase for the frequency response
    """
    node_ids: List[int]
    dofs: List[DOFType] = field(default_factory=lambda: [DOFType.T3])
    frequency_range: Optional[Tuple[float, float]] = None
    frequency_values: Optional[List[float]] = None
    response_attribute: ResponseAttribute = ResponseAttribute.MAGNITUDE
    subcase_id: int = 1

    def __post_init__(self):
        """Validate configuration."""
        if not self.node_ids:
            raise ValueError("At least one node ID is required")

        if self.frequency_range and self.frequency_values:
            raise ValueError("Specify either frequency_range or frequency_values, not both")

    def get_frequencies(self) -> List[float]:
        """Get list of frequencies for response extraction."""
        if self.frequency_values:
            return sorted(self.frequency_values)
        elif self.frequency_range:
            # This would be defined by FREQ cards in the model
            return []
        return []


@dataclass
class RMSResponseConfig:
    """
    Configuration for RMS (Root Mean Square) acceleration response.

    RMS is computed as: sqrt(sum(Ai^2) / N) over frequency range
    where Ai is the acceleration magnitude at frequency i.

    This requires DRESP2 with DEQATN to compute.

    Attributes:
        base_responses: List of DRESP1 IDs for individual frequency responses
        label: Label for the RMS response
        node_id: Grid point for the response
        dof: Degree of freedom
        weight_by_frequency: If True, weight by frequency bandwidth
    """
    base_responses: List[int]
    label: str
    node_id: int
    dof: DOFType = DOFType.T3
    weight_by_frequency: bool = False

    def __post_init__(self):
        """Validate configuration."""
        if not self.base_responses:
            raise ValueError("At least one base response is required for RMS")

        if len(self.label) > 8:
            raise ValueError(f"RMS label must be <= 8 characters: '{self.label}'")

    def create_rms_dresp2(self, dresp2_id: int, equation_id: int) -> DesignResponse:
        """Create DRESP2 for RMS calculation."""
        return DesignResponse(
            id=dresp2_id,
            label=self.label,
            response_type=ResponseType.EQUATION,
            is_synthetic=True,
            equation_id=equation_id,
            referenced_responses=self.base_responses.copy(),
            description=f"RMS acceleration at node {self.node_id}, DOF {self.dof.value}",
            unit="m/s²",
        )


class ResponseBuilder:
    """Builder class for creating common response configurations."""

    def __init__(self, start_id: int = 1):
        """Initialize with starting ID."""
        self._next_id = start_id
        self._responses: List[DesignResponse] = []

    def _get_next_id(self) -> int:
        """Get next available ID."""
        id = self._next_id
        self._next_id += 1
        return id

    def add_acceleration_response(
        self,
        node_id: int,
        dof: DOFType,
        frequency: float,
        attribute: ResponseAttribute = ResponseAttribute.MAGNITUDE,
        label: Optional[str] = None,
    ) -> DesignResponse:
        """Add a frequency response acceleration at a specific frequency."""
        if label is None:
            label = f"ACC{node_id}"[:8]

        response = DesignResponse(
            id=self._get_next_id(),
            label=label,
            response_type=ResponseType.FRACCL,
            atta=attribute.value,
            attb=frequency,  # Frequency in Hz
            atti=[node_id * 10 + dof.value],  # Grid point + DOF
            description=f"Acceleration at node {node_id}, DOF {dof.value}, freq {frequency} Hz",
            unit="m/s²",
        )
        self._responses.append(response)
        return response

    def add_displacement_response(
        self,
        node_id: int,
        dof: DOFType,
        frequency: float,
        attribute: ResponseAttribute = ResponseAttribute.MAGNITUDE,
        label: Optional[str] = None,
    ) -> DesignResponse:
        """Add a frequency response displacement at a specific frequency."""
        if label is None:
            label = f"DISP{node_id}"[:8]

        response = DesignResponse(
            id=self._get_next_id(),
            label=label,
            response_type=ResponseType.FRDISP,
            atta=attribute.value,
            attb=frequency,
            atti=[node_id * 10 + dof.value],
            description=f"Displacement at node {node_id}, DOF {dof.value}, freq {frequency} Hz",
            unit="m",
        )
        self._responses.append(response)
        return response

    def add_weight_response(self, label: str = "WEIGHT") -> DesignResponse:
        """Add total weight response."""
        response = DesignResponse(
            id=self._get_next_id(),
            label=label,
            response_type=ResponseType.WEIGHT,
            description="Total structural weight",
            unit="kg",
        )
        self._responses.append(response)
        return response

    def add_frequency_response(
        self,
        mode_number: int,
        label: Optional[str] = None,
    ) -> DesignResponse:
        """Add natural frequency response for a mode."""
        if label is None:
            label = f"FREQ{mode_number}"[:8]

        response = DesignResponse(
            id=self._get_next_id(),
            label=label,
            response_type=ResponseType.FREQ,
            atta=mode_number,
            description=f"Natural frequency of mode {mode_number}",
            unit="Hz",
        )
        self._responses.append(response)
        return response

    def get_all_responses(self) -> List[DesignResponse]:
        """Get all created responses."""
        return self._responses.copy()

    def get_response_by_id(self, response_id: int) -> Optional[DesignResponse]:
        """Get a response by its ID."""
        for r in self._responses:
            if r.id == response_id:
                return r
        return None
