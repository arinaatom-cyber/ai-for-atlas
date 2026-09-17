# -*- coding: utf-8 -*-
"""Anatomical body map HTML — same layout as arinaatom-cyber.github.io/TMT/."""
from __future__ import annotations

import base64
import html
from typing import Any

SYSTEMIC = frozenset({
    "Bone_Marrow", "Lymph_Node", "Nerve", "Adipose_Tissue",
    "Soft_Tissue", "Multiple_Organs", "Other",
})

# Organs shown only on the corresponding figure (dual-map mode).
FEMALE_ONLY = frozenset({"Uterus", "Ovary", "Cervix", "Breast"})
MALE_ONLY = frozenset({"Prostate", "Testis"})
PANEL_W = 480
PANEL_GAP = 480  # male panel offset

ANATOMY_COL = {
    "Brain": "#b898a8", "Pituitary": "#9a88a0", "Eye": "#d8d0c0", "Salivary_Gland": "#d4a098",
    "Thyroid": "#b88870", "Esophagus": "#c4a088", "Lung": "#c08080", "Heart": "#a84848",
    "Breast": "#d4a0a0", "Liver": "#8b5c48", "Stomach": "#c8a878", "Spleen": "#8b5868",
    "Pancreas": "#c4a860", "Adrenal_Gland": "#a89058", "Kidney": "#9a6860",
    "Small_Intestine": "#d4b888", "Colon": "#a07868", "Bladder": "#c8b070",
    "Uterus": "#c08890", "Ovary": "#d4a090", "Cervix": "#b87888", "Prostate": "#a89080",
    "Testis": "#c4a888", "Bone": "#d8d0c4", "Blood": "#a84040", "Bone_Marrow": "#8b4848",
    "Lymph_Node": "#88a088", "Skin": "#e0c0a8", "Muscle": "#9a7068",
    "Adipose_Tissue": "#d8c898", "Soft_Tissue": "#b8a090", "Nerve": "#d4c878",
    "Multiple_Organs": "#a0a0a8", "Other": "#9498a0",
}

# Display labels on map (internal data-o keys unchanged)
ORGAN_DISPLAY_NAMES: dict[str, str] = {
    "Pituitary": "PITUITARY GLAND",
    "Thyroid": "THYROID GLAND",
    "Eye": "EYES",
    "Breast": "BREAST TISSUE",
    "Cervix": "UTERINE CERVIX",
    "Testis": "TESTES",
    "Colon": "LARGE INTESTINE",
    "Kidney": "KIDNEYS",
    "Adrenal_Gland": "ADRENAL GLANDS",
    "Salivary_Gland": "SALIVARY GLANDS",
}

ANATOMY_SCHEMATIC_NOTE = (
    "Schematic anterior view. Organs are not shown to scale. "
    "Retroperitoneal organs are projected onto the anterior view."
)

