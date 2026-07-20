import re
import sys
from pypdf import PdfReader
import pprint
from database.setup import get_paycheck_db
from util.paycheck.save import save_paycheck_to_db

paycheck_data = {
    "Pay Date": "",
    "Net Pay": 0.0,
    "Income": {
        "Annual Bonus": 0.0,
        "Regular Pay": 0.0,
        "Goog Stock Unit": 0.0            
    },
    "Taxes": {
        "Federal Income Tax": 0.0,
        "CA State Income Tax": 0.0,
        "Employee Medicare": 0.0,
        "Social Security Employee Tax": 0.0,
        "CA Voluntary Plan EE": 0.0
    },    
    "Deductions": {
        "Pre-Tax Deductions": {
            "401K Pretax": 0.0,
            "Medical": 0.0,
            "Dental": 0.0,
            "Vision": 0.0,
            "Ltd Purpose FSA": 0.0,
            "HSA Employee": 0.0,
            "FSA Dependent": 0.0
        },
        "Post-Tax Deductions": {
            "LegalAccess": 0.0,
            "Group Term Life": 0.0,
            "401K After-Tax": 0.0
        }
    }
}

paycheck_reg_ex = {
    "Pay Date": {
        "reg-ex": r"(\d{2}/\d{2}/\d{4})",
        "position": 1             
    },
    "Net Pay": {
        "reg-ex": r"\$(0\.00|\d{1,3},\d{3}\.\d{2}|\d{1,3}\.\d{2})",
        "position": 1     
    },
    "Income": {
        # Adjusted to handle both normal lines and the compressed $$ string on Regular Pay
        "reg-ex": r"(\d+\.\d+)\$(\d+\.\d+)\$(?:\$|([\d,]+\.\d{2}))",
        "position": 3        
    },
    "Taxes": {
        # Capture Group 1 = Based On, Capture Group 2 = Current Value
        "reg-ex": r"\$(0\.00|\d{1,3},\d{3}\.\d{2}|\d{1,3}\.\d{2})\s+\$(0\.00|\d{1,3},\d{3}\.\d{2}|\d{1,3}\.\d{2})",
        "position": 2
    },
    "Deductions": {
        # Capture Group 1 = Current Value
        "reg-ex": r"\$(0\.00|\d{1,3},\d{3}\.\d{2}|\d{1,3}\.\d{2})",
        "position": 1
    }
}

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extracts all raw text from a PDF file."""
    reader = PdfReader(pdf_path)
    full_text = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            full_text.append(text)
    return "\n".join(full_text)

def clean_float(val_str: str) -> float:
    """Helper to convert matched text groups safely to float."""
    if not val_str:
        return 0.0
    return float(val_str.replace(",", ""))

def parse_paycheck(data_dict: dict, raw_text: str, current_section: str = None) -> dict:
    result = {}
    
    for key, value in data_dict.items():
        # Track hierarchical sections dynamically
        section_context = current_section
        
        # 1. If the key matches a specific rule definition, switch context
        if key in paycheck_reg_ex:
            section_context = key
        # 2. Inherit parent mapping for sub-dictionaries under Deductions
        elif current_section == "Deductions" or key in ["Pre-Tax Deductions", "Post-Tax Deductions"]:
            section_context = "Deductions"

        if isinstance(value, dict):
            result[key] = parse_paycheck(value, raw_text, current_section=section_context)
        else:
            rules = paycheck_reg_ex.get(section_context)
            if not rules:
                result[key] = value
                continue
            
            # UNIFIED LOGIC: Every pattern is now built exactly the same way
            escaped_key = re.escape(key).replace(r"\ ", r"\s+")
            full_pattern = rf"{escaped_key}\s*{rules['reg-ex']}"
            
            match = re.search(full_pattern, raw_text, re.MULTILINE)
            
            if match:
                pos = rules.get("position", 1)
                matched_val = match.group(pos)
                
                # Shield for the compressed space edge-case on Regular Pay
                if key == "Regular Pay" and matched_val is None:
                    hours = clean_float(match.group(1))
                    rate = clean_float(match.group(2))
                    result[key] = round(hours * rate, 2)
                elif key == "Pay Date":
                    result[key] = matched_val
                else:
                    result[key] = clean_float(matched_val)
            else:
                result[key] = "" if key == "Pay Date" else 0.0
                
    return result

def parse(path_to_file: str) -> str:
    reader = PdfReader(path_to_file)
    for page in reader.pages:
        text = page.extract_text()
        if text:
            populated_paycheck_data = parse_paycheck(paycheck_data, text)
            with get_paycheck_db() as session:
                save_paycheck_to_db(populated_paycheck_data, session)


if __name__ == "__main__":
    pdf_file_path = "data/pay2.pdf" 
    if len(sys.argv) < 2:
        print("Usage: python parser.py <file_path>")
        sys.exit(1)

    path_to_file = sys.argv[1]

    parse(f'data/{path_to_file}')
