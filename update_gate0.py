from docx import Document
from pathlib import Path

path = Path.home() / "Desktop" / "G0_Theme 1 Rule check Record Register Perishable Stock Verification Register.docx"
doc = Document(path)

# TABLE 1: Team members and engines
t = doc.tables[0]

# Member allocation
t.rows[1].cells[2].text = "Member 2"
t.rows[1].cells[3].text = "Basamma"
t.rows[1].cells[4].text = "Member 3"
t.rows[1].cells[5].text = "Khushi"
t.rows[1].cells[6].text = ""
t.rows[1].cells[7].text = "Member 4"
t.rows[1].cells[8].text = "---"

# Engine allocation
t.rows[2].cells[2].text = "(Engine 2)"
t.rows[2].cells[3].text = "Frontend / UI"
t.rows[2].cells[4].text = "(Engine 3)"
t.rows[2].cells[5].text = "Backend"
t.rows[2].cells[6].text = ""
t.rows[2].cells[7].text = "(Engine 4)"
t.rows[2].cells[8].text = "Testing and Validation"

# TABLE 2: Gate 0 evidence
t = doc.tables[1]

t.rows[1].cells[3].text = "Y"
t.rows[1].cells[4].text = (
    "Project Synopsis – Problem Statement and Stakeholders.\n"
    "Database evidence: https://github.com/rutika-bulabule/FreshFirst_Teamwork/tree/main/database\n"
    "Database testing report: https://github.com/rutika-bulabule/FreshFirst_Teamwork/blob/main/documentation/DATABASE_TESTING_REPORT.md"
)

t.rows[2].cells[3].text = "Y"
t.rows[2].cells[4].text = (
    "AS-IS Workflow: https://github.com/rutika-bulabule/FreshFirst_Teamwork/blob/main/diagrams/AS_IS_Workflow.md\n"
    "TO-BE Workflow: https://github.com/rutika-bulabule/FreshFirst_Teamwork/blob/main/diagrams/TO_BE_Workflow.md"
)

t.rows[3].cells[3].text = "Y"
t.rows[3].cells[4].text = (
    "Project Synopsis – Scope, out-of-scope, feasibility and risk details.\n"
    "Database evidence: https://github.com/rutika-bulabule/FreshFirst_Teamwork/tree/main/evidence/database"
)

t.rows[4].cells[3].text = "Y"
t.rows[4].cells[4].text = (
    "Project Requirement Analysis – Foundational Course Mapping.\n"
    "https://github.com/rutika-bulabule/FreshFirst_Teamwork/blob/main/documentation/Fresh_First_Project_Requirement_Analysis.docx"
)

t.rows[6].cells[3].text = "Y"
t.rows[6].cells[4].text = (
    "B1 Limitation Note – Physical stock quantity cannot be independently confirmed without physical verification.\n"
    "https://github.com/rutika-bulabule/FreshFirst_Teamwork/blob/main/documentation/B1_Limitation_Note.md"
)

# TABLE 3: Student statements
t = doc.tables[2]

t.rows[0].cells[1].text = (
    "The weakest part of our project is that frontend and backend integration "
    "and complete application testing are still pending. We need to integrate "
    "all modules and verify that the system works correctly according to the project requirements."
)

t.rows[1].cells[1].text = (
    "Question: How will FreshFirst reduce errors in perishable stock verification compared with the manual system?\n"
    "Answer: FreshFirst stores product information in a centralized MySQL database "
    "and applies predefined rules to check expiry dates, quantities and storage temperatures. "
    "It also assigns priorities and maintains verification history to support accurate stock monitoring."
)

t.rows[2].cells[1].text = (
    "Complete frontend and backend integration, define measurable acceptance criteria, "
    "and test all important stock verification rules using valid and invalid test cases."
)

doc.save(path)
print("SUCCESS: Gate 0 document updated.")
print("Original backup is preserved.")
print("File:", path)
