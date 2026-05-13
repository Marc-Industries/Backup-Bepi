"""MATLAB/Octave bridge — execute scripts with parameter mapping."""
import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from scipy.io import savemat, loadmat


TEMPLATE_DIR = Path(__file__).resolve().parents[3] / "templates" / "matlab"


@dataclass
class ParamMapping:
    node_code: str
    budget_field: str
    matlab_var: str


@dataclass
class ScriptConfig:
    name: str
    script_path: str
    engine: str = "octave"  # "matlab" or "octave"
    input_mapping: list[ParamMapping] = field(default_factory=list)
    output_mapping: list[ParamMapping] = field(default_factory=list)
    description: str = ""


@dataclass
class RunResult:
    success: bool
    outputs: dict = field(default_factory=dict)
    stdout: str = ""
    stderr: str = ""
    error: str = ""
    mat_file: str | None = None


def _resolve_engine(engine: str) -> str | None:
    if engine == "octave":
        for cmd in ["octave-cli", "octave"]:
            path = _which(cmd)
            if path:
                return path
    elif engine == "matlab":
        path = _which("matlab")
        if path:
            return path
    return None


def _which(cmd: str) -> str | None:
    try:
        result = subprocess.run(["which", cmd], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def prepare_inputs(config: ScriptConfig, node_data: dict[str, dict]) -> dict:
    inputs = {}
    for m in config.input_mapping:
        node = node_data.get(m.node_code, {})
        val = node.get(m.budget_field, 0)
        if isinstance(val, (int, float)):
            inputs[m.matlab_var] = float(val)
        elif isinstance(val, str):
            try:
                inputs[m.matlab_var] = float(val)
            except ValueError:
                inputs[m.matlab_var] = val
        else:
            inputs[m.matlab_var] = val
    return inputs


def run_script(config: ScriptConfig, inputs: dict,
               timeout: int = 120) -> RunResult:
    engine_path = _resolve_engine(config.engine)
    if not engine_path:
        return RunResult(success=False,
                         error=f"{config.engine} not found. Install GNU Octave or MATLAB.")

    work_dir = tempfile.mkdtemp(prefix="bepi_matlab_")
    input_mat = os.path.join(work_dir, "input.mat")
    output_mat = os.path.join(work_dir, "output.mat")

    # Save inputs to .mat
    mat_data = {}
    for k, v in inputs.items():
        if isinstance(v, (int, float)):
            mat_data[k] = np.array([[v]])
        elif isinstance(v, list):
            mat_data[k] = np.array(v)
        else:
            mat_data[k] = v
    savemat(input_mat, mat_data)

    # Build wrapper script
    script_path = config.script_path
    if not os.path.isabs(script_path):
        script_path = str(TEMPLATE_DIR / script_path)

    if not os.path.exists(script_path):
        return RunResult(success=False, error=f"Script not found: {script_path}")

    wrapper = f"""
load('{input_mat}');
run('{script_path}');
% Save all workspace variables to output
save('{output_mat}');
"""
    wrapper_path = os.path.join(work_dir, "wrapper.m")
    with open(wrapper_path, "w") as f:
        f.write(wrapper)

    # Execute
    if config.engine == "octave":
        cmd = [engine_path, "--no-gui", "--no-window-system", wrapper_path]
    else:
        cmd = [engine_path, "-batch", f"run('{wrapper_path}')"]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True,
                                timeout=timeout, cwd=work_dir)
        if os.path.exists(output_mat):
            out_data = loadmat(output_mat, squeeze_me=True)
            outputs = {k: v.item() if hasattr(v, 'item') else
                       (v.tolist() if hasattr(v, 'tolist') else v)
                       for k, v in out_data.items() if not k.startswith('_')}
            return RunResult(success=True, outputs=outputs,
                             stdout=result.stdout[-2000:],
                             stderr=result.stderr[-1000:],
                             mat_file=output_mat)
        else:
            return RunResult(success=False,
                             error="No output .mat file generated",
                             stdout=result.stdout[-2000:],
                             stderr=result.stderr[-1000:])
    except subprocess.TimeoutExpired:
        return RunResult(success=False, error=f"Script timed out ({timeout}s)")
    except FileNotFoundError:
        return RunResult(success=False, error=f"{config.engine} executable not found")


def apply_outputs(config: ScriptConfig, result: RunResult,
                  node_data: dict[str, dict]) -> dict[str, dict]:
    if not result.success:
        return node_data
    for m in config.output_mapping:
        if m.matlab_var in result.outputs:
            if m.node_code in node_data:
                node_data[m.node_code][m.budget_field] = result.outputs[m.matlab_var]
    return node_data


# ── Template scripts catalog ─────────────────────────────────────────

SCRIPT_TEMPLATES = {
    "Link Budget": ScriptConfig(
        name="Link Budget Analysis",
        script_path="link_budget.m",
        description="Calculates uplink/downlink margins given TX power, antenna gain, distance, and data rate.",
        input_mapping=[
            ParamMapping("COM-TX", "power", "P_tx_W"),
            ParamMapping("COM-TX", "gain", "G_tx_dBi"),
            ParamMapping("COM-RX", "gain", "G_rx_dBi"),
        ],
        output_mapping=[
            ParamMapping("COM", "link_margin_dB", "link_margin"),
        ],
    ),
    "Power Budget": ScriptConfig(
        name="Power Budget Sizing",
        script_path="power_budget.m",
        description="Computes solar array sizing and battery DOD from orbit parameters and power demands.",
        input_mapping=[
            ParamMapping("EPS-SA", "area", "SA_area_m2"),
            ParamMapping("EPS-BAT", "capacity", "BAT_Wh"),
        ],
        output_mapping=[
            ParamMapping("EPS", "power_margin", "power_margin_pct"),
        ],
    ),
    "Thermal Sizing": ScriptConfig(
        name="Thermal First-Cut Sizing",
        script_path="thermal_sizing.m",
        description="Estimates radiator area and heater power from thermal loads and orbit beta angle.",
    ),
    "Structural Sizing": ScriptConfig(
        name="Structural First-Cut Sizing",
        script_path="structural_sizing.m",
        description="Estimates structural mass from launch loads, panel dimensions, and material properties.",
    ),
}
