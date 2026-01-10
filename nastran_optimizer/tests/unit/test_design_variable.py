"""
Tests for design variable module.

Tests cover:
- DesignVariable creation and validation
- DesignVariableLink creation and card generation
- PropertyType and PropertyField enumerations
- Bounds validation
- DESVAR and DVPREL card generation
"""

import pytest
from nastran_optimizer.core.design_variable import (
    DesignVariable,
    DesignVariableLink,
    PropertyType,
    PropertyField,
    LinkType,
)


class TestDesignVariable:
    """Tests for DesignVariable dataclass."""

    def test_create_basic_design_variable(self):
        """Test creating a basic design variable."""
        dv = DesignVariable(
            label="THICK1",
            initial_value=0.005,
            lower_bound=0.001,
            upper_bound=0.010,
        )

        assert dv.label == "THICK1"
        assert dv.initial_value == 0.005
        assert dv.lower_bound == 0.001
        assert dv.upper_bound == 0.010
        assert dv.description == ""

    def test_create_design_variable_with_description(self):
        """Test creating a design variable with description."""
        dv = DesignVariable(
            label="THICK2",
            initial_value=0.008,
            lower_bound=0.002,
            upper_bound=0.015,
            description="Panel thickness for fuselage",
        )

        assert dv.description == "Panel thickness for fuselage"

    def test_label_truncation(self):
        """Test that label is limited to 8 characters."""
        dv = DesignVariable(
            label="VERYLONGLABEL",  # 13 chars
            initial_value=1.0,
            lower_bound=0.5,
            upper_bound=2.0,
        )

        # Label should be truncated to 8 chars
        assert len(dv.label) <= 8

    def test_bounds_validation_lower_greater_than_upper(self):
        """Test that lower bound must be less than upper bound."""
        with pytest.raises(ValueError, match="lower.*upper|bound"):
            DesignVariable(
                label="BAD",
                initial_value=1.0,
                lower_bound=2.0,  # Greater than upper
                upper_bound=1.0,
            )

    def test_bounds_validation_initial_outside_bounds(self):
        """Test that initial value must be within bounds."""
        with pytest.raises(ValueError, match="initial|bound"):
            DesignVariable(
                label="BAD",
                initial_value=5.0,  # Outside bounds
                lower_bound=1.0,
                upper_bound=2.0,
            )

    def test_generate_desvar_card(self):
        """Test DESVAR card generation."""
        dv = DesignVariable(
            label="T1",
            initial_value=0.01,
            lower_bound=0.005,
            upper_bound=0.02,
        )

        card = dv.to_desvar(dv_id=1)
        assert "DESVAR" in card
        assert "T1" in card
        assert "0.01" in card or "1.0E-02" in card.upper()


class TestDesignVariableLink:
    """Tests for DesignVariableLink dataclass."""

    def test_create_dvprel1_link(self):
        """Test creating a DVPREL1 link."""
        dv = DesignVariable(
            label="THICK1",
            initial_value=0.005,
            lower_bound=0.001,
            upper_bound=0.010,
        )

        link = DesignVariableLink(
            design_variable=dv,
            property_type=PropertyType.PSHELL,
            property_id=101,
            field=PropertyField.PSHELL_T,
            coefficient=1.0,
        )

        assert link.property_type == PropertyType.PSHELL
        assert link.property_id == 101
        assert link.link_type == LinkType.DVPREL1
        assert link.coefficient == 1.0

    def test_create_dvprel2_link(self):
        """Test creating a DVPREL2 link with equation."""
        dv = DesignVariable(
            label="DIM1",
            initial_value=0.05,
            lower_bound=0.02,
            upper_bound=0.10,
        )

        link = DesignVariableLink(
            design_variable=dv,
            property_type=PropertyType.PBARL,
            property_id=201,
            field=PropertyField.PBARL_DIM1,
            link_type=LinkType.DVPREL2,
            equation_id=1001,
        )

        assert link.link_type == LinkType.DVPREL2
        assert link.equation_id == 1001

    def test_generate_dvprel1_card(self):
        """Test DVPREL1 card generation."""
        dv = DesignVariable(
            label="T1",
            initial_value=0.01,
            lower_bound=0.005,
            upper_bound=0.02,
        )

        link = DesignVariableLink(
            design_variable=dv,
            property_type=PropertyType.PSHELL,
            property_id=100,
            field=PropertyField.PSHELL_T,
            coefficient=1.0,
        )

        card = link.to_dvprel(link_id=1, dv_id=1)
        assert "DVPREL1" in card or "dvprel1" in card.lower()


class TestPropertyType:
    """Tests for PropertyType enumeration."""

    def test_supported_property_types(self):
        """Test that all required property types exist."""
        assert hasattr(PropertyType, 'PSHELL')
        assert hasattr(PropertyType, 'PBAR')
        assert hasattr(PropertyType, 'PBARL')
        assert hasattr(PropertyType, 'PROD')

    def test_property_type_values(self):
        """Test property type string values."""
        assert PropertyType.PSHELL.value == "PSHELL"
        assert PropertyType.PBAR.value == "PBAR"
        assert PropertyType.PBARL.value == "PBARL"
        assert PropertyType.PROD.value == "PROD"


class TestPropertyField:
    """Tests for PropertyField enumeration."""

    def test_pshell_fields(self):
        """Test PSHELL property fields."""
        assert hasattr(PropertyField, 'PSHELL_T')
        field = PropertyField.PSHELL_T
        assert field.value[0] == "PSHELL"  # Property type
        assert field.value[1] == "T"       # Field name

    def test_pbar_fields(self):
        """Test PBAR property fields."""
        assert hasattr(PropertyField, 'PBAR_A')
        assert hasattr(PropertyField, 'PBAR_I1')
        assert hasattr(PropertyField, 'PBAR_I2')
        assert hasattr(PropertyField, 'PBAR_J')

    def test_pbarl_fields(self):
        """Test PBARL property fields."""
        assert hasattr(PropertyField, 'PBARL_DIM1')
        assert hasattr(PropertyField, 'PBARL_DIM2')

    def test_prod_fields(self):
        """Test PROD property fields."""
        assert hasattr(PropertyField, 'PROD_A')
        assert hasattr(PropertyField, 'PROD_J')


class TestLinkType:
    """Tests for LinkType enumeration."""

    def test_link_types(self):
        """Test that link types exist."""
        assert hasattr(LinkType, 'DVPREL1')
        assert hasattr(LinkType, 'DVPREL2')
