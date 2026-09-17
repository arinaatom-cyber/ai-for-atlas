from __future__ import annotations

from pathlib import Path

import pandas as pd

from aging_mrm import normalize as n
from aging_mrm.paths import COHORT_100, COHORT_50, COHORT_350, SHEET_FILES
from aging_mrm.tables import first_col, read_table

PATIENT_COLUMNS = [
    "patient_id",
    "cohort",
    "sex",
    "age",
    "age_bin",
    "bmi",
    "height_cm",
    "weight_kg",
    "barcode",
    "sample_id",
    "srm_id",
    "plate",
    "position",
    "pathology",
    "biomaterial",
    "partner",
    "tech_group",
    "comorbidities",
    "hypertension",
    "diabetes_t2",
    "osteoarthritis",
    "osteoporosis",
    "cancer_remission",
    "cognitive_impairment",
    "ascvd",
    "copd",
]


def _flag01(value) -> str:
    number = n.parse_number(value)
    if number is None:
        text = n.as_text(value)
        return text
    if number == 1:
        return "1"
    if number == 0:
        return "0"
    return n.as_text(value)


def load_patients_100(path: Path) -> pd.DataFrame:
    df = read_table(path)
    rows = []
    for _, row in df.iterrows():
        pid = n.patient_id(row.get("donor_id", row.get("ID донора")))
        if not pid:
            continue
        age = n.parse_age(row.get("donor_age"))
        rows.append(
            {
                "patient_id": pid,
                "cohort": COHORT_100,
                "sex": n.normalize_sex(row.get("donor_gender")),
                "age": age,
                "age_bin": n.age_bin(age),
                "bmi": n.parse_number(row.get("ИМТ (кг/м^2)")),
                "height_cm": n.parse_number(row.get("Рост (см)")),
                "weight_kg": n.parse_number(row.get("Вес (кг)")),
                "barcode": n.as_text(row.get("barcode")),
                "sample_id": n.as_text(row.get("Sample ID")),
                "srm_id": n.as_text(row.get("Progress")),
                "plate": n.as_text(row.get("Plate")),
                "position": n.as_text(row.get("Position")),
                "pathology": n.as_text(row.get("pathology_type") or row.get("pathology_class")),
                "biomaterial": n.as_text(row.get("biomaterial_type")),
                "partner": n.as_text(row.get("partner") or row.get("Клинический партнер")),
                "tech_group": n.as_text(row.get("Age group")),
                "comorbidities": "",
                "hypertension": "",
                "diabetes_t2": "",
                "osteoarthritis": "",
                "osteoporosis": "",
                "cancer_remission": "",
                "cognitive_impairment": "",
                "ascvd": "",
                "copd": "",
            }
        )
    return pd.DataFrame(rows, columns=PATIENT_COLUMNS)


def load_patients_50(path: Path) -> pd.DataFrame:
    df = read_table(path)
    sex_a = first_col(df, "Пол")
    rows = []
    for _, row in df.iterrows():
        pid = n.patient_id(row.get("ID донора") or row.get("Name"))
        if not pid:
            continue
        age = n.parse_age(row.get("Возраст"))
        sex_vals = [row.get(sex_a)] if sex_a else []
        if "Пол.1" in df.columns:
            sex_vals.append(row.get("Пол.1"))
        rows.append(
            {
                "patient_id": pid,
                "cohort": COHORT_50,
                "sex": n.normalize_sex(*sex_vals),
                "age": age,
                "age_bin": n.age_bin(age),
                "bmi": n.parse_number(row.get("ИМТ (кг/м^2)")),
                "height_cm": n.parse_number(row.get("Рост (см)")),
                "weight_kg": n.parse_number(row.get("Вес (кг)")),
                "barcode": n.as_text(row.get("Barcode")),
                "sample_id": n.as_text(row.get("ID_SRM_sample")),
                "srm_id": n.as_text(row.get("SRM ID")),
                "plate": n.as_text(row.get("Plate")),
                "position": n.as_text(row.get("Position")),
                "pathology": n.as_text(row.get("Патология") or row.get("МКБ-10")),
                "biomaterial": n.as_text(row.get("Тип биоматериала")),
                "partner": n.as_text(row.get("Клинический партнер")),
                "tech_group": n.as_text(row.get("Группа по тех заданию")),
                "comorbidities": n.as_text(row.get("Сопутствующие заболевания")),
                "hypertension": "",
                "diabetes_t2": "",
                "osteoarthritis": "",
                "osteoporosis": "",
                "cancer_remission": "",
                "cognitive_impairment": "",
                "ascvd": "",
                "copd": "",
            }
        )
    return pd.DataFrame(rows, columns=PATIENT_COLUMNS)


