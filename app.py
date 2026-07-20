"""
MiPower Case Editor - Streamlit UI
-----------------------------------
Reads a MiPower input.dat0 file, shows each internal table (Bus Data,
Transmission Line, Generator Data, Common Control Options, ...) as an
editable spreadsheet, and auto-generates a modify.txt in the exact
format VIA_main.py already expects.

Run with:  streamlit run app.py
"""

import os
import streamlit as st
import pandas as pd

st.set_page_config(page_title="MiPower Case Editor", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=Manrope:wght@700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}

.block-container {padding-top: 1.4rem; padding-bottom: 3rem; max-width: 1220px;}

/* ---------- Base typography ---------- */
h1, h2, h3 {
    font-family: 'Manrope', 'Inter', sans-serif !important;
    letter-spacing: -0.02em !important;
    color: #1E1B4B !important;
}
p, span, label, div { color: #1F2937; }
.stCaption, [data-testid="stCaptionContainer"] {
    font-size: 0.88rem !important;
    color: #64748B !important;
}
strong, b { color: #1E1B4B; font-weight: 800; }
code { color: #7C3AED; background: #F3F0FF; padding: 0.1rem 0.35rem; border-radius: 5px; font-weight: 600; }

/* ---------- Header banner ---------- */
.mce-header {
    background: linear-gradient(120deg, #3730A3 0%, #6D28D9 50%, #A21CAF 100%);
    padding: 1.8rem 2.1rem;
    border-radius: 18px;
    margin-bottom: 1.6rem;
    box-shadow: 0 10px 32px rgba(76, 29, 149, 0.35), 0 2px 8px rgba(76, 29, 149, 0.25);
    border: 1px solid rgba(255,255,255,0.12);
}
.mce-header h1 {
    color: white !important;
    font-family: 'Manrope', sans-serif !important;
    font-size: 2.1rem !important;
    font-weight: 900 !important;
    margin: 0 !important;
    letter-spacing: -0.03em;
    text-shadow: 0 2px 10px rgba(0,0,0,0.15);
}
.mce-header p {
    color: #EDE9FE;
    margin: 0.45rem 0 0 0;
    font-size: 1.02rem;
    font-weight: 500;
}

/* ---------- Section labels (used throughout as bold colored headers) ---------- */
.mce-section-label {
    font-family: 'Manrope', sans-serif;
    font-weight: 800;
    font-size: 1.15rem;
    color: #3730A3;
    margin: 1.1rem 0 0.55rem 0;
    padding-bottom: 0.35rem;
    border-bottom: 3px solid #E0E7FF;
    letter-spacing: -0.01em;
}
.mce-modify-label {
    font-family: 'Manrope', sans-serif;
    font-weight: 800;
    color: #3730A3;
    margin: 0.9rem 0 0.5rem 0;
    font-size: 1.08rem;
    letter-spacing: -0.01em;
}

/* ---------- Tabs ---------- */
button[data-baseweb="tab"] {
    font-weight: 700;
    font-size: 0.98rem;
    border-radius: 10px 10px 0 0 !important;
    padding: 0.6rem 1.3rem !important;
    color: #64748B !important;
}
button[data-baseweb="tab"][aria-selected="true"] {
    background: linear-gradient(180deg, #EEF2FF 0%, #E0E7FF 100%) !important;
    color: #3730A3 !important;
    font-weight: 800 !important;
    box-shadow: inset 0 -3px 0 #4338CA;
}
div[data-baseweb="tab-list"] {
    gap: 6px;
    border-bottom: 3px solid #E2E8F0;
}

/* ---------- Cards / containers ---------- */
div[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 14px !important;
    border: 1px solid #E2E8F0 !important;
    box-shadow: 0 2px 10px rgba(30, 27, 75, 0.06);
    padding: 0.2rem 0.2rem;
}

/* ---------- Metrics ---------- */
div[data-testid="stMetric"] {
    background: linear-gradient(160deg, #FAFAFF 0%, #F3F0FF 100%);
    border: 1.5px solid #DDD6FE;
    border-radius: 12px;
    padding: 0.85rem 1rem;
    box-shadow: 0 2px 8px rgba(76, 29, 149, 0.06);
}
div[data-testid="stMetricValue"] {
    color: #4338CA;
    font-weight: 900 !important;
    font-size: 1.7rem !important;
    font-family: 'Manrope', sans-serif;
}
div[data-testid="stMetricLabel"] {
    font-weight: 700 !important;
    color: #6D28D9 !important;
    font-size: 0.82rem !important;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}

/* ---------- Buttons ---------- */
.stButton > button, .stDownloadButton > button {
    border-radius: 9px;
    font-weight: 700;
    border: 1.5px solid #E2E8F0;
    transition: all 0.15s ease;
}
.stButton > button:hover, .stDownloadButton > button:hover {
    border-color: #A5B4FC;
    box-shadow: 0 2px 8px rgba(76, 29, 149, 0.15);
}
.stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"] {
    background: linear-gradient(120deg, #4338CA, #9333EA);
    border: none;
    font-weight: 800;
    box-shadow: 0 4px 14px rgba(76, 29, 149, 0.3);
}
.stButton > button[kind="primary"]:hover, .stDownloadButton > button[kind="primary"]:hover {
    box-shadow: 0 6px 20px rgba(76, 29, 149, 0.4);
    transform: translateY(-1px);
}

/* ---------- Inputs / selects ---------- */
.stTextInput input, .stSelectbox div[data-baseweb="select"] > div, .stTextArea textarea {
    border-radius: 9px !important;
    border: 1.5px solid #E2E8F0 !important;
    font-weight: 500;
}
.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: #818CF8 !important;
    box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.15) !important;
}

/* ---------- Sidebar ---------- */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #F8FAFC 0%, #F1F0FF 100%);
    border-right: 1px solid #E2E8F0;
}
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2 {
    color: #3730A3 !important;
    font-family: 'Manrope', sans-serif !important;
    font-size: 1.2rem !important;
    font-weight: 800 !important;
}

/* ---------- Combined export header ---------- */
.mce-export-header {
    background: linear-gradient(120deg, #047857 0%, #0D9488 55%, #0891B2 100%);
    color: white;
    padding: 1.15rem 1.6rem;
    border-radius: 16px;
    font-family: 'Manrope', sans-serif;
    font-weight: 900;
    font-size: 1.4rem;
    letter-spacing: -0.02em;
    margin-bottom: 1rem;
    box-shadow: 0 8px 26px rgba(6, 95, 70, 0.3);
    border: 1px solid rgba(255,255,255,0.12);
}

/* ---------- Footer ---------- */
.mce-footer {
    text-align: center;
    color: #94A3B8;
    font-size: 0.82rem;
    font-weight: 500;
    margin-top: 2rem;
    padding-top: 1.2rem;
    border-top: 2px solid #E2E8F0;
}

/* ---------- Code blocks / tables ---------- */
.stCodeBlock, pre {
    border-radius: 12px !important;
    border: 1px solid #E2E8F0 !important;
}
div[data-testid="stDataFrame"], div[data-testid="stDataEditor"] {
    border-radius: 12px;
    overflow: hidden;
    border: 1.5px solid #E2E8F0;
}

/* ---------- Dividers ---------- */
hr {
    border-top: 2px solid #E2E8F0 !important;
    margin: 1.6rem 0 !important;
}

/* ---------- Expanders ---------- */
details[data-testid="stExpander"] {
    border-radius: 12px !important;
    border: 1.5px solid #E2E8F0 !important;
}
summary {
    font-weight: 700 !important;
    color: #3730A3 !important;
}
</style>
""", unsafe_allow_html=True)

# =====================================================================
# 1. Low-level .dat0 parsing (mirrors VIA_main.py's own logic, so a
#    row identified here will always be found correctly by the real
#    modifyInput() when modify.txt is applied).
# =====================================================================

def load_lines(text: str):
    return text.replace('\r\n', '\n').split('\n')


def find_section(lines, section_name):
    """Exact match on a %... / %%... header line, same rule VIA_main.py uses."""
    target = section_name.strip().lower()
    for i, line in enumerate(lines):
        s = line.strip()
        if not s.startswith('%'):
            continue
        if s.lstrip('%').strip().lower() == target:
            return i
    return -1


def is_number(tok):
    try:
        float(tok)
        return True
    except ValueError:
        return False


def extract_numeric_tokens(line):
    return [t for t in line.split() if is_number(t)]


def parse_table_section(lines, section_name, columns):
    loc = find_section(lines, section_name)
    if loc == -1:
        return None
    i = loc + 1
    while i < len(lines):
        s = lines[i].strip()
        if not s or s.startswith('%'):
            i += 1
            continue
        break
    rows = []
    j = i
    while j < len(lines):
        s = lines[j].strip()
        if s.startswith('%'):
            break
        if s:
            tokens = s.split()
            if len(tokens) > len(columns):
                tokens = tokens[:len(columns) - 1] + [' '.join(tokens[len(columns) - 1:])]
            while len(tokens) < len(columns):
                tokens.append('')
            rows.append(tokens)
        j += 1
    return pd.DataFrame(rows, columns=columns)


def parse_two_row_table_section(lines, section_name, columns_row1, columns_row2):
    """
    Handles the %%%% two_row_table layout: each logical record spans TWO
    physical data lines (e.g. Generator Frequency Characteristics: FromBus/
    Rating/.../BiasSet on line 1, C0/C1/C2 on line 2 directly below it).
    """
    loc = find_section(lines, section_name)
    if loc == -1:
        return None
    i = loc + 1
    while i < len(lines):
        s = lines[i].strip()
        if not s or s.startswith('%'):
            i += 1
            continue
        break

    def fit(tokens, cols):
        tokens = list(tokens)
        if len(tokens) > len(cols):
            tokens = tokens[:len(cols)]
        while len(tokens) < len(cols):
            tokens.append('')
        return tokens

    rows = []
    j = i
    while j < len(lines):
        s1 = lines[j].strip()
        if s1.startswith('%'):
            break
        if not s1:
            j += 1
            continue
        tok1 = s1.split()
        k = j + 1
        while k < len(lines) and not lines[k].strip():
            k += 1
        if k >= len(lines) or lines[k].strip().startswith('%'):
            tok2 = []
            j = k
        else:
            tok2 = lines[k].strip().split()
            j = k + 1
        rows.append(fit(tok1, columns_row1) + fit(tok2, columns_row2))
    return pd.DataFrame(rows, columns=columns_row1 + columns_row2)


def parse_keyvalue_section(lines, section_name, labels, zero_fill=False):
    """
    Returns fields in TRUE global order (position 1..N across every data
    line in the section). This is the index _apply_subsection_mod() in
    VIA_main.py actually uses, regardless of how the file's own comments
    re-number things locally - so writing modify.txt with this index is
    always correct.

    zero_fill: when a section exists only as comment lines with no actual
    data row in this case file (e.g. an unused "Source Details" block),
    display every field as "0" instead of blank, so the table still reads
    cleanly and consistently with sections that do carry real data.
    """
    loc = find_section(lines, section_name)
    if loc == -1:
        if zero_fill:
            return pd.DataFrame(
                [{"field": f"{idx + 1}.{label}", "value": "0"} for idx, label in enumerate(labels)]
            )
        return None
    # Skip past ANY mix of blank lines and '%' comment lines - a blank line
    # can appear in the middle of a multi-line comment block (e.g. Common
    # Control Options, System Specification), so we can't stop at the
    # first blank line the way a naive "while starts with %" loop would.
    # However, if a '%' line is itself the header of a DIFFERENT known
    # section (e.g. Source Details has no data rows at all, and the very
    # next thing in the file is "%Sink Details"), we must stop there - not
    # skip through it - or values would be misattributed to the wrong
    # section entirely (Source Details would silently show Sink Details'
    # numbers instead of "no data").
    other_section_names = {
        c["section"].strip().lower()
        for c in TABLE_CONFIG.values()
        if c["section"].strip().lower() != section_name.strip().lower()
    } | {s.strip().lower() for s in RAW_SECTIONS if s.strip().lower() != section_name.strip().lower()}
    i = loc + 1
    hit_boundary = False
    while i < len(lines):
        s = lines[i].strip()
        if not s:
            i += 1
            continue
        if s.startswith('%'):
            if s.lstrip('%').strip().lower() in other_section_names:
                hit_boundary = True
                break
            i += 1
            continue
        break
    if hit_boundary:
        if zero_fill:
            return pd.DataFrame(
                [{"field": f"{idx + 1}.{label}", "value": "0"} for idx, label in enumerate(labels)]
            )
        return pd.DataFrame(
            [{"field": f"{idx + 1}.{label}", "value": ""} for idx, label in enumerate(labels)]
        )
    # Collect numeric values across every data line in the section. Some
    # sections (Common Control Options is the clearest example) split their
    # fields across TWO data lines with a comment block sitting in between
    # (base 15 fields, then a "%1.Q-Checking Limit..." comment, then 8 more
    # fields) - so we must skip PAST an embedded comment line and keep
    # collecting, only stopping once we reach a real section boundary (the
    # start of a different section) or run out of lines.
    values = []
    j = i
    while j < len(lines):
        s = lines[j].strip()
        if s.startswith('%'):
            if s.lstrip('%').strip().lower() in other_section_names:
                break
            j += 1
            continue
        if s:
            values.extend(extract_numeric_tokens(s))
        j += 1
    out = []
    for idx, label in enumerate(labels):
        if idx < len(values):
            val = values[idx]
        else:
            val = "0" if zero_fill else ""
        out.append({"field": f"{idx + 1}.{label}", "value": val})
    return pd.DataFrame(out)


def parse_simple_section(lines, section_name):
    loc = find_section(lines, section_name)
    if loc == -1:
        return None
    i = loc + 1
    while i < len(lines):
        s = lines[i].strip()
        if s and not s.startswith('%'):
            return s
        if s.startswith('%'):
            return None
        i += 1
    return None


def parse_raw_section(lines, section_name):
    loc = find_section(lines, section_name)
    if loc == -1:
        return None
    all_section_names = [c["section"] for c in TABLE_CONFIG.values()] + RAW_SECTIONS
    j = loc + 1
    out = []
    while j < len(lines):
        s = lines[j]
        stripped = s.strip()
        if stripped.startswith('%'):
            candidate = stripped.lstrip('%').strip()
            if any(candidate.lower() == sec.lower() for sec in all_section_names):
                break
        out.append(s)
        j += 1
    return '\n'.join(out).strip('\n')


# =====================================================================
# 2. Table registry - matches the 15 tables in the sketch.
#    Edit "editable" lists here to change which columns/fields a user
#    is allowed to touch.
# =====================================================================

TABLE_CONFIG = {
    "System Specification": {
        "kind": "keyvalue",
        "section": "First Power System Network",
        "labels": [
            "MaxBusID", "TotalBuses", "Total2Wdg", "Total3Wdg", "TotalLines",
            "TotalSeReac", "TotalSeCap", "TotalBusCoupler", "TotalShRea", "TotalShCap",
            "TotalMotor", "TotalGen+WindGen", "TotalLoad", "TotalLdChar", "TotalFreqRelay",
            "TotalGenCap", "TotalFilter", "TotalTieLines", "TotalHVDC", "TotalDCLinks",
            "TotalSFD", "FeedCurrent", "TotalTCSC", "TotalSPS", "TotalUPFC",
            "TotalDetailedWndGen", "NoOfWTCurves", "NoOfDetailedCurves",
            "NoOfSolarPVPlants", "TotalSynchronousMotor",
        ],
        "editable": [],
        # The file's own comment wording doesn't always match our clean label
        # names 1:1 (missing periods, extra spaces, different casing) - these
        # are the exact substrings VIA_main.py would need to locate each
        # field if it's ever made editable. Kept here even though nothing in
        # this table is editable yet, so turning one on later is a 1-line
        # change instead of a silent modify.txt bug.
        "field_overrides": {
            "TotalSFD": "21 TotalSFD",
            "FeedCurrent": "22: FeedCurrent",
            "TotalTCSC": "23. Total TCSC",
            "TotalSPS": "24. Total SPS",
            "TotalUPFC": "25. Total UPFC",
            "NoOfWTCurves": "27.No.ofWTCurves",
            "NoOfDetailedCurves": "28.No.ofDetailedCurves",
            "NoOfSolarPVPlants": "29.No.ofSolarPVPlants",
            "TotalSynchronousMotor": "30.Total SynchronousMotor",
        },
    },
    "Common Control Options": {
        "kind": "keyvalue",
        "section": "Common Control Options",
        "labels": [
            "LFAOption", "NumberOfZones", "PrintOption", "PlotOption",
            "FrequencyDependentLFA", "BaseMVA", "NominalFrequency", "FrequencyDeviation",
            "FlowTypeOption", "SlackBusID", "TapChangeOption", "ATC", "NoOfAreas",
            "NoOfSubsystems", "ScalingFactorType", "QCheckingLimit", "PTolerance",
            "QTolerance", "MaximumIterations", "LoadModelVoltage", "CBResistance",
            "CBReactance", "TransformerRXratio",
        ],
        "editable": [
            "PrintOption", "SlackBusID", "BaseMVA", "NominalFrequency",
        ],
        # Exact file wording for fields where it differs from our clean label
        # (a missing space breaks VIA_main.py's literal substring search -
        # this is what caused "Subsection '3.PrintOption' not found" and
        # "'6.BaseMVA' not found" warnings when applying a real modify.txt).
        "field_overrides": {
            "NumberOfZones": "2.Number Of Zones",
            "PrintOption": "3.Print Option",
            "PlotOption": "4.Plot Option",
            "FrequencyDependentLFA": "5.Frequency Dependent LFA",
            "BaseMVA": "6.Base MVA",
            "NominalFrequency": "7.Nominal Frequency",
            "FrequencyDeviation": "8.Frequency Deviation",
            "FlowTypeOption": "9.Flow Type Option",
            "SlackBusID": "10.Slack Bus ID",
            "TapChangeOption": "11.Tap Change Option",
            "NoOfAreas": "13.No of Areas",
            "NoOfSubsystems": "14.No of Subsystems",
            "ScalingFactorType": "15.Scaling factor type",
        },
        # NOTE: QCheckingLimit, PTolerance, QTolerance, MaximumIterations,
        # LoadModelVoltage, CBResistance, CBReactance, TransformerRXratio
        # sit past a comment block, AND the file re-numbers them 1-8 locally
        # (not 16-23), so even a text-matching override can't fix them - the
        # anchor VIA_main.py finds would still compute the wrong target index
        # from that local "1." prefix. They stay excluded from "editable"
        # until that's fixed in the engine itself, so this UI never generates
        # a modify.txt entry that would silently apply to the wrong field.
    },
    "Cost Factors": {
        "kind": "keyvalue",
        "section": "Cost Factors",
        "labels": [
            "InterestCharges", "OperationalCharges", "LifeOfEquipment",
            "EnergyCharges", "LossLoadFactor", "CostPerMvar",
        ],
        "editable": ["InterestCharges", "OperationalCharges", "CostPerMvar"],
        "field_overrides": {
            "InterestCharges": "1. Interest Charges",
            "OperationalCharges": "2. Operational Charges",
            "LifeOfEquipment": "3. Life of Equipment",
            "EnergyCharges": "4. Energy Charges",
            "LossLoadFactor": "5. Loss Load Factor",
            "CostPerMvar": "6. Cost per Mvar",
        },
    },
    "Zone Multiplication Factors": {
        "kind": "table",
        "section": "Zone wise Multiplication Factors",
        "columns": ["ZoneNumber", "PLoad", "QLoad", "PGen", "QGen", "ShRea", "ShCap", "CLoad"],
        "key_columns": ["ZoneNumber"],
        "editable": ["PLoad", "QLoad", "PGen", "QGen"],
    },
    "Area Numbers": {
        "kind": "table",
        "section": "Area Numbers",
        "columns": ["AreaNo"],
        "key_columns": ["AreaNo"],
        "editable": [],
    },
    "Bus Data": {
        "kind": "table",
        "section": "Bus Data",
        "columns": ["Bus_ID", "AreaNo", "ZoneNo", "SubsystemNo", "BasekV",
                    "MinVolt(pu)", "MaxVolt(pu)", "BusName"],
        "key_columns": ["Bus_ID"],
        "editable": ["MinVolt(pu)", "MaxVolt(pu)", "BasekV"],
    },
    "Transmission Line": {
        "kind": "table",
        "section": "Transmission Line",
        "columns": ["Status", "NoOfCkts", "FromBus", "ToBus", "R", "X", "B/2", "MVA", "kMs"],
        "key_columns": ["FromBus", "ToBus"],
        "editable": ["Status", "R", "X", "MVA"],
    },
    "Generator Data": {
        "kind": "table",
        "section": "Generator Data",
        "columns": ["Bus", "SchMW", "MinMvar", "MaxMvar", "SpecVoltage(pu)",
                    "CapCurveNo", "MVA", "Status", "Type"],
        "key_columns": ["Bus"],
        "editable": ["SchMW", "MinMvar", "MaxMvar", "SpecVoltage(pu)", "Status"],
    },
    "LOAD DATA": {
        "kind": "table",
        "section": "LOAD DATA",
        "columns": ["FromBus", "LoadMW", "LoadMvar", "CompMVAR", "MinCompMVAR",
                    "MaxCompMVAR", "CompStep", "LoadCharRefNo", "FreqRelayId",
                    "Status", "VoltRelayId", "Scalability"],
        "key_columns": ["FromBus"],
        "editable": ["LoadMW", "LoadMvar", "Status"],
    },
    "GENERATOR FREQUENCY CHARACTERISTICS": {
        "kind": "two_row_table",
        "section": "GENERATOR FREQUENCY CHARACTERISTICS",
        "columns_row1": ["FromBus", "Rating", "MinRat", "MaxRat", "%Droop", "PartFactor", "BiasSet"],
        "columns_row2": ["C0", "C1", "C2"],
        "key_columns": ["FromBus"],
        "editable": ["Rating", "MaxRat", "%Droop", "PartFactor", "C0", "C1", "C2"],
    },
    "Slack Bus Angle": {
        "kind": "simple",
        "section": "Slack Bus Angle",
        "editable": True,
    },
    "Source Details": {
        "kind": "keyvalue",
        "section": "Source Details",
        "labels": [
            "Area/Bus Number/Zone", "Option(1-Generation Increment)",
            "Incdec Loc(1-All Buses,2-selected Buses)",
            "Load Increment percent(1-equal/2-Unequal)",
            "%Contribution total change", "LoadBus/GenBusCount",
            "BusNumber", "Increment",
        ],
        # This case file has no actual Source Details data rows - only the
        # column/format comments are present in the .dat0 - so every field
        # is shown blank rather than a fabricated value. Read-only: with no
        # data row for VIA_main.py's _apply_subsection_mod() to locate,
        # any "edit" here couldn't be written back to the file, so this
        # table is display-only until a case with real source data exists.
        "editable": [],
        "zero_fill": False,
    },
    "Sink Details": {
        "kind": "keyvalue",
        "section": "Sink Details",
        "labels": [
            "Area/Bus Number/Zone", "Option(2-Load Increment)",
            "Load Increment percent(1-equal/2-Unequal)",
            "Incdec Loc(1-All Buses,2-selected Buses)",
            "Type (0 Collapse point,1 User specified)",
            "LoadType(0 ConstP, 1 ConstQ, 2 UserDefPQ, 3 UserDefPF, 4 Const PF)",
            "LoadBus/GenBusCount", "BusNumber", "Increment",
            "Min Real Power in MW", "Max Real Power in MW",
            "Real Power Step in MW", "Min Reactive power in MVAR",
            "Max Reactive Power in MVAR", "Reactive Power Step in MVAR",
        ],
        # Only the first 6 fields sit on the file's own "1.Area/Bus Number...
        # 6.LoadType..." numbered comment line, so only those resolve to a
        # real position for VIA_main.py's _apply_subsection_mod(). The rest
        # (BusNumber/Increment/MW/MVAR fields) live under their own
        # restart-numbered sub-headers and are shown read-only below, same
        # pattern already used for Common Control Options.
        "editable": [
            "Area/Bus Number/Zone", "Option(2-Load Increment)",
            "Load Increment percent(1-equal/2-Unequal)",
            "Incdec Loc(1-All Buses,2-selected Buses)",
            "Type (0 Collapse point,1 User specified)",
            "LoadType(0 ConstP, 1 ConstQ, 2 UserDefPQ, 3 UserDefPF, 4 Const PF)",
        ],
    },
}

# Single source of truth for display order + numbering (1-15, matching the
# sketch). Every entry here is either a key in TABLE_CONFIG (fully wired
# for editing) or a raw section name shown read-only. Numbering is derived
# purely from this list's order, so it can never collide again.
TABLE_ORDER = [
    "System Specification",
    "Common Control Options",
    "Cost Factors",
    "Zone Multiplication Factors",
    "Area Numbers",
    "Bus Data",
    "Transmission Line",
    "Generator Data",
    "LOAD DATA",
    "GENERATOR FREQUENCY CHARACTERISTICS",
    "Slack Bus Angle",
    "Source Details",
    "Sink Details",
    "Buses of interest",
    "Series elements of interest",
]

RAW_SECTIONS = [
    "LOAD DATA",
    "GENERATOR FREQUENCY CHARACTERISTICS",
    "Source Details",
    "Sink Details",
    "Buses of interest",
    "Series elements of interest",
]


# =====================================================================
# 3. modify.txt generation
#    Key includes the ROW-identifying conditions, not just the column
#    name - so editing row A then row B creates TWO entries, while
#    editing the SAME row/column twice just updates that one entry.
# =====================================================================

def mod_key_for_table(section, column, key_columns, row_values):
    cond_str = "|".join(f"{k}={row_values[k]}" for k in key_columns)
    return ("table", section, column, cond_str)


def mod_key_for_keyvalue(section, field):
    return ("keyvalue", section, field)


def mod_key_for_simple(section):
    return ("simple", section)


def append_mod(case_key, mod_key, block_text):
    st.session_state.cases[case_key]["mods"][mod_key] = block_text


def remove_mod(case_key, mod_key):
    st.session_state.cases[case_key]["mods"].pop(mod_key, None)


def build_modify_txt(case_key):
    mods = st.session_state.cases[case_key]["mods"]
    body = "\n\n".join(mods.values())
    return (body + "\n\n&compare&\n") if body else "&compare&\n"


def build_combined_modify_txt():
    """
    Single modify.txt covering every case study, in one file. Each case's
    edits sit under a plain '%'-comment banner (harmless to VIA_main.py's
    parser - it just becomes an inert section name that consumes no data
    line), so the file stays readable and organized per case. Exactly ONE
    '&compare&' terminator sits at the very end, since VIA_main.py stops
    reading the moment it hits the first one.
    """
    sections = []
    for case_name, case in st.session_state.cases.items():
        mods = case["mods"]
        if not mods:
            continue
        banner = f"%===== {case_name} ====="
        sections.append(banner + "\n\n" + "\n\n".join(mods.values()))
    body = "\n\n".join(sections)
    return (body + "\n\n&compare&\n") if body else "&compare&\n"


def mod_summary_rows(case_key):
    """Human-readable breakdown of every pending modification, for the
    friendly editable list (as opposed to the raw modify.txt text)."""
    rows = []
    for mod_key, block in st.session_state.cases[case_key]["mods"].items():
        kind = mod_key[0]
        section = mod_key[1]
        lines_ = block.split("\n")
        field_line = lines_[1] if len(lines_) > 1 else ""
        if "=" in field_line:
            field, rest = field_line.split("=", 1)
            if "->" in rest:
                new_val, cond = rest.split("->", 1)
            else:
                new_val, cond = rest, ""
            field, new_val, cond = field.strip(), new_val.strip(), cond.strip()
        else:
            field, new_val, cond = field_line.strip(), "", ""
        rows.append({
            "key": mod_key, "table": section, "field": field,
            "new_value": new_val, "condition": cond, "kind": kind,
        })
    return rows


def case_stats(case_key):
    mods = st.session_state.cases[case_key]["mods"]
    tables_touched = len({m[1] for m in mods.keys()})
    return len(mods), tables_touched


# =====================================================================
# 4. Streamlit state + UI
# =====================================================================

if "cases" not in st.session_state:
    st.session_state.cases = {"Case Study 1": {"mods": {}}}

st.markdown(
    '<div class="mce-header"><h1>MiPower Case Editor</h1>'
    '<p>Browse input.dat0 tables, edit permitted fields, and auto-build modify.txt</p></div>',
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Input file")
    default_folder = r"C:\Users\internstudent2\Desktop\Project\VIA"
    folder = st.text_input("Folder containing input.dat0", value=default_folder)

    raw_text = None
    chosen_path = None
    if os.path.isdir(folder):
        dat_files = sorted(
            f for f in os.listdir(folder)
            if f.lower().endswith(('.dat0', '.dat'))
        )
        if dat_files:
            picked = st.selectbox("Select file", dat_files)
            chosen_path = os.path.join(folder, picked)
        else:
            st.warning("No .dat0 files found in that folder.")
    else:
        st.caption("Folder not found on this machine yet - "
                    "you can also upload a file directly below.")

    uploaded = st.file_uploader("...or upload input.dat0 directly", type=None)

    if uploaded is not None:
        raw_text = uploaded.read().decode("utf-8", errors="ignore")
        st.session_state["raw_text"] = raw_text
    elif chosen_path and st.button("Load selected file", use_container_width=True):
        with open(chosen_path, "r", newline="") as f:
            st.session_state["raw_text"] = f.read()
        st.session_state["loaded_path"] = chosen_path

    raw_text = st.session_state.get("raw_text")
    if st.session_state.get("loaded_path"):
        st.caption(f"Loaded: {st.session_state['loaded_path']}")

    st.divider()
    total_mods = sum(len(c["mods"]) for c in st.session_state.cases.values())
    total_tables = len({m[1] for c in st.session_state.cases.values() for m in c["mods"].keys()})
    st.markdown(
        f'''<div style="display:flex;gap:8px;">
        <div style="flex:1;background:#EEF2FF;border-radius:10px;padding:10px;text-align:center;">
            <div style="font-size:1.4rem;font-weight:700;color:#4338CA;">{len(st.session_state.cases)}</div>
            <div style="font-size:0.75rem;color:#64748B;">Case studies</div>
        </div>
        <div style="flex:1;background:#ECFDF5;border-radius:10px;padding:10px;text-align:center;">
            <div style="font-size:1.4rem;font-weight:700;color:#059669;">{total_mods}</div>
            <div style="font-size:0.75rem;color:#64748B;">Total edits</div>
        </div>
        <div style="flex:1;background:#FEF3C7;border-radius:10px;padding:10px;text-align:center;">
            <div style="font-size:1.4rem;font-weight:700;color:#B45309;">{total_tables}</div>
            <div style="font-size:0.75rem;color:#64748B;">Tables touched</div>
        </div>
        </div>''',
        unsafe_allow_html=True,
    )

    st.divider()
    st.header("Add case study")
    new_case_name = st.text_input("New case study name", value="", placeholder="e.g. Case Study 2")
    if st.button("+ Add blank case study", use_container_width=True):
        name = new_case_name.strip() or f"Case Study {len(st.session_state.cases) + 1}"
        if name not in st.session_state.cases:
            st.session_state.cases[name] = {"mods": {}}
        st.rerun()

    dup_src = st.selectbox("Duplicate from", list(st.session_state.cases.keys()), key="dup_src_select")
    if st.button("⧉ Duplicate this case", use_container_width=True):
        name = new_case_name.strip() or f"{dup_src} (copy)"
        if name not in st.session_state.cases:
            st.session_state.cases[name] = {
                "mods": dict(st.session_state.cases[dup_src]["mods"])
            }
        st.rerun()

    with st.expander("Manage case studies"):
        for cname in list(st.session_state.cases.keys()):
            n_mods, n_tables = case_stats(cname)
            cc1, cc2 = st.columns([3, 1])
            cc1.markdown(f"**{cname}** &nbsp;·&nbsp; {n_mods} edits")
            if len(st.session_state.cases) > 1:
                if cc2.button("🗑️", key=f"delcase_{cname}", help=f"Delete {cname}"):
                    del st.session_state.cases[cname]
                    st.rerun()

if not raw_text:
    st.info("Load an input.dat0 file from the sidebar to begin.")
    st.stop()

lines = load_lines(raw_text)

# ---- one real Streamlit tab per case study - fully isolated state ----
case_names = list(st.session_state.cases.keys())
tabs = st.tabs(case_names)

table_options = [f"{i}. {name}" for i, name in enumerate(TABLE_ORDER, start=1)]

for tab, case_name in zip(tabs, case_names):
    with tab:
        n_mods, n_tables = case_stats(case_name)
        m1, m2, m3 = st.columns(3)
        m1.metric("Edits in this case", n_mods)
        m2.metric("Tables touched", n_tables)
        m3.metric("Total tables available", len(TABLE_ORDER))

        table_name = st.selectbox(
            "Power System Tables", table_options, key=f"table_select_{case_name}"
        )
        plain_name = table_name.split('. ', 1)[1] if '. ' in table_name else table_name
        cfg = TABLE_CONFIG.get(plain_name)

        if cfg is not None:
            has_editable = bool(cfg.get("editable"))
            badge = (
                '<span style="background:#DCFCE7;color:#166534;padding:2px 10px;'
                'border-radius:12px;font-size:0.8rem;font-weight:600;">✏️ Editable</span>'
                if has_editable else
                '<span style="background:#F1F5F9;color:#475569;padding:2px 10px;'
                'border-radius:12px;font-size:0.8rem;font-weight:600;">🔒 Read-only</span>'
            )
        else:
            badge = (
                '<span style="background:#FEF3C7;color:#92400E;padding:2px 10px;'
                'border-radius:12px;font-size:0.8rem;font-weight:600;">🚧 Not wired up yet</span>'
            )
        st.markdown(badge, unsafe_allow_html=True)
        st.caption(
            "✏️ To edit: **double-click** a cell in a column marked with the pencil icon "
            "(only editable columns have one), type the new value, then press **Enter** "
            "or click outside the cell. Locked columns (no pencil icon) can't be typed into."
        )
        st.write("")

        if cfg is not None and cfg["kind"] == "table":
            df = parse_table_section(lines, cfg["section"], cfg["columns"])
            if df is None:
                st.caption(f"Section '{cfg['section']}' not found in this file.")
            else:
                with st.container(border=True):
                    st.markdown(f"**{cfg['section']}**")
                    if len(df) > 5:
                        query = st.text_input(
                            "🔍 Search rows", key=f"search_{case_name}_{table_name}",
                            placeholder="Filter by any value, e.g. a bus name or ID...",
                        )
                    else:
                        query = ""
                    if query:
                        mask = df.apply(
                            lambda row: query.lower() in " ".join(str(v) for v in row).lower(), axis=1
                        )
                        view_df = df[mask]
                        if view_df.empty:
                            st.caption("No rows match that search.")
                    else:
                        view_df = df
                    disabled_cols = [c for c in cfg["columns"] if c not in cfg["editable"]]
                    edited = st.data_editor(
                        view_df, key=f"editor_{case_name}_{table_name}",
                        disabled=disabled_cols, hide_index=True, use_container_width=True,
                    )
                    if cfg["editable"]:
                        st.caption(f"Editable columns: {', '.join(cfg['editable'])}")
                    else:
                        st.caption("This table has no editable columns configured.")

                changed = not edited.equals(view_df)
                if changed:
                    for ridx in view_df.index:
                        row_vals = df.loc[ridx]
                        for col in cfg["editable"]:
                            old_v, new_v = df.at[ridx, col], edited.at[ridx, col]
                            if str(old_v) != str(new_v):
                                cond_str = " -> ".join(
                                    f"{k}={row_vals[k]}" for k in cfg["key_columns"]
                                )
                                block = f"%%%{cfg['section']}\n{col} = {new_v} -> {cond_str}"
                                key = mod_key_for_table(cfg["section"], col, cfg["key_columns"], row_vals)
                                append_mod(case_name, key, block)
                    st.success("modify.txt updated below.", icon="✅")

        elif cfg is not None and cfg["kind"] == "two_row_table":
            columns = cfg["columns_row1"] + cfg["columns_row2"]
            df = parse_two_row_table_section(lines, cfg["section"], cfg["columns_row1"], cfg["columns_row2"])
            if df is None:
                st.caption(f"Section '{cfg['section']}' not found in this file.")
            else:
                with st.container(border=True):
                    st.markdown(f"**{cfg['section']}**")
                    st.caption(
                        f"Each row combines 2 physical lines in the file "
                        f"({', '.join(cfg['columns_row1'])} on line 1; "
                        f"{', '.join(cfg['columns_row2'])} on line 2)."
                    )
                    if len(df) > 5:
                        query2 = st.text_input(
                            "🔍 Search rows", key=f"search_{case_name}_{table_name}",
                            placeholder="Filter by any value...",
                        )
                    else:
                        query2 = ""
                    if query2:
                        mask2 = df.apply(
                            lambda row: query2.lower() in " ".join(str(v) for v in row).lower(), axis=1
                        )
                        view_df = df[mask2]
                    else:
                        view_df = df
                    disabled_cols = [c for c in columns if c not in cfg["editable"]]
                    edited = st.data_editor(
                        view_df, key=f"editor_{case_name}_{table_name}",
                        disabled=disabled_cols, hide_index=True, use_container_width=True,
                    )
                    if cfg["editable"]:
                        st.caption(f"Editable columns: {', '.join(cfg['editable'])}")

                changed = not edited.equals(view_df)
                if changed:
                    for ridx in view_df.index:
                        row_vals = df.loc[ridx]
                        for col in cfg["editable"]:
                            old_v, new_v = df.at[ridx, col], edited.at[ridx, col]
                            if str(old_v) != str(new_v):
                                cond_str = " -> ".join(
                                    f"{k}={row_vals[k]}" for k in cfg["key_columns"]
                                )
                                # bare field name -> VIA_main.py auto-detects which
                                # of the two physical rows it belongs to
                                block = f"%%%%{cfg['section']}\n{col} = {new_v} -> {cond_str}"
                                key = mod_key_for_table(cfg["section"], col, cfg["key_columns"], row_vals)
                                append_mod(case_name, key, block)
                    st.success("modify.txt updated below.", icon="✅")

        elif cfg is not None and cfg["kind"] == "keyvalue":
            df = parse_keyvalue_section(lines, cfg["section"], cfg["labels"], zero_fill=cfg.get("zero_fill", False))
            if df is None:
                st.caption(f"Section '{cfg['section']}' not found in this file.")
            else:
                editable_fields = set(cfg["editable"])
                df["label"] = df["field"].apply(lambda f: f.split('.', 1)[1])
                edit_df = df[df["label"].isin(editable_fields)][["field", "value"]].reset_index(drop=True)
                locked_df = df[~df["label"].isin(editable_fields)][["field", "value"]].reset_index(drop=True)

                edited = edit_df.copy()
                if not edit_df.empty:
                    with st.container(border=True):
                        st.markdown(f"**{cfg['section']} - editable**")
                        edited = st.data_editor(
                            edit_df, key=f"editor_{case_name}_{table_name}",
                            disabled=["field"], hide_index=True, use_container_width=True,
                        )
                else:
                    st.caption("No editable fields configured for this table.")

                with st.expander(f"Show all {cfg['section']} fields (read-only)"):
                    st.dataframe(locked_df, hide_index=True, use_container_width=True)

                if not edited.equals(edit_df):
                    overrides = cfg.get("field_overrides", {})
                    for ridx in range(len(edit_df)):
                        old_v, new_v = edit_df.at[ridx, "value"], edited.at[ridx, "value"]
                        field = edit_df.at[ridx, "field"]
                        if str(old_v) != str(new_v):
                            # The text written into modify.txt must be a literal
                            # substring of the file's own comment line, or
                            # VIA_main.py's _apply_subsection_mod() can't find it
                            # (e.g. our clean "3.PrintOption" label vs. the file's
                            # actual "3.Print Option" wording). field_overrides
                            # holds the exact wording per field where it differs.
                            label_only = field.split('.', 1)[1] if '.' in field else field
                            anchor = overrides.get(label_only, field)
                            block = f"%%{cfg['section']}\n{anchor} = {new_v}"
                            key = mod_key_for_keyvalue(cfg["section"], field)
                            append_mod(case_name, key, block)
                    st.success("modify.txt updated below.", icon="✅")

        elif cfg is not None and cfg["kind"] == "simple":
            val = parse_simple_section(lines, cfg["section"])
            if val is None:
                st.caption(f"Section '{cfg['section']}' not found in this file.")
            else:
                with st.container(border=True):
                    new_val = st.text_input(cfg["section"], value=val, key=f"simple_{case_name}_{table_name}")
                if new_val != val:
                    block = f"%{cfg['section']}\n{new_val}"
                    key = mod_key_for_simple(cfg["section"])
                    append_mod(case_name, key, block)
                    st.success("modify.txt updated below.", icon="✅")

        else:
            text = parse_raw_section(lines, plain_name)
            section_exists = find_section(lines, plain_name) != -1
            if section_exists and not text:
                st.caption(
                    "This case file has no data in this section — it only "
                    "defines the column layout, with no rows recorded."
                )
            else:
                st.caption("This table isn't wired up for editing yet - shown read-only. "
                           "Add it to TABLE_CONFIG using the same pattern as Bus Data.")
                st.code(text or "(section not found)", language="text")

        st.divider()
        st.markdown('<div class="mce-modify-label">📝 Pending modifications</div>', unsafe_allow_html=True)
        summary = mod_summary_rows(case_name)
        if not summary:
            st.caption("No edits yet in this case study - changes you make above will appear here.")
        else:
            for row in summary:
                rc1, rc2, rc3, rc4 = st.columns([2.2, 1.6, 1.6, 0.4])
                rc1.markdown(f"**{row['table']}**")
                rc2.markdown(f"`{row['field']}` → **{row['new_value']}**")
                rc3.caption(row["condition"] or "—")
                if rc4.button("✕", key=f"delmod_{case_name}_{hash(row['key'])}", help="Remove this edit"):
                    remove_mod(case_name, row["key"])
                    st.rerun()
            if st.button("🗑️ Reset all edits in this case", key=f"reset_{case_name}"):
                st.session_state.cases[case_name]["mods"] = {}
                st.rerun()

        st.markdown('<div class="mce-modify-label">📄 modify.txt preview for this case</div>', unsafe_allow_html=True)
        mod_text = build_modify_txt(case_name)
        st.code(mod_text, language="text")
        st.caption(
            "This preview is per case study. Scroll down to **📦 Combined Export** "
            "to download or save every case study's edits together in a single modify.txt file."
        )

st.divider()
st.markdown(
    '<div class="mce-export-header">📦 Combined Export — all case studies, one file</div>',
    unsafe_allow_html=True,
)

combined_mods = sum(len(c["mods"]) for c in st.session_state.cases.values())
non_empty_cases = [name for name, c in st.session_state.cases.items() if c["mods"]]

if combined_mods == 0:
    st.info("No edits yet in any case study. Once you edit a table above, its changes will "
            "appear here bundled into one modify.txt.")
else:
    st.caption(
        f"Bundling **{combined_mods}** edit(s) from **{len(non_empty_cases)}** case "
        f"stud{'y' if len(non_empty_cases) == 1 else 'ies'} "
        f"({', '.join(non_empty_cases)}) into a single file, each under its own "
        "labeled section, ending in one `&compare&` marker."
    )

combined_text = build_combined_modify_txt()
with st.expander("📄 Preview combined modify.txt", expanded=(combined_mods > 0)):
    st.code(combined_text, language="text")

ce1, ce2 = st.columns(2)
with ce1:
    st.download_button(
        "⬇️ Download combined modify.txt", combined_text, file_name="modify.txt",
        key="dl_combined", use_container_width=True, type="primary",
        disabled=(combined_mods == 0),
    )
with ce2:
    combined_save_path = st.text_input(
        "Save to local path", value="modify.txt", key="savepath_combined",
        label_visibility="collapsed", placeholder="Save to local path (e.g. modify.txt)",
    )
    if st.button("💾 Save to disk", key="save_combined", use_container_width=True,
                 disabled=(combined_mods == 0)):
        try:
            with open(combined_save_path, "w", newline="") as f:
                f.write(combined_text.replace("\n", "\r\n"))
            st.success(f"Saved combined modify.txt for all case studies to {combined_save_path}")
        except Exception as e:
            st.error(f"Could not save: {e}")

st.markdown(
    '<div class="mce-footer">MiPower Case Editor · built for VIA_main.py · '
    'edits are only written to disk when you click Save</div>',
    unsafe_allow_html=True,
)