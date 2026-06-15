#!/usr/bin/env Rscript
# precompute_survival_hr.R
# -----------------------------------------------------------------------------
# Computes, for EACH OPO, an ADJUSTED Cox hazard ratio for graft failure with
# the REST OF THE COUNTRY as the reference, adjusting for exactly the same
# covariates as the manuscript graft-survival model (Table 4).
#
# The manuscript Table 4 model (tmp_run_recip_survival_alt_sav.R::fit_overall) is:
#   Surv(GraftTime, GraftDeath) ~ any_DCU + time_period + <covariates>
#                                 + frailty(DON_OPO_FAC)
# For the per-OPO HR we make the two structurally-required swaps:
#   - replace the DCU exposure (any_DCU) with a per-OPO indicator
#     I(OPO == target), so the HR is "this OPO vs. the rest of the US"
#   - drop frailty(DON_OPO_FAC), because OPO is now the variable being tested
#     (it cannot simultaneously be the random grouping term)
# All other covariates and their coding are reused verbatim via prep_rec().
#
# Output: viz_survival_hr.csv  (consumed by app_final.py / Survival tab)
# Cohort: ALL recipients (DBD + DCD), matching the manuscript model.
# -----------------------------------------------------------------------------

suppressPackageStartupMessages({
  library(haven)
  library(dplyr)
  library(stringr)
  library(survival)
})

# --- Paths -------------------------------------------------------------------
DATA_DIR <- "/Users/yangzhizhou/Documents/Yang/Puri CT lab/SRTR_Matchrun/DCU"
SOURCE_FILE <- file.path(DATA_DIR, "LU_REC_CLEAN.sav")

# Resolve the directory this script lives in (so the CSV lands next to app_final.py)
.args <- commandArgs(trailingOnly = FALSE)
.file_arg <- sub("--file=", "", .args[grep("--file=", .args)])
SCRIPT_DIR <- if (length(.file_arg) > 0) dirname(normalizePath(.file_arg)) else getwd()

# Minimum graft-failure events within an OPO for the adjusted HR to be
# considered stable/reliable (flagged, not dropped).
MIN_EVENTS_RELIABLE <- 20

# --- Diagnosis-group code maps (verbatim from tmp_run_recip_survival_alt_sav.R) ---
GROUP_A_CODES <- c(103, 106, 109, 111, 113, 114, 116, 450, 452, 1554, 1557, 1606, 1607, 1608, 1612)
GROUP_B_CODES <- c(200, 202, 203, 205, 206, 208, 209, 210, 212, 216, 218, 220, 1500, 1501, 1502, 1517, 1548, 1549, 1601, 1614, 1615)
GROUP_C_CODES <- c(100, 105, 107, 300, 302, 303, 1602)
GROUP_D_CODES <- c(213, 214, 215, 217, 219, 400, 401, 402, 403, 404, 405, 406, 407, 408, 409, 410, 411, 412, 413, 414, 415, 416, 417, 418, 419, 420, 422, 423, 424, 432, 434, 437, 438, 440, 441, 442, 444, 446, 447, 448, 449, 451, 453, 454, 999, 1518, 1519, 1520, 1521, 1522, 1523, 1524, 1525, 1550, 1551, 1552, 1553, 1555, 1556, 1599, 1600, 1603, 1604, 1605, 1609, 1610, 1611, 1613, 1616, 1617, 1620, 1997, 1999)

parse_date <- function(x) {
  as.Date(trimws(as.character(x)), format = "%Y-%m-%d")
}

