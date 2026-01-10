"""
Core optimization engine for MSC Nastran SOL200.

This module provides the fundamental building blocks for structural optimization:
- Design variables (DESVAR, DVPREL1/2)
- Design responses (DRESP1, DRESP2)
- Design constraints (DCONSTR)
- Objective functions
- Equation parsing (DEQATN)
"""

from .design_variable import (
    DesignVariable,
    DesignVariableLink,
    PropertyType,
    PropertyField,
    LinkType,
)
from .response import (
    DesignResponse,
    ResponseType,
    ResponseAttribute,
)
from .constraint import (
    DesignConstraint,
    ConstraintType,
)
from .objective import (
    ObjectiveFunction,
    ObjectiveType,
)
from .equation_parser import (
    EquationParser,
    ParsedEquation,
)
from .bdf_manager import BDFManager
from .optimization_model import OptimizationModel
from .nastran_runner import NastranRunner, NastranResult
from .validator import (
    ValidationResult,
    ValidationSeverity,
    ModelValidator,
)

__all__ = [
    'DesignVariable',
    'DesignVariableLink',
    'PropertyType',
    'PropertyField',
    'LinkType',
    'DesignResponse',
    'ResponseType',
    'ResponseAttribute',
    'DesignConstraint',
    'ConstraintType',
    'ObjectiveFunction',
    'ObjectiveType',
    'EquationParser',
    'ParsedEquation',
    'BDFManager',
    'OptimizationModel',
    'NastranRunner',
    'NastranResult',
    'ValidationResult',
    'ValidationSeverity',
    'ModelValidator',
]
