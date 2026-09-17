"""Aging plasma MRM-SIS: patient × channel × intensity.

Wide SRM matrix (peptides × acquisition channels) is converted to a tidy
table where every row is one quantified peptide in one patient channel.
"""

from aging_mrm.pipeline import AgingMrmTables, build_aging_mrm

__all__ = ["AgingMrmTables", "build_aging_mrm"]
