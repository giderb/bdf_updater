"""
Nastran Runner for executing SOL200 optimization.

Handles:
- MSC Nastran execution
- Job monitoring
- Result parsing (F06, OP2)
- Convergence tracking
"""

import os
import re
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple, Union
from enum import Enum, auto
import threading


class NastranStatus(Enum):
    """Status of Nastran execution."""
    NOT_STARTED = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()


@dataclass
class DesignCycleResult:
    """Results from a single design cycle."""
    cycle_number: int
    objective_value: float
    max_constraint_violation: float
    design_variable_values: Dict[int, float] = field(default_factory=dict)
    response_values: Dict[int, float] = field(default_factory=dict)
    constraint_values: Dict[int, float] = field(default_factory=dict)
    is_feasible: bool = True


@dataclass
class NastranResult:
    """
    Complete results from Nastran SOL200 execution.

    Attributes:
        success: Whether execution completed successfully
        exit_code: Process exit code
        cycles: List of design cycle results
        initial_objective: Starting objective value
        final_objective: Final objective value
        improvement: Percentage improvement
        final_design: Final design variable values
        cpu_time: Total CPU time
        wall_time: Wall clock time
        error_message: Error message if failed
        warnings: List of warning messages
    """
    success: bool
    exit_code: int = 0
    cycles: List[DesignCycleResult] = field(default_factory=list)
    initial_objective: Optional[float] = None
    final_objective: Optional[float] = None
    improvement: Optional[float] = None
    final_design: Dict[int, float] = field(default_factory=dict)
    cpu_time: float = 0.0
    wall_time: float = 0.0
    error_message: str = ""
    warnings: List[str] = field(default_factory=list)

    def get_convergence_history(self) -> List[float]:
        """Get objective values over design cycles."""
        return [c.objective_value for c in self.cycles]

    def get_final_cycle(self) -> Optional[DesignCycleResult]:
        """Get the final design cycle result."""
        return self.cycles[-1] if self.cycles else None


