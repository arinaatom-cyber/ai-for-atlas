# Stats plan for PXD031107
# Design: paired | Patient level: patient
library(limma)

# 1) Load protein matrix from Result File: 41375_2022_1796_MOESM2_ESM
# mat <- read_protein_matrix("tmt-projects/Projects/PXD031107/...")

# 2) Filter: >=70% valid values per comparison group
# mat_f <- filter_by_group_presence(mat, groups, min_frac=0.7)

# 3) Log2 if not already (check Normalization Strategy in sheet)
# norm_in_sheet: TMT reporter ratios normalized to internal reference and median and log2 transformed

# 4) Design matrix
# design <- model.matrix(~ 0 + group + patient_id)

# 5) Test: limma_paired
# fit <- lmFit(mat_f, design)
# fit2 <- eBayes(contrasts.fit(fit, contrast_matrix))
# topTable(fit2, adjust.method="BH", number=Inf)

# 6) Patient-level: aggregate technical replicates to patient before DE if needed
