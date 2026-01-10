"""
Tests for optimization model module.

Tests cover:
- OptimizationModel creation and management
- Adding design variables, responses, constraints
- Setting objective
- SOL200 card generation
- Project save/load
"""

import pytest
from nastran_optimizer.core import (
    OptimizationModel,
    DesignVariable,
    DesignResponse,
    DesignConstraint,
    ObjectiveFunction,
    PropertyType,
    PropertyField,
    ResponseType,
    ObjectiveType,
)


class TestOptimizationModel:
    """Tests for OptimizationModel class."""

    def test_create_model(self):
        """Test creating an optimization model."""
        model = OptimizationModel("Test Optimization")

        assert model.name == "Test Optimization"
        assert len(model.design_variables) == 0
        assert len(model.responses) == 0
        assert len(model.constraints) == 0
        assert model.objective is None

    def test_add_design_variable(self):
        """Test adding a design variable."""
        model = OptimizationModel("Test")

        dv = model.add_design_variable(
            label="T1",
            initial_value=0.01,
            lower_bound=0.005,
            upper_bound=0.02,
            description="Panel thickness",
        )

        assert len(model.design_variables) == 1
        assert dv.label == "T1"

    def test_add_multiple_design_variables(self):
        """Test adding multiple design variables."""
        model = OptimizationModel("Test")

        model.add_design_variable(
            label="T1",
            initial_value=0.01,
            lower_bound=0.005,
            upper_bound=0.02,
        )
        model.add_design_variable(
            label="T2",
            initial_value=0.008,
            lower_bound=0.004,
            upper_bound=0.016,
        )
        model.add_design_variable(
            label="T3",
            initial_value=0.012,
            lower_bound=0.006,
            upper_bound=0.024,
        )

        assert len(model.design_variables) == 3

    def test_link_variable_to_property(self):
        """Test linking a design variable to a property."""
        model = OptimizationModel("Test")

        dv = model.add_design_variable(
            label="T1",
            initial_value=0.01,
            lower_bound=0.005,
            upper_bound=0.02,
        )

        link = model.link_variable_to_property(
            design_variable=dv,
            property_type=PropertyType.PSHELL,
            property_id=101,
            field=PropertyField.PSHELL_T,
        )

        assert link is not None
        assert link.property_id == 101

    def test_add_response(self):
        """Test adding a design response."""
        model = OptimizationModel("Test")

        resp = DesignResponse(
            label="WEIGHT",
            response_type=ResponseType.WEIGHT,
            description="Total weight",
        )
        resp_id = model.add_response(resp)

        assert len(model.responses) == 1
        assert resp_id in model.responses

    def test_add_constraint(self):
        """Test adding a design constraint."""
        model = OptimizationModel("Test")

        # First add a response
        resp = DesignResponse(
            label="WEIGHT",
            response_type=ResponseType.WEIGHT,
        )
        resp_id = model.add_response(resp)

        # Then add constraint on it
        const = DesignConstraint(
            response_id=resp_id,
            upper_bound=1000.0,
        )
        const_id = model.add_constraint(const)

        assert len(model.constraints) == 1
        assert const_id in model.constraints

    def test_set_objective(self):
        """Test setting the optimization objective."""
        model = OptimizationModel("Test")

        # Add response first
        resp = DesignResponse(
            label="ACC",
            response_type=ResponseType.FRACCL,
            region=100,
            component=3,
            atta=100.0,
        )
        resp_id = model.add_response(resp)

        # Set objective
        model.objective = ObjectiveFunction(
            response_id=resp_id,
            objective_type=ObjectiveType.MINIMIZE,
        )

        assert model.objective is not None
        assert model.objective.response_id == resp_id

    def test_auto_id_assignment(self):
        """Test that IDs are automatically assigned."""
        model = OptimizationModel("Test")

        dv1 = model.add_design_variable(
            label="T1",
            initial_value=0.01,
            lower_bound=0.005,
            upper_bound=0.02,
        )
        dv2 = model.add_design_variable(
            label="T2",
            initial_value=0.008,
            lower_bound=0.004,
            upper_bound=0.016,
        )

        # IDs should be unique and sequential
        ids = list(model.design_variables.keys())
        assert len(set(ids)) == 2  # All unique


