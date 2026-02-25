# Long-Range Hubbard DQMC

DQMC study of the 1D attractive Hubbard model with power-law long-range hopping:

$$t(r) = \frac{t}{r^\alpha}, \quad r = 1, \ldots, R_{\max}$$

Setting $R_{\max} = 1$ recovers standard nearest-neighbor hopping.

**Research goal**: map out the finite-temperature phase diagram in $(\alpha, T)$ space,
and confirm the enhancement of pairing correlations ($\eta_P \to 0$) as $\alpha$ decreases.

---

## Repository layout

```
lrHub/
├── simulation/
│   ├── hubbard_dqmc.jl       unified Julia DQMC engine (NN + LR)
│   └── run_simulation.py     SLURM submission script (argparse CLI)
├── analysis/
│   ├── __init__.py
│   └── extract.py            unified extraction module
├── notebooks/
│   ├── 00_sanity.ipynb       dispersion, DOS, density calibration
│   ├── 01_correlations.ipynb pair/Green's analysis, power-law fits
│   └── 02_phase_diagram.ipynb finite-T phase diagram (Step 4)
├── docs/                     reference PDFs (gitignored)
├── data/                     cluster output data (gitignored)
│   └── .gitkeep
└── results/                  selected figures (tracked, PDFs gitignored)
    └── .gitkeep
```

---

## Quickstart

### 1. Local test (small parameters)

```bash
julia simulation/hubbard_dqmc.jl 1 -5 -2.2 15 16 2.0 1 100 200 10
# args:  sID U μ β L α Rmax N_burnin N_updates N_bins
```

### 2. Submit to cluster (NN, density calibration sweep)

```bash
python simulation/run_simulation.py \
    --U -5.0 --beta 40 --L 100 --alpha 2.0 --Rmax 1 \
    --sweep-mu -- -3.5 -3.0 -2.5 -2.0 -1.5 -1.0
```

### 3. Submit β sweep (after finding μ*)

```bash
python simulation/run_simulation.py \
    --U -5.0 --mu <mu_star> --L 100 --alpha 2.0 --Rmax 1 \
    --sweep-beta 40 60 80 100
```

### 4. LR α sweep

```bash
python simulation/run_simulation.py \
    --U -5.0 --mu <mu_lr_star> --beta 60 --L 100 --Rmax 50 \
    --sweep-alpha 0.5 0.8 1.0 1.5 2.0
```

---

## Analysis

```python
from analysis.extract import SimParams, extract_equal_time, scan_density_vs_mu

# Load pair correlator
params = SimParams(U=-5.0, mu=-2.4, beta=60.0, L=100, alpha=2.0, Rmax=1)
data = extract_equal_time(params, 'pair', 'position', base='/nfs/home/gissa/Hubbard')
r, P, err = data['r'], data['values'], data['errors']

# Density calibration scan
result = scan_density_vs_mu(U=-5.0, beta=40.0, L=100,
                            mu_range=[-3.5, -3.0, -2.5, -2.0],
                            alpha=2.0, Rmax=1)
```

Set the `DATA_ROOT` environment variable to avoid passing `base=` everywhere:

```bash
export DATA_ROOT=/nfs/home/gissa/Hubbard
```

---

## Research roadmap

| Step | Task | Notebook |
|------|------|----------|
| 1 | Find μ* for n_σ = 0.4 (NN) | `00_sanity.ipynb` §4 |
| 2 | NN simulations at n_σ = 0.4, β ∈ {40,60,80,100} | `01_correlations.ipynb` §1 |
| 3 | LR simulations (fix Rmax, vary α) at n_σ = 0.4 | `01_correlations.ipynb` §2 |
| 4 | Finite-T phase diagram (η_P vs T for each α) | `02_phase_diagram.ipynb` |

---

## Dependencies

- **Julia**: `SmoQyDQMC` (includes `LatticeUtilities`, `JDQMCFramework`, `JDQMCMeasurements`)
- **Python**: `numpy`, `matplotlib`, `scipy`
- **HPC**: SLURM (for `run_simulation.py`)
