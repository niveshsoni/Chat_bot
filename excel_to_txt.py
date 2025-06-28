import pandas as pd

def convert_excel_to_txt(excel_path, txt_output_path):
    # Load all sheets
    xls = pd.ExcelFile(excel_path)
    page_counter = 1
    all_text_lines = []

    for sheet_name in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet_name)
        df.fillna("", inplace=True)  # Replace NaN with empty string

        for idx, row in df.iterrows():
            title = row.get('Title', '').strip()
            subtitle = row.get('Subtitle', '').strip()
            content = row.get('Content', '').strip()

            text_block = [
                f"Page: {page_counter} \n",
                f"Information Type: {sheet_name} \n",
                f"Title: {title} \n",
                f"SubTitle: {subtitle} \n",
                "======================================== \n",
                f"{content} \n",
                "======================================== \n\n\n"
            ]

            all_text_lines.extend(text_block)
            page_counter += 1

    # Write to output .txt file
    with open(txt_output_path, "w", encoding="utf-8") as f:
        f.writelines(all_text_lines)

    print(f"Conversion complete. Output saved to: {txt_output_path}")

# Example usage
excel_file = r"C:\Users\91887\Desktop\Finance_playbook_bot\finance_playbook.xlsx"
output_txt = "finance_playbook.txt"
convert_excel_to_txt(excel_file, output_txt)
