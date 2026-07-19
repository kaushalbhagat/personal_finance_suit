from util.paycheck.parser import extract_text_from_pdf, parse_paycheck, paycheck_data
import pprint

if __name__ == "__main__":
    pdf_file_path = "data/pay2.pdf" 

    raw_text = extract_text_from_pdf(pdf_file_path)
    populated_paycheck_data = parse_paycheck(paycheck_data, raw_text)
    pprint.pprint(populated_paycheck_data)