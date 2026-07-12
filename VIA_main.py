"""
VIA_main.py
A module for parsing and applying modifications to MIP (Model Input Parameters) data files
used in Voltage Instability Analysis (VIA) case files.
This module provides functionality to:
- Parse modification specifications from a modify.txt file supporting four format types
- Apply modifications to corresponding data files based on parsed specifications
- Handle simple value replacements, subsection modifications, tabular row updates, and two-row table modifications
Format Types:
    '%' (simple): Single section with a single value to replace
    '%%' (subsection): Section with named subsections and individual values
    '%%%' (tabular): Find and modify ALL rows matching specified conditions
    '%%%%' (two_row_table): Handle paired rows where conditions are checked on row 1 but modification can target row 1 or 2
The module integrates with MIPComp for post-processing comparison and generates unique output filenames
when conflicts exist.
Dependencies:
    - sys: System-specific parameters
    - os: Operating system interfaces
    - re: Regular expression operations
    - MIPComp: Custom module for output comparison

"""
import sys
import os
import re
# import MIPComp

def findFileCount(input_file):
    """
    Generates a unique output filename by appending a counter to the base name.
    Example: input.txt -> input_1.dat0, input_2.dat0, etc.
    """
    base_name = input_file.rsplit(".", 1)[0]
    count = 1
    while True:
        output_file = f"{base_name}_{count}.dat0"
        if not os.path.exists(output_file):
            break
        count += 1
    return output_file


def parse_modifications(mod_data):
    """
    Parse modifications from modify.txt with four formats:
    
    '%' - Simple format: Section with single value
    %Section_Name
    value
    
    '%%' - Subsection format: Section with subsections and values
    %%Section_Name
    subsection = new_value
    
    '%%%' - Tabular format: Find rows matching condition(s) and modify ALL matching rows
    %%%Section_Name
    column = new_value -> condition1 -> condition2 -> ...
    
    '%%%%' - Two-row table format: Handle paired rows (first row = main data, second row = control)
    %%%%Section_Name
    column = new_value -> condition1 -> condition2 -> ... -> row=1_or_2

    '&compare&' - Represents End of modifications marker
    """
    modifications = []
    lines = mod_data.split('\n')
    
    current_section = None
    format_type = None  # 'simple', 'subsection', 'tabular', 'two_row_table'
    
    for line in lines:
        line_stripped = line.strip()
        
        if not line_stripped:
            continue
        
        # End of modifications marker
        if line_stripped == "&compare&" :
            break
        
        # Check for section headers (check longer prefixes first)
        if line_stripped.startswith('%%%%'):
            current_section = line_stripped[4:].strip()
            format_type = 'two_row_table'
            continue
        elif line_stripped.startswith('%%%'):
            current_section = line_stripped[3:].strip()
            format_type = 'tabular'
            continue
        elif line_stripped.startswith('%%'):
            current_section = line_stripped[2:].strip()
            format_type = 'subsection'
            continue
        elif line_stripped.startswith('%'):
            current_section = line_stripped[1:].strip()
            format_type = 'simple'
            continue
        
        # Parse modification line
        if current_section:
            if format_type == 'simple':
                # Simple format: just value on next line
                new_value = line_stripped
                modifications.append({
                    'section': current_section,
                    'subsection1': None,
                    'new_value': new_value,
                    'format_type': 'simple'
                })
            
            elif format_type == 'subsection':
                # Subsection format: subsection = new_value
                if '=' in line_stripped:
                    subsection = line_stripped.split('=')[0].strip()
                    new_value = line_stripped.split('=')[1].strip()
                    
                    modifications.append({
                        'section': current_section,
                        'subsection1': subsection,
                        'new_value': new_value,
                        'format_type': 'subsection'
                    })
            
            elif format_type == 'tabular':
                # Tabular format: column = new_value -> condition1 -> condition2 -> ...
                if '->' in line_stripped:
                    parts = line_stripped.split('->')
                    assignment = parts[0].strip()
                    conditions = [cond.strip() for cond in parts[1:]]
                    
                    if '=' in assignment:
                        subsection = assignment.split('=')[0].strip()
                        new_value = assignment.split('=')[1].strip()
                        
                        modifications.append({
                            'section': current_section,
                            'subsection1': subsection,
                            'conditions': conditions,
                            'new_value': new_value,
                            'format_type': 'tabular'
                        })
            
            elif format_type == 'two_row_table':
                # Two-row table format: column = new_value -> condition1 -> ... -> row=1_or_2
                if '->' in line_stripped:
                    parts = line_stripped.split('->')
                    assignment = parts[0].strip()
                    conditions_and_row = [cond.strip() for cond in parts[1:]]
                    
                    if '=' in assignment:
                        subsection = assignment.split('=')[0].strip()
                        new_value = assignment.split('=')[1].strip()
                        
                        # Extract row number from last condition (format: row=1 or row=2)
                        target_row = None  # Will be auto-detected if not specified
                        conditions = []
                        for cond in conditions_and_row:
                            if cond.startswith('row='):
                                target_row = int(cond.split('=')[1])
                            else:
                                conditions.append(cond)
                        
                        modifications.append({
                            'section': current_section,
                            'subsection1': subsection,
                            'conditions': conditions,
                            'new_value': new_value,
                            'target_row': target_row,
                            'format_type': 'two_row_table'
                        })
    
    return modifications


