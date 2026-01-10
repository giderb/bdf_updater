"""
Pytest fixtures for SOL200 Optimizer tests.

Provides common fixtures for:
- Sample BDF models
- Pre-configured optimization models
- Test data paths
"""

import pytest
import tempfile
from pathlib import Path


@pytest.fixture
def sample_bdf_content():
    """Sample BDF file content for testing."""
    return """$ Sample BDF for SOL200 Optimizer testing
SOL 200
CEND
SUBCASE 1
  ANALYSIS = MODES
  METHOD = 10
  SPC = 1
  DESOBJ(MIN) = 1
  DESSUB = 1
BEGIN BULK
$
$ Grid points
GRID,1,,0.0,0.0,0.0
GRID,2,,1.0,0.0,0.0
GRID,3,,1.0,1.0,0.0
GRID,4,,0.0,1.0,0.0
GRID,100,,0.5,0.5,0.0
$
$ Shell elements
CQUAD4,1,101,1,2,3,4
$
$ Shell property
PSHELL,101,1,0.01,,1
$
$ Bar property
PBAR,201,1,0.001,0.0001,0.0001,0.0002
$
$ PBARL rectangular property
PBARL,301,1,,BAR
,0.05,0.02
$
$ Rod property
PROD,401,1,0.0005,0.0001
$
$ Material
MAT1,1,2.1E11,,0.3,7800.0
$
$ Constraints
SPC1,1,123456,1
$
$ Frequency method
EIGRL,10,0.0,2000.0,20
$
ENDDATA
"""


@pytest.fixture
def temp_bdf_file(sample_bdf_content):
    """Create a temporary BDF file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.bdf', delete=False) as f:
        f.write(sample_bdf_content)
        return Path(f.name)


@pytest.fixture
def sample_optimization_model():
    """Create a sample optimization model for testing."""
    from nastran_optimizer.core import (
        OptimizationModel,
        DesignResponse,
        DesignConstraint,
        ObjectiveFunction,
        ResponseType,
        ObjectiveType,
    )

    model = OptimizationModel("Test Optimization")

    # Add design variables
    model.add_design_variable(
        label="T1",
        initial_value=0.01,
        lower_bound=0.005,
        upper_bound=0.02,
        description="Panel 1 thickness",
    )
    model.add_design_variable(
        label="T2",
        initial_value=0.008,
        lower_bound=0.004,
        upper_bound=0.016,
        description="Panel 2 thickness",
    )

    # Add weight response
    weight_resp = DesignResponse(
        label="WEIGHT",
        response_type=ResponseType.WEIGHT,
        description="Total weight",
    )
    weight_id = model.add_response(weight_resp)

    # Add acceleration response
    acc_resp = DesignResponse(
        label="ACC1",
        response_type=ResponseType.FRACCL,
        description="Acceleration at node 100",
        region=100,
        component=3,
        atta=100.0,
    )
    acc_id = model.add_response(acc_resp)

    # Add weight constraint
    model.add_constraint(DesignConstraint(
        response_id=weight_id,
        upper_bound=1000.0,
    ))

    # Set objective
    model.objective = ObjectiveFunction(
        response_id=acc_id,
        objective_type=ObjectiveType.MINIMIZE,
    )

    return model


@pytest.fixture
def complete_rms_model():
    """Create a complete RMS optimization model."""
    import numpy as np
    from nastran_optimizer.core import (
        OptimizationModel,
        DesignResponse,
        DesignConstraint,
        ObjectiveFunction,
        ResponseType,
        ObjectiveType,
    )

    model = OptimizationModel("RMS Optimization")

    # Add design variables
    for i in range(1, 4):
        model.add_design_variable(
            label=f"T{i}",
            initial_value=0.01,
            lower_bound=0.005,
            upper_bound=0.02,
        )

    # Add acceleration responses at multiple frequencies
    frequencies = np.logspace(np.log10(20), np.log10(2000), 5)
    dresp1_ids = []

    for i, freq in enumerate(frequencies):
        resp = DesignResponse(
            label=f"A{i+1:02d}",
            response_type=ResponseType.FRACCL,
            region=100,
            component=3,
            atta=freq,
        )
        resp_id = model.add_response(resp)
        dresp1_ids.append(resp_id)

    # Add RMS response
    rms_resp = DesignResponse(
        label="RMSACC",
        response_type=ResponseType.DRESP2,
        description="RMS Acceleration",
        dresp1_refs=dresp1_ids,
    )
    rms_id = model.add_response(rms_resp)

    # Set objective
    model.objective = ObjectiveFunction(
        response_id=rms_id,
        objective_type=ObjectiveType.MINIMIZE,
    )

    # Add weight response and constraint
    weight_resp = DesignResponse(
        label="WEIGHT",
        response_type=ResponseType.WEIGHT,
    )
    weight_id = model.add_response(weight_resp)

    model.add_constraint(DesignConstraint(
        response_id=weight_id,
        upper_bound=1500.0,
    ))

    return model


@pytest.fixture
def temp_project_dir():
    """Create a temporary directory for project files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


# Fixtures for GUI testing
@pytest.fixture
def qapp():
    """Create a QApplication for GUI tests."""
    try:
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        yield app
    except ImportError:
        pytest.skip("PyQt6 not available")


@pytest.fixture
def main_window(qapp, sample_optimization_model):
    """Create a main window for GUI tests."""
    try:
        from nastran_optimizer.ui.main_window import SOL200OptimizerWindow
        window = SOL200OptimizerWindow()
        window.opt_model = sample_optimization_model
        yield window
        window.close()
    except ImportError:
        pytest.skip("GUI components not available")
