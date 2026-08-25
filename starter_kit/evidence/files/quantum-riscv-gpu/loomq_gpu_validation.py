#!/usr/bin/env python3
"""Kaggle GPU evidence run for the LoomQ LQ-Q32 instruction extension."""

from datetime import datetime, timezone
import glob
import hashlib
import importlib.metadata
import importlib.util
import json
from pathlib import Path
import subprocess
import sys


SHOTS = 4096


def install_runtime():
    if importlib.util.find_spec("cupy") is not None:
        return
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q", "cupy-cuda12x"],
        check=True,
    )


def locate_source():
    matches = glob.glob("/kaggle/input/**/quantum_riscv.py", recursive=True)
    if len(matches) != 1:
        raise RuntimeError("expected exactly one uploaded quantum_riscv.py source file")
    source_dir = Path(matches[0]).resolve().parent
    emulator = source_dir / "riscv_emulator.py"
    if not emulator.is_file():
        raise RuntimeError("uploaded riscv_emulator.py source file is missing")
    sys.path.insert(0, str(source_dir))
    return source_dir


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def gpu_identity():
    command = [
        "nvidia-smi",
        "--query-gpu=name,uuid,driver_version,memory.total,compute_cap",
        "--format=csv,noheader,nounits",
    ]
    completed = subprocess.run(command, text=True, capture_output=True, check=True)
    rows = []
    for line in completed.stdout.splitlines():
        if not line.strip():
            continue
        name, uuid, driver, memory, capability = [item.strip() for item in line.split(",")]
        rows.append(
            {
                "name": name,
                "uuid": uuid,
                "driver_version": driver,
                "memory_mib": int(memory),
                "compute_capability": capability,
            }
        )
    if not rows:
        raise RuntimeError("nvidia-smi reported no GPU")
    return rows


def gpu_probabilities(decoded, cp, np):
    h_kernel = cp.RawKernel(
        r'''
        extern "C" __global__ void apply_h(double2* state, int qubits, int target) {
          int pair = blockDim.x * blockIdx.x + threadIdx.x;
          int pairs = 1 << (qubits - 1);
          if (pair >= pairs) return;
          int low_mask = (1 << target) - 1;
          int i0 = (pair & low_mask) | ((pair >> target) << (target + 1));
          int i1 = i0 | (1 << target);
          double2 a = state[i0];
          double2 b = state[i1];
          const double scale = 0.70710678118654752440;
          state[i0] = make_double2((a.x + b.x) * scale, (a.y + b.y) * scale);
          state[i1] = make_double2((a.x - b.x) * scale, (a.y - b.y) * scale);
        }
        ''',
        "apply_h",
    )
    cx_kernel = cp.RawKernel(
        r'''
        extern "C" __global__ void apply_cx(
            double2* state, int qubits, int control, int target) {
          int pair = blockDim.x * blockIdx.x + threadIdx.x;
          int pairs = 1 << (qubits - 1);
          if (pair >= pairs) return;
          int low_mask = (1 << target) - 1;
          int i0 = (pair & low_mask) | ((pair >> target) << (target + 1));
          if (((i0 >> control) & 1) == 0) return;
          int i1 = i0 | (1 << target);
          double2 temporary = state[i0];
          state[i0] = state[i1];
          state[i1] = temporary;
        }
        ''',
        "apply_cx",
    )
    qubit_count = 3
    state = cp.zeros(1 << qubit_count, dtype=cp.complex128)
    state[0] = 1.0
    for instruction in decoded:
        name = instruction.name
        qubits = instruction.qubits
        if name == "measure":
            continue
        if name == "h":
            h_kernel(
                (1,),
                (1 << (qubit_count - 1),),
                (state, np.int32(qubit_count), np.int32(qubits[0])),
            )
        elif name == "cx":
            cx_kernel(
                (1,),
                (1 << (qubit_count - 1),),
                (
                    state,
                    np.int32(qubit_count),
                    np.int32(qubits[0]),
                    np.int32(qubits[1]),
                ),
            )
        else:
            raise RuntimeError("GPU evidence circuit contains unsupported operation %s" % name)
    cp.cuda.runtime.deviceSynchronize()
    return cp.asnumpy(cp.abs(state) ** 2)


def cpu_probabilities(decoded, np):
    qubit_count = 3
    state = np.zeros(1 << qubit_count, dtype=np.complex128)
    state[0] = 1.0
    for instruction in decoded:
        name = instruction.name
        if name == "measure":
            continue
        if name == "h":
            target = instruction.qubits[0]
            for pair in range(1 << (qubit_count - 1)):
                low_mask = (1 << target) - 1
                i0 = (pair & low_mask) | ((pair >> target) << (target + 1))
                i1 = i0 | (1 << target)
                a, b = state[i0], state[i1]
                state[i0] = (a + b) / (2.0 ** 0.5)
                state[i1] = (a - b) / (2.0 ** 0.5)
        elif name == "cx":
            control, target = instruction.qubits
            for i0 in range(1 << qubit_count):
                if ((i0 >> control) & 1) and not ((i0 >> target) & 1):
                    i1 = i0 | (1 << target)
                    state[i0], state[i1] = state[i1], state[i0]
        else:
            raise RuntimeError("CPU evidence circuit contains unsupported operation %s" % name)
    return np.abs(state) ** 2