# pos x,y; optional anchor x,y for leader lines; side L/R; z draw order; d=svg path
ANATOMY: dict[str, dict[str, Any]] = {
    "Brain": {"pos": (240, 42), "side": "R", "z": 1, "d": (
        "M 218 26 Q 240 16 262 26 Q 272 48 264 68 Q 240 78 216 68 Q 208 48 218 26 Z"
    )},
    "Pituitary": {"pos": (240, 56), "side": "R", "z": 3, "d": (
        "M 236 54 A 4 3 0 1 0 244 54 A 4 3 0 1 0 236 54 Z"
    )},
    "Eye": {"pos": (248, 62), "side": "R", "z": 2, "d": (
        "M 224 62 A 6 3 0 1 0 236 62 A 6 3 0 1 0 224 62 Z "
        "M 244 62 A 6 3 0 1 0 256 62 A 6 3 0 1 0 244 62 Z "
        "M 230 62 A 1.6 1.6 0 1 0 230.01 62 Z "
        "M 250 62 A 1.6 1.6 0 1 0 250.01 62 Z"
    )},
    "Salivary_Gland": {"pos": (240, 84), "side": "R", "z": 3, "d": (
        "M 222 80 Q 216 76 220 72 Q 228 70 232 76 Q 230 84 224 85 Z "
        "M 258 80 Q 264 76 260 72 Q 252 70 248 76 Q 250 84 256 85 Z"
    )},
    "Thyroid": {"pos": (240, 120), "anchor": (208, 120), "side": "L", "z": 2, "d": (
        "M 230 112 Q 224 116 226 126 L 229 130 Q 235 132 237 124 L 237 116 Q 235 112 230 112 Z "
        "M 250 112 Q 256 116 254 126 L 251 130 Q 245 132 243 124 L 243 116 Q 245 112 250 112 Z "
        "M 237 120 L 243 120 L 243 124 L 237 124 Z"
    )},
    "Esophagus": {"pos": (240, 172), "anchor": (241, 172), "side": "L", "z": 1, "d": (
        "M 239.2 128 L 240.8 128 L 240.8 200 L 241.5 216 L 244 228 L 250 234 L 254 232 "
        "L 250 226 L 246 222 L 242 216 L 240.5 200 L 239.2 128 Z"
    )},
    "Lung": {"pos": (240, 182), "anchor": (240, 182), "side": "L", "z": 2, "d": (
        "M 228 136 Q 204 138 195 156 Q 186 188 190 216 Q 196 230 218 230 L 230 224 "
        "Q 232 194 232 158 Q 231 140 228 136 Z "
        "M 258 138 Q 274 140 282 154 Q 290 178 288 206 Q 284 226 266 228 L 262 218 "
        "Q 256 208 258 194 Q 256 174 258 158 Q 258 146 258 138 Z "
        "M 262 178 Q 268 184 266 196 Q 262 204 258 198 Q 256 188 262 178 Z"
    )},
    "Thymus": {"pos": (240, 156), "anchor": (208, 154), "side": "L", "z": 2, "map_hidden": True, "d": (
        "M 230 146 Q 240 143 250 146 Q 252 156 248 166 Q 240 170 232 166 Q 228 156 230 146 Z"
    )},
    "Heart": {"pos": (244, 190), "anchor": (244, 190), "side": "R", "z": 3, "d": (
        "M 242 168 Q 230 170 226 182 Q 224 198 236 210 L 252 218 Q 264 208 264 192 "
        "Q 262 176 250 168 Q 246 166 242 168 Z"
    )},
    "Breast": {"pos": (240, 198), "anchor": (178, 198), "side": "L", "z": 4, "breast": True, "d": (
        "M 176 184 Q 168 192 170 204 Q 178 214 190 210 Q 198 200 196 188 Q 190 180 176 184 Z "
        "M 284 182 Q 292 190 290 202 Q 282 212 270 208 Q 262 198 264 186 Q 270 178 284 182 Z"
    )},
    "Liver": {"pos": (208, 244), "anchor": (188, 242), "side": "L", "z": 2, "d": (
        "M 186 224 Q 214 216 246 219 Q 268 223 274 236 Q 273 252 258 261 Q 224 269 198 264 "
        "Q 186 259 183 244 Q 182 230 186 224 Z"
    )},
    "Gallbladder": {"pos": (210, 276), "anchor": (182, 276), "side": "L", "z": 3, "map_hidden": True, "d": (
        "M 206 262 Q 216 260 218 270 Q 219 282 212 290 Q 204 292 202 282 Q 201 270 206 262 Z"
    )},
    "Stomach": {"pos": (258, 242), "anchor": (298, 238), "side": "R", "z": 4, "d": (
        "M 248 224 Q 252 218 258 220 Q 268 224 272 236 Q 274 248 268 258 Q 258 264 248 260 "
        "Q 240 252 242 240 Q 244 230 248 224 Z"
    )},
    "Spleen": {"pos": (294, 232), "anchor": (300, 234), "side": "R", "z": 4, "d": (
        "M 288 218 Q 298 222 300 236 Q 298 248 290 250 Q 282 244 284 230 Q 286 222 288 218 Z"
    )},
    "Pancreas": {"pos": (242, 258), "anchor": (248, 256), "side": "R", "z": 2, "d": (
        "M 186 260 Q 202 252 222 254 Q 244 256 264 258 Q 280 260 288 252 Q 282 246 266 250 "
        "Q 244 252 224 254 Q 204 256 192 264 Q 184 268 186 260 Z"
    )},
    "Kidney": {"pos": (238, 262), "anchor": (192, 266), "side": "L", "z": 3, "kidney": True, "d": (
        "M 176 248 C 170 254 168 266 172 278 C 176 290 186 294 198 290 C 208 284 210 272 208 260 "
        "C 206 250 198 246 188 246 C 180 246 176 248 176 248 Z "
        "M 286 238 C 292 244 294 256 290 268 C 286 280 276 284 266 280 C 256 274 254 262 256 250 "
        "C 258 240 266 236 276 238 C 282 238 286 238 286 238 Z"
    )},
    "Adrenal_Gland": {"pos": (238, 248), "anchor": (192, 244), "side": "R", "z": 5, "adrenal": True, "d": (
        "M 184 246 L 190 240 L 196 246 L 190 250 Z "
        "M 264 234 Q 272 232 278 236 Q 272 240 266 238 Z"
    )},
    "Colon": {"pos": (240, 302), "anchor": (302, 298), "side": "R", "z": 2, "colon": True, "d": (
        "M 236 346 Q 252 344 264 334 Q 278 318 284 296 Q 288 276 282 260 Q 272 252 254 254 "
        "Q 236 256 220 262 Q 204 270 196 286 Q 190 304 196 322 Q 206 338 224 344 Q 230 346 236 346 Z "
        "M 222 288 Q 240 284 258 288 Q 272 296 274 310 Q 270 324 254 330 Q 236 332 220 324 "
        "Q 210 312 212 298 Q 216 290 222 288 Z"
    )},
    "Small_Intestine": {"pos": (240, 306), "anchor": (240, 306), "side": "L", "z": 3, "small_bowel": True, "d": (
        "M 216 292 Q 230 286 244 294 Q 250 304 238 310 Q 224 308 216 300 Z "
        "M 248 296 Q 262 290 272 300 Q 270 314 256 316 Q 244 312 248 296 Z "
        "M 224 306 Q 238 302 250 310 Q 246 322 232 324 Q 220 318 224 306 Z "
        "M 256 304 Q 266 308 264 320 Q 252 324 246 314 Q 248 304 256 304 Z "
        "M 230 316 Q 242 312 254 318 Q 250 330 236 332 Q 226 326 230 316 Z "
        "M 248 318 Q 260 314 266 324 Q 258 334 246 330 Q 242 324 248 318 Z "
        "M 236 300 Q 246 296 250 304 Q 244 312 234 310 Q 232 304 236 300 Z"
    )},
    "Appendix": {"pos": (198, 348), "anchor": (178, 348), "side": "L", "z": 5, "map_hidden": True, "d": (
        "M 200 332 Q 192 336 190 346 Q 192 356 198 359 Q 203 353 201 344 Q 200 336 200 332 Z"
    )},
    "Bladder": {"pos": (240, 342), "anchor": (240, 344), "side": "R", "z": 6, "d": (
        "M 226 336 Q 240 330 254 336 Q 256 346 248 352 Q 240 354 232 352 Q 224 346 226 336 Z"
    )},
    "Uterus": {"pos": (240, 312), "anchor": (244, 310), "side": "L", "z": 3, "d": (
        "M 236 304 Q 248 298 254 310 Q 256 320 250 326 Q 244 328 238 324 Q 232 316 234 308 Q 234 304 236 304 Z"
    )},
    "Ovary": {"pos": (240, 308), "anchor": (206, 308), "side": "L", "z": 4, "d": (
        "M 206 304 Q 200 308 202 314 Q 208 316 212 310 Q 210 304 206 304 Z "
        "M 274 302 Q 280 306 278 312 Q 272 314 268 308 Q 270 302 274 302 Z"
    )},
    "Cervix": {"pos": (240, 328), "anchor": (218, 328), "side": "L", "z": 4, "d": (
        "M 238 324 Q 242 324 244 328 Q 242 332 240 332 Q 237 330 238 324 Z"
    )},
    "Prostate": {"pos": (241, 358), "anchor": (241, 356), "side": "R", "z": 5, "d": (
        "M 232 352 Q 241 348 250 352 Q 252 360 241 364 Q 230 360 232 352 Z"
    )},
    "Testis": {"pos": (240, 386), "anchor": (240, 386), "side": "R", "z": 3, "d": (
        "M 214 378 Q 240 370 266 378 Q 268 394 240 398 Q 212 394 214 378 Z "
        "M 228 382 Q 224 388 228 394 Q 234 396 238 390 Q 236 384 228 382 Z "
        "M 252 382 Q 256 388 252 394 Q 246 396 242 390 Q 244 384 252 382 Z"
    )},
    "Bone": {"pos": (240, 165), "side": "R", "z": 0, "skeleton": True, "d": (
        "M 237 132 L 243 132 L 242 198 L 238 198 Z"
    )},
}


