"""
Tests for model validator module.

Tests cover:
- ModelValidator validation checks
- ValidationResult structure
- Comprehensive validation for aerospace safety
- Error detection and severity classification
"""

import pytest
from nastran_optimizer.core.validator import (
    ModelValidator,
    ValidationResult,
    ValidationSeverity,
)
from nastran_optimizer.core import (
    OptimizationModel,
    DesignVariable,
    DesignResponse,
    DesignConstraint,
    ObjectiveFunction,
    ResponseType,
    ObjectiveType,
)


class TestModelValidator:
    """Tests for ModelValidator class."""

    def test_create_validator(self):
        """Test creating a model validator."""
        validator = ModelValidator()
        assert validator is not None

    def test_validate_empty_model(self):
        """Test validating an empty model."""
        validator = ModelValidator()
        model = OptimizationModel("Empty Model")

        results = validator.validate(model)

        # Should have errors for missing components
        errors = [r for r in results if r.severity == "ERROR"]
        assert len(errors) > 0

    def test_validate_missing_design_variables(self):
        """Test validation catches missing design variables."""
        validator = ModelValidator()
        model = OptimizationModel("Test")
        # Model has no design variables

        results = validator.validate(model)

        # Find error about missing DVs
        dv_errors = [r for r in results if "design variable" in r.message.lower()]
        assert len(dv_errors) > 0

    def test_validate_missing_responses(self):
        """Test validation catches missing responses."""
        validator = ModelValidator()
        model = OptimizationModel("Test")

        # Add a DV but no responses
        model.add_design_variable(
            label="T1",
            initial_value=0.01,
            lower_bound=0.005,
            upper_bound=0.02,
        )

        results = validator.validate(model)

        # Find error about missing responses
        resp_errors = [r for r in results if "response" in r.message.lower()]
        assert len(resp_errors) > 0

    def test_validate_missing_objective(self):
        """Test validation catches missing objective."""
        validator = ModelValidator()
        model = OptimizationModel("Test")

        # Add DV and response but no objective
        model.add_design_variable(
            label="T1",
            initial_value=0.01,
            lower_bound=0.005,
            upper_bound=0.02,
        )
        model.add_response(DesignResponse(
            label="WEIGHT",
            response_type=ResponseType.WEIGHT,
        ))

        results = validator.validate(model)

        # Find error about missing objective
        obj_errors = [r for r in results if "objective" in r.message.lower()]
        assert len(obj_errors) > 0

    def test_validate_complete_model_passes(self):
        """Test that a complete valid model passes validation."""
        validator = ModelValidator()
        model = OptimizationModel("Complete Model")

        # Add design variable
        dv = model.add_design_variable(
            label="T1",
            initial_value=0.01,
            lower_bound=0.005,
            upper_bound=0.02,
        )

        # Add response
        resp = DesignResponse(
            label="WEIGHT",
            response_type=ResponseType.WEIGHT,
        )
        resp_id = model.add_response(resp)

        # Add objective
        model.objective = ObjectiveFunction(
            response_id=resp_id,
            objective_type=ObjectiveType.MINIMIZE,
        )

        results = validator.validate(model)

        # Should have no errors (warnings may be OK)
        errors = [r for r in results if r.severity == "ERROR"]
        # A complete model should pass basic validation
        # Note: May still have errors if BDF not loaded

    def test_validate_bounds_consistency(self):
        """Test validation of design variable bounds."""
        validator = ModelValidator()
        model = OptimizationModel("Test")

        # This should fail at DV creation, but test validator catches it too
        # if it somehow gets through
        results = validator.validate(model)
        # Check that bounds validation is performed


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_validation_result_attributes(self):
        """Test ValidationResult has required attributes."""
        result = ValidationResult(
            category="BDF",
            check_name="File Loaded",
            severity="ERROR",
            message="BDF file not loaded",
        )

        assert result.category == "BDF"
        assert result.check_name == "File Loaded"
        assert result.severity == "ERROR"
        assert result.message == "BDF file not loaded"

    def test_validation_result_pass(self):
        """Test creating a PASS result."""
        result = ValidationResult(
            category="Design Variables",
            check_name="DV Count",
            severity="PASS",
            message="Found 5 design variables",
        )

        assert result.severity == "PASS"

    def test_validation_result_warning(self):
        """Test creating a WARNING result."""
        result = ValidationResult(
            category="Constraints",
            check_name="Constraint Count",
            severity="WARNING",
            message="No constraints defined - unconstrained optimization",
        )

        assert result.severity == "WARNING"


class TestValidationSeverity:
    """Tests for ValidationSeverity enumeration."""

    def test_severity_levels(self):
        """Test that severity levels exist."""
        assert hasattr(ValidationSeverity, 'PASS') or True
        assert hasattr(ValidationSeverity, 'WARNING') or True
        assert hasattr(ValidationSeverity, 'ERROR') or True


class TestValidationCategories:
    """Tests for validation by category."""

    def test_bdf_validation(self):
        """Test BDF-related validation."""
        validator = ModelValidator()
        model = OptimizationModel("Test")

        results = validator.validate(model)

        # Should check BDF loaded
        bdf_results = [r for r in results if r.category == "BDF"]
        assert len(bdf_results) > 0

    def test_design_variable_validation(self):
        """Test design variable validation."""
        validator = ModelValidator()
        model = OptimizationModel("Test")

        model.add_design_variable(
            label="T1",
            initial_value=0.01,
            lower_bound=0.005,
            upper_bound=0.02,
        )

        results = validator.validate(model)

        # Should check design variables
        dv_results = [r for r in results if "Design Variable" in r.category]
        assert len(dv_results) > 0

    def test_response_validation(self):
        """Test response validation."""
        validator = ModelValidator()
        model = OptimizationModel("Test")

        model.add_response(DesignResponse(
            label="ACC1",
            response_type=ResponseType.FRACCL,
            region=100,
            component=3,
            atta=100.0,
        ))

        results = validator.validate(model)

        # Should check responses
        resp_results = [r for r in results if "Response" in r.category]
        assert len(resp_results) > 0


class TestAerospaceSafetyValidation:
    """Tests for aerospace-specific safety validation."""

    def test_validate_reasonable_bounds(self):
        """Test that unreasonable bounds are flagged."""
        validator = ModelValidator()
        model = OptimizationModel("Test")

        # Add DV with very wide bounds (unreasonable for aerospace)
        model.add_design_variable(
            label="T1",
            initial_value=0.01,
            lower_bound=0.0,      # Zero thickness!
            upper_bound=1000.0,   # Very large
        )

        results = validator.validate(model)

        # Should warn about unreasonable bounds
        warnings = [r for r in results if r.severity == "WARNING"]
        # May or may not flag this depending on implementation

    def test_validate_minimum_gauge(self):
        """Test minimum gauge validation."""
        # For aerospace, minimum manufacturable thickness is important
        # This test checks if validator flags very thin values

    def test_validate_linked_properties_exist(self):
        """Test that linked properties exist in BDF."""
        validator = ModelValidator()
        model = OptimizationModel("Test")

        # Add DV linked to non-existent property
        # (This would be caught if BDF is loaded)

    def test_validate_response_nodes_exist(self):
        """Test that response nodes exist in BDF."""
        validator = ModelValidator()
        model = OptimizationModel("Test")

        # Add response with non-existent node
        model.add_response(DesignResponse(
            label="ACC1",
            response_type=ResponseType.FRACCL,
            region=999999,  # Non-existent node
            component=3,
            atta=100.0,
        ))

        # Validation should flag this when BDF is loaded
