"""
Unified extraction module for 1D Hubbard DQMC simulation outputs.

Replaces:
  extract_equal-time_NN.py
  extract_equal-time_LR.py
  extract_global_NN.py
  extract_global_LR.py
  extract_global.py
  extract_integrated_LR.py

Public API
----------
SimParams          — dataclass holding all simulation parameters
get_data_dir       — resolve the output directory path (new + legacy formats)
extract_equal_time — load equal-time correlators (pair, greens, density, spin_z)
extract_global     — load a scalar quantity from global_stats.csv
extract_integrated — load Matsubara-integrated correlators
scan_density_vs_mu — sweep μ → return density vs μ dict

Default cluster path: set DATA_ROOT env variable, or pass base= to each function.
"""

import os
from dataclasses import dataclass, field
from typing import Optional
import numpy as np

# ---------------------------------------------------------------------------
# Default path to the cluster data directory. Override with DATA_ROOT env var
# or pass base= explicitly to each function.
# ---------------------------------------------------------------------------
_DEFAULT_BASE = os.environ.get("DATA_ROOT", "/nfs/home/gissa/Hubbard")


# ---------------------------------------------------------------------------
# Parameter container
# ---------------------------------------------------------------------------

@dataclass
class SimParams:
    """All parameters that uniquely identify a DQMC run."""
    U: float
    mu: float
    beta: float
    L: int
    alpha: float = 2.0
    Rmax: int = 1
    sID: int = 1


# ---------------------------------------------------------------------------
# Directory resolution
# ---------------------------------------------------------------------------

def get_data_dir(params: SimParams, base: Optional[str] = None) -> str:
    """
    Return the path to the simulation output directory.

    Tries candidate directory names in this order:
      1. New unified format:
           hubbard_U{U:.2f}_m{mu:.2f}_b{beta:.2f}_L{L}_a{alpha:.2f}_Rmax{Rmax}-{sID}
      2. Legacy LR format (old hubbard_chain_LR.jl):
           hubbard_chain_LR_U{U:.2f}_m{mu:.2f}_b{beta:.2f}_L{L}_a{alpha:.2f}_Rmax{Rmax}-{sID}
      3. Legacy NN format (old hubbard_chain.jl):
           hubbard_chain_U{U:.2f}_m{mu:.2f}_L{L}_b{beta:.2f}-{sID}

    Raises FileNotFoundError if none of the candidates exist.
    """
    base = base or _DEFAULT_BASE
    p = params

    candidates = [
        # new unified format
        (f"hubbard_U{p.U:.2f}_mu{p.mu:.2f}_b{p.beta:.2f}_L{p.L}"
         f"_a{p.alpha:.2f}_Rmax{p.Rmax}-{p.sID}"),
        # legacy LR format (uses 'm' not 'mu', different field order)
        (f"hubbard_chain_LR_U{p.U:.2f}_m{p.mu:.2f}_b{p.beta:.2f}_L{p.L}"
         f"_a{p.alpha:.2f}_Rmax{p.Rmax}-{p.sID}"),
        # legacy NN format
        (f"hubbard_chain_U{p.U:.2f}_m{p.mu:.2f}_L{p.L}_b{p.beta:.2f}-{p.sID}"),
    ]

    for name in candidates:
        path = os.path.join(base, name)
        if os.path.isdir(path):
            return path

    # None found — report what was tried
    tried = "\n  ".join(os.path.join(base, c) for c in candidates)
    raise FileNotFoundError(
        f"Simulation directory not found. Tried:\n  {tried}"
    )


# ---------------------------------------------------------------------------
# CSV reader helpers
# ---------------------------------------------------------------------------

def _read_correlation_csv(filepath: str):
    """
    Parse a SmoQyDQMC correlation stats CSV.
    Columns (1-indexed): ..., r/k (col 4), mean (col 5), ..., error (col 7)
    Returns (rs, values, errors) as numpy arrays.
    """
    rs, values, errors = [], [], []
    with open(filepath, "r") as f:
        lines = f.readlines()
    for line in lines[1:]:   # skip header
        parts = line.split()
        if len(parts) < 7:
            continue
        rs.append(float(parts[3]))
        values.append(float(parts[4]))
        errors.append(float(parts[6]))
    return np.array(rs), np.array(values), np.array(errors)


def _read_global_csv(filepath: str, quantity: str) -> Optional[float]:
    """
    Find the row matching `quantity` in global_stats.csv and return the value.
    Returns None if not found.
    """
    with open(filepath, "r") as f:
        for line in f:
            if quantity in line:
                parts = line.split()
                return float(parts[1])
    return None


