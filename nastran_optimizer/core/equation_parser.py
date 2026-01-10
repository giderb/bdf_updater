"""
Equation Parser for DEQATN card generation.

Parses user-defined mathematical expressions and generates valid
MSC Nastran DEQATN cards.

DEQATN Format:
    DEQATN  EQID    EQUATION

Supported functions:
    - Arithmetic: +, -, *, /, **
    - Functions: SQRT, ABS, SIN, COS, TAN, ATAN, ATAN2, EXP, LOG, LOG10
    - Comparison: MIN, MAX
    - Special: SUM, AVG (custom implementation)

Example:
    RMS(A1,A2,A3) = SQRT((A1**2 + A2**2 + A3**2) / 3)
"""

import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Set, Tuple, Union
import sympy as sp


class EquationError(Exception):
    """Exception raised for equation parsing errors."""
    pass


class NastranFunction(Enum):
    """Functions supported by Nastran DEQATN."""
    SQRT = "SQRT"
    ABS = "ABS"
    SIN = "SIN"
    COS = "COS"
    TAN = "TAN"
    ASIN = "ASIN"
    ACOS = "ACOS"
    ATAN = "ATAN"
    ATAN2 = "ATAN2"
    EXP = "EXP"
    LOG = "LOG"       # Natural log
    LOG10 = "LOG10"   # Base-10 log
    MIN = "MIN"
    MAX = "MAX"
    MOD = "MOD"
    INT = "INT"
    SIGN = "SIGN"
    DIM = "DIM"       # Positive difference


@dataclass
class ParsedEquation:
    """
    Parsed and validated equation ready for DEQATN generation.

    Attributes:
        id: DEQATN ID
        name: Function name (left side of =)
        arguments: List of argument names
        expression: Right side expression
        variables: Set of variable names used
        functions_used: Set of Nastran functions used
        original_input: Original user input
        nastran_format: Equation in Nastran DEQATN format
    """
    id: int
    name: str
    arguments: List[str]
    expression: str
    variables: Set[str] = field(default_factory=set)
    functions_used: Set[str] = field(default_factory=set)
    original_input: str = ""
    nastran_format: str = ""

    def to_deqatn(self) -> str:
        """Generate DEQATN card."""
        eq_str = f"{self.name}({','.join(self.arguments)}) = {self.expression}"
        return f"DEQATN  {self.id}       {eq_str}"

    def to_deqatn_lines(self, max_length: int = 64) -> List[str]:
        """
        Generate DEQATN card split into continuation lines if needed.

        Nastran has a max line length of 72 characters (80 with sequence).
        """
        eq_str = f"{self.name}({','.join(self.arguments)}) = {self.expression}"
        first_line = f"DEQATN  {self.id}       "

        if len(first_line + eq_str) <= max_length:
            return [first_line + eq_str]

        # Need to split equation
        lines = []
        remaining = eq_str
        lines.append(first_line + remaining[:max_length - len(first_line)])
        remaining = remaining[max_length - len(first_line):]

        while remaining:
            cont_prefix = "+       "
            chunk_size = max_length - len(cont_prefix)
            lines.append(cont_prefix + remaining[:chunk_size])
            remaining = remaining[chunk_size:]

        return lines