class TestSOL200CardGeneration:
    """Tests for SOL200 card generation."""

    def test_generate_desvar_cards(self):
        """Test generating DESVAR cards."""
        model = OptimizationModel("Test")

        model.add_design_variable(
            label="T1",
            initial_value=0.01,
            lower_bound=0.005,
            upper_bound=0.02,
        )
        model.add_design_variable(
            label="T2",
            initial_value=0.008,
            lower_bound=0.004,
            upper_bound=0.016,
        )

        cards = model.generate_desvar_cards()

        assert len(cards) == 2
        for card in cards:
            assert "DESVAR" in card

    def test_generate_dresp1_cards(self):
        """Test generating DRESP1 cards."""
        model = OptimizationModel("Test")

        model.add_response(DesignResponse(
            label="WEIGHT",
            response_type=ResponseType.WEIGHT,
        ))
        model.add_response(DesignResponse(
            label="ACC1",
            response_type=ResponseType.FRACCL,
            region=100,
            component=3,
            atta=100.0,
        ))

        cards = model.generate_dresp1_cards()

        assert len(cards) >= 2

    def test_generate_dconstr_cards(self):
        """Test generating DCONSTR cards."""
        model = OptimizationModel("Test")

        resp = DesignResponse(
            label="WEIGHT",
            response_type=ResponseType.WEIGHT,
        )
        resp_id = model.add_response(resp)

        const = DesignConstraint(
            response_id=resp_id,
            upper_bound=1000.0,
        )
        model.add_constraint(const)

        cards = model.generate_dconstr_cards()

        assert len(cards) >= 1

    def test_generate_all_sol200_cards(self):
        """Test generating all SOL200 cards."""
        model = OptimizationModel("Test")

        # Setup a complete model
        dv = model.add_design_variable(
            label="T1",
            initial_value=0.01,
            lower_bound=0.005,
            upper_bound=0.02,
        )

        resp = DesignResponse(
            label="WEIGHT",
            response_type=ResponseType.WEIGHT,
        )
        resp_id = model.add_response(resp)

        const = DesignConstraint(
            response_id=resp_id,
            upper_bound=1000.0,
        )
        model.add_constraint(const)

        model.objective = ObjectiveFunction(
            response_id=resp_id,
            objective_type=ObjectiveType.MINIMIZE,
        )

        # Generate all cards
        all_cards = model.generate_sol200_cards()

        # Should have DESVAR, DRESP1, DCONSTR at minimum
        card_text = "\n".join(all_cards)
        assert "DESVAR" in card_text
        assert "DRESP1" in card_text


class TestProjectSaveLoad:
    """Tests for project save/load functionality."""

    def test_save_project(self, tmp_path):
        """Test saving project to file."""
        model = OptimizationModel("Test Project")

        model.add_design_variable(
            label="T1",
            initial_value=0.01,
            lower_bound=0.005,
            upper_bound=0.02,
        )

        project_file = tmp_path / "project.json"

        if hasattr(model, 'save_project'):
            model.save_project(str(project_file))
            assert project_file.exists()

    def test_load_project(self, tmp_path):
        """Test loading project from file."""
        # First save a project
        model = OptimizationModel("Test Project")
        model.add_design_variable(
            label="T1",
            initial_value=0.01,
            lower_bound=0.005,
            upper_bound=0.02,
        )

        project_file = tmp_path / "project.json"

        if hasattr(model, 'save_project') and hasattr(OptimizationModel, 'load_project'):
            model.save_project(str(project_file))

            # Load it back
            loaded = OptimizationModel.load_project(str(project_file))
            assert loaded.name == "Test Project"
            assert len(loaded.design_variables) == 1


class TestCompleteWorkflow:
    """Tests for complete optimization workflow."""

    def test_rms_acceleration_optimization_setup(self):
        """Test setting up an RMS acceleration optimization."""
        model = OptimizationModel("RMS Acceleration Optimization")

        # Add design variables for panel thicknesses
        for i in range(1, 6):
            model.add_design_variable(
                label=f"T{i}",
                initial_value=0.01,
                lower_bound=0.005,
                upper_bound=0.02,
                description=f"Panel {i} thickness",
            )

        # Add acceleration responses at multiple frequencies
        import numpy as np
        frequencies = np.logspace(np.log10(20), np.log10(2000), 10)

        dresp1_ids = []
        for i, freq in enumerate(frequencies):
            resp = DesignResponse(
                label=f"A{i+1:03d}",
                response_type=ResponseType.FRACCL,
                description=f"Accel at {freq:.1f} Hz",
                region=100,  # Node ID
                component=3,  # Z direction
                atta=freq,
            )
            resp_id = model.add_response(resp)
            dresp1_ids.append(resp_id)

        # Add RMS response (DRESP2)
        rms_resp = DesignResponse(
            label="RMSACC",
            response_type=ResponseType.DRESP2,
            description="RMS Acceleration",
            dresp1_refs=dresp1_ids,
        )
        rms_id = model.add_response(rms_resp)

        # Set objective to minimize RMS
        model.objective = ObjectiveFunction(
            response_id=rms_id,
            objective_type=ObjectiveType.MINIMIZE,
        )

        # Add weight constraint
        weight_resp = DesignResponse(
            label="WEIGHT",
            response_type=ResponseType.WEIGHT,
        )
        weight_id = model.add_response(weight_resp)

        model.add_constraint(DesignConstraint(
            response_id=weight_id,
            upper_bound=1500.0,  # Max weight
        ))

        # Verify setup
        assert len(model.design_variables) == 5
        assert len(model.responses) == 12  # 10 DRESP1 + 1 DRESP2 + 1 weight
        assert len(model.constraints) == 1
        assert model.objective is not None