class NastranRunner:
    """
    Runner for MSC Nastran SOL200 optimization.

    Executes Nastran jobs and monitors progress.
    """

    # Default Nastran executable paths by OS
    DEFAULT_PATHS = {
        'win32': [
            r'C:\MSC.Software\MSC_Nastran\2023\bin\nastran.exe',
            r'C:\MSC.Software\MSC_Nastran\2022\bin\nastran.exe',
            r'C:\MSC.Software\MSC_Nastran\2021\bin\nastran.exe',
        ],
        'linux': [
            '/msc/MSC_Nastran/2023/bin/nastran',
            '/msc/MSC_Nastran/2022/bin/nastran',
            '/opt/msc/nastran/bin/nastran',
        ],
        'darwin': [
            '/Applications/MSC_Nastran/2023/bin/nastran',
        ],
    }

    def __init__(self, nastran_path: Optional[str] = None):
        """
        Initialize the runner.

        Args:
            nastran_path: Path to Nastran executable (auto-detected if None)
        """
        self.nastran_path = nastran_path or self._find_nastran()
        self.status = NastranStatus.NOT_STARTED
        self._process: Optional[subprocess.Popen] = None
        self._monitor_thread: Optional[threading.Thread] = None
        self._cancel_flag = False

        # Callbacks
        self.on_progress: Optional[Callable[[int, str], None]] = None
        self.on_cycle_complete: Optional[Callable[[DesignCycleResult], None]] = None
        self.on_complete: Optional[Callable[[NastranResult], None]] = None

    def _find_nastran(self) -> Optional[str]:
        """Auto-detect Nastran installation."""
        import sys
        platform = sys.platform

        paths = self.DEFAULT_PATHS.get(platform, [])
        for path in paths:
            if os.path.exists(path):
                return path

        # Check PATH environment
        nastran_cmd = 'nastran.exe' if platform == 'win32' else 'nastran'
        for path_dir in os.environ.get('PATH', '').split(os.pathsep):
            full_path = os.path.join(path_dir, nastran_cmd)
            if os.path.exists(full_path):
                return full_path

        return None

    def is_nastran_available(self) -> bool:
        """Check if Nastran is available."""
        return self.nastran_path is not None and os.path.exists(self.nastran_path)

    def run(
        self,
        bdf_path: Union[str, Path],
        output_dir: Optional[Union[str, Path]] = None,
        memory: str = "4gb",
        parallel: int = 1,
        scratch_dir: Optional[str] = None,
        additional_args: Optional[List[str]] = None,
    ) -> NastranResult:
        """
        Run Nastran SOL200 optimization.

        Args:
            bdf_path: Path to input BDF file
            output_dir: Output directory (uses BDF directory if None)
            memory: Memory allocation (e.g., "4gb")
            parallel: Number of parallel processors
            scratch_dir: Scratch directory
            additional_args: Additional command line arguments

        Returns:
            NastranResult with execution results
        """
        bdf_path = Path(bdf_path)
        if not bdf_path.exists():
            return NastranResult(
                success=False,
                error_message=f"BDF file not found: {bdf_path}",
            )

        if not self.is_nastran_available():
            return NastranResult(
                success=False,
                error_message="Nastran executable not found",
            )

        if output_dir is None:
            output_dir = bdf_path.parent
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Build command
        cmd = [
            self.nastran_path,
            str(bdf_path),
            f"mem={memory}",
            f"parallel={parallel}",
            f"out={output_dir}",
        ]

        if scratch_dir:
            cmd.append(f"scratch={scratch_dir}")

        if additional_args:
            cmd.extend(additional_args)

        # Track timing
        start_time = time.time()
        self.status = NastranStatus.RUNNING
        self._cancel_flag = False

        try:
            # Run Nastran
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(output_dir),
            )

            # Start monitor thread
            self._start_monitor(bdf_path.stem, output_dir)

            # Wait for completion
            stdout, stderr = self._process.communicate()

            # Check result
            exit_code = self._process.returncode
            wall_time = time.time() - start_time

            if self._cancel_flag:
                self.status = NastranStatus.CANCELLED
                return NastranResult(
                    success=False,
                    exit_code=exit_code,
                    wall_time=wall_time,
                    error_message="Job cancelled by user",
                )

            if exit_code != 0:
                self.status = NastranStatus.FAILED
                return NastranResult(
                    success=False,
                    exit_code=exit_code,
                    wall_time=wall_time,
                    error_message=f"Nastran exited with code {exit_code}",
                )

            # Parse results
            self.status = NastranStatus.COMPLETED
            f06_path = output_dir / f"{bdf_path.stem}.f06"

            return self._parse_results(f06_path, wall_time)

        except Exception as e:
            self.status = NastranStatus.FAILED
            return NastranResult(
                success=False,
                error_message=str(e),
            )

    def _start_monitor(self, job_name: str, output_dir: Path):
        """Start background monitoring thread."""
        def monitor():
            f06_path = output_dir / f"{job_name}.f06"
            last_size = 0

            while self.status == NastranStatus.RUNNING and not self._cancel_flag:
                time.sleep(2)

                if f06_path.exists():
                    current_size = f06_path.stat().st_size
                    if current_size > last_size:
                        # Parse recent progress
                        progress = self._parse_progress(f06_path)
                        if progress and self.on_progress:
                            self.on_progress(*progress)
                        last_size = current_size

        self._monitor_thread = threading.Thread(target=monitor, daemon=True)
        self._monitor_thread.start()

    def _parse_progress(self, f06_path: Path) -> Optional[Tuple[int, str]]:
        """Parse F06 for current progress."""
        try:
            with open(f06_path, 'r') as f:
                content = f.read()

            # Look for design cycle markers
            cycle_matches = re.findall(r'DESIGN CYCLE\s+(\d+)', content)
            if cycle_matches:
                cycle = int(cycle_matches[-1])
                return (cycle, f"Design cycle {cycle}")

        except Exception:
            pass
        return None

    def _parse_results(self, f06_path: Path, wall_time: float) -> NastranResult:
        """Parse F06 file for optimization results."""
        result = NastranResult(
            success=True,
            wall_time=wall_time,
        )

        if not f06_path.exists():
            result.warnings.append("F06 file not found")
            return result

        try:
            with open(f06_path, 'r') as f:
                content = f.read()

            # Parse design cycles
            result.cycles = self._parse_design_cycles(content)

            # Extract final values
            if result.cycles:
                result.initial_objective = result.cycles[0].objective_value
                result.final_objective = result.cycles[-1].objective_value

                if result.initial_objective and result.initial_objective != 0:
                    result.improvement = (
                        (result.initial_objective - result.final_objective)
                        / abs(result.initial_objective) * 100
                    )

                # Final design variables
                result.final_design = result.cycles[-1].design_variable_values.copy()

            # Check for fatal errors
            if 'FATAL' in content or 'USER FATAL' in content:
                result.success = False
                fatal_match = re.search(r'FATAL.*?MESSAGE.*?\n(.+?)(?=\n\n|\Z)', content, re.DOTALL)
                if fatal_match:
                    result.error_message = fatal_match.group(1).strip()

            # Check for warnings
            warning_matches = re.findall(r'USER WARNING MESSAGE\s+\d+.*?\n(.+?)(?=\n\n)', content)
            result.warnings.extend([w.strip() for w in warning_matches])

            # Parse CPU time
            cpu_match = re.search(r'TOTAL CPU TIME\s+=\s+([\d.]+)', content)
            if cpu_match:
                result.cpu_time = float(cpu_match.group(1))

        except Exception as e:
            result.warnings.append(f"Error parsing F06: {e}")

        return result

    def _parse_design_cycles(self, content: str) -> List[DesignCycleResult]:
        """Parse design cycle information from F06 content."""
        cycles = []

        # Pattern for design cycle summary
        # This is a simplified parser - actual F06 format varies
        cycle_pattern = re.compile(
            r'DESIGN CYCLE\s+(\d+).*?'
            r'OBJECTIVE\s*=\s*([\d.E+-]+).*?'
            r'MAXIMUM CONSTRAINT\s*=\s*([\d.E+-]+)',
            re.DOTALL
        )

        for match in cycle_pattern.finditer(content):
            try:
                cycle = DesignCycleResult(
                    cycle_number=int(match.group(1)),
                    objective_value=float(match.group(2)),
                    max_constraint_violation=float(match.group(3)),
                    is_feasible=float(match.group(3)) <= 0.003,  # CTOL tolerance
                )
                cycles.append(cycle)
            except (ValueError, IndexError):
                continue

        return cycles

    def cancel(self):
        """Cancel running job."""
        self._cancel_flag = True
        if self._process and self._process.poll() is None:
            self._process.terminate()
            self.status = NastranStatus.CANCELLED

    def get_status(self) -> NastranStatus:
        """Get current execution status."""
        return self.status