def find_section(lines, section_name):
    """
    Find the starting line number of a section using an exact match.
    """

    target = section_name.strip().lower()

    for i, line in enumerate(lines):

        line = line.strip()

        if not line.startswith('%'):
            continue

        # Remove leading '%' characters
        section = line.lstrip('%').strip().lower()

        if section == target:
            return i

    return -1


def extract_numeric_values(line):
    """Extract a list of float values from a line, ignoring non-numeric tokens."""
    values = []
    tokens = line.split()
    for token in tokens:
        try:
            values.append(float(token))
        except ValueError:
            pass
    return values


def extract_all_numeric_values(lines, start_idx):
    """
    Extract all numeric values from multiple lines starting at start_idx 
    until a new section (starting with '%') is encountered.
    """
    all_values = []
    end_idx = start_idx
    
    for i in range(start_idx, len(lines)):
        line = lines[i].strip()
        if not line:
            continue
        if line.startswith('%'):
            end_idx = i
            break
        
        values = extract_numeric_values(line)
        if values:
            all_values.extend(values)
            end_idx = i
    
    return all_values, end_idx


def replace_value_in_line(line, idx, new_value):
    """Replace the Nth numeric value (idx) in a line with new_value, preserving whitespace."""
    values = re.split(r'(\s+)', line)
    numeric_positions = []
    
    for i, val in enumerate(values):
        try:
            float(val)
            numeric_positions.append(i)
        except ValueError:
            pass
    
    if idx < len(numeric_positions):
        values[numeric_positions[idx]] = str(new_value)
    
    return ''.join(values)


def _apply_simple_mod(lines, modified_lines, search_start, new_value):
    """
    Applies simple format modification: replaces the first numeric value found 
    in the data section.
    """
    data_start_idx = -1
    for i in range(search_start, len(lines)):
        line = lines[i].strip()
        if not line or line.startswith('%'):
            continue
        
        values = extract_numeric_values(line)
        if values:
            data_start_idx = i
            break
    
    if data_start_idx >= 0:
        modified_lines[data_start_idx] = replace_value_in_line(modified_lines[data_start_idx], 0, new_value)


