# Stats plan for PXD025052
# Design: paired | Patient level: unknown
library(limma)

# 1) Load protein matrix from Result File: thnov11p9705s3
# mat <- read_protein_matrix("tmt-projects/Projects/PXD025052/...")

# 2) Filter: >=70% valid values per comparison group
# mat_f <- filter_by_group_presence(mat, groups, min_frac=0.7)

# 3) Log2 if not already (check Normalization Strategy in sheet)
# norm_in_sheet: Reporter ion intensity normalization in MaxQuant

# 4) Design matrix
# design <- model.matrix(~ 0 + group + patient_id)

# 5) Test: limma_paired
# fit <- lmFit(mat_f, design)
# fit2 <- eBayes(contrasts.fit(fit, contrast_matrix))
# topTable(fit2, adjust.method="BH", number=Inf)

# 6) Patient-level: aggregate technical replicates to patient before DE if needed