def _esc(s: str) -> str:
    return html.escape(str(s), quote=True)


def _organ_color(o: str) -> str:
    return ANATOMY_COL.get(o, "#b8a090")


def _icon_url(icon: str, color: str) -> str:
    from urllib.parse import quote
    return f"https://api.iconify.design/{icon}.svg?color={quote(color)}"


def _twemoji_url(code: str) -> str:
    return f"https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/svg/{code}.svg"


def _body_silhouette() -> str:
    head = "M 240 20 Q 272 20 274 50 Q 274 80 258 94 L 222 94 Q 206 80 206 50 Q 208 20 240 20 Z"
    neck = "M 224 94 L 256 94 L 260 130 L 220 130 Z"
    torso = (
        "M 220 130 Q 196 134 184 144 L 178 188 Q 180 230 184 270 "
        "Q 186 300 192 332 Q 198 350 206 362 L 212 370 L 268 370 L 274 362 "
        "Q 282 350 288 332 Q 294 300 296 270 Q 300 230 302 188 L 296 144 Q 284 134 260 130 Z"
    )
    arm_l = (
        "M 184 144 Q 162 154 152 188 L 144 260 Q 140 310 148 350 L 158 384 Q 164 396 174 392 "
        "L 184 388 Q 184 366 178 348 L 170 280 Q 170 240 178 200 Q 184 168 196 152 Z"
    )
    arm_r = (
        "M 296 144 Q 318 154 328 188 L 336 260 Q 340 310 332 350 L 322 384 Q 316 396 306 392 "
        "L 296 388 Q 296 366 302 348 L 310 280 Q 310 240 302 200 Q 296 168 284 152 Z"
    )
    leg_l = "M 212 370 L 206 410 Q 200 500 198 580 Q 196 650 194 700 L 172 700 Q 168 650 172 580 Q 178 500 196 410 L 212 370 Z"
    leg_r = "M 268 370 L 274 410 Q 280 500 282 580 Q 284 650 286 700 L 308 700 Q 312 650 308 580 Q 302 500 284 410 L 268 370 Z"
    stroke, fill = "#d89a9a", "rgba(216,154,154,.03)"
    parts = [
        f'<path d="{head}" fill="{fill}" stroke="{stroke}" stroke-width="1.1"/>',
        f'<path d="{neck}" fill="{fill}" stroke="{stroke}" stroke-width="1.1"/>',
        f'<path d="{torso}" fill="{fill}" stroke="{stroke}" stroke-width="1.1"/>',
        f'<path d="{arm_l}" fill="{fill}" stroke="{stroke}" stroke-width="1.1"/>',
        f'<path d="{arm_r}" fill="{fill}" stroke="{stroke}" stroke-width="1.1"/>',
        f'<path d="{leg_l}" fill="{fill}" stroke="{stroke}" stroke-width="1.1"/>',
        f'<path d="{leg_r}" fill="{fill}" stroke="{stroke}" stroke-width="1.1"/>',
        '<text x="240" y="10" text-anchor="middle" fill="#94a3b8" font-family="Inter,sans-serif" '
        'font-size="8" letter-spacing="4" font-weight="600">ANATOMICAL ATLAS · ANTERIOR VIEW</text>',
    ]
    return f'<g class="body-silhouette" pointer-events="none">{"".join(parts)}</g>'