class EquationParser:
    """
    Parser for mathematical expressions to Nastran DEQATN format.

    Validates expressions and converts to Nastran-compatible syntax.
    """

    # Pattern for function definition: NAME(args) = expression
    FUNCTION_PATTERN = re.compile(
        r'^([A-Z][A-Z0-9_]*)\s*\(\s*([^)]+)\s*\)\s*=\s*(.+)$',
        re.IGNORECASE
    )

    # Pattern for variable names
    VARIABLE_PATTERN = re.compile(r'[A-Z][A-Z0-9_]*', re.IGNORECASE)

    # Nastran function names (case insensitive)
    NASTRAN_FUNCTIONS = {f.value.upper() for f in NastranFunction}

    # Operator precedence for validation
    OPERATORS = {'+', '-', '*', '/', '**', '^'}

    def __init__(self):
        """Initialize the parser."""
        self._next_id = 1
        self._parsed_equations: Dict[int, ParsedEquation] = {}

    def set_next_id(self, id: int):
        """Set the next equation ID to use."""
        self._next_id = id

    def parse(self, equation_str: str) -> ParsedEquation:
        """
        Parse an equation string into a ParsedEquation.

        Args:
            equation_str: Equation like "RMS(A1,A2,A3) = SQRT((A1**2+A2**2+A3**2)/3)"

        Returns:
            ParsedEquation object

        Raises:
            EquationError: If parsing fails
        """
        # Clean input
        equation_str = equation_str.strip()

        # Try to match function pattern
        match = self.FUNCTION_PATTERN.match(equation_str)
        if not match:
            raise EquationError(
                f"Invalid equation format. Expected: NAME(args) = expression\n"
                f"Got: {equation_str}"
            )

        name = match.group(1).upper()
        args_str = match.group(2)
        expression = match.group(3).strip()

        # Parse arguments
        arguments = [arg.strip().upper() for arg in args_str.split(',')]
        if not all(self._is_valid_name(arg) for arg in arguments):
            raise EquationError(f"Invalid argument names: {arguments}")

        # Validate and normalize expression
        expression, variables, functions = self._process_expression(expression, arguments)

        # Create parsed equation
        eq_id = self._next_id
        self._next_id += 1

        parsed = ParsedEquation(
            id=eq_id,
            name=name,
            arguments=arguments,
            expression=expression,
            variables=variables,
            functions_used=functions,
            original_input=equation_str,
        )
        parsed.nastran_format = parsed.to_deqatn()

        self._parsed_equations[eq_id] = parsed
        return parsed

    def _is_valid_name(self, name: str) -> bool:
        """Check if a name is valid for Nastran."""
        if not name:
            return False
        if len(name) > 8:
            return False
        if not name[0].isalpha():
            return False
        return name.replace('_', '').isalnum()

    def _process_expression(
        self,
        expression: str,
        valid_args: List[str],
    ) -> Tuple[str, Set[str], Set[str]]:
        """
        Process and validate an expression.

        Args:
            expression: The expression to process
            valid_args: List of valid argument names

        Returns:
            Tuple of (processed_expression, variables_used, functions_used)
        """
        # Convert to uppercase for Nastran
        expression = expression.upper()

        # Replace ^ with ** for exponentiation
        expression = expression.replace('^', '**')

        # Find all identifiers
        identifiers = set(self.VARIABLE_PATTERN.findall(expression))

        # Separate variables from functions
        variables = set()
        functions = set()

        valid_args_upper = {a.upper() for a in valid_args}

        for ident in identifiers:
            ident_upper = ident.upper()
            if ident_upper in self.NASTRAN_FUNCTIONS:
                functions.add(ident_upper)
            elif ident_upper in valid_args_upper:
                variables.add(ident_upper)
            else:
                # Check if it might be a number or constant
                if not self._is_numeric_or_constant(ident):
                    raise EquationError(
                        f"Unknown identifier '{ident}' in expression. "
                        f"Valid arguments: {valid_args}"
                    )

        # Validate parentheses balance
        if expression.count('(') != expression.count(')'):
            raise EquationError("Unbalanced parentheses in expression")

        # Try to parse with sympy for validation
        try:
            self._sympy_validate(expression, valid_args_upper)
        except Exception as e:
            raise EquationError(f"Expression validation failed: {e}")

        return expression, variables, functions

    def _is_numeric_or_constant(self, s: str) -> bool:
        """Check if string is a number or known constant."""
        # Try to parse as number
        try:
            float(s)
            return True
        except ValueError:
            pass

        # Known constants
        constants = {'PI', 'E'}
        return s.upper() in constants

    def _sympy_validate(self, expression: str, valid_vars: Set[str]):
        """
        Validate expression using sympy.

        This catches syntax errors and unsupported operations.
        """
        # Create sympy symbols for all variables
        symbols = {v: sp.Symbol(v) for v in valid_vars}

        # Map Nastran functions to sympy equivalents
        func_map = {
            'SQRT': 'sqrt',
            'ABS': 'Abs',
            'SIN': 'sin',
            'COS': 'cos',
            'TAN': 'tan',
            'ASIN': 'asin',
            'ACOS': 'acos',
            'ATAN': 'atan',
            'EXP': 'exp',
            'LOG': 'log',
            'LOG10': 'log',
        }

        # Replace Nastran functions with sympy equivalents
        expr_sympy = expression
        for nastran_func, sympy_func in func_map.items():
            expr_sympy = re.sub(
                rf'\b{nastran_func}\b',
                sympy_func,
                expr_sympy,
                flags=re.IGNORECASE
            )

        # Try to parse (this validates syntax)
        try:
            sp.sympify(expr_sympy, locals=symbols)
        except sp.SympifyError as e:
            raise EquationError(f"Sympy parsing error: {e}")

    def create_rms_equation(
        self,
        num_responses: int,
        prefix: str = "R",
    ) -> ParsedEquation:
        """
        Create an RMS (Root Mean Square) equation.

        RMS = SQRT((R1**2 + R2**2 + ... + RN**2) / N)

        Args:
            num_responses: Number of responses to include
            prefix: Variable name prefix (default "R")

        Returns:
            ParsedEquation for RMS calculation
        """
        if num_responses < 1:
            raise EquationError("RMS requires at least 1 response")

        args = [f"{prefix}{i+1}" for i in range(num_responses)]
        sum_terms = " + ".join([f"{arg}**2" for arg in args])
        expression = f"SQRT(({sum_terms}) / {num_responses})"

        equation_str = f"RMS({','.join(args)}) = {expression}"
        return self.parse(equation_str)

    def create_weighted_sum_equation(
        self,
        weights: List[float],
        prefix: str = "R",
    ) -> ParsedEquation:
        """
        Create a weighted sum equation.

        WSUM = W1*R1 + W2*R2 + ... + WN*RN

        Args:
            weights: List of weights for each response
            prefix: Variable name prefix (default "R")

        Returns:
            ParsedEquation for weighted sum
        """
        if not weights:
            raise EquationError("Weighted sum requires at least 1 weight")

        args = [f"{prefix}{i+1}" for i in range(len(weights))]
        terms = []
        for i, w in enumerate(weights):
            if w == 1.0:
                terms.append(args[i])
            elif w == -1.0:
                terms.append(f"-{args[i]}")
            else:
                terms.append(f"{w:.6g}*{args[i]}")

        expression = " + ".join(terms).replace("+ -", "- ")

        equation_str = f"WSUM({','.join(args)}) = {expression}"
        return self.parse(equation_str)

    def create_max_equation(
        self,
        num_responses: int,
        prefix: str = "R",
    ) -> ParsedEquation:
        """
        Create a maximum of responses equation.

        For 2 responses: MAXR = MAX(R1, R2)
        For more: uses nested MAX calls

        Args:
            num_responses: Number of responses
            prefix: Variable name prefix

        Returns:
            ParsedEquation for maximum
        """
        if num_responses < 2:
            raise EquationError("MAX requires at least 2 responses")

        args = [f"{prefix}{i+1}" for i in range(num_responses)]

        # Build nested MAX for more than 2 args (Nastran MAX takes 2 args)
        if num_responses == 2:
            expression = f"MAX({args[0]}, {args[1]})"
        else:
            # Nest: MAX(MAX(MAX(R1,R2),R3),R4)...
            expression = f"MAX({args[0]}, {args[1]})"
            for i in range(2, num_responses):
                expression = f"MAX({expression}, {args[i]})"

        equation_str = f"MAXR({','.join(args)}) = {expression}"
        return self.parse(equation_str)

    def create_custom_equation(
        self,
        name: str,
        arguments: List[str],
        expression: str,
    ) -> ParsedEquation:
        """
        Create a custom equation from components.

        Args:
            name: Function name
            arguments: List of argument names
            expression: Mathematical expression

        Returns:
            ParsedEquation
        """
        equation_str = f"{name}({','.join(arguments)}) = {expression}"
        return self.parse(equation_str)

    def get_equation(self, eq_id: int) -> Optional[ParsedEquation]:
        """Get a parsed equation by ID."""
        return self._parsed_equations.get(eq_id)

    def get_all_equations(self) -> List[ParsedEquation]:
        """Get all parsed equations."""
        return list(self._parsed_equations.values())