def _apply_subsection_mod(lines, modified_lines, search_start, section, subsection_name, new_value):
    """
    Applies subsection modification.
    Finds the subsection, collects all numeric values, and updates the specific index
    indicated by the subsection name (e.g., '1.Name' -> index 0).
    """
    # Find subsection header
    subsection_line = -1
    for i in range(search_start, len(lines)):
        if lines[i].startswith('%') and subsection_name in lines[i]:
            subsection_line = i
            break
    
    if subsection_line == -1:
        print(f"Warning: Subsection '{subsection_name}' not found in section '{section}'")
        return
    
    search_start = subsection_line + 1
    
    # Find first data row
    data_start_idx = -1
    for i in range(search_start, len(lines)):
        line = lines[i].strip()
        if not line or line.startswith('%'):
            continue
        
        values = extract_numeric_values(line)
        if values:
            data_start_idx = i
            break
    
    if data_start_idx == -1:
        print(f"Warning: No data found for modification in section '{section}'")
        return
    
    # Extract all numeric values from multiple lines to find the target index
    all_values, end_idx = extract_all_numeric_values(lines, data_start_idx)
    
    if not all_values:
        print(f"Warning: No numeric values found after {section}")
        return
    
    # Determine target index from subsection_name (expects format like '1.Name')
    target_idx = -1
    match = re.match(r'^(\d+)', subsection_name)
    if match:
        target_idx = int(match.group(1)) - 1
    
    if target_idx >= 0 and target_idx < len(all_values):
        # Find which line contains the target value
        value_count = 0
        for i in range(data_start_idx, end_idx + 1):
            line = lines[i].strip()
            if not line or line.startswith('%'):
                continue
            
            line_values = extract_numeric_values(line)
            if value_count + len(line_values) > target_idx:
                local_idx = target_idx - value_count
                modified_lines[i] = replace_value_in_line(modified_lines[i], local_idx, new_value)
                break
            
            value_count += len(line_values)


def _numeric_word_position_map(line):
    """
    Map each whitespace-delimited token's word position in `line` to its
    position among only the numeric tokens in that line. Non-numeric tokens
    (e.g. a text field like BusName embedded between numeric columns) are
    skipped, so this lets a header word position be translated into the
    correct index for extract_numeric_values()/replace_value_in_line(),
    which only ever see the numeric tokens.
    """
    tokens = line.split()
    mapping = {}
    numeric_idx = 0
    for i, tok in enumerate(tokens):
        try:
            float(tok)
            mapping[i] = numeric_idx
            numeric_idx += 1
        except ValueError:
            pass
    return mapping


def _find_first_data_line(lines, start_idx):
    """Return the first non-blank, non-header line at/after start_idx, or None if a new section starts first."""
    for i in range(start_idx, len(lines)):
        line = lines[i].strip()
        if not line:
            continue
        if line.startswith('%'):
            return None
        if extract_numeric_values(line):
            return line
    return None


def _apply_tabular_mod(lines, modified_lines, search_start, section, column_name, new_value, conditions):
    """
    Applies tabular modification.
    Finds a column by name or index, checks row conditions, and updates matching rows.
    """
    # Find column header line
    column_line = -1

    for i in range(search_start, len(lines)):
        if lines[i].strip().startswith('%'):

            header = lines[i].lstrip('%').strip()

            # check whether requested column exists in this header
            header_parts = header.split()

            for part in header_parts:
                if part.lower() == column_name.lower():
                    column_line = i
                    break

            if column_line != -1:
                break
    
    if column_line == -1:
        print(f"Warning: Column '{column_name}' not found in section '{section}'")
        return

    # Sample data row used to translate header word positions into numeric
    # column positions (handles headers with embedded text fields like BusName)
    sample_line = _find_first_data_line(lines, column_line + 1)
    numeric_map = _numeric_word_position_map(sample_line) if sample_line else {}

    # Determine column index
    column_idx = -1
    match = re.match(r'^(\d+)', column_name)
    if match:
        column_idx = int(match.group(1)) - 1
    else:
        # Try to find by name in header line
        header_parts = lines[column_line].lstrip('%').split()
        field_name = column_name.split('.')[-1].lower()

        for idx, part in enumerate(header_parts):

            header_name = part.split('.')[-1].lower()

            if header_name == field_name:
                column_idx = numeric_map.get(idx, -1)
                break
    
    # Parse conditions
    parsed_conditions = {}
    header_parts = lines[column_line].lstrip('%').split()
    
    for condition in conditions:
        if '=' in condition:
            cond_field, cond_value = [x.strip() for x in condition.split('=', 1)]
            
            cond_idx = -1
            match = re.match(r'^(\d+)', cond_field)
            if match:
                cond_idx = int(match.group(1)) - 1
            else:
                field_name = cond_field.split('.')[-1].lower()

                for idx, part in enumerate(header_parts):

                    header_name = part.split('.')[-1].lower()

                    if header_name == field_name:
                        cond_idx = numeric_map.get(idx, -1)
                        break
            
            if cond_idx >= 0:
                parsed_conditions[cond_idx] = cond_value
    
    # Apply modifications to matching rows
    if column_idx >= 0:
        for i in range(column_line + 1, len(lines)):
            line = lines[i].strip()
            if not line:
                continue
            if line.startswith('%'):
                break
            
            line_values = extract_numeric_values(line)
            
            all_conditions_met = True

            for cond_idx, cond_value in parsed_conditions.items():

                if cond_idx < 0 or cond_idx >= len(line_values):
                    all_conditions_met = False
                    break

                try:
                    if abs(float(line_values[cond_idx]) - float(cond_value)) > 1e-6:
                        all_conditions_met = False
                        break

                except ValueError:
                    if str(line_values[cond_idx]) != cond_value:
                        all_conditions_met = False
                        break

            if all_conditions_met:
                modified_lines[i] = replace_value_in_line(
                    modified_lines[i],
                    column_idx,
                    new_value
                )


