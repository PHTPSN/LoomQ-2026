# LQ-Q32 GPU validation evidence

This directory contains the reproducible private Kaggle GPU validation script
for the LoomQ quantum RISC-V extension. The script consumes the submitted
`quantum_riscv.py` and `riscv_emulator.py` through a minimal private Kaggle
source dataset, records their SHA-256 hashes, decodes actual `custom-0` machine
words, and executes the resulting GHZ circuit with open-source CuPy CUDA
`RawKernel` programs compiled by NVRTC for the assigned GPU. An independent
NumPy CPU statevector provides the reference probabilities; the evidence
requires CPU and GPU output to agree within `1e-12`.

The Kaggle kernel and source dataset remain private during the competition.
After a successful run, the downloaded machine-readable result and the
rendered run output are stored in this directory and linked from
`starter_kit/evidence/README.md`.

## Successful run

- Platform: Kaggle Notebooks
- GPU: Tesla P100-PCIE-16GB, 16 GiB, compute capability 6.0
- GPU runtime: CuPy 14.0.1 with NVRTC-compiled CUDA kernels
- Instruction opcode: RISC-V `custom-0` (`0x0B`)
- Whitelist encodings checked: all 12 gates plus measurement
- GPU result: `{"000": 2048, "111": 2048}`
- Independent CPU result: `{"000": 2048, "111": 2048}`
- Maximum statevector probability delta: `2.22044604925031e-16`

The uploaded source hashes in
[`loomq-quantum-riscv-gpu-evidence.json`](loomq-quantum-riscv-gpu-evidence.json)
match the submitted `starter_kit/quantum_riscv.py` and
`starter_kit/riscv_emulator.py`. The complete Kaggle output is preserved in
[`loomq-lq-q32-gpu-validation.log`](loomq-lq-q32-gpu-validation.log).
