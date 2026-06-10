# Stats plan for PXD013024
# Design: cell_line | Patient level: cell_line
library(limma)

# 1) Load protein matrix from Result File: NET-tumors_iTRAQset1_200ugIPG37-49_fr01-72_proteingroups
# mat <- read_protein_matrix("tmt-projects/Projects/PXD013024/...")

# 2) Filter: >=70% valid values per comparison group
# mat_f <- filter_by_group_presence(mat, groups, min_frac=0.7)

# 3) Log2 if not already (check Normalization Strategy in sheet)
# norm_in_sheet: Reporter-ion median normalization per channel (OpenMS IsobaricAnalyzer10) 126

# 4) Design matrix
# design <- model.matrix(~ 0 + group + cell_line)

# 5) Test: limma
# fit <- lmFit(mat_f, design)
# fit2 <- eBayes(contrasts.fit(fit, contrast_matrix))
# topTable(fit2, adjust.method="BH", number=Inf)

# 6) Patient-level: aggregate technical replicates to patient before DE if needed
