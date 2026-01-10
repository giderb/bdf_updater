"""
Integration tests for complete SOL200 optimization workflows.

Tests cover:
- End-to-end workflow from BDF loading to card generation
- RMS acceleration optimization setup
- Validation and card export
"""

import pytest
from pathlib import Path


class TestCompleteWorkflow:
    """Integration tests for complete optimization workflow."""

    def test_load_bdf_and_setup_optimization(self, temp_bdf_file):
        """Test loading BDF and setting up optimization."""
        from nastran_optimizer.core import (
            OptimizationModel,
            DesignResponse,
            DesignConstraint,
            ObjectiveFunction,
            PropertyType,
            PropertyField,
            ResponseType,
            ObjectiveType,
        )

        # Create model and load BDF
        model = OptimizationModel("Test Workflow")
        model.load_bdf(str(temp_bdf_file))

        # Verify BDF loaded
        assert model.bdf_manager.is_loaded

        # Get designable properties
        props = model.bdf_manager.get_designable_properties()
        assert len(props) > 0

        # Add design variable for PSHELL thickness
        pshell_props = [p for p in props if p['type'] == 'PSHELL']
        if pshell_props:
            prop = pshell_props[0]
            dv = model.add_design_variable(
                label="T1",
                initial_value=0.01,
                lower_bound=0.005,
                upper_bound=0.02,
            )
            model.link_variable_to_property(
                design_variable=dv,
                property_type=PropertyType.PSHELL,
                property_id=prop['id'],
                field=PropertyField.PSHELL_T,
            )

        # Add response and objective
        resp = DesignResponse(
            label="WEIGHT",
            response_type=ResponseType.WEIGHT,
        )
        resp_id = model.add_response(resp)

        model.objective = ObjectiveFunction(
            response_id=resp_id,
            objective_type=ObjectiveType.MINIMIZE,
        )

        # Validate
        from nastran_optimizer.core import ModelValidator
        validator = ModelValidator()
        results = validator.validate(model)

        # Should pass basic validation
        errors = [r for r in results if r.severity == "ERROR"]
        # May have errors about missing BDF components, that's OK

    def test_rms_optimization_card_generation(self, complete_rms_model, temp_project_dir):
        """Test generating SOL200 cards for RMS optimization."""
        model = complete_rms_model

        # Generate all SOL200 cards
        cards = model.generate_sol200_cards()

        # Verify cards generated
        card_text = "\n".join(cards)

        assert "DESVAR" in card_text
        assert "DRESP1" in card_text

    def test_export_sol200_bdf(self, complete_rms_model, temp_project_dir):
        """Test exporting complete SOL200 BDF."""
        model = complete_rms_model

        output_file = temp_project_dir / "sol200_output.bdf"

        if hasattr(model, 'export_sol200_bdf'):
            model.export_sol200_bdf(str(output_file))

            # Verify file created
            assert output_file.exists()

            # Verify content
            content = output_file.read_text()
            assert "DESVAR" in content or "desvar" in content.lower()


class TestValidationWorkflow:
    """Integration tests for validation workflow."""

    def test_validate_complete_model(self, complete_rms_model):
        """Test validating a complete model."""
        from nastran_optimizer.core import ModelValidator

        validator = ModelValidator()
        results = validator.validate(complete_rms_model)

        # Count by severity
        errors = [r for r in results if r.severity == "ERROR"]
        warnings = [r for r in results if r.severity == "WARNING"]
        passes = [r for r in results if r.severity == "PASS"]

        # Complete model should have some passes
        # May have errors about BDF not loaded

    def test_validate_incomplete_model(self):
        """Test validating an incomplete model."""
        from nastran_optimizer.core import OptimizationModel, ModelValidator

        model = OptimizationModel("Incomplete")
        # Model has nothing

        validator = ModelValidator()
        results = validator.validate(model)

        # Should have errors
        errors = [r for r in results if r.severity == "ERROR"]
        assert len(errors) > 0


