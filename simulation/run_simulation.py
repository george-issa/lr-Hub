"""
Unified SLURM submission script for 1D attractive Hubbard DQMC simulations.

Usage examples:
  # Single run using the CONFIG block below (edit the file directly)
  python simulation/run_simulation.py

  # Override any CONFIG value from the command line
  python simulation/run_simulation.py --U -5.0 --mu -2.4 --beta 50 --Rmax 1

  # Sweeps (override CONFIG sweeps from the command line)
  python simulation/run_simulation.py --sweep-beta 40 60 80 100
  python simulation/run_simulation.py --sweep-mu -- -3.5 -3.0 -2.5 -2.0 -1.5 -1.0
  python simulation/run_simulation.py --Rmax 50 --sweep-alpha 0.5 0.8 1.0 1.5 2.0
"""

import argparse
import subprocess
from pathlib import Path

# =============================================================================
# CONFIG — edit these values directly when running from the text editor.
# Any value set here is used as the default; CLI flags override them.
# For sweeps, set a list (e.g. SWEEP_BETA = [40, 60, 80]) — leave as []
# to run a single job at the scalar value above.
# =============================================================================

# --- Physics ---
SID     = 1
U       = -5.0
MU      = -2.2      # update after density calibration
BETA    = 50.0
L       = 100
ALPHA   = 2.0       # hopping decay exponent
RMAX    = 1         # 1 = NN; set to L//2 for full LR

# --- DQMC ---
N_BURNIN  = 5000
N_UPDATES = 20000
N_BINS    = 100

# --- Sweeps (set to [] to use the scalar above) ---
SWEEP_BETA  = []    # e.g. [40, 60, 80, 100]
SWEEP_MU    = []    # e.g. [-3.5, -3.0, -2.5, -2.0, -1.5]
SWEEP_ALPHA = []    # e.g. [0.5, 0.8, 1.0, 1.5, 2.0]

# --- Priority ---
# SLURM nice value: negative = higher priority, positive = lower priority.
# Range: -10000 (highest) to 10000 (lowest). Default is 0.
# Tip: set to -1000 to jump ahead of your long-running jobs.
NICE = -1000

# =============================================================================

JULIA_SCRIPT = "simulation/hubbard_dqmc.jl"


def generate_slurm_script(sID, U, mu, beta, L, alpha, Rmax, N_burnin, N_updates, N_bins, nice=0):
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
        f.write(f"#SBATCH --cpus-per-task=1\n")
        if nice != 0:
            f.write(f"#SBATCH --nice={nice}\n")
        f.write("\n")
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
        description="Submit Hubbard DQMC jobs to SLURM.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Physics parameters — defaults come from CONFIG block above
    parser.add_argument("--sID",     type=int,   default=SID,       help="Simulation ID")
    parser.add_argument("--U",       type=float, default=U,         help="On-site interaction")
    parser.add_argument("--mu",      type=float, default=MU,        help="Chemical potential")
    parser.add_argument("--beta",    type=float, default=BETA,      help="Inverse temperature β")
    parser.add_argument("--L",       type=int,   default=L,         help="Lattice size")
    parser.add_argument("--alpha",   type=float, default=ALPHA,     help="Hopping decay exponent α")
    parser.add_argument("--Rmax",    type=int,   default=RMAX,      help="Max hopping range (1=NN)")

    # DQMC parameters
    parser.add_argument("--N-burnin",  type=int, default=N_BURNIN,  help="Thermalization sweeps")
    parser.add_argument("--N-updates", type=int, default=N_UPDATES, help="Measurement sweeps")
    parser.add_argument("--N-bins",    type=int, default=N_BINS,    help="Number of bins")

    # Sweeps — defaults come from CONFIG block above
    parser.add_argument("--sweep-beta",  type=float, nargs="+", default=SWEEP_BETA or None,
                        metavar="β", help="Submit one job per β value (overrides --beta)")
    parser.add_argument("--sweep-mu",    type=float, nargs="+", default=SWEEP_MU or None,
                        metavar="μ", help="Submit one job per μ value (overrides --mu)")
    parser.add_argument("--sweep-alpha", type=float, nargs="+", default=SWEEP_ALPHA or None,
                        metavar="α", help="Submit one job per α value (overrides --alpha)")

    # Priority
    parser.add_argument("--nice", type=int, default=NICE,
                        help="SLURM nice value: negative = higher priority (default: %(default)s)")

    args = parser.parse_args()

    betas  = args.sweep_beta  if args.sweep_beta  else [args.beta]
    mus    = args.sweep_mu    if args.sweep_mu    else [args.mu]
    alphas = args.sweep_alpha if args.sweep_alpha else [args.alpha]

    total = len(betas) * len(mus) * len(alphas)
    print(f"Submitting {total} job(s)...")
    print(f"  U={args.U}, L={args.L}, Rmax={args.Rmax}, sID={args.sID}")
    print(f"  N_burnin={args.N_burnin}, N_updates={args.N_updates}, N_bins={args.N_bins}")
    print(f"  nice={args.nice}")
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
                    nice=args.nice,
                )


if __name__ == "__main__":
    main()
