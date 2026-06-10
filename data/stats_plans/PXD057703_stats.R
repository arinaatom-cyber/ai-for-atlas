# Stats plan for PXD057703
# Design: time_course | Patient level: sample
library(limma)

# 1) Load protein matrix from Result File: pbio.3002943.s011
# mat <- read_protein_matrix("tmt-projects/Projects/PXD057703/...")

# 2) Filter: >=70% valid values per comparison group
# mat_f <- filter_by_group_presence(mat, groups, min_frac=0.7)

# 3) Log2 if not already (check Normalization Strategy in sheet)
# norm_in_sheet: LOESS normalization; reporter ion intensity normalization

# 4) Design matrix
# design <- model.matrix(~ 0 + group + patient_id)

# 5) Test: mixed_model_or_limma_time
# fit <- lmFit(mat_f, design)
# fit2 <- eBayes(contrasts.fit(fit, contrast_matrix))
# topTable(fit2, adjust.method="BH", number=Inf)

# 6) Patient-level: aggregate technical replicates to patient before DE if needed
