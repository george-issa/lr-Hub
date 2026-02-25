"""
Unified SLURM submission script for 1D attractive Hubbard DQMC simulations.

Replaces run_hubbard.py and run_hubbard_chain_LR.py. Generates and submits
SLURM scripts that call simulation/hubbard_dqmc.jl.

Usage examples:
  # Single run (NN, default params)
  python simulation/run_simulation.py

  # Single run with custom params
  python simulation/run_simulation.py --U -5.0 --mu -2.4 --beta 50 --Rmax 1

  # Beta sweep (NN at n_sigma=0.4)
  python simulation/run_simulation.py --mu -2.4 --sweep-beta 40 60 80 100

  # Alpha sweep (LR hopping, fixed density)
  python simulation/run_simulation.py --mu -2.4 --Rmax 50 --sweep-alpha 0.5 0.8 1.0 1.5 2.0

  # Mu sweep (density calibration)
  python simulation/run_simulation.py --sweep-mu -- -3.5 -3.0 -2.5 -2.0 -1.5 -1.0
"""

import argparse
import subprocess
from pathlib import Path

JULIA_SCRIPT = "simulation/hubbard_dqmc.jl"


def generate_slurm_script(sID, U, mu, beta, L, alpha, Rmax, N_burnin, N_updates, N_bins):
    """Generate and submit a single SLURM job."""
    job_name = (
        f"hubbard_U{U:.2f}_mu{mu:.2f}_b{beta:.2f}_L{L}"
        f"_a{alpha:.2f}_Rmax{Rmax}-{sID}"
    )
    script_name = f"{job_name}.sh"

    with open(script_name, "w") as f:
        f.write("#!/bin/bash\n")
        f.write(f"#SBATCH --partition=puma,puma-i9\n")
        f.write(f"#SBATCH -J {job_name}\n")
        f.write(f"#SBATCH -o {job_name}-%j.output\n")
        f.write(f"#SBATCH --cpus-per-task=1\n\n")
        f.write(
            f"julia {JULIA_SCRIPT} "
            f"{sID} {U} {mu} {beta} {L} {alpha} {Rmax} "
            f"{N_burnin} {N_updates} {N_bins}\n"
        )

    subprocess.run(["sbatch", script_name])
    print(
        f"Submitted: U={U:.2f}, mu={mu:.2f}, beta={beta:.2f}, "
        f"L={L}, alpha={alpha:.2f}, Rmax={Rmax}, sID={sID}"
    )


def main():
    parser = argparse.ArgumentParser(
        description="Submit Hubbard DQMC jobs to SLURM."
    )

    # Physics parameters
    parser.add_argument("--sID",     type=int,   default=1,     help="Simulation ID")
    parser.add_argument("--U",       type=float, default=-5.0,  help="On-site interaction")
    parser.add_argument("--mu",      type=float, default=-2.2,  help="Chemical potential")
    parser.add_argument("--beta",    type=float, default=50.0,  help="Inverse temperature β")
    parser.add_argument("--L",       type=int,   default=100,   help="Lattice size")
    parser.add_argument("--alpha",   type=float, default=2.0,   help="Hopping decay exponent α")
    parser.add_argument("--Rmax",    type=int,   default=1,     help="Max hopping range (1=NN)")

    # DQMC parameters
    parser.add_argument("--N-burnin",  type=int, default=5000,  help="Thermalization sweeps")
    parser.add_argument("--N-updates", type=int, default=20000, help="Measurement sweeps")
    parser.add_argument("--N-bins",    type=int, default=100,   help="Number of bins")

    # Sweep options (submit an array of jobs varying one parameter)
    parser.add_argument("--sweep-beta",  type=float, nargs="+", metavar="β",
                        help="Submit one job per β value (overrides --beta)")
    parser.add_argument("--sweep-mu",    type=float, nargs="+", metavar="μ",
                        help="Submit one job per μ value (overrides --mu)")
    parser.add_argument("--sweep-alpha", type=float, nargs="+", metavar="α",
                        help="Submit one job per α value (overrides --alpha)")

    args = parser.parse_args()

    # Build the list of (beta, mu, alpha) combinations to submit
    betas  = args.sweep_beta  if args.sweep_beta  else [args.beta]
    mus    = args.sweep_mu    if args.sweep_mu    else [args.mu]
    alphas = args.sweep_alpha if args.sweep_alpha else [args.alpha]

    total = len(betas) * len(mus) * len(alphas)
    print(f"Submitting {total} job(s)...")
    print(f"  U={args.U}, L={args.L}, Rmax={args.Rmax}, sID={args.sID}")
    print(f"  N_burnin={args.N_burnin}, N_updates={args.N_updates}, N_bins={args.N_bins}")
    print()

    for beta in betas:
        for mu in mus:
            for alpha in alphas:
                generate_slurm_script(
                    sID=args.sID,
                    U=args.U,
                    mu=mu,
                    beta=beta,
                    L=args.L,
                    alpha=alpha,
                    Rmax=args.Rmax,
                    N_burnin=args.N_burnin,
                    N_updates=args.N_updates,
                    N_bins=args.N_bins,
                )


if __name__ == "__main__":
    main()
