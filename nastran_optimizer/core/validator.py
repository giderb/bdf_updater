"""
Model Validator for SOL200 optimization.

Comprehensive validation of optimization models before execution.
Ensures aerospace-grade safety through rigorous checks.

Validation categories:
1. Structural integrity - BDF model completeness
2. Design variable bounds - Physical feasibility
3. Response definitions - Valid response configurations
4. Constraint consistency - Non-conflicting constraints
5. Optimization setup - Complete and consistent setup
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Set, Tuple
import math


class ValidationSeverity(Enum):
    """Severity levels for validation messages."""
    INFO = auto()      # Informational message
    WARNING = auto()   # Potential issue
    ERROR = auto()     # Must be fixed before running
    CRITICAL = auto()  # Serious structural issue


@dataclass
class ValidationResult:
    """
    Result of a validation check.

    Attributes:
        severity: Issue severity level
        category: Validation category
        message: Human-readable message
        details: Additional details
        suggestion: Suggested fix
        location: Where the issue was found
    """
    severity: ValidationSeverity
    category: str
    message: str
    details: str = ""
    suggestion: str = ""
    location: str = ""

    def __str__(self) -> str:
        """String representation."""
        sev = self.severity.name
        return f"[{sev}] {self.category}: {self.message}"

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'severity': self.severity.name,
            'category': self.category,
            'message': self.message,
            'details': self.details,
            'suggestion': self.suggestion,
            'location': self.location,
        }


class ModelValidator:
    """
    Comprehensive validator for SOL200 optimization models.

    Performs multiple validation passes to ensure model integrity
    and optimization feasibility.
    """

    def __init__(self):
        """Initialize the validator."""
        self.results: List[ValidationResult] = []
        self._error_count = 0
        self._warning_count = 0

    def clear(self):
        """Clear previous validation results."""
        self.results.clear()
        self._error_count = 0
        self._warning_count = 0

    def add_result(self, result: ValidationResult):
        """Add a validation result."""
        self.results.append(result)
        if result.severity == ValidationSeverity.ERROR:
            self._error_count += 1
        elif result.severity == ValidationSeverity.WARNING:
            self._warning_count += 1

    def validate(self, model) -> List[ValidationResult]:
        """
        Perform complete validation of an optimization model.

        Args:
            model: OptimizationModel to validate

        Returns:
            List of ValidationResult objects
        """
        self.clear()

        # Run all validation checks
        self._validate_bdf_model(model)
        self._validate_design_variables(model)
        self._validate_variable_links(model)
        self._validate_responses(model)
        self._validate_constraints(model)
        self._validate_objective(model)
        self._validate_parameters(model)
        self._validate_cross_references(model)
        self._validate_physical_feasibility(model)

        return self.results

    def _validate_bdf_model(self, model):
        """Validate the base BDF model."""
        category = "BDF Model"

        if not model.bdf_manager.is_loaded:
            self.add_result(ValidationResult(
                severity=ValidationSeverity.ERROR,
                category=category,
                message="No BDF model loaded",
                suggestion="Load a BDF file before setting up optimization",
            ))
            return

        summary = model.bdf_manager.get_summary()

        # Check for nodes
        if summary.num_nodes == 0:
            self.add_result(ValidationResult(
                severity=ValidationSeverity.ERROR,
                category=category,
                message="Model has no grid points",
            ))

        # Check for elements
        if summary.num_elements == 0:
            self.add_result(ValidationResult(
                severity=ValidationSeverity.ERROR,
                category=category,
                message="Model has no elements",
            ))

        # Check for properties
        if summary.num_properties == 0:
            self.add_result(ValidationResult(
                severity=ValidationSeverity.ERROR,
                category=category,
                message="Model has no supported properties (PSHELL, PBAR, PBARL, PROD)",
                suggestion="Ensure model has designable properties",
            ))

        # Check for constraints
        if not summary.has_spc:
            self.add_result(ValidationResult(
                severity=ValidationSeverity.WARNING,
                category=category,
                message="No SPC constraints found",
                suggestion="Add boundary conditions to prevent rigid body motion",
            ))

        # Check for loads (needed for static/frequency response)
        if not summary.has_loads:
            self.add_result(ValidationResult(
                severity=ValidationSeverity.WARNING,
                category=category,
                message="No loads defined",
                suggestion="Add loads for response analysis",
            ))

        # Check for frequency cards (SOL111 within SOL200)
        if not summary.has_frequency_cards:
            self.add_result(ValidationResult(
                severity=ValidationSeverity.INFO,
                category=category,
                message="No frequency definition cards (FREQ)",
                details="Required for frequency response analysis",
            ))

    def _validate_design_variables(self, model):
        """Validate design variables."""
        category = "Design Variables"

        if not model.design_variables:
            self.add_result(ValidationResult(
                severity=ValidationSeverity.ERROR,
                category=category,
                message="No design variables defined",
                suggestion="Add at least one design variable",
            ))
            return

        labels_seen = set()
        for dv_id, dv in model.design_variables.items():
            loc = f"DESVAR {dv_id} ({dv.label})"

            # Check label uniqueness
            if dv.label in labels_seen:
                self.add_result(ValidationResult(
                    severity=ValidationSeverity.ERROR,
                    category=category,
                    message=f"Duplicate design variable label: {dv.label}",
                    location=loc,
                ))
            labels_seen.add(dv.label)

            # Check bounds
            if dv.lower_bound >= dv.upper_bound:
                self.add_result(ValidationResult(
                    severity=ValidationSeverity.ERROR,
                    category=category,
                    message="Lower bound >= upper bound",
                    details=f"Lower: {dv.lower_bound}, Upper: {dv.upper_bound}",
                    location=loc,
                ))

            # Check initial value
            if not (dv.lower_bound <= dv.initial_value <= dv.upper_bound):
                self.add_result(ValidationResult(
                    severity=ValidationSeverity.ERROR,
                    category=category,
                    message="Initial value outside bounds",
                    details=f"Initial: {dv.initial_value}, Bounds: [{dv.lower_bound}, {dv.upper_bound}]",
                    location=loc,
                ))

            # Check for very tight bounds (may cause numerical issues)
            range_ratio = (dv.upper_bound - dv.lower_bound) / max(abs(dv.initial_value), 1e-10)
            if range_ratio < 0.01:
                self.add_result(ValidationResult(
                    severity=ValidationSeverity.WARNING,
                    category=category,
                    message="Very narrow design variable bounds",
                    details=f"Range is only {range_ratio*100:.2f}% of initial value",
                    location=loc,
                    suggestion="Consider widening bounds for better optimization",
                ))

            # Check for non-physical values
            if dv.lower_bound < 0:
                self.add_result(ValidationResult(
                    severity=ValidationSeverity.WARNING,
                    category=category,
                    message="Negative lower bound for physical property",
                    details=f"Lower bound: {dv.lower_bound}",
                    location=loc,
                    suggestion="Physical properties typically require positive values",
                ))

    def _validate_variable_links(self, model):
        """Validate design variable to property links."""
        category = "Variable Links"

        if not model.variable_links:
            self.add_result(ValidationResult(
                severity=ValidationSeverity.ERROR,
                category=category,
                message="No DVPREL cards defined",
                suggestion="Link design variables to properties with DVPREL",
            ))
            return

        linked_properties = set()
        linked_desvars = set()

        for link_id, link in model.variable_links.items():
            loc = f"DVPREL {link_id}"

            # Check property exists
            prop = model.bdf_manager.get_property(link.property_id)
            if prop is None:
                self.add_result(ValidationResult(
                    severity=ValidationSeverity.ERROR,
                    category=category,
                    message=f"Property {link.property_id} not found in model",
                    location=loc,
                ))
            elif prop.type != link.property_type.value:
                self.add_result(ValidationResult(
                    severity=ValidationSeverity.ERROR,
                    category=category,
                    message=f"Property type mismatch: expected {link.property_type.value}, found {prop.type}",
                    location=loc,
                ))

            linked_properties.add(link.property_id)

            # Track linked design variables
            for dv, coef in link.design_variables:
                linked_desvars.add(dv.id)

                if abs(coef) < 1e-10:
                    self.add_result(ValidationResult(
                        severity=ValidationSeverity.WARNING,
                        category=category,
                        message=f"Near-zero coefficient for DESVAR {dv.id}",
                        details=f"Coefficient: {coef}",
                        location=loc,
                    ))

        # Check for unlinked design variables
        for dv_id in model.design_variables:
            if dv_id not in linked_desvars:
                self.add_result(ValidationResult(
                    severity=ValidationSeverity.WARNING,
                    category=category,
                    message=f"Design variable {dv_id} is not linked to any property",
                    suggestion="Link the variable via DVPREL or remove it",
                ))

    def _validate_responses(self, model):
        """Validate design responses."""
        category = "Design Responses"

        if not model.responses:
            self.add_result(ValidationResult(
                severity=ValidationSeverity.ERROR,
                category=category,
                message="No design responses defined",
                suggestion="Add at least one response for objective or constraints",
            ))
            return

        labels_seen = set()
        for resp_id, resp in model.responses.items():
            loc = f"DRESP{1 if not resp.is_synthetic else 2} {resp_id} ({resp.label})"

            # Check label uniqueness
            if resp.label in labels_seen:
                self.add_result(ValidationResult(
                    severity=ValidationSeverity.ERROR,
                    category=category,
                    message=f"Duplicate response label: {resp.label}",
                    location=loc,
                ))
            labels_seen.add(resp.label)

            # For synthetic responses (DRESP2)
            if resp.is_synthetic:
                # Check equation reference
                if resp.equation_id and resp.equation_id not in model.equations:
                    self.add_result(ValidationResult(
                        severity=ValidationSeverity.ERROR,
                        category=category,
                        message=f"DRESP2 references unknown equation {resp.equation_id}",
                        location=loc,
                    ))

                # Check referenced responses
                for ref_id in resp.referenced_responses:
                    if ref_id not in model.responses:
                        self.add_result(ValidationResult(
                            severity=ValidationSeverity.ERROR,
                            category=category,
                            message=f"DRESP2 references unknown response {ref_id}",
                            location=loc,
                        ))

    def _validate_constraints(self, model):
        """Validate design constraints."""
        category = "Design Constraints"

        if not model.constraints:
            self.add_result(ValidationResult(
                severity=ValidationSeverity.INFO,
                category=category,
                message="No constraints defined",
                details="Unconstrained optimization will only optimize the objective",
            ))
            return

        for constr_id, constr in model.constraints.items():
            loc = f"DCONSTR {constr_id}"

            # Check response reference
            if constr.response_id not in model.responses:
                self.add_result(ValidationResult(
                    severity=ValidationSeverity.ERROR,
                    category=category,
                    message=f"Constraint references unknown response {constr.response_id}",
                    location=loc,
                ))

            # Check bounds
            if constr.lower_bound is None and constr.upper_bound is None:
                self.add_result(ValidationResult(
                    severity=ValidationSeverity.ERROR,
                    category=category,
                    message="Constraint has no bounds",
                    location=loc,
                ))

            # Check for conflicting bounds
            if constr.lower_bound is not None and constr.upper_bound is not None:
                if constr.lower_bound > constr.upper_bound:
                    self.add_result(ValidationResult(
                        severity=ValidationSeverity.ERROR,
                        category=category,
                        message="Lower bound exceeds upper bound",
                        details=f"Lower: {constr.lower_bound}, Upper: {constr.upper_bound}",
                        location=loc,
                    ))

    def _validate_objective(self, model):
        """Validate objective function."""
        category = "Objective Function"

        if model.objective is None:
            self.add_result(ValidationResult(
                severity=ValidationSeverity.ERROR,
                category=category,
                message="No objective function defined",
                suggestion="Set an objective with model.set_objective()",
            ))
            return

        # Check response reference
        if model.objective.response_id not in model.responses:
            self.add_result(ValidationResult(
                severity=ValidationSeverity.ERROR,
                category=category,
                message=f"Objective references unknown response {model.objective.response_id}",
            ))

    def _validate_parameters(self, model):
        """Validate optimization parameters."""
        category = "Optimization Parameters"
        params = model.parameters

        if params.max_iterations < 1:
            self.add_result(ValidationResult(
                severity=ValidationSeverity.ERROR,
                category=category,
                message=f"Invalid max iterations: {params.max_iterations}",
                suggestion="Set max_iterations >= 1",
            ))

        if params.max_iterations > 100:
            self.add_result(ValidationResult(
                severity=ValidationSeverity.WARNING,
                category=category,
                message=f"High iteration count: {params.max_iterations}",
                details="May result in long computation time",
            ))

        if params.delp <= 0 or params.delp > 1:
            self.add_result(ValidationResult(
                severity=ValidationSeverity.WARNING,
                category=category,
                message=f"Unusual move limit: {params.delp}",
                suggestion="Typical values are 0.1-0.3 (10-30%)",
            ))

    def _validate_cross_references(self, model):
        """Validate cross-references between components."""
        category = "Cross References"

        # This is handled by other validators
        pass

    def _validate_physical_feasibility(self, model):
        """Validate physical feasibility of the optimization."""
        category = "Physical Feasibility"

        # Check for potential mass reduction issues
        for dv_id, dv in model.design_variables.items():
            if dv.lower_bound > 0 and dv.upper_bound / dv.lower_bound > 10:
                self.add_result(ValidationResult(
                    severity=ValidationSeverity.INFO,
                    category=category,
                    message=f"Large design space for variable {dv.label}",
                    details=f"Ratio of bounds: {dv.upper_bound/dv.lower_bound:.1f}x",
                    location=f"DESVAR {dv_id}",
                ))

    # === Summary Methods ===

    def has_errors(self) -> bool:
        """Check if any errors were found."""
        return self._error_count > 0

    def has_warnings(self) -> bool:
        """Check if any warnings were found."""
        return self._warning_count > 0

    def get_summary(self) -> Dict:
        """Get validation summary."""
        return {
            'total': len(self.results),
            'errors': self._error_count,
            'warnings': self._warning_count,
            'info': len(self.results) - self._error_count - self._warning_count,
            'can_run': not self.has_errors(),
        }

    def get_errors(self) -> List[ValidationResult]:
        """Get only error results."""
        return [r for r in self.results if r.severity == ValidationSeverity.ERROR]

    def get_warnings(self) -> List[ValidationResult]:
        """Get only warning results."""
        return [r for r in self.results if r.severity == ValidationSeverity.WARNING]

    def format_report(self) -> str:
        """Format validation results as a report."""
        lines = ["=" * 60, "VALIDATION REPORT", "=" * 60, ""]

        summary = self.get_summary()
        lines.append(f"Total issues: {summary['total']}")
        lines.append(f"  Errors: {summary['errors']}")
        lines.append(f"  Warnings: {summary['warnings']}")
        lines.append(f"  Info: {summary['info']}")
        lines.append("")

        if summary['can_run']:
            lines.append("✓ Model can be executed")
        else:
            lines.append("✗ Model has errors that must be fixed")

        lines.append("")
        lines.append("-" * 60)

        for result in self.results:
            lines.append(str(result))
            if result.details:
                lines.append(f"  Details: {result.details}")
            if result.suggestion:
                lines.append(f"  Suggestion: {result.suggestion}")
            lines.append("")

        return "\n".join(lines)
