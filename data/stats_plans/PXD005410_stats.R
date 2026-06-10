# Stats plan for PXD005410
# Design: cell_line | Patient level: cell_line
library(limma)

# 1) Load protein matrix from Result File: ElenaP_perv-mitotic_2015feb_TMT_nonphospho_300ugIPG3-10_50min_10of15ul_fr01-72_1
# mat <- read_protein_matrix("tmt-projects/Projects/PXD005410/...")

# 2) Filter: >=70% valid values per comparison group
# mat_f <- filter_by_group_presence(mat, groups, min_frac=0.7)

# 3) Log2 if not already (check Normalization Strategy in sheet)
# norm_in_sheet: Reporter ion median normalization per channel

# 4) Design matrix
# design <- model.matrix(~ 0 + group + cell_line)

# 5) Test: limma
# fit <- lmFit(mat_f, design)
# fit2 <- eBayes(contrasts.fit(fit, contrast_matrix))
# topTable(fit2, adjust.method="BH", number=Inf)

# 6) Patient-level: aggregate technical replicates to patient before DE if needed
