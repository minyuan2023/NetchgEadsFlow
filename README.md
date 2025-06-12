# NetchgEadsFlow
An automated workflow for charge-adaptive tuning and adsorption energy evaluation in catalytic systems, designed to accelerate catalyst screening with dynamic NELECT adjustment and reaction-specific binding energy calculations.

**NetchgEadsFlow** is a modular and automated workflow designed for the **rational screening and design of catalytic systems** through **dynamic charge tuning and adsorption energy evaluation**. It addresses the key challenges in traditional catalyst development: time-consuming trial-and-error loops, computational inefficiencies, and complex parameter management.

This system integrates automated charge control, adaptive adsorption energy calculation, and high-throughput task execution—making it an essential tool for **materials scientists**, **computational chemists**, and **energy/environment researchers**.

---

## Key Features

- **Dynamic charge (NELECT) adjustment** tailored to the electronic environment of the catalyst system
- **Adsorption energy evaluation** across multiple adsorbates and intermediates
- **Adaptive algorithm** to select appropriate energy calculation schemes based on charge state
- Automated job generation, submission, monitoring, and result parsing
- Thermodynamic stability evaluation (optional)
- Modular script design: each step can be used standalone or integrated in the full pipeline

---

## Core Modules

| Script | Function |
|--------|----------|
| `NELECT.py` | Auto-adjusts NELECT value for charge-consistent calculations |
| `adsorbate-NELECT.py` | Optimizes adsorbate structure and performs charge-aware adsorption energy computation |
| `binding.py` | Calculates binding energies for target molecules/intermediates |
| `stability.py` | (Optional) Thermodynamic stability assessment of catalysts under operating conditions |

---

## Application Domains

- Clean energy materials (e.g. ORR, HER, CO₂RR catalysts)
- Environmental catalysis
- Fine chemical design
- Data-driven catalyst screening

---

## Installation

### Requirements
- Python ≥ 3.8
- VASP (or other DFT engine compatible with your setup)
- `pymatgen`, `ase`, `numpy`, `yaml`, `matplotlib`, etc.

Install dependencies:
```bash
pip install -r requirements.txt
