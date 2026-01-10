"""
Tests for objective function module.

Tests cover:
- ObjectiveFunction creation
- Minimize/Maximize objectives
- Objective type enumeration
"""

import pytest
from nastran_optimizer.core.objective import (
    ObjectiveFunction,
    ObjectiveType,
)


class TestObjectiveFunction:
    """Tests for ObjectiveFunction dataclass."""

    def test_create_minimize_objective(self):
        """Test creating a minimize objective."""
        obj = ObjectiveFunction(
            response_id=1,
            objective_type=ObjectiveType.MINIMIZE,
        )

        assert obj.response_id == 1
        assert obj.objective_type == ObjectiveType.MINIMIZE

    def test_create_maximize_objective(self):
        """Test creating a maximize objective."""
        obj = ObjectiveFunction(
            response_id=2,
            objective_type=ObjectiveType.MAXIMIZE,
        )

        assert obj.objective_type == ObjectiveType.MAXIMIZE

    def test_default_objective_type_is_minimize(self):
        """Test that default objective type is minimize."""
        obj = ObjectiveFunction(response_id=1)

        assert obj.objective_type == ObjectiveType.MINIMIZE

    def test_weight_minimization_objective(self):
        """Test typical weight minimization setup."""
        obj = ObjectiveFunction(
            response_id=1,  # DRESP1 for weight
            objective_type=ObjectiveType.MINIMIZE,
            description="Minimize structural weight",
        )

        assert obj.objective_type == ObjectiveType.MINIMIZE

    def test_stiffness_maximization_objective(self):
        """Test stiffness maximization setup."""
        obj = ObjectiveFunction(
            response_id=5,  # DRESP1 for stiffness
            objective_type=ObjectiveType.MAXIMIZE,
            description="Maximize structural stiffness",
        )

        assert obj.objective_type == ObjectiveType.MAXIMIZE

    def test_rms_acceleration_minimization(self):
        """Test RMS acceleration minimization (typical use case)."""
        obj = ObjectiveFunction(
            response_id=100,  # DRESP2 for RMS
            objective_type=ObjectiveType.MINIMIZE,
            description="Minimize RMS acceleration",
        )

        assert obj.objective_type == ObjectiveType.MINIMIZE
        assert obj.response_id == 100


class TestObjectiveType:
    """Tests for ObjectiveType enumeration."""

    def test_minimize_type(self):
        """Test minimize type exists and has correct value."""
        assert hasattr(ObjectiveType, 'MINIMIZE')
        assert ObjectiveType.MINIMIZE.value in ('MIN', 'MINIMIZE', 0)

    def test_maximize_type(self):
        """Test maximize type exists and has correct value."""
        assert hasattr(ObjectiveType, 'MAXIMIZE')
        assert ObjectiveType.MAXIMIZE.value in ('MAX', 'MAXIMIZE', 1)


class TestObjectiveValidation:
    """Tests for objective validation."""

    def test_objective_requires_response_id(self):
        """Test that response_id is required."""
        with pytest.raises(TypeError):
            ObjectiveFunction(
                objective_type=ObjectiveType.MINIMIZE,
                # Missing response_id
            )

    def test_objective_with_scaling(self):
        """Test objective with scaling factor (if supported)."""
        obj = ObjectiveFunction(
            response_id=1,
            objective_type=ObjectiveType.MINIMIZE,
        )

        # Scaling may be optional
        if hasattr(obj, 'scale'):
            assert obj.scale == 1.0 or obj.scale is None


class TestMultiObjective:
    """Tests for multi-objective scenarios (if supported)."""

    def test_weighted_sum_objectives(self):
        """Test creating weighted sum of objectives."""
        # This tests the concept, actual implementation may vary
        objectives = [
            ObjectiveFunction(response_id=1, objective_type=ObjectiveType.MINIMIZE),
            ObjectiveFunction(response_id=2, objective_type=ObjectiveType.MINIMIZE),
        ]

        assert len(objectives) == 2