# ---------------------------------------------------------------------------
# Public extraction functions
# ---------------------------------------------------------------------------

def extract_equal_time(
    params: SimParams,
    observable: str,
    space: str = "position",
    base: Optional[str] = None,
) -> dict:
    """
    Load an equal-time correlator from a simulation output directory.

    Parameters
    ----------
    params     : SimParams
    observable : 'pair' | 'greens' | 'density' | 'spin_z'
    space      : 'position' | 'momentum'
    base       : override for the data root path

    Returns
    -------
    dict with keys: 'r' (or 'k'), 'values', 'errors', 'density', 'params'
    """
    data_dir = get_data_dir(params, base)
    csv_path = os.path.join(
        data_dir, "equal-time", observable,
        f"{observable}_{space}_equal-time_stats.csv"
    )
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    rs, values, errors = _read_correlation_csv(csv_path)
    density = extract_global(params, "density", base=base)

    coord_key = "k" if space == "momentum" else "r"
    return {
        coord_key: rs,
        "values": values,
        "errors": errors,
        "density": density,
        "params": params,
    }


def extract_global(
    params: SimParams,
    quantity: str = "density",
    base: Optional[str] = None,
) -> Optional[float]:
    """
    Read a scalar global quantity from global_stats.csv.

    Parameters
    ----------
    params   : SimParams
    quantity : 'density' | 'density_up' | 'density_dn' | any row label
    base     : override for the data root path

    Returns
    -------
    float value, or None if not found
    """
    data_dir = get_data_dir(params, base)
    csv_path = os.path.join(data_dir, "global_stats.csv")
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"global_stats.csv not found in: {data_dir}")
    return _read_global_csv(csv_path, quantity)


def extract_integrated(
    params: SimParams,
    observable: str,
    space: str = "position",
    base: Optional[str] = None,
) -> dict:
    """
    Load a Matsubara-integrated correlator from the simulation output.

    Parameters
    ----------
    params     : SimParams
    observable : 'greens' | 'pair' | 'density' | 'spin_z'
    space      : 'position' | 'momentum'
    base       : override for the data root path

    Returns
    -------
    dict with keys: 'r' (or 'k'), 'values', 'errors', 'density', 'params'
    """
    data_dir = get_data_dir(params, base)
    csv_path = os.path.join(
        data_dir, "integrated", observable,
        f"{observable}_{space}_integrated_stats.csv"
    )
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    rs, values, errors = _read_correlation_csv(csv_path)
    density = extract_global(params, "density", base=base)

    coord_key = "k" if space == "momentum" else "r"
    return {
        coord_key: rs,
        "values": values,
        "errors": errors,
        "density": density,
        "params": params,
    }


def scan_density_vs_mu(
    U: float,
    beta: float,
    L: int,
    mu_range,
    alpha: float = 2.0,
    Rmax: int = 1,
    sID: int = 1,
    base: Optional[str] = None,
) -> dict:
    """
    Sweep over chemical potential values and collect the average density.

    Parameters
    ----------
    U         : on-site interaction
    beta      : inverse temperature
    L         : lattice size
    mu_range  : iterable of μ values to scan
    alpha     : hopping decay exponent
    Rmax      : max hopping range
    sID       : simulation ID
    base      : override for the data root path

    Returns
    -------
    dict with keys: 'mu', 'density', 'density_up', 'density_dn'
    (skips μ values where data is missing)
    """
    mu_out, density_out, density_up_out, density_dn_out = [], [], [], []

    for mu in mu_range:
        params = SimParams(U=U, mu=mu, beta=beta, L=L, alpha=alpha, Rmax=Rmax, sID=sID)
        try:
            n     = extract_global(params, "density",    base=base)
            n_up  = extract_global(params, "density_up", base=base)
            n_dn  = extract_global(params, "density_dn", base=base)
        except FileNotFoundError:
            print(f"  [skip] μ={mu:.4f} — data not found")
            continue

        if n is None:
            print(f"  [skip] μ={mu:.4f} — density not in global_stats")
            continue

        mu_out.append(mu)
        density_out.append(n)
        density_up_out.append(n_up)
        density_dn_out.append(n_dn)
        print(f"  μ={mu:.4f}  n={n:.4f}  n_up={n_up:.4f}")

    return {
        "mu":         np.array(mu_out),
        "density":    np.array(density_out),
        "density_up": np.array(density_up_out),
        "density_dn": np.array(density_dn_out),
    }
