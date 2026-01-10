"""
Complete Optimization Model for SOL200.

Ties together all components:
- BDF model
- Design variables
- Responses
- Constraints
- Objective
- Equations

Generates complete SOL200 input deck.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import json
import yaml

from .bdf_manager import BDFManager, PropertyInfo
from .design_variable import (
    DesignVariable, DesignVariableLink, PropertyType, PropertyField, LinkType
)
from .response import DesignResponse, ResponseType, ResponseBuilder
from .constraint import DesignConstraint, ConstraintSet, ConstraintBuilder
from .objective import ObjectiveFunction, ObjectiveType
from .equation_parser import EquationParser, ParsedEquation


@dataclass
class OptimizationParameters:
    """
    Optimization control parameters (DOPTPRM).

    Attributes:
        max_iterations: Maximum number of design cycles (DESMAX)
        convergence_tolerance: Convergence criteria (CONV1, CONV2)
        constraint_tolerance: Constraint tolerance (CTOL)
        move_limit: Global move limit (DELP)
        method: Optimization method (METHOD)
        print_level: Output print level (P1, P2)
    """
    max_iterations: int = 30
    conv1: float = 0.001  # Objective convergence
    conv2: float = 0.001  # Design variable convergence
    ctol: float = 0.003   # Constraint tolerance
    delp: float = 0.2     # Move limit (20%)
    dpmin: float = 0.01   # Minimum move
    method: str = "MSCADS"  # Optimization method
    p1: int = 1           # Print level 1
    p2: int = 1           # Print level 2

    def to_nastran(self) -> str:
        """Generate DOPTPRM card."""
        lines = [
            f"DOPTPRM,DESMAX,{self.max_iterations},CONV1,{self.conv1:.6g},",
            f"+,CONV2,{self.conv2:.6g},CTOL,{self.ctol:.6g},DELP,{self.delp:.3f},",
            f"+,DPMIN,{self.dpmin:.6g},P1,{self.p1},P2,{self.p2}"
        ]
        return "\n".join(lines)


class OptimizationModel:
    """
    Complete optimization model for SOL200.

    Manages all aspects of the optimization setup:
    - Model (BDF)
    - Design variables and links
    - Responses
    - Constraints
    - Objective
    - Equations
    """

    def __init__(self, name: str = "Optimization"):
        """Initialize the optimization model."""
        self.name = name
        self.bdf_manager = BDFManager()

        # ID counters
        self._next_desvar_id = 1
        self._next_dvprel_id = 1
        self._next_dresp_id = 1
        self._next_dconstr_id = 1
        self._next_deqatn_id = 1

        # Collections
        self.design_variables: Dict[int, DesignVariable] = {}
        self.variable_links: Dict[int, DesignVariableLink] = {}
        self.responses: Dict[int, DesignResponse] = {}
        self.constraints: Dict[int, DesignConstraint] = {}
        self.equations: Dict[int, ParsedEquation] = {}

        # Objective
        self.objective: Optional[ObjectiveFunction] = None

        # Parameters
        self.parameters = OptimizationParameters()

        # Equation parser
        self.equation_parser = EquationParser()

        # Subcase configuration
        self.subcases: Dict[int, Dict] = {
            1: {
                'label': 'Frequency Response',
                'analysis': 'FRRESPONSE',
                'spc': None,
                'load': None,
            }
        }

    def load_bdf(self, bdf_path: Union[str, Path]):
        """Load the base BDF model."""
        return self.bdf_manager.load(bdf_path)

    # === Design Variable Management ===

    def add_design_variable(
        self,
        label: str,
        initial_value: float,
        lower_bound: float,
        upper_bound: float,
        description: str = "",
        unit: str = "",
    ) -> DesignVariable:
        """
        Add a design variable.

        Args:
            label: 8-char label
            initial_value: Starting value
            lower_bound: Minimum allowed
            upper_bound: Maximum allowed
            description: Human-readable description
            unit: Engineering unit

        Returns:
            Created DesignVariable
        """
        dv = DesignVariable(
            id=self._next_desvar_id,
            label=label,
            initial_value=initial_value,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            description=description,
            unit=unit,
        )
        self._next_desvar_id += 1
        self.design_variables[dv.id] = dv
        return dv

    def link_variable_to_property(
        self,
        design_variable: DesignVariable,
        property_type: PropertyType,
        property_id: int,
        field: PropertyField,
        coefficient: float = 1.0,
        constant: float = 0.0,
        p_min: Optional[float] = None,
        p_max: Optional[float] = None,
    ) -> DesignVariableLink:
        """
        Link a design variable to a property field.

        Args:
            design_variable: The design variable
            property_type: Type of property (PSHELL, PBAR, etc.)
            property_id: Property card ID
            field: Property field to link
            coefficient: Linear coefficient
            constant: Constant offset
            p_min: Minimum property value
            p_max: Maximum property value

        Returns:
            Created DesignVariableLink
        """
        link = DesignVariableLink(
            id=self._next_dvprel_id,
            property_type=property_type,
            property_id=property_id,
            field=field,
            link_type=LinkType.DVPREL1,
            design_variables=[(design_variable, coefficient)],
            constant=constant,
            p_min=p_min,
            p_max=p_max,
        )
        self._next_dvprel_id += 1
        self.variable_links[link.id] = link
        return link

    def create_thickness_design_variable(
        self,
        property_id: int,
        label: str,
        lower_bound: float,
        upper_bound: float,
        initial_value: Optional[float] = None,
    ) -> Tuple[DesignVariable, DesignVariableLink]:
        """
        Convenience method to create a thickness design variable.

        Args:
            property_id: PSHELL property ID
            label: Variable label
            lower_bound: Min thickness
            upper_bound: Max thickness
            initial_value: Initial thickness (reads from model if None)

        Returns:
            Tuple of (DesignVariable, DesignVariableLink)
        """
        # Get current value from model
        if initial_value is None:
            prop = self.bdf_manager.get_property(property_id)
            if prop and prop.type == 'PSHELL':
                initial_value = prop.data.get('thickness', (lower_bound + upper_bound) / 2)
            else:
                initial_value = (lower_bound + upper_bound) / 2

        dv = self.add_design_variable(
            label=label,
            initial_value=initial_value,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            description=f"Thickness for PSHELL {property_id}",
            unit="m",
        )

        link = self.link_variable_to_property(
            design_variable=dv,
            property_type=PropertyType.PSHELL,
            property_id=property_id,
            field=PropertyField.PSHELL_T,
            coefficient=1.0,
            p_min=lower_bound,
            p_max=upper_bound,
        )

        return dv, link

    # === Response Management ===

    def add_response(self, response: DesignResponse) -> DesignResponse:
        """Add a design response."""
        if response.id is None:
            response.id = self._next_dresp_id
            self._next_dresp_id += 1
        self.responses[response.id] = response
        return response

    def add_acceleration_response(
        self,
        node_id: int,
        dof: int,
        frequency: float,
        label: Optional[str] = None,
    ) -> DesignResponse:
        """
        Add frequency response acceleration (DRESP1).

        Args:
            node_id: Grid point ID
            dof: Degree of freedom (1-6)
            frequency: Frequency in Hz
            label: Response label

        Returns:
            Created DesignResponse
        """
        if label is None:
            label = f"AC{node_id}"[:8]

        response = DesignResponse(
            id=self._next_dresp_id,
            label=label,
            response_type=ResponseType.FRACCL,
            atta=3,  # Magnitude
            attb=frequency,
            atti=[node_id * 10 + dof],
            description=f"Acceleration at node {node_id}, DOF {dof}, {frequency} Hz",
            unit="m/s²",
        )
        self._next_dresp_id += 1
        self.responses[response.id] = response
        return response

    def add_weight_response(self, label: str = "WEIGHT") -> DesignResponse:
        """Add total weight response."""
        response = DesignResponse(
            id=self._next_dresp_id,
            label=label,
            response_type=ResponseType.WEIGHT,
            description="Total structural weight",
            unit="kg",
        )
        self._next_dresp_id += 1
        self.responses[response.id] = response
        return response

    def add_rms_response(
        self,
        base_response_ids: List[int],
        label: str = "RMSACC",
    ) -> Tuple[DesignResponse, ParsedEquation]:
        """
        Add RMS response combining multiple frequency point responses.

        Args:
            base_response_ids: List of DRESP1 IDs to combine
            label: Response label

        Returns:
            Tuple of (DRESP2 response, DEQATN equation)
        """
        n = len(base_response_ids)
        equation = self.equation_parser.create_rms_equation(n)
        equation.id = self._next_deqatn_id
        self._next_deqatn_id += 1
        self.equations[equation.id] = equation

        response = DesignResponse(
            id=self._next_dresp_id,
            label=label,
            response_type=ResponseType.EQUATION,
            is_synthetic=True,
            equation_id=equation.id,
            referenced_responses=base_response_ids,
            description="RMS acceleration",
            unit="m/s²",
        )
        self._next_dresp_id += 1
        self.responses[response.id] = response

        return response, equation

    # === Constraint Management ===

    def add_constraint(
        self,
        response_id: int,
        upper_bound: Optional[float] = None,
        lower_bound: Optional[float] = None,
        label: str = "",
    ) -> DesignConstraint:
        """Add a design constraint."""
        constraint = DesignConstraint(
            id=self._next_dconstr_id,
            response_id=response_id,
            upper_bound=upper_bound,
            lower_bound=lower_bound,
            label=label,
        )
        self._next_dconstr_id += 1
        self.constraints[constraint.id] = constraint
        return constraint

    def add_acceleration_constraint(
        self,
        response_id: int,
        max_acceleration: float,
        label: str = "ACCLIM",
    ) -> DesignConstraint:
        """Add constraint on acceleration response."""
        return self.add_constraint(
            response_id=response_id,
            upper_bound=max_acceleration,
            label=label,
        )

    def add_weight_constraint(
        self,
        response_id: int,
        max_weight: float,
        min_weight: Optional[float] = None,
        label: str = "WTLIM",
    ) -> DesignConstraint:
        """Add constraint on weight."""
        return self.add_constraint(
            response_id=response_id,
            upper_bound=max_weight,
            lower_bound=min_weight,
            label=label,
        )

    # === Objective Management ===

    def set_objective(
        self,
        response_id: int,
        objective_type: ObjectiveType = ObjectiveType.MINIMIZE,
        label: str = "OBJ",
    ):
        """
        Set the optimization objective.

        Args:
            response_id: Response to optimize
            objective_type: MINIMIZE or MAXIMIZE
            label: Objective label
        """
        self.objective = ObjectiveFunction(
            response_id=response_id,
            objective_type=objective_type,
            label=label,
        )

    # === Card Generation ===

    def generate_desvar_cards(self) -> List[str]:
        """Generate all DESVAR cards."""
        return [dv.to_nastran() for dv in self.design_variables.values()]

    def generate_dvprel_cards(self) -> List[str]:
        """Generate all DVPREL cards."""
        return [link.to_nastran() for link in self.variable_links.values()]

    def generate_dresp_cards(self) -> List[str]:
        """Generate all DRESP cards."""
        return [resp.to_nastran() for resp in self.responses.values()]

    def generate_dconstr_cards(self) -> List[str]:
        """Generate all DCONSTR cards."""
        return [constr.to_nastran() for constr in self.constraints.values()]

    def generate_deqatn_cards(self) -> List[str]:
        """Generate all DEQATN cards."""
        return [eq.to_deqatn() for eq in self.equations.values()]

    def generate_doptprm_card(self) -> str:
        """Generate DOPTPRM card."""
        return self.parameters.to_nastran()

    def generate_case_control(self) -> List[str]:
        """Generate case control commands."""
        commands = []

        # Analysis disciplines
        commands.append("ANALYSIS = FREQ")

        # Objective
        if self.objective:
            commands.append(self.objective.to_case_control())

        # Constraints (reference all DCONSTR)
        if self.constraints:
            dconstr_ids = list(self.constraints.keys())
            commands.append(f"DESSUB = {dconstr_ids[0]}")

        return commands

    # === Complete Model Export ===

    def export_sol200(
        self,
        output_path: Union[str, Path],
        include_original: bool = True,
    ) -> Path:
        """
        Export complete SOL200 input deck.

        Args:
            output_path: Output file path
            include_original: Include original model data

        Returns:
            Path to exported file
        """
        output_path = Path(output_path)

        # Collect all cards
        desvar_cards = self.generate_desvar_cards()
        dvprel_cards = self.generate_dvprel_cards()
        dresp_cards = self.generate_dresp_cards()
        dconstr_cards = self.generate_dconstr_cards()
        deqatn_cards = self.generate_deqatn_cards()
        doptprm_card = self.generate_doptprm_card()

        # Add to BDF manager
        self.bdf_manager.set_solution(200)
        self.bdf_manager.add_case_control(self.generate_case_control())
        self.bdf_manager.add_optimization_cards(
            desvar_cards=desvar_cards,
            dvprel_cards=dvprel_cards,
            dresp_cards=dresp_cards,
            dconstr_cards=dconstr_cards,
            deqatn_cards=deqatn_cards,
            doptprm_card=doptprm_card,
        )

        return self.bdf_manager.save(output_path)

    # === Validation ===

    def validate(self) -> List[str]:
        """
        Validate the optimization model.

        Returns:
            List of validation issues
        """
        issues = []

        # Check BDF
        issues.extend(self.bdf_manager.validate_for_sol200())

        # Check design variables
        if not self.design_variables:
            issues.append("ERROR: No design variables defined")

        # Check responses
        if not self.responses:
            issues.append("ERROR: No design responses defined")

        # Check objective
        if self.objective is None:
            issues.append("ERROR: No objective function defined")
        else:
            if self.objective.response_id not in self.responses:
                issues.append(
                    f"ERROR: Objective references unknown response {self.objective.response_id}"
                )

        # Check constraints reference valid responses
        for cid, constraint in self.constraints.items():
            if constraint.response_id not in self.responses:
                issues.append(
                    f"ERROR: Constraint {cid} references unknown response {constraint.response_id}"
                )

        # Check DVPREL references valid design variables
        for link in self.variable_links.values():
            for dv, _ in link.design_variables:
                if dv.id not in self.design_variables:
                    issues.append(
                        f"ERROR: DVPREL {link.id} references unknown DESVAR {dv.id}"
                    )

        return issues

    # === Serialization ===

    def to_dict(self) -> Dict:
        """Serialize model to dictionary."""
        return {
            'name': self.name,
            'bdf_path': str(self.bdf_manager.bdf_path) if self.bdf_manager.bdf_path else None,
            'design_variables': {
                id: {
                    'label': dv.label,
                    'initial': dv.initial_value,
                    'lower': dv.lower_bound,
                    'upper': dv.upper_bound,
                    'description': dv.description,
                }
                for id, dv in self.design_variables.items()
            },
            'parameters': {
                'max_iterations': self.parameters.max_iterations,
                'conv1': self.parameters.conv1,
                'conv2': self.parameters.conv2,
            },
        }

    def save_project(self, path: Union[str, Path]):
        """Save project to YAML file."""
        with open(path, 'w') as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False)

    @classmethod
    def load_project(cls, path: Union[str, Path]) -> 'OptimizationModel':
        """Load project from YAML file."""
        with open(path, 'r') as f:
            data = yaml.safe_load(f)

        model = cls(name=data.get('name', 'Optimization'))

        if data.get('bdf_path'):
            model.load_bdf(data['bdf_path'])

        return model