def _body_silhouette_sex(sex: str) -> str:
    """Female / male variant — for dual-map mode only."""
    head = "M 240 20 Q 272 20 274 50 Q 274 80 258 94 L 222 94 Q 206 80 206 50 Q 208 20 240 20 Z"
    neck = "M 224 94 L 256 94 L 260 130 L 220 130 Z"
    if sex == "male":
        torso = (
            "M 222 130 Q 196 132 184 142 L 178 186 Q 180 228 184 268 "
            "Q 186 300 192 332 Q 198 350 206 362 L 212 370 L 268 370 L 274 362 "
            "Q 282 350 288 332 Q 294 300 296 268 Q 300 228 302 188 L 296 144 "
            "Q 286 136 260 130 Z"
        )
        arm_l = (
            "M 184 144 Q 160 152 148 188 L 140 260 Q 136 310 144 350 L 154 384 "
            "Q 160 396 170 392 L 180 388 Q 180 366 174 348 L 166 280 Q 166 240 "
            "174 200 Q 180 168 192 152 Z"
        )
        arm_r = (
            "M 296 144 Q 320 152 332 188 L 340 260 Q 344 310 336 350 L 326 384 "
            "Q 320 396 310 392 L 300 388 Q 300 366 306 348 L 314 280 Q 314 240 "
            "306 200 Q 300 168 288 152 Z"
        )
        leg_l = (
            "M 214 370 Q 202 376 198 396 L 194 468 Q 192 528 196 578 "
            "L 202 624 Q 208 640 216 638 L 224 630 Q 226 556 229 482 "
            "L 232 412 Q 234 382 238 372 L 240 370 L 214 370 Z"
        )
        leg_r = (
            "M 266 370 Q 278 376 282 396 L 286 468 Q 288 528 284 578 "
            "L 278 624 Q 272 640 264 638 L 256 630 Q 254 556 251 482 "
            "L 248 412 Q 246 382 242 372 L 240 370 L 266 370 Z"
        )
        title = "MALE · ANTERIOR VIEW"
    else:
        torso = (
            "M 218 130 Q 192 136 180 146 L 174 188 Q 176 230 180 270 "
            "Q 184 304 192 336 Q 200 352 206 362 L 210 370 L 270 370 L 276 362 "
            "Q 284 348 290 330 Q 296 300 300 270 Q 304 230 306 188 L 300 144 "
            "Q 288 132 262 130 Z"
        )
        arm_l = (
            "M 186 144 Q 166 154 156 188 L 148 260 Q 144 310 152 350 L 162 384 "
            "Q 168 396 178 392 L 188 388 Q 188 366 182 348 L 174 280 Q 174 240 "
            "182 200 Q 188 168 200 152 Z"
        )
        arm_r = (
            "M 294 144 Q 314 154 324 188 L 332 260 Q 336 310 328 350 L 318 384 "
            "Q 312 396 302 392 L 292 388 Q 292 366 298 348 L 306 280 Q 306 240 "
            "298 200 Q 292 168 280 152 Z"
        )
        leg_l = (
            "M 206 370 Q 194 376 190 396 L 186 468 Q 184 528 188 578 "
            "L 194 624 Q 200 640 208 638 L 216 630 Q 218 556 221 482 "
            "L 224 412 Q 226 382 230 372 L 232 370 L 206 370 Z"
        )
        leg_r = (
            "M 274 370 Q 286 376 290 396 L 294 468 Q 296 528 292 578 "
            "L 286 624 Q 280 640 272 638 L 264 630 Q 262 556 259 482 "
            "L 256 412 Q 254 382 250 372 L 248 370 L 274 370 Z"
        )
        title = "FEMALE · ANTERIOR VIEW"
    stroke, fill = "#d89a9a", "rgba(216,154,154,.03)"
    parts = [
        f'<path d="{head}" fill="{fill}" stroke="{stroke}" stroke-width="1.1"/>',
        f'<path d="{neck}" fill="{fill}" stroke="{stroke}" stroke-width="1.1"/>',
        f'<path d="{torso}" fill="{fill}" stroke="{stroke}" stroke-width="1.1"/>',
        f'<path d="{arm_l}" fill="{fill}" stroke="{stroke}" stroke-width="1.1"/>',
        f'<path d="{arm_r}" fill="{fill}" stroke="{stroke}" stroke-width="1.1"/>',
        f'<path d="{leg_l}" fill="{fill}" stroke="{stroke}" stroke-width="1.1"/>',
        f'<path d="{leg_r}" fill="{fill}" stroke="{stroke}" stroke-width="1.1"/>',
        f'<text x="240" y="10" text-anchor="middle" fill="#94a3b8" font-family="Inter,sans-serif" '
        f'font-size="8" letter-spacing="3" font-weight="600">{title}</text>',
    ]
    return f'<g class="body-silhouette body-{sex}" pointer-events="none">{"".join(parts)}</g>'


