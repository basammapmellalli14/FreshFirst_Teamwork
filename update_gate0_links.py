from docx import Document
from pathlib import Path
import shutil

source = Path.home() / "Desktop" / "G0_Theme 1 Rule check Record Register Perishable Stock Verification Register.docx"
destination = Path("documentation/Gate0_Register_Updated.docx")

if not source.exists():
    raise FileNotFoundError(f"Original document not found: {source}")

shutil.copy2(source, destination)
doc = Document(destination)

updated = 0

for rel in list(doc.part.rels.values()):
    if not rel.reltype.endswith("/hyperlink"):
        continue

    url = rel.target_ref

    if "github.com/rutika-bulabule/FreshFirst_Teamwork/" not in url:
        continue

    if url.endswith("/database") or url.endswith("/diagrams") or url.endswith("/evidence/database"):
        new_url = url.split("/tree/")[0] + "/tree/main/" + url.split("/")[-1]

    elif url.endswith("/Fresh_First_Project_Requirement_Analysis.docx"):
        new_url = "https://github.com/rutika-bulabule/FreshFirst_Teamwork/blob/main/documentation/Fresh_First_Project_Requirement_Analysis.docx"

    elif url.endswith("/B1_Limitation_Note.md"):
        new_url = "https://github.com/rutika-bulabule/FreshFirst_Teamwork/blob/main/documentation/B1_Limitation_Note.md"

    else:
        continue

    rel._target = new_url
    updated += 1

doc.save(destination)

print("Updated document:", destination.resolve())
print("GitHub links updated:", updated)

if updated != 5:
    print("WARNING: Expected 5 links. Please check the document before uploading.")
else:
    print("SUCCESS: All 5 GitHub links updated.")