# --- Variable coding (verbatim from tmp_run_recip_survival_alt_sav.R::prep_rec) ---
prep_rec <- function(df) {
  df %>%
    mutate(
      hospital_DCU = as.numeric(str_replace_all(as.character(hospital_DCU), " ", "0")),
      any_DCU = as.numeric(any_DCU),
      independent_DCU = as.numeric(independent_DCU),
      REC_TX_DATE = parse_date(REC_TX_DT),
      DON_OPO_FAC = as.factor(DON_OPO),
      REC_LU_LF_ISCH_NUM = as.numeric(REC_LU_LF_ISCH),
      REC_LU_RT_ISCH_NUM = as.numeric(REC_LU_RT_ISCH),
      Max_Ischemic_Time = pmax(REC_LU_LF_ISCH_NUM, REC_LU_RT_ISCH_NUM, na.rm = TRUE),
      Gender_Male = ifelse(CAN_GENDER == "M", 1, 0),
      Chronic_Steroids_Yes = ifelse(REC_CHRONIC_STEROIDS == "Y", 1, 0),
      Single_Lung_TX = ifelse(REC_TX_PROCEDURE_TY %in% c(601, 602), 1, 0),
      Preop_Ventilator_Yes = as.numeric(REC_VENTILATOR),
      Preop_ECMO_Yes = as.numeric(REC_ECMO),
      Medical_Acuity_Level = case_when(
        REC_MED_COND == 1 ~ "ICU",
        REC_MED_COND == 2 ~ "Hospitalized (non-ICU)",
        REC_MED_COND == 3 ~ "Not Hospitalized (Ref)",
        TRUE ~ NA_character_
      ),
      DGN_Group_ABCD = case_when(
        CAN_DGN %in% GROUP_A_CODES ~ "Group A (Obstructive) (Ref)",
        CAN_DGN %in% GROUP_B_CODES ~ "Group B (Vascular)",
        CAN_DGN %in% GROUP_C_CODES ~ "Group C (CF/Immuno)",
        CAN_DGN %in% GROUP_D_CODES ~ "Group D (Restrictive)",
        TRUE ~ "Other/Unmapped DGN"
      ),
      DON_AGE = as.numeric(DON_AGE),
      PFratio = as.numeric(PFratio),
      Donor_Male = ifelse(DON_GENDER == "M", 1, 0),
      Death_Mech_Drown_Asphyxia = ifelse(DON_DEATH_MECH %in% c(1, 4), 1, 0),
      DCD_Yes = ifelse(DCD == 1, 1, 0),
      EVLP_Yes = ifelse(EVLP == 1, 1, 0),
      XrayAbnormal = case_when(
        DON_CHEST_XRAY %in% c(3, 4, 5) ~ 1,
        DON_CHEST_XRAY == 2 ~ 0,
        TRUE ~ NA_real_
      ),
      time_period = factor(
        case_when(
          REC_TX_DATE < as.Date("2020-01-01") ~ "2018-2019",
          REC_TX_DATE < as.Date("2023-01-01") ~ "2020-2022",
          REC_TX_DATE <= as.Date("2025-12-31") ~ "2023-2025",
          TRUE ~ NA_character_
        ),
        levels = c("2018-2019", "2020-2022", "2023-2025")
      )
    )
}

# --- Load & prep -------------------------------------------------------------
cat("Reading", SOURCE_FILE, "...\n")
rec <- read_sav(SOURCE_FILE)
rec <- prep_rec(rec)
rec$Medical_Acuity_Level <- relevel(as.factor(rec$Medical_Acuity_Level), ref = "Not Hospitalized (Ref)")
rec$DGN_Group_ABCD <- relevel(as.factor(rec$DGN_Group_ABCD), ref = "Group A (Obstructive) (Ref)")
rec$DON_OPO <- as.character(rec$DON_OPO)

# Covariate block shared by the sanity model and the per-OPO models
COVARS <- paste(
  "time_period",
  "REC_AGE_AT_TX",
  "Gender_Male",
  "Chronic_Steroids_Yes",
  "Preop_Ventilator_Yes",
  "Preop_ECMO_Yes",
  "Single_Lung_TX",
  "Medical_Acuity_Level",
  "DGN_Group_ABCD",
  "DON_AGE",
  "I(Max_Ischemic_Time / 60)",
  "PFratio",
  "Death_Mech_Drown_Asphyxia",
  "DCD_Yes",
  "EVLP_Yes",
  "XrayAbnormal",
  sep = " + "
)

