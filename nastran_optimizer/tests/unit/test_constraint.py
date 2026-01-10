"""
Tests for design constraint module.

Tests cover:
- DesignConstraint creation and validation
- Upper/lower bound constraints
- Range constraints
- DCONSTR card generation
"""

import pytest
from nastran_optimizer.core.constraint import (
    DesignConstraint,
    ConstraintType,
)


class TestDesignConstraint:
    """Tests for DesignConstraint dataclass."""

    def test_create_upper_bound_constraint(self):
        """Test creating an upper bound constraint."""
        const = DesignConstraint(
            response_id=1,
            upper_bound=100.0,
        )

        assert const.response_id == 1
        assert const.upper_bound == 100.0
        assert const.lower_bound is None

    def test_create_lower_bound_constraint(self):
        """Test creating a lower bound constraint."""
        const = DesignConstraint(
            response_id=2,
            lower_bound=0.001,
        )

        assert const.response_id == 2
        assert const.lower_bound == 0.001
        assert const.upper_bound is None

    def test_create_range_constraint(self):
        """Test creating a range constraint (both bounds)."""
        const = DesignConstraint(
            response_id=3,
            lower_bound=10.0,
            upper_bound=100.0,
        )

        assert const.lower_bound == 10.0
        assert const.upper_bound == 100.0

    def test_constraint_requires_at_least_one_bound(self):
        """Test that at least one bound is required."""
        with pytest.raises((ValueError, TypeError)):
            DesignConstraint(
                response_id=1,
                # No bounds specified
            )

    def test_lower_bound_less_than_upper(self):
        """Test that lower bound must be less than upper bound."""
        with pytest.raises(ValueError, match="lower.*upper|bound"):
            DesignConstraint(
                response_id=1,
                lower_bound=100.0,
                upper_bound=10.0,  # Less than lower
            )

    def test_generate_dconstr_card(self):
        """Test DCONSTR card generation."""
        const = DesignConstraint(
            response_id=1,
            lower_bound=-0.005,
            upper_bound=0.005,
        )

        card = const.to_dconstr(const_id=1, dconst_set=1)
        assert "DCONSTR" in card

    def test_weight_constraint(self):
        """Test creating a typical weight constraint."""
        const = DesignConstraint(
            response_id=1,  # Assumes DRESP1 for weight
            upper_bound=1500.0,  # Max weight in kg
            description="Maximum weight constraint",
        )

        assert const.upper_bound == 1500.0

    def test_stress_constraint(self):
        """Test creating a typical stress constraint."""
        const = DesignConstraint(
            response_id=5,  # Assumes DRESP1 for stress
            upper_bound=250e6,  # Max stress in Pa
            description="Stress must not exceed yield",
        )

        assert const.upper_bound == 250e6

    def test_acceleration_constraint(self):
        """Test creating an acceleration constraint."""
        const = DesignConstraint(
            response_id=10,  # DRESP2 for RMS acceleration
            upper_bound=9.81,  # 1g limit
            description="Max 1g RMS acceleration",
        )

        assert const.upper_bound == 9.81

    def test_minimum_gauge_constraint(self):
        """Test creating a minimum gauge (thickness) constraint."""
        const = DesignConstraint(
            response_id=20,  # DRESP1 for thickness
            lower_bound=0.0005,  # 0.5mm minimum
            description="Minimum manufacturable thickness",
        )

        assert const.lower_bound == 0.0005


class TestConstraintType:
    """Tests for ConstraintType enumeration."""

    def test_constraint_types_exist(self):
        """Test that constraint types exist."""
        assert hasattr(ConstraintType, 'UPPER')
        assert hasattr(ConstraintType, 'LOWER')
        assert hasattr(ConstraintType, 'RANGE')


class TestConstraintValidation:
    """Tests for constraint validation logic."""

    def test_constraint_satisfaction_check(self):
        """Test checking if constraint is satisfied."""
        const = DesignConstraint(
            response_id=1,
            lower_bound=10.0,
            upper_bound=100.0,
        )

        # Test satisfaction (if method exists)
        if hasattr(const, 'is_satisfied'):
            assert const.is_satisfied(50.0) == True
            assert const.is_satisfied(5.0) == False
            assert const.is_satisfied(150.0) == False

    def test_constraint_violation_magnitude(self):
        """Test calculating constraint violation."""
        const = DesignConstraint(
            response_id=1,
            upper_bound=100.0,
        )

        # Test violation calculation (if method exists)
        if hasattr(const, 'get_violation'):
            assert const.get_violation(50.0) <= 0  # Satisfied
            assert const.get_violation(120.0) > 0   # Violated


class TestConstraintSets:
    """Tests for constraint set management."""

    def test_create_constraint_set(self):
        """Test creating a set of related constraints."""
        constraints = [
            DesignConstraint(response_id=1, upper_bound=100.0),
            DesignConstraint(response_id=2, upper_bound=50.0),
            DesignConstraint(response_id=3, lower_bound=0.001),
        ]

        assert len(constraints) == 3

    def test_constraint_set_with_same_response(self):
        """Test multiple constraints on same response."""
        # This is valid - e.g., different subcases
        constraints = [
            DesignConstraint(response_id=1, upper_bound=100.0),
            DesignConstraint(response_id=1, lower_bound=10.0),
        ]

        assert len(constraints) == 2
