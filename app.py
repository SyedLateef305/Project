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
.block-container {padding-top: 1.5rem; padding-bottom: 3rem;}

/* Header banner */
.mce-header {
    background: linear-gradient(90deg, #4F46E5 0%, #7C3AED 100%);
    padding: 1.1rem 1.5rem;
    border-radius: 12px;
    margin-bottom: 1.2rem;
}
.mce-header h1 {
    color: white !important;
    font-size: 1.6rem !important;
    margin: 0 !important;
}
.mce-header p {
    color: #E0E7FF;
    margin: 0.2rem 0 0 0;
    font-size: 0.9rem;
}

/* Tabs */
button[data-baseweb="tab"] {
    font-weight: 600;
    border-radius: 8px 8px 0 0 !important;
}
button[data-baseweb="tab"][aria-selected="true"] {
    background-color: #EEF2FF !important;
    color: #4F46E5 !important;
}

/* Cards */
div[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 10px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background-color: #F8FAFC;
}
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2 {
    color: #4F46E5;
    font-size: 1.15rem !important;
}

/* modify.txt code block */
.mce-modify-label {
    font-weight: 700;
    color: #4F46E5;
    margin-bottom: 0.3rem;
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


def parse_keyvalue_section(lines, section_name, labels):
    """
    Returns fields in TRUE global order (position 1..N across every data
    line in the section). This is the index _apply_subsection_mod() in
    VIA_main.py actually uses, regardless of how the file's own comments
    re-number things locally - so writing modify.txt with this index is
    always correct.
    """
    loc = find_section(lines, section_name)
    if loc == -1:
        return None
    # Skip past ANY mix of blank lines and '%' comment lines - a blank line
    # can appear in the middle of a multi-line comment block (e.g. Common
    # Control Options, System Specification), so we can't stop at the
    # first blank line the way a naive "while starts with %" loop would.
    i = loc + 1
    while i < len(lines):
        s = lines[i].strip()
        if not s or s.startswith('%'):
            i += 1
            continue
        break
    values = []
    j = i
    while j < len(lines):
        s = lines[j].strip()
        if s.startswith('%'):
            break
        if s:
            values.extend(extract_numeric_tokens(s))
        j += 1
    out = []
    for idx, label in enumerate(labels):
        val = values[idx] if idx < len(values) else ""
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
        # NOTE: QCheckingLimit, PTolerance, QTolerance, MaximumIterations,
        # LoadModelVoltage, CBResistance, CBReactance, TransformerRXratio
        # sit past a comment block that breaks VIA_main.py's own
        # extract_all_numeric_values() (it stops at the first '%' line).
        # They're excluded from "editable" until that's fixed in the
        # engine itself, so this UI never generates a modify.txt entry
        # that would silently fail to apply.
    },
    "Cost Factors": {
        "kind": "keyvalue",
        "section": "Cost Factors",
        "labels": [
            "InterestCharges", "OperationalCharges", "LifeOfEquipment",
            "EnergyCharges", "LossLoadFactor", "CostPerMvar",
        ],
        "editable": ["InterestCharges", "OperationalCharges", "CostPerMvar"],
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
            <div style="font-size:1.4rem;font-weight:700;color:#4F46E5;">{len(st.session_state.cases)}</div>
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
            df = parse_keyvalue_section(lines, cfg["section"], cfg["labels"])
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
                    for ridx in range(len(edit_df)):
                        old_v, new_v = edit_df.at[ridx, "value"], edited.at[ridx, "value"]
                        field = edit_df.at[ridx, "field"]
                        if str(old_v) != str(new_v):
                            block = f"%%{cfg['section']}\n{field} = {new_v}"
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

        st.markdown('<div class="mce-modify-label">📄 modify.txt preview</div>', unsafe_allow_html=True)
        mod_text = build_modify_txt(case_name)
        st.code(mod_text, language="text")

        c1, c2 = st.columns(2)
        with c1:
            st.download_button(
                "Download modify.txt", mod_text, file_name="modify.txt",
                key=f"dl_{case_name}", use_container_width=True,
            )
        with c2:
            save_path = st.text_input(
                "Save to local path", value="modify.txt", key=f"savepath_{case_name}"
            )
            if st.button("Save to disk", key=f"save_{case_name}", use_container_width=True):
                try:
                    with open(save_path, "w", newline="") as f:
                        f.write(mod_text.replace("\n", "\r\n"))
                    st.success(f"Saved to {save_path}")
                except Exception as e:
                    st.error(f"Could not save: {e}")