# --- Sanity check: reproduce the manuscript Table 4 any_DCU HR ----------------
cat("\n=== SANITY CHECK: reproduce manuscript Table 4 (any_DCU HR ~ 1.03) ===\n")
rec$DON_OPO_FAC <- as.factor(rec$DON_OPO)
fit_overall <- coxph(
  as.formula(paste("Surv(GraftTime, GraftDeath) ~ any_DCU +", COVARS, "+ frailty(DON_OPO_FAC)")),
  data = rec
)
cf_o <- summary(fit_overall)$coefficients
rn <- rownames(cf_o)
i_dcu <- which(rn == "any_DCU")
coef_col <- which(colnames(cf_o) %in% c("coef"))[1]
se_col <- which(colnames(cf_o) %in% c("se(coef)", "se2"))[1]
hr_dcu <- exp(cf_o[i_dcu, coef_col])
se_dcu <- cf_o[i_dcu, se_col]
cat(sprintf("  any_DCU HR = %.3f (95%% CI %.3f-%.3f)   [manuscript Table 4: 1.030, 0.958-1.109]\n",
            hr_dcu, exp(cf_o[i_dcu, coef_col] - 1.96 * se_dcu), exp(cf_o[i_dcu, coef_col] + 1.96 * se_dcu)))
mf_overall <- model.frame(formula(fit_overall), data = rec, na.action = na.omit)
cat(sprintf("  analytic N = %d, events = %d\n", nrow(mf_overall), fit_overall$nevent))

# --- Per-OPO adjusted HR (this OPO vs rest of US) ----------------------------
cat("\n=== Per-OPO adjusted Cox models (this OPO vs rest of US) ===\n")
opos <- sort(unique(rec$DON_OPO))
opos <- opos[!is.na(opos) & opos != ""]
cat("  Fitting", length(opos), "OPO models...\n")

per_opo_formula <- as.formula(paste("Surv(GraftTime, GraftDeath) ~ is_opo +", COVARS))

results <- lapply(opos, function(o) {
  d <- rec
  d$is_opo <- factor(ifelse(d$DON_OPO == o, "ThisOPO", "Rest"), levels = c("Rest", "ThisOPO"))

  # x=TRUE, y=TRUE stores the design matrix and response in the fit object so we
  # can count cases without re-evaluating `d` (which is out of scope for
  # model.frame() inside lapply).
  fit <- tryCatch(coxph(per_opo_formula, data = d, x = TRUE, y = TRUE), error = function(e) NULL)
  if (is.null(fit)) {
    return(data.frame(OPO = o, HR = NA_real_, HR_Lower = NA_real_, HR_Upper = NA_real_,
                      Adj_P_Value = NA_real_, N = NA_integer_, Events = NA_integer_, Reliable = FALSE))
  }

  # N and events among the complete cases actually used by the model, for this OPO
  in_opo <- fit$x[, "is_opoThisOPO"] == 1
  n_opo <- sum(in_opo)
  ev_opo <- sum(fit$y[in_opo, 2] == 1)

  cf <- summary(fit)$coefficients
  ri <- which(rownames(cf) == "is_opoThisOPO")
  if (length(ri) == 0) {
    return(data.frame(OPO = o, HR = NA_real_, HR_Lower = NA_real_, HR_Upper = NA_real_,
                      Adj_P_Value = NA_real_, N = n_opo, Events = ev_opo, Reliable = FALSE))
  }
  b <- cf[ri, "coef"]; se <- cf[ri, "se(coef)"]; p <- cf[ri, "Pr(>|z|)"]
  data.frame(
    OPO = o,
    HR = exp(b),
    HR_Lower = exp(b - 1.96 * se),
    HR_Upper = exp(b + 1.96 * se),
    Adj_P_Value = p,
    N = n_opo,
    Events = ev_opo,
    Reliable = is.finite(se) && se < 2 && ev_opo >= MIN_EVENTS_RELIABLE
  )
})

out <- do.call(rbind, results)
out <- out[order(out$OPO), ]

out_path <- file.path(SCRIPT_DIR, "viz_survival_hr.csv")
write.csv(out, out_path, row.names = FALSE)
cat(sprintf("\nWrote %s  (%d OPOs, %d flagged reliable)\n",
            out_path, nrow(out), sum(out$Reliable, na.rm = TRUE)))
cat("\nPreview (sorted by HR):\n")
print(utils::head(out[order(-out$HR), ], 8), row.names = FALSE)
cat("DONE.\n")
