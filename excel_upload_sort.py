import pandas as pd
from google.colab import files
import io
import re

# =============================
# 1. Upload Excel file
# =============================
uploaded = files.upload()
file_name = list(uploaded.keys())[0]

df = pd.read_excel(io.BytesIO(uploaded[file_name]))

# Normalize column headers safely
df.columns = (
    df.columns
    .astype(str)
    .str.replace('"', '', regex=False)
    .str.replace('\t', '', regex=False)
    .str.strip()
)

# =============================
# 2. Detect required columns dynamically
# =============================
student_col = 'Student'
branch_col = 'Branch Name'
slot_col = 'Slot'
exam_date_col = 'Exam Date'
exam_time_col = 'Exam Time'
session_col = 'Session'
eligibility_col = 'Eligibility'
fee_col = 'Fee Paid/Not paid'

# Detect Course column safely
course_col = next(
    col for col in df.columns
    if 'course' in col.lower()
)

# =============================
# 3. Extract Student Name & Register No
# =============================
def extract_name(student):
    match = re.match(r'(.+?)\(', str(student))
    return match.group(1).strip() if match else student

def extract_regno(student):
    match = re.search(r'\(([^)]+)\)', str(student))
    return match.group(1).strip() if match else ""

df['Student Name'] = df[student_col].apply(extract_name)
df['Register No'] = df[student_col].apply(extract_regno)

# =============================
# 4. Extract YEAR & SERIAL for sorting
# =============================
def extract_year(reg):
    match = re.search(r'(?:LLBT|LBT)(\d{2})', reg)
    return int(match.group(1)) if match else 99

def extract_serial(reg):
    match = re.search(r'([A-Z]{2})(\d{3})$', reg)
    return int(match.group(2)) if match else 999

df['_year'] = df['Register No'].apply(extract_year)
df['_serial'] = df['Register No'].apply(extract_serial)

# =============================
# 5. Build FINAL OUTPUT STRUCTURE
# =============================
final_df = df[[
    'Student Name',
    'Register No',
    branch_col,
    slot_col,
    course_col,
    exam_date_col,
    exam_time_col,
    session_col,
    eligibility_col,
    fee_col
]].copy()

final_df.columns = [
    'Student',
    'Register No',
    'Branch Name',
    'Slot',
    'Course',
    'Exam Date',
    'Exam Time',
    'Session',
    'Eligibility',
    'Fee Paid/Not paid'
]

# =============================
# 6. SORTING (Branch → Slot → Year → Roll)
# =============================
final_df['_year'] = df['_year']
final_df['_serial'] = df['_serial']

final_df = final_df.sort_values(
    by=['Branch Name', 'Slot', '_year', '_serial'],
    ascending=[True, True, True, True],
    kind='mergesort'
)

# =============================
# 7. Add Sl.No
# =============================
final_df.insert(0, 'Sl.No', range(1, len(final_df) + 1))
final_df = final_df.drop(columns=['_year', '_serial'])

# =============================
# 8. Save MASTER file
# =============================
master_file = 'Master_Sorted_List.xlsx'
final_df.to_excel(master_file, index=False)
files.download(master_file)

# =============================
# 9. SLOT-WISE FILES
# =============================
for slot in final_df['Slot'].dropna().unique():
    slot_df = final_df[final_df['Slot'] == slot].copy()
    slot_df['Sl.No'] = range(1, len(slot_df) + 1)

    fname = f'Slot_{slot}_Sorted_List.xlsx'
    slot_df.to_excel(fname, index=False)
    files.download(fname)

print("✅ COMPLETED SUCCESSFULLY — no column errors, correct sorting")