def _format_project_count(n: int) -> str:
    return "1 project" if n == 1 else f"{n} projects"


def _format_map_organ_stats(s: dict) -> str:
    pan = f" · Pan: {s['nPan']}" if s.get("nPan") else ""
    return f"{_format_project_count(s['n'])} · C: {s['nC']} · N: {s['nN']}{pan}"


def _map_organ_visible(o: str) -> bool:
    a = ANATOMY.get(o)
    return bool(a and o not in SYSTEMIC and not a.get("skeleton") and not a.get("map_hidden"))


def _organ_anchor(a: dict[str, Any]) -> tuple[float, float]:
    if "anchor" in a:
        return a["anchor"]
    return a["pos"]


def _organ_display_name(o: str) -> str:
    return ORGAN_DISPLAY_NAMES.get(o, o.replace("_", " ").upper())


def _assign_label_positions(
    active: list[str],
    force_side: str | None = None,
) -> tuple[dict[str, float], dict[str, float]]:
    min_gap = 34 if force_side else 40
    top, bottom = 40, 620

    def layout(arr: list[dict]) -> dict[str, float]:
        arr.sort(key=lambda x: x["y"])
        prev = top - min_gap
        for it in arr:
            it["y"] = max(it["y"], prev + min_gap)
            prev = it["y"]
        if arr:
            excess = arr[-1]["y"] - bottom
            if excess > 0:
                for it in arr:
                    it["y"] -= excess
        return {it["o"]: it["y"] for it in arr}

    if force_side in ("L", "R"):
        arr = [{"o": o, "y": _organ_anchor(ANATOMY[o])[1]} for o in active]
        laid = layout(arr)
        return (laid, {}) if force_side == "L" else ({}, laid)

    left, right = [], []
    for o in active:
        a = ANATOMY[o]
        ax, ay = _organ_anchor(a)
        (left if a["side"] == "L" else right).append({"o": o, "y": ay})
    return layout(left), layout(right)