def _apply_two_row_table_mod(lines, modified_lines, search_start, section, column_name, new_value, conditions, target_row):
    """
    Applies two-row table modification.
    Handles paired rows where conditions are checked on the first row, 
    but modification can target row 1 or 2.
    """
    # Find all header lines
    header_lines = []
    for i in range(search_start, len(lines)):
        if lines[i].strip().startswith('%'):
            if '\t' in lines[i] or len(lines[i].split()) > 1:
                header_lines.append(i)
        elif not lines[i].strip():
            continue
        else:
            break
    
    if not header_lines:
        print(f"Warning: No data headers found in section '{section}'")
        return

    # Build a numeric-position map per header row, from that row's own
    # sample data (row 1 or row 2 of the first pair), so name-based lookups
    # land on the correct numeric column even when a header row has an
    # embedded text field (e.g. BusName among numeric columns).
    first_data_line = header_lines[-1] + 1
    sample_lines = []
    scan_idx = first_data_line
    for _ in range(len(header_lines)):
        s = _find_first_data_line(lines, scan_idx)
        sample_lines.append(s)
        if s is None:
            break
        # advance scan_idx past this sample line
        for j in range(scan_idx, len(lines)):
            if lines[j].strip() == s:
                scan_idx = j + 1
                break
    numeric_maps = [_numeric_word_position_map(s) if s else {} for s in sample_lines]
    while len(numeric_maps) < len(header_lines):
        numeric_maps.append({})

    # Determine column index and auto-detect target row if needed
    column_idx = -1
    auto_target_row = 1
    match = re.match(r'^(\d+)', column_name)
    if match:
        column_idx = int(match.group(1)) - 1
    else:
        field_name = column_name.split('.')[-1] if '.' in column_name else column_name
        for header_idx, header_line_num in enumerate(header_lines):
            header_parts = lines[header_line_num].lstrip('%').split()
            for idx, part in enumerate(header_parts):
                header_name = part.split('.')[-1].lower()
                if header_name == field_name.lower():
                    column_idx = numeric_maps[header_idx].get(idx, -1)
                    auto_target_row = header_idx + 1
                    break
            if column_idx >= 0:
                break
    
    if target_row is None:
        target_row = auto_target_row
    
    parsed_conditions = {}

    for condition in conditions:

        if '=' not in condition:
            continue

        cond_field, cond_value = [x.strip() for x in condition.split('=', 1)]

        cond_idx = -1

        # Numeric condition (1.BusId etc.)
        match = re.match(r'^(\d+)', cond_field)

        if match:
            cond_idx = int(match.group(1)) - 1

        else:
            field_name = cond_field.split('.')[-1] if '.' in cond_field else cond_field

            # Search ALL header lines (conditions are always checked
            # against row 1's data, so translate using row 1's numeric map)
            for header_line_num in header_lines:

                header_parts = lines[header_line_num].lstrip('%').split()

                for idx, part in enumerate(header_parts):

                    header_name = part.split('.')[-1].lower()
                    if header_name == field_name.lower():

                        cond_idx = numeric_maps[0].get(idx, -1)
                        break

                if cond_idx >= 0:
                    break

        if cond_idx >= 0:
            parsed_conditions[cond_idx] = cond_value
    
    if column_idx < 0:
        print(f"Warning: Column '{column_name}' not found in section '{section}'")
        return

    # Process row pairs
    first_data_line = header_lines[-1] + 1
    i = first_data_line
    while i < len(lines):
        line1 = lines[i].strip()
        
        if not line1 or line1.startswith('%'):
            i += 1
            if line1.startswith('%'):
                break
            continue
        
        line1_values = extract_numeric_values(line1)
        if not line1_values:
            i += 1
            continue
        
       # Find second row safely
        line2_idx = -1
        j = i + 1

        while j < len(lines):

            line2 = lines[j].strip()

            # skip blank lines
            if not line2:
                j += 1
                continue

            # stop at next section
            if line2.startswith('%'):
                break

            # ensure second row contains numeric data
            second_values = extract_numeric_values(line2)

            if second_values:
                line2_idx = j

            break
        
        # Check conditions on first row
        all_conditions_met = True

        for cond_idx, cond_value in parsed_conditions.items():

            if cond_idx < 0 or cond_idx >= len(line1_values):
                all_conditions_met = False
                break

            try:
                # Numeric comparison (supports integers and floating-point values)
                if abs(line1_values[cond_idx] - float(cond_value)) > 1e-9:
                    all_conditions_met = False
                    break

            except ValueError:
                # Fallback string comparison
                if str(line1_values[cond_idx]) != cond_value:
                    all_conditions_met = False
                    break
        
        if all_conditions_met:
            if target_row == 1:
                modified_lines[i] = replace_value_in_line(modified_lines[i], column_idx, new_value)
            elif target_row == 2 and line2_idx >= 0:
                modified_lines[line2_idx] = replace_value_in_line(modified_lines[line2_idx], column_idx, new_value)
        
        if line2_idx >= 0:
            i = line2_idx + 1
        else:
            i += 1


