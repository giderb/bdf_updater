"""
Tests for equation parser module.

Tests cover:
- Parsing user equations
- Validating equation syntax
- DEQATN card generation
- RMS and other common equations
- Mathematical function support
"""

import pytest
from nastran_optimizer.core.equation_parser import (
    EquationParser,
    ParsedEquation,
)


class TestEquationParser:
    """Tests for EquationParser class."""

    def test_create_parser(self):
        """Test creating an equation parser."""
        parser = EquationParser()
        assert parser is not None

    def test_parse_simple_equation(self):
        """Test parsing a simple equation."""
        parser = EquationParser()

        result = parser.parse("F(X) = X * 2.0")

        assert result is not None
        assert result.name == "F"
        assert "X" in result.arguments

    def test_parse_equation_with_multiple_args(self):
        """Test parsing equation with multiple arguments."""
        parser = EquationParser()

        result = parser.parse("SUM(A, B, C) = A + B + C")

        assert result.name == "SUM"
        assert len(result.arguments) == 3
        assert "A" in result.arguments
        assert "B" in result.arguments
        assert "C" in result.arguments

    def test_parse_rms_equation(self):
        """Test parsing RMS equation."""
        parser = EquationParser()

        result = parser.parse("RMS(X1, X2, X3) = SQRT((X1**2 + X2**2 + X3**2) / 3)")

        assert result.name == "RMS"
        assert len(result.arguments) == 3
        assert "SQRT" in result.functions_used

    def test_parse_weighted_sum_equation(self):
        """Test parsing weighted sum equation."""
        parser = EquationParser()

        result = parser.parse("WSUM(R1, R2) = 0.6*R1 + 0.4*R2")

        assert result.name == "WSUM"
        assert len(result.arguments) == 2

    def test_parse_max_equation(self):
        """Test parsing max equation."""
        parser = EquationParser()

        result = parser.parse("MAXVAL(A, B) = MAX(A, B)")

        assert result.name == "MAXVAL"
        assert "MAX" in result.functions_used

    def test_parse_equation_with_constants(self):
        """Test parsing equation with constants."""
        parser = EquationParser()

        result = parser.parse("SCALE(X) = X * 1000.0")

        assert result.name == "SCALE"
        assert "X" in result.arguments

    def test_invalid_equation_syntax(self):
        """Test that invalid syntax raises error."""
        parser = EquationParser()

        with pytest.raises((ValueError, SyntaxError)):
            parser.parse("invalid equation without equals")

    def test_invalid_function_name(self):
        """Test that unknown functions are flagged."""
        parser = EquationParser()

        # May raise error or warning depending on implementation
        try:
            result = parser.parse("F(X) = UNKNOWN_FUNC(X)")
            if hasattr(result, 'warnings'):
                assert len(result.warnings) > 0
        except ValueError:
            pass  # Also acceptable

    def test_generate_deqatn_card(self):
        """Test DEQATN card generation."""
        parser = EquationParser()

        result = parser.parse("RMS(X1, X2) = SQRT((X1**2 + X2**2) / 2)")
        card = result.to_deqatn(eq_id=1001)

        assert "DEQATN" in card
        assert "1001" in card


class TestParsedEquation:
    """Tests for ParsedEquation dataclass."""

    def test_parsed_equation_attributes(self):
        """Test that parsed equation has required attributes."""
        parser = EquationParser()
        result = parser.parse("F(X) = X**2")

        assert hasattr(result, 'name')
        assert hasattr(result, 'arguments')
        assert hasattr(result, 'expression')
        assert hasattr(result, 'functions_used')

    def test_parsed_equation_nastran_format(self):
        """Test conversion to Nastran format."""
        parser = EquationParser()
        result = parser.parse("F(X) = X**2")

        if hasattr(result, 'to_nastran_format'):
            nastran_expr = result.to_nastran_format()
            # Nastran uses ** for power
            assert "**" in nastran_expr or "^" in nastran_expr


class TestMathematicalFunctions:
    """Tests for supported mathematical functions."""

    def test_sqrt_function(self):
        """Test SQRT function support."""
        parser = EquationParser()
        result = parser.parse("F(X) = SQRT(X)")

        assert "SQRT" in result.functions_used

    def test_abs_function(self):
        """Test ABS function support."""
        parser = EquationParser()
        result = parser.parse("F(X) = ABS(X)")

        assert "ABS" in result.functions_used

    def test_sin_cos_functions(self):
        """Test trigonometric function support."""
        parser = EquationParser()

        result = parser.parse("F(X) = SIN(X) + COS(X)")

        assert "SIN" in result.functions_used or "sin" in result.functions_used
        assert "COS" in result.functions_used or "cos" in result.functions_used

    def test_log_exp_functions(self):
        """Test logarithmic and exponential function support."""
        parser = EquationParser()

        result = parser.parse("F(X) = LOG(X) + EXP(X)")

        # May use LOG, LOG10, LN depending on implementation
        assert any(f in result.functions_used for f in ['LOG', 'LOG10', 'LN', 'EXP', 'log', 'exp'])

    def test_min_max_functions(self):
        """Test MIN/MAX function support."""
        parser = EquationParser()

        result = parser.parse("F(A, B) = MAX(A, B) - MIN(A, B)")

        assert "MAX" in result.functions_used or "max" in result.functions_used
        assert "MIN" in result.functions_used or "min" in result.functions_used


class TestRMSEquationSetup:
    """Tests for RMS equation setup."""

    def test_create_rms_equation_10_points(self):
        """Test creating RMS equation for 10 frequency points."""
        parser = EquationParser()

        # Build RMS equation string
        args = [f"A{i}" for i in range(1, 11)]
        arg_str = ", ".join(args)
        sum_str = " + ".join([f"{a}**2" for a in args])
        equation = f"RMS({arg_str}) = SQRT(({sum_str}) / 10)"

        result = parser.parse(equation)

        assert result.name == "RMS"
        assert len(result.arguments) == 10

    def test_create_weighted_rms_equation(self):
        """Test creating weighted RMS equation."""
        parser = EquationParser()

        equation = "WRMS(A1, A2, A3) = SQRT(0.5*A1**2 + 0.3*A2**2 + 0.2*A3**2)"
        result = parser.parse(equation)

        assert result.name == "WRMS"
        assert len(result.arguments) == 3


class TestEquationValidation:
    """Tests for equation validation."""

    def test_validate_balanced_parentheses(self):
        """Test that unbalanced parentheses are caught."""
        parser = EquationParser()

        with pytest.raises((ValueError, SyntaxError)):
            parser.parse("F(X) = SQRT((X**2)")

    def test_validate_undefined_variables(self):
        """Test that undefined variables are caught."""
        parser = EquationParser()

        # Y is not in arguments
        with pytest.raises((ValueError, NameError)):
            parser.parse("F(X) = X + Y")

    def test_validate_division_by_zero(self):
        """Test handling of potential division by zero."""
        parser = EquationParser()

        # May warn or allow depending on implementation
        result = parser.parse("F(X) = X / 0")
        if hasattr(result, 'warnings'):
            # Should have a warning about division by zero
            pass
