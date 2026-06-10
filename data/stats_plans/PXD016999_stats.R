# Stats plan for PXD016999
# Design: paired | Patient level: unknown
library(limma)

# 1) Load protein matrix from Result File: NIHMS1624446-supplement-2
# mat <- read_protein_matrix("tmt-projects/Projects/PXD016999/...")

# 2) Filter: >=70% valid values per comparison group
# mat_f <- filter_by_group_presence(mat, groups, min_frac=0.7)

# 3) Log2 if not already (check Normalization Strategy in sheet)
# norm_in_sheet: TMT126 and TMT131 were both used for the same pooled reference sample in each run as a quality check

# 4) Design matrix
# design <- model.matrix(~ 0 + group + patient_id)

# 5) Test: limma_paired
# fit <- lmFit(mat_f, design)
# fit2 <- eBayes(contrasts.fit(fit, contrast_matrix))
# topTable(fit2, adjust.method="BH", number=Inf)

# 6) Patient-level: aggregate technical replicates to patient before DE if needed