def _organ_group(o: str, selected: str | None) -> str:
    if not _map_organ_visible(o):
        return ""
    a = ANATOMY[o]
    fill = _organ_color(o)
    hi = " hi" if selected == o else ""
    if not a.get("d"):
        return ""
    if a.get("skeleton"):
        psty = "fill:none;stroke:rgba(255,255,255,.55);stroke-width:1"
        pcls = "skeleton-part"
        pe = ' pointer-events="none"'
        extra = " organ-skeleton"
    elif a.get("breast"):
        psty = (
            f"fill:{fill};fill-opacity:.34;fill-rule:evenodd;"
            f"stroke:rgba(255,255,255,.48);stroke-width:.7"
        )
        pcls = "anatomy-part"
        pe = ""
        extra = ""
    elif a.get("small_bowel"):
        psty = (
            f"fill:{fill};fill-opacity:.72;"
            f"stroke:rgba(255,255,255,.45);stroke-width:.65"
        )
        pcls = "anatomy-part"
        pe = ""
        extra = ""
    elif a.get("adrenal"):
        psty = (
            f"fill:{fill};fill-opacity:.96;fill-rule:evenodd;"
            f"stroke:rgba(255,255,255,.6);stroke-width:.65"
        )
        pcls = "anatomy-part"
        pe = ""
        extra = ""
    elif a.get("kidney"):
        psty = (
            f"fill:{fill};fill-opacity:.93;fill-rule:evenodd;"
            f"stroke:rgba(255,255,255,.55);stroke-width:.75"
        )
        pcls = "anatomy-part"
        pe = ""
        extra = ""
    elif a.get("colon"):
        psty = (
            f"fill:{fill};fill-opacity:.86;fill-rule:evenodd;"
            f"stroke:rgba(255,255,255,.5);stroke-width:.7"
        )
        pcls = "anatomy-part"
        pe = ""
        extra = ""
    else:
        psty = (
            f"fill:{fill};fill-opacity:.9;fill-rule:evenodd;"
            f"stroke:rgba(255,255,255,.5);stroke-width:.7"
        )
        pcls = "anatomy-part"
        pe = ""
        extra = ""
    return (
        f'<g class="organ-g{extra}{hi}" data-o="{o}">'
        f'<path class="{pcls}" d="{a["d"]}" style="{psty}"{pe}/></g>'
    )


def _organ_label(
    o: str,
    label_y: float,
    stats: dict,
    selected: str | None,
    force_side: str | None = None,
) -> str:
    a = ANATOMY[o]
    compact = force_side in ("L", "R")
    is_l = force_side == "L" if compact else a["side"] == "L"
    label_x = 30 if is_l else 450
    anchor = "start" if is_l else "end"
    name = _organ_display_name(o)
    s = stats.get(o, {"n": 0, "nC": 0, "nN": 0, "nPan": 0})
    pan = f" · Pan: {s['nPan']}" if s.get("nPan") else ""
    count = _format_map_organ_stats(s) if not compact else (
        f"{_format_project_count(s['n'])} · C: {s['nC']} · N: {s['nN']}{pan}"
    )
    ox, oy = _organ_anchor(a)
    turn_x = 168 if is_l else 312
    line_end = label_x + 4 if is_l else label_x - 4
    col = _organ_color(o)
    hi = " hi" if selected == o else ""
    tx = label_x + (12 if is_l else -12)
    fs_name = "9" if compact else "10"
    fs_count = "6.5" if compact else "7.5"
    return (
        f'<g class="lbl-g{hi}" data-cb="{o}">'
        f'<path fill="none" stroke="#94a3b8" stroke-width="0.5" opacity="0.35" '
        f'd="M {ox} {oy} L {turn_x} {oy} L {turn_x} {label_y} L {line_end} {label_y}"/>'
        f'<circle cx="{ox}" cy="{oy}" r="1.5" fill="{col}"/>'
        f'<text fill="#e8ecf4" font-size="{fs_name}" font-weight="700" font-family="Inter,sans-serif" '
        f'x="{tx}" y="{label_y - 3}" text-anchor="{anchor}">{_esc(name)}</text>'
        f'<text fill="#94a3b8" font-size="{fs_count}" font-family="Inter,sans-serif" '
        f'x="{tx}" y="{label_y + 7}" text-anchor="{anchor}">{_esc(count)}</text>'
        f"</g>"
    )


# Embedded in SVG — works in interactive component and base64 <img>.
SVG_STYLE_BLOCK = """<style>
.organ-g,.lbl-g{cursor:pointer}
.organ-g:hover .anatomy-part,.organ-g.hi .anatomy-part{stroke:#fff;filter:brightness(1.15)}
.lbl-g:hover .lbl-lead,.lbl-g.hi .lbl-lead{stroke:#9cb8d9;opacity:1}
.lbl-g:hover .lbl-name,.lbl-g.hi .lbl-name{fill:#9cb8d9}
.lbl-lead{fill:none;stroke:#94a3b8;stroke-width:.5;opacity:.35}
.lbl-name{font-size:10px;font-weight:700;fill:#e8ecf4;font-family:Inter,sans-serif}
.lbl-count{font-size:7.5px;fill:#94a3b8;font-family:Inter,sans-serif}
</style>"""


MAP_MODE = "dual"  # "dual" | "single" — set "single" to restore one combined body


MAP_EMBED_CSS = """
<style>
.atlas-map-wrap {
  max-width: 1080px;
  margin: 0 auto;
  background: #0b0e14;
  border-radius: 12px;
  padding: 8px 4px 4px;
  border: 1px solid #2a3650;
}
.atlas-map-wrap .anatomy-svg {
  width: 100%;
  height: auto;
  display: block;
  filter: drop-shadow(0 4px 18px rgba(0,0,0,.35));
}
.atlas-map-wrap .atlas-map-img {
  width: 100%;
  height: auto;
  display: block;
}
.atlas-map-wrap .anatomy-part { stroke: rgba(255,255,255,.55); stroke-width: .9; }
.atlas-map-wrap .lbl-name { font-size: 10px; font-weight: 700; fill: #e8ecf4; }
.atlas-map-wrap .lbl-count { font-size: 7.5px; fill: #94a3b8; }
.atlas-map-wrap .lbl-lead { fill: none; stroke: #94a3b8; stroke-width: .5; opacity: .35; }
.atlas-map-caption { text-align: center; font-size: 11px; color: #64748b; margin-top: 6px; }
</style>
"""