def load_patients_350(path: Path) -> pd.DataFrame:
    df = read_table(path)
    pid_col = first_col(df, "Donor ID", "ID Донора", "№ пациента")
    age_col = first_col(df, "Возраст")
    sex_numeric = first_col(df, "Пол")
    sex_text = "Пол.1" if "Пол.1" in df.columns else first_col(df, "Пол")
    bmi_col = first_col(df, "ИМТ, кг/м2", "ИМТ")
    height_col = first_col(df, "Рост, м", "Рост (см)", "Рост")
    weight_col = first_col(df, "Вес, кг", "Вес (кг)", "Вес")
    plate_col = first_col(df, "Plate")
    pos_col = first_col(df, "Position")
    proteomics_col = first_col(df, "Proteomics ID")
    sample_type_col = first_col(df, "Тип образца")
    age_group_col = first_col(df, "Возрастная группа")

    def grab(name: str | None, row: pd.Series):
        if not name:
            return None
        return row.get(name)

    rows = []
    for _, row in df.iterrows():
        pid = n.patient_id(grab(pid_col, row))
        if not pid:
            continue
        age = n.parse_age(grab(age_col, row))
        height_raw = n.parse_number(grab(height_col, row))
        height_cm = None
        if height_raw is not None:
            height_cm = height_raw * 100 if height_raw <= 3 else height_raw
        labeled_bin = n.normalize_age_group_label(grab(age_group_col, row))
        rows.append(
            {
                "patient_id": pid,
                "cohort": COHORT_350,
                "sex": n.normalize_sex(grab(sex_text, row), grab(sex_numeric, row)),
                "age": age,
                "age_bin": n.age_bin(age),
                "bmi": n.parse_number(grab(bmi_col, row)),
                "height_cm": height_cm,
                "weight_kg": n.parse_number(grab(weight_col, row)),
                "barcode": "",
                "sample_id": n.as_text(grab(proteomics_col, row)),
                "srm_id": n.as_text(grab(proteomics_col, row)),
                "plate": n.as_text(grab(plate_col, row)),
                "position": n.as_text(grab(pos_col, row)),
                "pathology": "conditionally_healthy_volunteers",
                "biomaterial": n.as_text(grab(sample_type_col, row)) or "плазма ЭДТА",
                "partner": "",
                "tech_group": labeled_bin or n.age_bin(age),
                "comorbidities": n.as_text(row.get("Другое:")),
                "hypertension": _flag01(row.get("Артериальная гипертензия")),
                "diabetes_t2": _flag01(row.get("Сахарный диабет 2 типа")),
                "osteoarthritis": _flag01(row.get("Остеоартроз")),
                "osteoporosis": _flag01(row.get("Остеопороз (без переломов)")),
                "cancer_remission": _flag01(
                    row.get("Онкологическое заболевание (при условии ремиссии более 3 лет)")
                ),
                "cognitive_impairment": _flag01(
                    row.get(
                        "Когнитивные нарушения, выявленные ранее или по результатам данного обследования"
                    )
                ),
                "ascvd": _flag01(
                    row.get(
                        "Клинически значимые атеросклеротические сердечно-сосудистые заболевания "
                        "(ИБС, реваскуляризация в любом сосудистом бассейне, перемежающая хромота)"
                    )
                ),
                "copd": _flag01(row.get("Хроническая обструктивная болезнь легких")),
            }
        )
    return pd.DataFrame(rows, columns=PATIENT_COLUMNS)


def load_all_patients(csv_dir: Path) -> pd.DataFrame:
    parts = [
        load_patients_100(csv_dir / SHEET_FILES["patients_100"]),
        load_patients_50(csv_dir / SHEET_FILES["patients_50"]),
        load_patients_350(csv_dir / SHEET_FILES["patients_350"]),
    ]
    patients = pd.concat(parts, ignore_index=True)
    dup = patients["patient_id"].duplicated(keep=False)
    if dup.any():
        patients = patients.copy()
        patients["patient_id_conflict"] = dup.map({True: "1", False: "0"})
    else:
        patients["patient_id_conflict"] = "0"
    return patients
