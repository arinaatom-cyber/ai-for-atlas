# Stats plan for PXD027335
# Design: cell_line | Patient level: cell_line
library(limma)

# 1) Load protein matrix from Result File: GBM_BT_stem_cells_TMT10plex_250ug__HiRIEF_IPG_3-10_proteins_table
# mat <- read_protein_matrix("tmt-projects/Projects/PXD027335/...")

# 2) Filter: >=70% valid values per comparison group
# mat_f <- filter_by_group_presence(mat, groups, min_frac=0.7)

# 3) Log2 if not already (check Normalization Strategy in sheet)
# norm_in_sheet: Median of PSM ratios with internal standards

# 4) Design matrix
# design <- model.matrix(~ 0 + group + cell_line)

# 5) Test: limma
# fit <- lmFit(mat_f, design)
# fit2 <- eBayes(contrasts.fit(fit, contrast_matrix))
# topTable(fit2, adjust.method="BH", number=Inf)

# 6) Patient-level: aggregate technical replicates to patient before DE if needed