def build_map_embed(
    counts: dict[str, int],
    stats: dict[str, dict],
    selected: str | None = None,
) -> str:
    """Inline HTML for st.markdown — SVG as base64 <img> (Streamlit strips raw <svg>)."""
    svg = build_svg_markup(counts, stats, selected)
    b64 = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    w, h = (960, 720) if MAP_MODE == "dual" else (480, 720)
    caption = (
        "Female (left) · Male (right) · anterior view"
        if MAP_MODE == "dual"
        else "Anterior view · anatomical atlas"
    )
    return (
        f"{MAP_EMBED_CSS}"
        f'<div class="atlas-map-wrap">'
        f'<img class="atlas-map-img" src="data:image/svg+xml;base64,{b64}" '
        f'alt="Anatomical body map" width="{w}" height="{h}"/>'
        f"</div>"
        f'<p class="atlas-map-caption">{caption}</p>'
        f'<p class="atlas-map-caption" style="margin-top:2px;opacity:.85">{ANATOMY_SCHEMATIC_NOTE}</p>'
    )


def build_svg_markup_single(
    counts: dict[str, int],
    stats: dict[str, dict],
    selected: str | None = None,
) -> str:
    """Single combined figure — set MAP_MODE = \"single\" to use."""
    active = [o for o in ANATOMY if counts.get(o, 0) > 0 and _map_organ_visible(o)]
    draw_order = sorted(active, key=lambda o: ANATOMY[o].get("z", 1))
    label_l, label_r = _assign_label_positions(active)

    organs_svg = "".join(_organ_group(o, selected) for o in draw_order)
    labels_svg = ""
    for o in active:
        a = ANATOMY[o]
        ymap = label_l if a["side"] == "L" else label_r
        labels_svg += _organ_label(o, ymap.get(o, a["pos"][1]), stats, selected)

    return (
        f'<svg viewBox="0 0 480 720" preserveAspectRatio="xMidYMid meet" xmlns="http://www.w3.org/2000/svg" class="anatomy-svg">'
        f"{SVG_STYLE_BLOCK}{_body_silhouette()}"
        f'<g class="organs-layer">{organs_svg}</g>'
        f'<g class="labels-layer">{labels_svg}</g></svg>'
    )


def build_svg_markup_dual(
    counts: dict[str, int],
    stats: dict[str, dict],
    selected: str | None = None,
) -> str:
    """Female + male figures side by side."""
    female = _build_figure_panel("female", 0, counts, stats, selected)
    male = _build_figure_panel("male", PANEL_GAP, counts, stats, selected)
    divider = (
        '<line x1="480" y1="16" x2="480" y2="704" stroke="#2a3650" '
        'stroke-width="1" opacity="0.4"/>'
    )
    return (
        f'<svg viewBox="0 0 960 720" preserveAspectRatio="xMidYMid meet" xmlns="http://www.w3.org/2000/svg" class="anatomy-svg anatomy-dual">'
        f"{SVG_STYLE_BLOCK}{divider}{female}{male}</svg>"
    )


def build_svg_markup(
    counts: dict[str, int],
    stats: dict[str, dict],
    selected: str | None = None,
) -> str:
    if MAP_MODE == "dual":
        return build_svg_markup_dual(counts, stats, selected)
    return build_svg_markup_single(counts, stats, selected)


# ---------------------------------------------------------------------------
# DUAL MAP helpers (female left, male right)
# ---------------------------------------------------------------------------
def _active_organs_for_sex(sex: str, counts: dict[str, int]) -> list[str]:
    exclude = MALE_ONLY if sex == "female" else FEMALE_ONLY
    return [
        o for o in ANATOMY
        if counts.get(o, 0) > 0 and _map_organ_visible(o) and o not in exclude
    ]


def _build_figure_panel(
    sex: str,
    offset_x: int,
    counts: dict[str, int],
    stats: dict[str, dict],
    selected: str | None,
) -> str:
    active = _active_organs_for_sex(sex, counts)
    label_side = "L" if sex == "female" else "R"
    draw_order = sorted(active, key=lambda o: ANATOMY[o].get("z", 1))
    label_l, label_r = _assign_label_positions(active, label_side)
    ymap = label_l if label_side == "L" else label_r

    organs_svg = "".join(_organ_group(o, selected) for o in draw_order)
    labels_svg = ""
    for o in active:
        a = ANATOMY[o]
        labels_svg += _organ_label(
            o, ymap.get(o, a["pos"][1]), stats, selected, label_side
        )

    return (
        f'<g class="figure-panel figure-{sex}" transform="translate({offset_x},0)">'
        f"{_body_silhouette_sex(sex)}"
        f'<g class="organs-layer">{organs_svg}</g>'
        f'<g class="labels-layer">{labels_svg}</g>'
        f"</g>"
    )


