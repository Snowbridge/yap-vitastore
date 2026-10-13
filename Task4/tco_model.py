"""TCO-модель VitaStore: 100 магазинов, 36 месяцев, As-Is vs To-Be.

Запуск из каталога Task4:
    python tco_model.py                         # пересобрать 02-tco-analysis.md и break-even.svg
    python tco_model.py --scenario full-capex   # вывести один сценарий чувствительности в консоль

Только стандартная библиотека. Все суммы — рубли без НДС, цены 2026 года (ADR-009).
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
ANALYSIS_MD = HERE / "02-tco-analysis.md"
CHART_SVG = HERE / "break-even.svg"
BEGIN, END = "<!-- TCO:BEGIN -->", "<!-- TCO:END -->"


@dataclass(frozen=True)
class P:
    value: float
    unit: str
    title: str
    source: str = "оценка"


PARAMS: dict[str, dict[str, P]] = {
    "Периметр и график": {
        "stores": P(100, "магазинов", "Магазинов в периметре", "постановка Task4"),
        "network_stores": P(500, "магазинов", "Магазинов в сети", "описание кейса"),
        "registers_per_store": P(2, "касс", "Касс в магазине", "ADR-010"),
        "platform_allocation": P(0.2, "доля", "Доля общих затрат платформы на периметр (100/500)", "ADR-010"),
        "dev_months": P(6, "мес.", "Разработка и пилот", "ADR-010"),
        "pilot_stores": P(5, "магазинов", "Пилотных магазинов (переход в последний месяц разработки)", "ADR-010"),
        "rollout_months": P(6, "мес.", "Тираж остальных магазинов", "ADR-010"),
        "horizon_months": P(36, "мес.", "Горизонт расчёта", "постановка Task4"),
    },
    "Ставки ФОТ (с взносами и накладными)": {
        "engineer_cost_year": P(1_900_000, "руб./год", "Инженер поддержки L2 (оклад ~120 тыс./мес.)"),
        "dev_cost_year": P(4_200_000, "руб./год", "Разработчик / инженер продукта (оклад ~270 тыс./мес.)"),
        "working_days_year": P(247, "дней", "Рабочих дней в году", "производственный календарь"),
        "merch_hour": P(1_100, "руб./ч", "Час товароведа"),
    },
    "As-Is: магазин": {
        "server_price": P(250_000, "руб.", "Сервер в подсобке (RAID, 2 диска)"),
        "ups_price": P(25_000, "руб.", "ИБП сервера"),
        "pc_price": P(90_000, "руб./касса", "POS-моноблок толстого клиента"),
        "hw_cycle_years": P(5, "лет", "Цикл обновления серверов и ПК (равномерно по парку)"),
        "server_license_year": P(75_000, "руб./год", "Windows Server + SQL Server (продление через партнёров)", "описание кейса, оценка"),
        "pos_os_year": P(5_000, "руб./касса/год", "ОС кассового ПК"),
        "antivirus_year": P(3_000, "руб./устройство/год", "Антивирус (сервер и кассовые ПК)"),
        "integration_year": P(3_000, "руб./магазин/год", "Доля центрального обмена (FTP, XML-пакеты ERP)", "Артефакт 2, оценка"),
        "stores_per_engineer_asis": P(25, "магазинов", "Магазинов на одного инженера Store Ops (легаси)", "описание кейса, оценка"),
        "legacy_dev_fte": P(6, "FTE", "Команда толстого клиента на всю сеть", "INC-8415, оценка"),
        "visits_asis": P(4, "выездов/магазин/год", "Плановые и аварийные выезды инженера"),
        "visit_cost": P(15_000, "руб./выезд", "Выезд инженера (день работы + транспорт)"),
        "server_failure_rate": P(0.10, "доля/год", "Вероятность отказа сервера за год", "INC-8433, оценка"),
        "incident_cost": P(45_000, "руб./инцидент", "Простой 6 ч (упущенная маржа) + аварийный выезд", "INC-8433, оценка"),
        "wired_month": P(3_000, "руб./мес.", "Проводной интернет магазина"),
    },
    "To-Be: магазин": {
        "tablet_kit": P(40_000, "руб./касса", "Android-планшет + подставка и USB-хаб", "ADR-007, оценка"),
        "spare_share": P(0.05, "доля", "Подменный фонд планшетов", "Task1 9.3, оценка"),
        "router_lte": P(15_000, "руб./магазин", "Роутер с резервным LTE", "Task1 9.1, оценка"),
        "kkt_replace_share": P(0.30, "доля касс", "Нестандартные ККТ под замену на АТОЛ / Штрих-М", "ADR-007, оценка"),
        "kkt_price": P(32_000, "руб./ККТ", "ККТ АТОЛ / Штрих-М"),
        "kkt_registration": P(3_000, "руб./ККТ", "Перерегистрация ККТ в ФНС"),
        "tablet_failure_rate": P(0.05, "доля/год", "Отказы планшетов (замена из подменного фонда)"),
        "courier_cost": P(1_500, "руб./замена", "Доставка подменного планшета курьером"),
        "mdm_year": P(2_500, "руб./планшет/год", "MDM + защита (Kaspersky / SafePhone)", "Task1 5.3, оценка"),
        "cloud_per_store_month": P(600, "руб./магазин/мес.", "Переменная часть Yandex Cloud (вычисления, БД, трафик)"),
        "stores_per_engineer_tobe": P(100, "магазинов", "Магазинов на одного инженера (стандартный стек, MDM)"),
        "visits_tobe": P(1, "выезд/магазин/год", "Выезды (ККТ, сеть)"),
        "downtime_tobe_year": P(1_000, "руб./магазин/год", "Остаточные потери от сбоев (вторая касса, LTE, офлайн)", "ADR-008, оценка"),
        "lte_month": P(800, "руб./мес.", "Резервный LTE-канал"),
        "migration_services": P(35_000, "руб./магазин", "Монтаж (25 тыс.), обучение (5 тыс.), вывод сервера (5 тыс.)"),
    },
    "To-Be: платформа (вся сеть)": {
        "dev_fte": P(14, "FTE", "Команда Cloud POS, Edge Agent / HAL, Payment Gateway", "ADR-006, ADR-007, оценка"),
        "sku_fte": P(5, "FTE", "Команда SKU Matching и оркестратора онбординга", "Task2, оценка"),
        "external_capex": P(5_000_000, "руб.", "SDK вендоров, сертификация плагинов, пентест"),
        "dev_cost_multiplier": P(1.0, "×", "Множитель бюджета разработки (чувствительность)"),
        "product_fte": P(8, "FTE", "Продуктовая команда POS после запуска", "ADR-006, оценка"),
        "cloud_fixed_month": P(450_000, "руб./мес.", "Фиксированная часть Yandex Cloud: Managed K8s, PostgreSQL, Kafka, окружения"),
        "cloud_fixed_dev_share": P(0.5, "доля", "Фиксированная часть облака в период разработки (dev / stage)"),
        "cloud_cost_multiplier": P(1.0, "×", "Множитель цен облака (чувствительность)"),
    },
    "Общие для обоих сценариев": {
        "ofd_year": P(3_000, "руб./касса/год", "ОФД", "Task1 1.3, оценка"),
        "fn_price": P(9_000, "руб.", "Фискальный накопитель"),
        "fn_months": P(15, "мес.", "Срок ФН"),
        "terminal_rent_month": P(1_000, "руб./касса/мес.", "Аренда банковского терминала"),
        "loyalty_year": P(15_000, "руб./магазин/год", "SaaS-лояльность (Manzana / Mindbox)", "Task1 2.1, оценка"),
    },
    "Онбординг купленных магазинов": {
        "acquisitions_month": P(10, "магазинов/мес.", "Поток M&A по сети", "Артефакт 4"),
        "brigade_engineers": P(2, "чел.", "As-Is: ИТ-бригада на выезде", "описание кейса, оценка"),
        "brigade_days": P(5, "дней", "As-Is: длительность выезда"),
        "per_diem": P(5_000, "руб./чел./день", "As-Is: суточные и гостиница"),
        "travel": P(15_000, "руб./чел.", "As-Is: дорога в регион и обратно"),
        "merch_hours_asis": P(24, "ч", "As-Is: товаровед, 16 ч маппинга + 8 ч исправления ошибок", "Task2 G14-G15"),
        "install_visit": P(25_000, "руб.", "To-Be: монтаж комплекта (1 день)", "Task2 ADR-004, оценка"),
        "merch_hours_tobe": P(5, "ч", "To-Be: товаровед на проверку AI-маппинга", "Task2"),
    },
    "Финансы": {
        "discount_rate": P(0.20, "в год", "Ставка дисконтирования для NPV", "ADR-010"),
    },
}

CATEGORIES = [
    ("hw", "Оборудование (CapEx)"),
    ("dev", "Разработка платформы (CapEx)"),
    ("migr", "Миграция магазинов (разово)"),
    ("lic", "Лицензии и подписки (OpEx)"),
    ("cloud", "Облачная инфраструктура (OpEx)"),
    ("staff", "ФОТ поддержки и разработки"),
    ("field", "Выезды и простои"),
    ("net", "Каналы связи"),
    ("common", "Общие: ОФД, ФН, терминалы, лояльность"),
    ("onb", "Онбординг купленных (24 магазина/год)"),
]

SCENARIOS: dict[str, tuple[str, dict[str, float]]] = {
    "base": ("Базовый", {}),
    "full-capex": ("Все затраты платформы — на 100 магазинов", {"platform_allocation": 1.0}),
    "cloud+30": ("Облако +30%", {"cloud_cost_multiplier": 1.3}),
    "cloud-30": ("Облако −30%", {"cloud_cost_multiplier": 0.7}),
    "dev+50": ("Бюджет разработки +50%", {"dev_cost_multiplier": 1.5}),
    "slow-rollout": ("Тираж 12 мес. вместо 6", {"rollout_months": 12}),
    "asis-lean": ("As-Is: 1 инженер на 40 магазинов", {"stores_per_engineer_asis": 40}),
}


def values(overrides: dict[str, float] | None = None) -> dict[str, float]:
    v = {k: p.value for group in PARAMS.values() for k, p in group.items()}
    for k, x in (overrides or {}).items():
        if k not in v:
            raise KeyError(f"неизвестный параметр: {k}")
        v[k] = x
    return v


def zero() -> dict[str, float]:
    return {k: 0.0 for k, _ in CATEGORIES}


def common_store_month(v):
    r = v["registers_per_store"]
    return r * (v["ofd_year"] / 12 + v["fn_price"] / v["fn_months"] + v["terminal_rent_month"]) + v["loyalty_year"] / 12


def asis_store_month(v):
    r = v["registers_per_store"]
    c = zero()
    c["hw"] = (v["server_price"] + v["ups_price"] + r * v["pc_price"]) / v["hw_cycle_years"] / 12
    c["lic"] = (v["server_license_year"] + r * v["pos_os_year"] + (1 + r) * v["antivirus_year"]) / 12
    c["cloud"] = v["integration_year"] / 12
    c["staff"] = (
        v["engineer_cost_year"] / v["stores_per_engineer_asis"]
        + v["legacy_dev_fte"] * v["dev_cost_year"] / v["network_stores"]
    ) / 12
    c["field"] = (v["visits_asis"] * v["visit_cost"] + v["server_failure_rate"] * v["incident_cost"]) / 12
    c["net"] = v["wired_month"]
    c["common"] = common_store_month(v)
    return c


def tobe_store_month(v):
    r = v["registers_per_store"]
    c = zero()
    c["hw"] = r * v["tablet_failure_rate"] * v["tablet_kit"] / 12
    c["lic"] = r * v["mdm_year"] / 12
    c["cloud"] = v["cloud_per_store_month"] * v["cloud_cost_multiplier"]
    c["staff"] = v["engineer_cost_year"] / v["stores_per_engineer_tobe"] / 12
    c["field"] = (
        v["visits_tobe"] * v["visit_cost"]
        + r * v["tablet_failure_rate"] * v["courier_cost"]
        + v["downtime_tobe_year"]
    ) / 12
    c["net"] = v["wired_month"] + v["lte_month"]
    c["common"] = common_store_month(v)
    return c


def kit_hw(v):
    r = v["registers_per_store"]
    return (
        r * v["tablet_kit"] * (1 + v["spare_share"])
        + v["router_lte"]
        + r * v["kkt_replace_share"] * (v["kkt_price"] + v["kkt_registration"])
    )


def dev_capex_total(v):
    team = (v["dev_fte"] + v["sku_fte"]) * v["dev_cost_year"] * v["dev_months"] / 12
    return (team + v["external_capex"]) * v["dev_cost_multiplier"]


def onboarding_cost(v):
    engineer_day = v["engineer_cost_year"] / v["working_days_year"]
    asis = (
        v["brigade_engineers"] * v["brigade_days"] * (engineer_day + v["per_diem"])
        + v["brigade_engineers"] * v["travel"]
        + v["merch_hours_asis"] * v["merch_hour"]
    )
    tobe = v["install_visit"] + v["merch_hours_tobe"] * v["merch_hour"]
    return asis, tobe


def migrations(v, m):
    pilot, dev = v["pilot_stores"], v["dev_months"]
    if m == dev:
        return pilot
    if dev < m <= dev + v["rollout_months"]:
        return (v["stores"] - pilot) / v["rollout_months"]
    return 0.0


def add(dst, src, k=1.0):
    for key, x in src.items():
        dst[key] += x * k


@dataclass
class Result:
    v: dict[str, float]
    asis: list[dict[str, float]]
    tobe: list[dict[str, float]]
    invest: float

    @property
    def months(self):
        return len(self.asis)

    def total(self, series, months=None):
        rng = months or range(self.months)
        return sum(sum(series[i].values()) for i in rng)

    def year(self, series, y, cat=None):
        rng = range(12 * (y - 1), 12 * y)
        if cat:
            return sum(series[i][cat] for i in rng)
        return self.total(series, rng)

    def diffs(self):
        return [sum(a.values()) - sum(t.values()) for a, t in zip(self.asis, self.tobe)]

    def break_even(self, discounted=False):
        rm = (1 + self.v["discount_rate"]) ** (1 / 12) - 1
        cum, prev = 0.0, 0.0
        flows = self.diffs()
        for i, d in enumerate(flows, start=1):
            if discounted:
                d /= (1 + rm) ** i
            prev, cum = cum, cum + d
            if cum >= 0 and prev < 0:
                return i - 1 + (-prev) / (cum - prev), False
        tail = sum(flows[-12:]) / 12
        if cum < 0 and tail > 0:
            return self.months + (-cum) / tail, True
        return None, True

    def npv(self):
        rm = (1 + self.v["discount_rate"]) ** (1 / 12) - 1
        return sum(d / (1 + rm) ** i for i, d in enumerate(self.diffs(), start=1))

    def roi(self):
        return (self.total(self.asis) - self.total(self.tobe)) / self.invest


def simulate(v) -> Result:
    n = int(v["horizon_months"])
    alloc = v["platform_allocation"]
    asis_unit, tobe_unit = asis_store_month(v), tobe_store_month(v)
    onb_asis, onb_tobe = onboarding_cost(v)
    onb_per_month = v["acquisitions_month"] * v["stores"] / v["network_stores"]
    dev_month = dev_capex_total(v) * alloc / v["dev_months"]
    kit = kit_hw(v)

    asis, tobe, invest, migrated = [], [], 0.0, 0.0
    for m in range(1, n + 1):
        a = zero()
        add(a, asis_unit, v["stores"])
        a["onb"] = onb_per_month * onb_asis
        asis.append(a)

        new = migrations(v, m)
        t = zero()
        add(t, asis_unit, v["stores"] - migrated)
        migrated += new
        add(t, tobe_unit, migrated)
        t["hw"] += new * kit
        t["migr"] += new * v["migration_services"]
        invest += new * (kit + v["migration_services"])
        if m <= v["dev_months"]:
            t["dev"] += dev_month
            invest += dev_month
            fixed_share = v["cloud_fixed_dev_share"]
        else:
            t["staff"] += v["product_fte"] * v["dev_cost_year"] / 12 * alloc
            fixed_share = 1.0
        t["cloud"] += v["cloud_fixed_month"] * fixed_share * v["cloud_cost_multiplier"] * alloc
        t["onb"] = onb_per_month * (onb_asis if m <= v["dev_months"] else onb_tobe)
        tobe.append(t)
    return Result(v, asis, tobe, invest)


def min_network_size(v) -> float | None:
    """Размер сети, при котором доля платформы даёт нулевую экономию за горизонт."""

    def saving(alloc):
        r = simulate({**v, "platform_allocation": alloc})
        return r.total(r.asis) - r.total(r.tobe)

    lo, hi = 1e-6, 1.0
    if saving(hi) >= 0:
        return v["stores"]
    if saving(lo) <= 0:
        return None
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if saving(mid) > 0 else (lo, mid)
    return v["stores"] / lo


# ---------- форматирование ----------

def mln(x):
    return f"{x / 1e6:.1f}".replace(".", ",").replace("-", "−")


def rub(x):
    return f"{x:,.0f}".replace(",", " ").replace("-", "−")


def pct(x):
    return f"{x * 100:+.0f}%".replace("-", "−")


def num(x):
    if float(x).is_integer():
        return rub(x)
    return f"{x:g}".replace(".", ",")


def roi_text(r: Result):
    return f"{r.roi() * 100:.0f}%".replace("-", "−")


def months_text(be):
    m, extrapolated = be
    if m is None:
        return "не окупается"
    text = f"{m:.1f}".replace(".", ",") + " мес."
    return f"≈ {text} (экстраполяция)" if extrapolated else text


def per_store_y3(r: Result, series, cats):
    return sum(r.year(series, 3, c) for c in cats) / r.v["stores"]


def md_tables(r: Result) -> str:
    out = []
    years = (1, 2, 3)
    out.append("### Таблица TCO, млн руб. без НДС\n")
    out.append("| Статья | As-Is Г1 | As-Is Г2 | As-Is Г3 | **As-Is Σ** | To-Be Г1 | To-Be Г2 | To-Be Г3 | **To-Be Σ** | Δ Σ |")
    out.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for key, title in CATEGORIES:
        a = [r.year(r.asis, y, key) for y in years]
        t = [r.year(r.tobe, y, key) for y in years]
        out.append(
            f"| {title} | " + " | ".join(mln(x) for x in a) + f" | **{mln(sum(a))}** | "
            + " | ".join(mln(x) for x in t) + f" | **{mln(sum(t))}** | {mln(sum(t) - sum(a))} |"
        )
    a = [r.year(r.asis, y) for y in years]
    t = [r.year(r.tobe, y) for y in years]
    out.append(
        "| **Итого** | " + " | ".join(f"**{mln(x)}**" for x in a) + f" | **{mln(sum(a))}** | "
        + " | ".join(f"**{mln(x)}**" for x in t) + f" | **{mln(sum(t))}** | **{mln(sum(t) - sum(a))}** |"
    )
    out.append("\nΔ — To-Be минус As-Is: отрицательное значение — экономия.\n")

    out.append("### Итог по годам, млн руб.\n")
    out.append("| Показатель | Год 1 | Год 2 | Год 3 | Σ 3 года |")
    out.append("| --- | ---: | ---: | ---: | ---: |")
    saving = [x - y for x, y in zip(a, t)]
    cum, acc = [], 0.0
    for s in saving:
        acc += s
        cum.append(acc)
    out.append("| TCO As-Is | " + " | ".join(mln(x) for x in a) + f" | {mln(sum(a))} |")
    out.append("| TCO To-Be | " + " | ".join(mln(x) for x in t) + f" | {mln(sum(t))} |")
    out.append("| Экономия (As-Is − To-Be) | " + " | ".join(mln(x) for x in saving) + f" | {mln(sum(saving))} |")
    out.append("| Накопленная экономия | " + " | ".join(mln(x) for x in cum) + " | — |")

    out.append("\n### Финансовые показатели\n")
    out.append("| Показатель | Значение |")
    out.append("| --- | ---: |")
    out.append(f"| Разовые инвестиции To-Be (доля разработки, комплекты, миграция) | {mln(r.invest)} млн руб. |")
    out.append(f"| Экономия за 3 года | {mln(sum(saving))} млн руб. |")
    out.append(f"| Снижение TCO за 3 года | {pct(sum(t) / sum(a) - 1)} |")
    out.append(f"| ROI за 3 года (экономия / инвестиции) | {roi_text(r)} |")
    out.append(f"| NPV экономии при {r.v['discount_rate'] * 100:.0f}% годовых | {mln(r.npv())} млн руб. |")
    out.append(f"| Точка безубыточности (от старта проекта) | {months_text(r.break_even())} |")
    out.append(f"| Дисконтированный срок окупаемости | {months_text(r.break_even(discounted=True))} |")
    size = min_network_size(r.v)
    size_text = "не достигается" if size is None else f"{rub(size)} магазинов"
    out.append(f"| Минимальный размер сети, при котором платформа окупается за 3 года | {size_text} |")

    store_cats = [k for k, _ in CATEGORIES if k != "onb"]
    no_common = [k for k in store_cats if k != "common"]
    support = ["staff", "field"]
    out.append("\n### Проверка цели кейса: установившийся год (Год 3) на один магазин, руб./год\n")
    out.append("| Срез | As-Is | To-Be | Изменение |")
    out.append("| --- | ---: | ---: | ---: |")
    for title, cats in (
        ("TCO магазина (без онбординга)", store_cats),
        ("TCO магазина без общих сервисов (ОФД, ФН, терминалы, лояльность)", no_common),
        ("ИТ-поддержка: ФОТ поддержки и разработки, выезды и простои", support),
    ):
        x, y = per_store_y3(r, r.asis, cats), per_store_y3(r, r.tobe, cats)
        out.append(f"| {title} | {rub(x)} | {rub(y)} | {pct(y / x - 1)} |")
    return "\n".join(out)


def md_sensitivity() -> str:
    out = ["### Анализ чувствительности\n"]
    out.append("| Сценарий | TCO As-Is, млн | TCO To-Be, млн | Экономия, млн | ROI | NPV, млн | Безубыточность | Δ TCO магазина, Г3 |")
    out.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    store_cats = [k for k, _ in CATEGORIES if k != "onb"]
    for key, (title, overrides) in SCENARIOS.items():
        r = simulate(values(overrides))
        a, t = r.total(r.asis), r.total(r.tobe)
        y3 = per_store_y3(r, r.tobe, store_cats) / per_store_y3(r, r.asis, store_cats) - 1
        out.append(
            f"| {title} (`{key}`) | {mln(a)} | {mln(t)} | {mln(a - t)} | {roi_text(r)} | "
            f"{mln(r.npv())} | {months_text(r.break_even())} | {pct(y3)} |"
        )
    return "\n".join(out)


def md_params() -> str:
    out = ["### Реестр допущений\n", "Генерируется из `PARAMS` в [tco_model.py](tco_model.py). «Оценка» — учебная экспертная цена ([ADR-009](adr/ADR-009-training-price-assumptions.md)).\n"]
    out.append("| Параметр | Значение | Единица | Источник |")
    out.append("| --- | ---: | --- | --- |")
    for group, items in PARAMS.items():
        out.append(f"| **{group}** | | | |")
        for p in items.values():
            out.append(f"| {p.title} | {num(p.value)} | {p.unit} | {p.source} |")
    v = values()
    asis_onb, tobe_onb = onboarding_cost(v)
    out.append("\nПроизводные величины базового сценария:\n")
    out.append(f"- Разработка платформы на всю сеть: {mln(dev_capex_total(v))} млн руб., доля периметра — {mln(dev_capex_total(v) * v['platform_allocation'])} млн руб.")
    out.append(f"- Комплект To-Be на магазин: {rub(kit_hw(v))} руб. оборудования + {rub(v['migration_services'])} руб. услуг миграции.")
    out.append(f"- Онбординг одного купленного магазина: As-Is {rub(asis_onb)} руб., To-Be {rub(tobe_onb)} руб.")
    out.append(f"- Месячные затраты магазина: As-Is {rub(sum(asis_store_month(v).values()))} руб., To-Be {rub(sum(tobe_store_month(v).values()))} руб. (без общих затрат платформы).")
    return "\n".join(out)


def svg_chart(r: Result) -> str:
    w, h, left, right, top, bottom = 900, 460, 80, 30, 50, 60
    cum_a, cum_t, sa, st = [0.0], [0.0], 0.0, 0.0
    for a, t in zip(r.asis, r.tobe):
        sa += sum(a.values())
        st += sum(t.values())
        cum_a.append(sa / 1e6)
        cum_t.append(st / 1e6)
    n = r.months
    ymax = max(cum_a[-1], cum_t[-1])
    step = 20 if ymax > 100 else 10
    ymax = (int(ymax / step) + 1) * step

    def x(m):
        return left + (w - left - right) * m / n

    def y(val):
        return h - bottom - (h - top - bottom) * val / ymax

    def line(series, color):
        pts = " ".join(f"{x(i):.1f},{y(val):.1f}" for i, val in enumerate(series))
        return f'<polyline fill="none" stroke="{color}" stroke-width="3" points="{pts}"/>'

    s = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" font-family="Segoe UI, Arial, sans-serif" font-size="13">',
        f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
        f'<text x="{w / 2}" y="28" text-anchor="middle" font-size="17" font-weight="bold">Накопленные затраты, 100 магазинов, млн руб. без НДС</text>',
    ]
    for val in range(0, int(ymax) + 1, step):
        s.append(f'<line x1="{left}" y1="{y(val):.1f}" x2="{w - right}" y2="{y(val):.1f}" stroke="#e5e5e5"/>')
        s.append(f'<text x="{left - 8}" y="{y(val) + 4:.1f}" text-anchor="end" fill="#555">{val}</text>')
    for m in range(0, n + 1, 6):
        s.append(f'<line x1="{x(m):.1f}" y1="{top}" x2="{x(m):.1f}" y2="{h - bottom}" stroke="{"#bbbbbb" if m % 12 == 0 else "#f0f0f0"}"/>')
        s.append(f'<text x="{x(m):.1f}" y="{h - bottom + 18}" text-anchor="middle" fill="#555">{m}</text>')
    s.append(f'<text x="{(left + w - right) / 2}" y="{h - 18}" text-anchor="middle" fill="#333">Месяц от старта проекта</text>')
    dev = r.v["dev_months"]
    roll_end = dev + r.v["rollout_months"]
    s.append(f'<rect x="{x(0):.1f}" y="{top}" width="{x(dev) - x(0):.1f}" height="{h - top - bottom}" fill="#fff4e0" opacity="0.6"/>')
    s.append(f'<rect x="{x(dev):.1f}" y="{top}" width="{x(roll_end) - x(dev):.1f}" height="{h - top - bottom}" fill="#e8f2ff" opacity="0.6"/>')
    s.append(f'<text x="{(x(0) + x(dev)) / 2:.1f}" y="{top + 16}" text-anchor="middle" fill="#a06000">разработка, пилот</text>')
    s.append(f'<text x="{(x(dev) + x(roll_end)) / 2:.1f}" y="{top + 16}" text-anchor="middle" fill="#2060a0">тираж</text>')
    s.append(line(cum_a, "#c0392b"))
    s.append(line(cum_t, "#1e8449"))
    be, extrapolated = r.break_even()
    if be is not None and not extrapolated:
        i = int(be)
        frac = be - i
        val = cum_a[i] + (cum_a[i + 1] - cum_a[i]) * frac
        s.append(f'<line x1="{x(be):.1f}" y1="{top}" x2="{x(be):.1f}" y2="{h - bottom}" stroke="#333" stroke-dasharray="6,4"/>')
        s.append(f'<circle cx="{x(be):.1f}" cy="{y(val):.1f}" r="6" fill="#333"/>')
        label = "Безубыточность: " + f"{be:.1f}".replace(".", ",") + " мес."
        s.append(f'<text x="{x(be) + 12:.1f}" y="{y(val) + 26:.1f}" font-weight="bold">{label}</text>')
    lx, ly = left + 20, top + 40
    s.append(f'<line x1="{lx}" y1="{ly}" x2="{lx + 30}" y2="{ly}" stroke="#c0392b" stroke-width="3"/>')
    s.append(f'<text x="{lx + 38}" y="{ly + 4}">As-Is: {mln(cum_a[-1] * 1e6)} млн за 3 года</text>')
    s.append(f'<line x1="{lx}" y1="{ly + 22}" x2="{lx + 30}" y2="{ly + 22}" stroke="#1e8449" stroke-width="3"/>')
    s.append(f'<text x="{lx + 38}" y="{ly + 26}">To-Be: {mln(cum_t[-1] * 1e6)} млн за 3 года</text>')
    s.append(f'<line x1="{left}" y1="{h - bottom}" x2="{w - right}" y2="{h - bottom}" stroke="#333"/>')
    s.append(f'<line x1="{left}" y1="{top}" x2="{left}" y2="{h - bottom}" stroke="#333"/>')
    s.append("</svg>")
    return "\n".join(s) + "\n"


def summary(key: str) -> str:
    title, overrides = SCENARIOS[key]
    r = simulate(values(overrides))
    return f"## Сценарий: {title} (`{key}`)\n\n{md_tables(r)}\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--scenario", choices=SCENARIOS, help="вывести сценарий в консоль, файлы не менять")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    if args.scenario:
        print(summary(args.scenario))
        return 0

    r = simulate(values())
    block = "\n\n".join([md_params(), md_tables(r), md_sensitivity()])
    text = ANALYSIS_MD.read_text(encoding="utf-8")
    start, end = text.find(BEGIN), text.find(END)
    if start < 0 or end < start:
        print(f"нет маркеров {BEGIN} / {END} в {ANALYSIS_MD.name}", file=sys.stderr)
        return 1
    text = text[: start + len(BEGIN)] + "\n\n" + block + "\n\n" + text[end:]
    ANALYSIS_MD.write_text(text, encoding="utf-8", newline="\n")
    CHART_SVG.write_text(svg_chart(r), encoding="utf-8", newline="\n")
    print(f"обновлены {ANALYSIS_MD.name}, {CHART_SVG.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
