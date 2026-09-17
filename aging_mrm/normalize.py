from __future__ import annotations

import math
import re
from typing import Any

import pandas as pd

AGE_BINS = ("18-24", "25-44", "45-59", "60-74", "75+")

_SEX_MALE = {
    "муж",
    "м",
    "m",
    "male",
    "man",
    "1",
}
_SEX_FEMALE = {
    "жен",
    "ж",
    "f",
    "female",
    "woman",
    "2",
}

_AGE_GROUP_ALIASES = {
    "18-24": "18-24",
    "18-24 г": "18-24",
    "18-24г": "18-24",
    "25-44": "25-44",
    "25-44 года": "25-44",
    "25-44года": "25-44",
    "45-59": "45-59",
    "45-59 лет": "45-59",
    "45-59лет": "45-59",
    "60-74": "60-74",
    "60-74 года": "60-74",
    "60-74года": "60-74",
    "75+": "75+",
    "above 75": "75+",
    "above75": "75+",
    "старше 75": "75+",
    "старше 75 лет": "75+",
    "75 лет и старше": "75+",
    "75лет и старше": "75+",
}


def is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return True
    try:
        if pd.isna(value):
            return True
    except (TypeError, ValueError):
        pass
    text = str(value).strip().lower()
    return text in {"", "nan", "none", "null", "-", "na"}


def as_text(value: Any) -> str:
    if is_missing(value):
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    text = str(value).strip()
    if re.fullmatch(r"-?\d+\.0+", text):
        return text.split(".", 1)[0]
    return text


def patient_id(value: Any) -> str:
    return as_text(value)


def parse_number(value: Any) -> float | None:
    if is_missing(value):
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        number = float(value)
        return None if math.isnan(number) else number
    text = str(value).strip().replace(" ", "").replace(",", ".")
    text = re.sub(r"[^0-9.eE+-]", "", text)
    if not text or text in {".", "+", "-"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def parse_age(value: Any) -> float | None:
    age = parse_number(value)
    if age is None:
        return None
    if age < 0 or age > 130:
        return None
    return age


def age_bin(age: float | None) -> str:
    if age is None:
        return ""
    try:
        a = float(age)
    except (TypeError, ValueError):
        return ""
    if math.isnan(a) or math.isinf(a):
        return ""
    if a < 18:
        return "<18"
    if age <= 24:
        return "18-24"
    if age <= 44:
        return "25-44"
    if age <= 59:
        return "45-59"
    if age <= 74:
        return "60-74"
    return "75+"


def normalize_age_group_label(value: Any) -> str:
    if is_missing(value):
        return ""
    text = re.sub(r"\s+", " ", str(value).strip().lower())
    text = text.replace("–", "-").replace("—", "-")
    if text in _AGE_GROUP_ALIASES:
        return _AGE_GROUP_ALIASES[text]
    for key, canon in _AGE_GROUP_ALIASES.items():
        if key in text:
            return canon
    return as_text(value)


def normalize_sex(*values: Any) -> str:
    for value in values:
        if is_missing(value):
            continue
        token = str(value).strip().lower()
        if token in _SEX_MALE:
            return "male"
        if token in _SEX_FEMALE:
            return "female"
    return ""


def sex_label_ru(sex: str) -> str:
    if sex == "male":
        return "муж"
    if sex == "female":
        return "жен"
    return ""