def build_body_map_html(
    counts: dict[str, int],
    stats: dict[str, dict],
    selected: str | None = None,
) -> str:
    svg = build_svg_markup(counts, stats, selected)

    css = """
    *{box-sizing:border-box;margin:0;padding:0}
    body{background:#0b0e14;color:#e8ecf4;font-family:Inter,system-ui,sans-serif;overflow:hidden}
    .wrap{position:relative;max-width:520px;margin:0 auto}
    .anatomy-svg{width:100%;height:auto;display:block;filter:drop-shadow(0 4px 18px rgba(0,0,0,.35))}
    .anatomy-part{stroke:rgba(255,255,255,.55);stroke-width:.9;stroke-linejoin:round}
    .skeleton-part{opacity:.85}
    .organ-g{cursor:pointer}
    .organ-g:hover .anatomy-part,.organ-g.hi .anatomy-part{stroke:#fff;filter:brightness(1.15)}
    .organ-g:hover .skeleton-part,.organ-g.hi .skeleton-part{stroke:#fff;stroke-width:2}
    .lbl-g{cursor:pointer}
    .lbl-lead{fill:none;stroke:#94a3b8;stroke-width:.5;opacity:.35}
    .lbl-g:hover .lbl-lead,.lbl-g.hi .lbl-lead{stroke:#9cb8d9;opacity:1}
    .lbl-name{font-size:10px;font-weight:700;letter-spacing:.12em;fill:#e8ecf4}
    .lbl-count{font-size:7.5px;fill:#94a3b8}
    .lbl-g:hover .lbl-name,.lbl-g.hi .lbl-name{fill:#9cb8d9}
    .caption{text-align:center;font-size:10px;color:#64748b;margin-top:8px}
    """

    return (
        f"<!DOCTYPE html><html><head><meta charset='utf-8'>"
        f"<style>{css}</style></head><body>"
        f'<div class="wrap">{svg}</div>'
        f'<p class="caption">Anterior view · use the organ dropdown to filter projects</p>'
        f"</body></html>"
    )


def build_interactive_map_html(
    counts: dict[str, int],
    stats: dict[str, dict],
    selected: str | None = None,
) -> str:
    """Self-contained HTML for st.components.v1.html — no custom component assets."""
    svg = build_svg_markup(counts, stats, selected)
    caption = (
        "Female (left) · Male (right) · click organ or label"
        if MAP_MODE == "dual"
        else "Click an organ or label to filter projects"
    )
    css = """
    *{box-sizing:border-box;margin:0;padding:0}
    html,body{background:#0b0e14;color:#e8ecf4;font-family:Inter,system-ui,sans-serif}
    .wrap{position:relative;width:100%;max-width:1080px;margin:0 auto;padding:4px 0}
    .anatomy-svg{width:100%;height:auto;display:block;filter:drop-shadow(0 4px 18px rgba(0,0,0,.35))}
    .anatomy-part{stroke:rgba(255,255,255,.55);stroke-width:.9;stroke-linejoin:round}
    .organ-g,.lbl-g{cursor:pointer}
    .organ-g:hover .anatomy-part,.organ-g.hi .anatomy-part{stroke:#fff;filter:brightness(1.15)}
    .lbl-g:hover .lbl-lead,.lbl-g.hi .lbl-lead{stroke:#9cb8d9;opacity:1}
    .lbl-g:hover .lbl-name,.lbl-g.hi .lbl-name{fill:#9cb8d9}
    .caption{text-align:center;font-size:11px;color:#64748b;margin-top:8px}
    """
    script = """
    (function () {
      function pickOrgan(o) {
        try {
          var u = new URL(window.parent.location.href);
          if (u.searchParams.get("organ") === o) u.searchParams.delete("organ");
          else u.searchParams.set("organ", o);
          window.parent.location.href = u.toString();
        } catch (e) { console.error(e); }
      }
      document.querySelectorAll(".organ-g[data-o], .lbl-g[data-cb]").forEach(function (el) {
        var o = el.getAttribute("data-o") || el.getAttribute("data-cb");
        el.addEventListener("click", function (ev) {
          ev.preventDefault();
          ev.stopPropagation();
          pickOrgan(o);
        });
      });
    })();
    """
    return (
        f"<!DOCTYPE html><html><head><meta charset='utf-8'><style>{css}</style></head><body>"
        f'<div class="wrap">{svg}</div>'
        f'<p class="caption">{html.escape(caption)}</p>'
        f"<script>{script}</script></body></html>"
    )
