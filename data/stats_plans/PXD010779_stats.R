# Stats plan for PXD010779
# Design: paired | Patient level: sample
library(limma)

# 1) Load protein matrix from Result File: TMT_proteins_patientdatabase_proteinGroups
# mat <- read_protein_matrix("tmt-projects/Projects/PXD010779/...")

# 2) Filter: >=70% valid values per comparison group
# mat_f <- filter_by_group_presence(mat, groups, min_frac=0.7)

# 3) Log2 if not already (check Normalization Strategy in sheet)
# norm_in_sheet: Relative ratios of each channel to the reference pool

# 4) Design matrix
# design <- model.matrix(~ 0 + group + patient_id)

# 5) Test: limma_paired
# fit <- lmFit(mat_f, design)
# fit2 <- eBayes(contrasts.fit(fit, contrast_matrix))
# topTable(fit2, adjust.method="BH", number=Inf)

# 6) Patient-level: aggregate technical replicates to patient before DE if needed