def modifyInput(data, modifications):
    """
    Apply modifications to data based on specifications.
    Iterates through modifications and delegates to specific format handlers.
    """
    lines = data.split('\n')
    modified_lines = lines.copy()
    
    for mod in modifications:
        section = mod['section']
        subsection_name = mod['subsection1']
        new_value = mod['new_value']
        format_type = mod['format_type']
        
        # Find section start
        section_line = find_section(lines, section)
        if section_line == -1:
            print(f"Warning: Section '{section}' not found")
            continue
        
        search_start = section_line + 1
        
        if format_type == 'simple':
            _apply_simple_mod(lines, modified_lines, search_start, new_value)
        
        elif format_type == 'subsection':
            _apply_subsection_mod(lines, modified_lines, search_start, section, subsection_name, new_value)
        
        elif format_type == 'tabular':
            conditions = mod.get('conditions', [])
            _apply_tabular_mod(modified_lines, modified_lines, search_start, section, subsection_name, new_value, conditions)
        
        elif format_type == 'two_row_table':
            conditions = mod.get('conditions', [])
            target_row = mod.get('target_row', None)
            _apply_two_row_table_mod(lines, modified_lines, search_start, section, subsection_name, new_value, conditions, target_row)
    
    return '\n'.join(modified_lines)


def main(input_file, output_file, mod_file):

    try:
        with open(input_file, 'r') as infile:
            data = infile.read()

        with open(mod_file, 'r') as modfile:
            mod_data = modfile.read()

        modifications = parse_modifications(mod_data)
        processed_data = modifyInput(data, modifications)
        # output_file = input_file.rsplit(".", 1)[0] + "_1.dat0"
        if output_file == None or output_file.strip() == "":
            output_file = findFileCount(input_file)

        with open(output_file, 'w') as outfile:
            outfile.write(processed_data)
        print(f"Processed data written to {output_file}")
        print(f"Applied {len(modifications)} modification(s)")
        out1 = input_file.replace('.dat0', '.out0')
        out2 = output_file.replace('.dat0', '.out0')
        # MIPComp.main(out1, out2, mod_file)

    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    input_file = None
    mod_file = None
    output_file = None

    if len(sys.argv) >= 3:
        input_file = sys.argv[1]
        mod_file = sys.argv[2]
        output_file = sys.argv[3] if len(sys.argv) > 3 else None
    else:
        input_file = input("enter input file names :").strip()
        mod_file = input("enter mod file names :").strip()
        output_file = input("enter output file names :").strip()

    main(input_file, output_file, mod_file)