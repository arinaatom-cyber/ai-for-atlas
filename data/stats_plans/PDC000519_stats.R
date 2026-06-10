# Stats plan for PDC000519
# Design: case_control | Patient level: sample
library(limma)

# 1) Load protein matrix from Result File: result_PDC000519.xlsx
# mat <- read_protein_matrix("tmt-projects/Projects/PDC000519/...")

# 2) Filter: >=70% valid values per comparison group
# mat_f <- filter_by_group_presence(mat, groups, min_frac=0.7)

# 3) Log2 if not already (check Normalization Strategy in sheet)
# norm_in_sheet: Median norm; log2 ratio

# 4) Design matrix
# design <- model.matrix(~ 0 + group + group)

# 5) Test: limma
# fit <- lmFit(mat_f, design)
# fit2 <- eBayes(contrasts.fit(fit, contrast_matrix))
# topTable(fit2, adjust.method="BH", number=Inf)

# 6) Patient-level: aggregate technical replicates to patient before DE if needed