def run():
    install_runtime()
    source_dir = locate_source()

    from quantum_riscv import CUSTOM_0_OPCODE, decode_program, encode_program
    from riscv_emulator import TinyRISCVEmulator
    import cupy as cp
    import numpy as np

    gpu_devices = gpu_identity()
    print("GPU identity:", json.dumps(gpu_devices, sort_keys=True))

    whitelist_operations = [
        "h q[0];",
        "x q[1];",
        "s q[2];",
        "sdg q[0];",
        "t q[1];",
        "tdg q[2];",
        "ry(0.44879895051282759) q[0];",
        "rz(-1.0471975511965976) q[1];",
        "cx q[0], q[1];",
        "cu1(0.75) q[1], q[2];",
        "swap q[0], q[2];",
        "ccx q[0], q[1], q[2];",
        "measure q[0] -> c[0];",
    ]
    whitelist_words = encode_program(whitelist_operations)
    whitelist_decoded = decode_program(whitelist_words)
    if [item.name for item in whitelist_decoded] != [
        "h", "x", "s", "sdg", "t", "tdg", "ry", "rz", "cx", "cu1", "swap", "ccx", "measure"
    ]:
        raise AssertionError("the complete whitelist did not survive binary decoding")

    ghz_operations = [
        "h q[0];",
        "cx q[0], q[1];",
        "cx q[1], q[2];",
        "measure q[0] -> c[0];",
        "measure q[1] -> c[1];",
        "measure q[2] -> c[2];",
    ]
    ghz_words = encode_program(ghz_operations)
    if not all((word & 0x7F) == CUSTOM_0_OPCODE for word in ghz_words):
        raise AssertionError("the GPU circuit did not originate from custom-0 words")

    emulator = TinyRISCVEmulator()
    emulator.load_machine_code(ghz_words)
    trace = emulator.execute_machine_code()
    if trace != ghz_operations:
        raise AssertionError("emulator execution trace differs from the encoded program")
    decoded = decode_program(ghz_words)
    gpu_probability_vector = gpu_probabilities(decoded, cp, np)
    cpu_probability_vector = cpu_probabilities(decoded, np)
    max_probability_delta = float(np.max(np.abs(gpu_probability_vector - cpu_probability_vector)))
    if max_probability_delta > 1e-12:
        raise AssertionError("CPU and GPU statevector probabilities differ")

    gpu_counts = {
        format(index, "03b"): int(round(float(probability) * SHOTS))
        for index, probability in enumerate(gpu_probability_vector)
        if probability > 1e-12
    }
    cpu_counts = {
        format(index, "03b"): int(round(float(probability) * SHOTS))
        for index, probability in enumerate(cpu_probability_vector)
        if probability > 1e-12
    }

    expected_states = {"000", "111"}
    if set(gpu_counts) != expected_states or set(cpu_counts) != expected_states:
        raise AssertionError("CPU or GPU GHZ result contains an unexpected state")

    result = {
        "schema": "loomq.quantum-riscv-gpu-evidence.v1",
        "status": "PASS",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "platform": "Kaggle Notebooks",
        "gpu": gpu_devices,
        "software": {
            "python": sys.version.split()[0],
            "cupy": importlib.metadata.version("cupy-cuda12x"),
            "numpy": importlib.metadata.version("numpy"),
            "cuda_runtime_version": cp.cuda.runtime.runtimeGetVersion(),
            "gpu_kernel": "CuPy RawKernel (NVRTC runtime compilation)",
        },
        "source_sha256": {
            "quantum_riscv.py": sha256(source_dir / "quantum_riscv.py"),
            "riscv_emulator.py": sha256(source_dir / "riscv_emulator.py"),
        },
        "instruction_encoding": {
            "name": "LQ-Q32",
            "opcode": "0x%02x" % CUSTOM_0_OPCODE,
            "whitelist_instruction_count": len(whitelist_words),
            "whitelist_machine_code": ["0x%08x" % word for word in whitelist_words],
            "ghz_machine_code": ["0x%08x" % word for word in ghz_words],
            "decoded_ghz_trace": trace,
        },
        "execution": {
            "shots": SHOTS,
            "counts_method": "deterministic rounding of GPU/CPU statevector probabilities",
            "expected_states": sorted(expected_states),
            "gpu_counts": gpu_counts,
            "cpu_counts": cpu_counts,
            "max_probability_delta": max_probability_delta,
        },
    }
    output = Path("/kaggle/working/loomq-quantum-riscv-gpu-evidence.json")
    output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return result


if __name__ == "__main__":
    run()