def create_rms_acceleration_equations(
    node_ids: List[int],
    dof: int,
    frequencies: List[float],
    start_id: int = 1000,
) -> Tuple[List[str], int]:
    """
    Create all equations needed for RMS acceleration calculation.

    This creates:
    1. DRESP1 for each frequency point
    2. DRESP2 for RMS combining all frequencies
    3. DEQATN for the RMS calculation

    Args:
        node_ids: Grid point IDs
        dof: Degree of freedom (1-6)
        frequencies: List of frequencies in Hz
        start_id: Starting ID for cards

    Returns:
        Tuple of (list of card strings, final DRESP2 ID for objective)
    """
    cards = []
    dresp1_ids = []
    current_id = start_id

    # Create DRESP1 for each node/frequency combination
    for node_id in node_ids:
        for freq in frequencies:
            dresp1_id = current_id
            current_id += 1
            dresp1_ids.append(dresp1_id)

            label = f"AC{node_id}"[:8]
            # DRESP1, ID, LABEL, RTYPE, PTYPE, REGION, ATTA, ATTB, ATTi
            # ATTA=3 for magnitude, ATTi = node*10 + dof
            card = f"DRESP1,{dresp1_id},{label},FRACCL,,3,{freq},{node_id*10+dof}"
            cards.append(card)

    # Create DEQATN for RMS
    n = len(dresp1_ids)
    eq_id = current_id
    current_id += 1

    args = ",".join([f"R{i+1}" for i in range(n)])
    sum_terms = " + ".join([f"R{i+1}**2" for i in range(n)])
    deqatn = f"DEQATN  {eq_id}       RMS({args}) = SQRT(({sum_terms}) / {n})"
    cards.append(deqatn)

    # Create DRESP2 for RMS
    dresp2_id = current_id
    cards.append(f"DRESP2,{dresp2_id},RMSACC,{eq_id},,,,")
    cards.append("+,DRESP1," + ",".join(str(d) for d in dresp1_ids))

    return cards, dresp2_id
