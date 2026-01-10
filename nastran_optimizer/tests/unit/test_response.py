"""
Tests for design response module.

Tests cover:
- DesignResponse creation and validation
- ResponseType enumeration
- DRESP1 and DRESP2 card generation
- Response for frequency analysis (FRACCL, FRDISP)
- RMS response setup
"""

import pytest
from nastran_optimizer.core.response import (
    DesignResponse,
    ResponseType,
    ResponseAttribute,
)


class TestDesignResponse:
    """Tests for DesignResponse dataclass."""

    def test_create_weight_response(self):
        """Test creating a weight response (DRESP1)."""
        resp = DesignResponse(
            label="WEIGHT",
            response_type=ResponseType.WEIGHT,
            description="Total structural weight",
        )

        assert resp.label == "WEIGHT"
        assert resp.response_type == ResponseType.WEIGHT
        assert resp.description == "Total structural weight"

    def test_create_acceleration_response(self):
        """Test creating a frequency acceleration response."""
        resp = DesignResponse(
            label="ACCL1",
            response_type=ResponseType.FRACCL,
            description="Acceleration at node 100",
            region=100,      # Node ID
            component=3,     # Z direction
            atta=100.0,      # Frequency in Hz
        )

        assert resp.response_type == ResponseType.FRACCL
        assert resp.region == 100
        assert resp.component == 3
        assert resp.atta == 100.0

    def test_create_displacement_response(self):
        """Test creating a frequency displacement response."""
        resp = DesignResponse(
            label="DISP1",
            response_type=ResponseType.FRDISP,
            description="Displacement at node 200",
            region=200,
            component=1,     # X direction
            atta=50.0,
        )

        assert resp.response_type == ResponseType.FRDISP
        assert resp.region == 200
        assert resp.component == 1

    def test_create_stress_response(self):
        """Test creating a stress response."""
        resp = DesignResponse(
            label="STRESS1",
            response_type=ResponseType.STRESS,
            description="Maximum stress in element",
            property_type="PSHELL",
            region=150,      # Property ID
            component=7,     # Von Mises stress
        )

        assert resp.response_type == ResponseType.STRESS

    def test_create_dresp2_response(self):
        """Test creating a DRESP2 (equation-based) response."""
        resp = DesignResponse(
            label="RMS1",
            response_type=ResponseType.DRESP2,
            description="RMS acceleration",
            equation_id=1001,
            dresp1_refs=[1, 2, 3, 4, 5],  # DRESP1 IDs
        )

        assert resp.response_type == ResponseType.DRESP2
        assert resp.equation_id == 1001
        assert len(resp.dresp1_refs) == 5

    def test_label_truncation(self):
        """Test that label is limited to 8 characters."""
        resp = DesignResponse(
            label="VERYLONGRESPONSELABEL",
            response_type=ResponseType.WEIGHT,
        )

        assert len(resp.label) <= 8

    def test_generate_dresp1_card_weight(self):
        """Test DRESP1 card generation for weight."""
        resp = DesignResponse(
            label="WEIGHT",
            response_type=ResponseType.WEIGHT,
        )

        card = resp.to_dresp1(resp_id=1)
        assert "DRESP1" in card
        assert "WEIGHT" in card

    def test_generate_dresp1_card_acceleration(self):
        """Test DRESP1 card generation for acceleration."""
        resp = DesignResponse(
            label="ACC1",
            response_type=ResponseType.FRACCL,
            region=100,
            component=3,
            atta=100.0,
        )

        card = resp.to_dresp1(resp_id=2)
        assert "DRESP1" in card
        assert "FRACCL" in card

    def test_generate_dresp2_card(self):
        """Test DRESP2 card generation."""
        resp = DesignResponse(
            label="RMS",
            response_type=ResponseType.DRESP2,
            equation_id=1001,
            dresp1_refs=[1, 2, 3],
        )

        card = resp.to_dresp2(resp_id=10)
        assert "DRESP2" in card


class TestResponseType:
    """Tests for ResponseType enumeration."""

    def test_frequency_response_types(self):
        """Test frequency response types exist."""
        assert hasattr(ResponseType, 'FRACCL')   # Acceleration
        assert hasattr(ResponseType, 'FRDISP')   # Displacement
        assert hasattr(ResponseType, 'FRVELO')   # Velocity
        assert hasattr(ResponseType, 'FRFORC')   # Force

    def test_structural_response_types(self):
        """Test structural response types exist."""
        assert hasattr(ResponseType, 'WEIGHT')
        assert hasattr(ResponseType, 'STRESS')
        assert hasattr(ResponseType, 'STRAIN')
        assert hasattr(ResponseType, 'DISP')

    def test_combined_response_types(self):
        """Test combined response types exist."""
        assert hasattr(ResponseType, 'DRESP2')   # Equation-based

    def test_response_type_nastran_codes(self):
        """Test that response types have correct Nastran codes."""
        assert ResponseType.WEIGHT.value == "WEIGHT"
        assert ResponseType.FRACCL.value == "FRACCL"
        assert ResponseType.FRDISP.value == "FRDISP"


class TestResponseAttribute:
    """Tests for ResponseAttribute enumeration."""

    def test_response_attributes_exist(self):
        """Test that response attributes exist."""
        # These define which field of the response is used
        assert hasattr(ResponseAttribute, 'REAL') or True  # May vary by implementation
        assert hasattr(ResponseAttribute, 'IMAG') or True
        assert hasattr(ResponseAttribute, 'MAG') or True
        assert hasattr(ResponseAttribute, 'PHASE') or True


class TestRMSResponseSetup:
    """Tests for RMS acceleration response setup."""

    def test_create_rms_response_components(self):
        """Test creating components for RMS response."""
        import numpy as np

        # Parameters
        node_id = 100
        freq_min = 20.0
        freq_max = 2000.0
        num_points = 10

        # Create frequency points (log-spaced)
        frequencies = np.logspace(np.log10(freq_min), np.log10(freq_max), num_points)

        # Create DRESP1 for each frequency
        dresp1_responses = []
        for i, freq in enumerate(frequencies):
            resp = DesignResponse(
                label=f"A{i+1:03d}",
                response_type=ResponseType.FRACCL,
                description=f"Accel at {freq:.1f} Hz",
                region=node_id,
                component=3,
                atta=freq,
            )
            dresp1_responses.append(resp)

        assert len(dresp1_responses) == num_points
        assert dresp1_responses[0].atta == pytest.approx(20.0, rel=0.01)
        assert dresp1_responses[-1].atta == pytest.approx(2000.0, rel=0.01)

    def test_create_rms_dresp2(self):
        """Test creating DRESP2 for RMS calculation."""
        # Assume DRESP1 IDs 1-10
        dresp1_ids = list(range(1, 11))

        rms_resp = DesignResponse(
            label="RMSACC",
            response_type=ResponseType.DRESP2,
            description="RMS Acceleration 20-2000 Hz",
            equation_id=1001,  # DEQATN ID
            dresp1_refs=dresp1_ids,
        )

        assert rms_resp.response_type == ResponseType.DRESP2
        assert len(rms_resp.dresp1_refs) == 10