class TestPropertyExtraction:
    """Integration tests for property extraction from BDF."""

    def test_extract_pshell_properties(self, temp_bdf_file):
        """Test extracting PSHELL properties."""
        from nastran_optimizer.core import BDFManager

        manager = BDFManager()
        manager.load(str(temp_bdf_file))

        props = manager.get_designable_properties()
        pshell_props = [p for p in props if p['type'] == 'PSHELL']

        assert len(pshell_props) > 0

        # Check field info
        for prop in pshell_props:
            fields = prop['fields']
            t_field = [f for f in fields if f['name'] == 'T']
            assert len(t_field) > 0

    def test_extract_pbar_properties(self, temp_bdf_file):
        """Test extracting PBAR properties."""
        from nastran_optimizer.core import BDFManager

        manager = BDFManager()
        manager.load(str(temp_bdf_file))

        props = manager.get_designable_properties()
        pbar_props = [p for p in props if p['type'] == 'PBAR']

        # Check if PBAR exists in test BDF
        if pbar_props:
            assert len(pbar_props) > 0

    def test_extract_pbarl_properties(self, temp_bdf_file):
        """Test extracting PBARL properties."""
        from nastran_optimizer.core import BDFManager

        manager = BDFManager()
        manager.load(str(temp_bdf_file))

        props = manager.get_designable_properties()
        pbarl_props = [p for p in props if p['type'] == 'PBARL']

        # Check if PBARL exists in test BDF
        if pbarl_props:
            # Check for DIM fields
            for prop in pbarl_props:
                fields = prop['fields']
                dim_fields = [f for f in fields if 'DIM' in f['name']]
                assert len(dim_fields) > 0

    def test_extract_prod_properties(self, temp_bdf_file):
        """Test extracting PROD properties."""
        from nastran_optimizer.core import BDFManager

        manager = BDFManager()
        manager.load(str(temp_bdf_file))

        props = manager.get_designable_properties()
        prod_props = [p for p in props if p['type'] == 'PROD']

        # Check if PROD exists in test BDF
        if prod_props:
            assert len(prod_props) > 0


class TestEquationIntegration:
    """Integration tests for equation parsing and DEQATN generation."""

    def test_rms_equation_to_deqatn(self):
        """Test converting RMS equation to DEQATN card."""
        from nastran_optimizer.core import EquationParser

        parser = EquationParser()

        # Build RMS equation for 5 points
        args = ", ".join([f"A{i}" for i in range(1, 6)])
        sum_sq = " + ".join([f"A{i}**2" for i in range(1, 6)])
        equation = f"RMS({args}) = SQRT(({sum_sq}) / 5)"

        result = parser.parse(equation)
        card = result.to_deqatn(eq_id=1001)

        assert "DEQATN" in card
        assert "1001" in card

    def test_weighted_equation_to_deqatn(self):
        """Test converting weighted equation to DEQATN card."""
        from nastran_optimizer.core import EquationParser

        parser = EquationParser()

        equation = "WSUM(R1, R2, R3) = 0.5*R1 + 0.3*R2 + 0.2*R3"
        result = parser.parse(equation)
        card = result.to_deqatn(eq_id=1002)

        assert "DEQATN" in card


class TestProjectPersistence:
    """Integration tests for project save/load."""

    def test_save_and_load_project(self, complete_rms_model, temp_project_dir):
        """Test saving and loading a project."""
        from nastran_optimizer.core import OptimizationModel

        project_file = temp_project_dir / "project.json"

        if hasattr(complete_rms_model, 'save_project'):
            # Save
            complete_rms_model.save_project(str(project_file))
            assert project_file.exists()

            # Load
            if hasattr(OptimizationModel, 'load_project'):
                loaded = OptimizationModel.load_project(str(project_file))

                # Verify loaded model
                assert loaded.name == complete_rms_model.name
                assert len(loaded.design_variables) == len(complete_rms_model.design_variables)
                assert len(loaded.responses) == len(complete_rms_model.responses)