class NastranResultParser:
    """
    Parser for Nastran result files.

    Handles F06 and OP2 parsing for SOL200 results.
    """

    @staticmethod
    def parse_f06(f06_path: Union[str, Path]) -> Dict:
        """
        Parse F06 file for optimization results.

        Args:
            f06_path: Path to F06 file

        Returns:
            Dictionary with parsed results
        """
        f06_path = Path(f06_path)
        results = {
            'design_cycles': [],
            'final_design': {},
            'convergence_history': [],
            'warnings': [],
            'errors': [],
        }

        if not f06_path.exists():
            results['errors'].append(f"F06 file not found: {f06_path}")
            return results

        with open(f06_path, 'r') as f:
            content = f.read()

        # Parse design cycle summary table
        cycle_table = re.search(
            r'DESIGN CYCLE SUMMARY.*?\n(.*?)(?=\n\n)',
            content,
            re.DOTALL
        )

        if cycle_table:
            lines = cycle_table.group(1).strip().split('\n')
            for line in lines:
                parts = line.split()
                if len(parts) >= 3 and parts[0].isdigit():
                    results['design_cycles'].append({
                        'cycle': int(parts[0]),
                        'objective': float(parts[1]),
                        'constraint': float(parts[2]) if len(parts) > 2 else 0.0,
                    })

        return results

    @staticmethod
    def parse_op2(op2_path: Union[str, Path]) -> Dict:
        """
        Parse OP2 file for detailed results.

        Args:
            op2_path: Path to OP2 file

        Returns:
            Dictionary with parsed results
        """
        try:
            from pyNastran.op2.op2 import OP2
        except ImportError:
            return {'error': 'pyNastran OP2 module not available'}

        op2_path = Path(op2_path)
        if not op2_path.exists():
            return {'error': f'OP2 file not found: {op2_path}'}

        try:
            op2 = OP2()
            op2.read_op2(str(op2_path))

            results = {
                'subcases': list(op2.displacements.keys()),
                'has_displacements': bool(op2.displacements),
                'has_stresses': bool(op2.cquad4_stress),
                'has_accelerations': bool(op2.accelerations),
            }

            return results

        except Exception as e:
            return {'error': str(e)}
