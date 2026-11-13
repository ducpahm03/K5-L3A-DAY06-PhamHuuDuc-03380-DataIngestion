import json
import re
import unicodedata
from pathlib import Path
from pypdf import PdfReader

pdf_path = Path("F:/vinai/K5-L3A-DAY06-PhamHuuDuc-03380-DataIngestion/data/chapter1_workplace_skills.pdf")
reader = PdfReader(str(pdf_path))

def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    # Join hyphenated line breaks e.g. read-\nonly -> read-only
    text = re.sub(r"(\w+)-\n(\w+)", r"\1-\2", text)
    # Normalize multiple whitespace/newlines
    text = re.sub(r"\s+", " ", text)
    return text.strip()

pages = {i + 1: normalize_text(reader.pages[i].extract_text() or "") for i in range(len(reader.pages))}

def get_exact_slice(page_num, start_phrase, end_phrase):
    text = pages[page_num]
    idx1 = text.find(start_phrase)
    if idx1 == -1:
        raise ValueError(f"Start phrase '{start_phrase}' not found on page {page_num}")
    idx2 = text.find(end_phrase, idx1)
    if idx2 == -1:
        raise ValueError(f"End phrase '{end_phrase}' not found on page {page_num}")
    return text[idx1 : idx2 + len(end_phrase)]

specs = [
    # Dev 1-15
    ("q01", "dev", 3, "1.1_history",
     "What early machine used punch cards to perform calculations and tabulate data in 1889?",
     "Herman Hollerith's punch-card tabulating machine, awarded a patent in 1889.",
     "Herman Hollerith’s punch-card tabulating machine", "patent in 1889.", None),

    ("q02", "dev", 4, "1.1_history",
     "Who was Grace Hopper and what computer did she work with in 1960?",
     "Grace Hopper was a pioneer in computer science who earned her PhD in mathematics and worked with the UNIVAC computer.",
     "Grace Hopper, shown here in 1960 with a UNIVAC computer", "PhD in mathematics", None),

    ("q03", "dev", 8, "1.1_history",
     "How have nontechnical industries like agriculture adopted computing technology?",
     "Farmers control irrigation and monitor field conditions using computing technology.",
     "for example, farmers can control irrigation", "monitor field conditions.", None),

    ("q04", "dev", 12, "1.1_history",
     "What are the two dominant operating systems running smartphones today?",
     "The two operating systems are iOS running iPhones and Android running devices such as Samsung Galaxy phones.",
     "two operating systems that run iPhones and Android devices", "performance capabilities", None),

    ("q05", "dev", 16, "1.1_history",
     "How fast do computers typically double their capabilities according to historical trends?",
     "Computers typically double their capabilities in less than two years.",
     "Computers today typically double their capabilities", "less than two years.", None),

    ("q06", "dev", 24, "1.2_hardware_network",
     "What are hardwired instructions needed before an operating system loads called?",
     "They are called read-only memory (ROM).",
     "operating system loads and is ready to use", "read-only memory (ROM).",
     {"section": "1.2_hardware_network"}),

    ("q07", "dev", 24, "1.2_hardware_network",
     "Why should businesses procure computers with sufficient RAM?",
     "To make sure programs run efficiently without slowdown.",
     "Businesses should be sure to procure computers with sufficient RAM", "make sure",
     {"section": "1.2_hardware_network"}),

    ("q08", "dev", 28, "1.3_cloud_iot",
     "What does HTML provide for web pages?",
     "HTML provides the structure on which web pages are based, describing elements such as font size and background colors.",
     "HTML provides the structure on which web pages are based", "displayed page.", None),

    ("q09", "dev", 28, "1.3_cloud_iot",
     "What is a Uniform Resource Locator (URL)?",
     "A URL is an address similar to a postal address directing users to a unique location or page on the World Wide Web.",
     "The uniform resource locator (URL) is an address", "World Wide Web.", None),

    ("q10", "dev", 30, "1.3_cloud_iot",
     "How can users quickly access frequently visited websites in a web browser?",
     "By bookmarking or favoriting websites.",
     "You can also bookmark/favorite websites that you frequent", "quick access", None),

    ("q11", "dev", 34, "1.3_cloud_iot",
     "Which email programs lead the market and are integrated with other productivity products?",
     "Gmail from Google and Outlook by Microsoft lead the market.",
     "Gmail from Google and Outlook by Microsoft led the email market", "between users.",
     {"section": "1.3_cloud_iot"}),

    ("q12", "dev", 38, "1.3_cloud_iot",
     "How does cloud storage lower IT costs for businesses?",
     "Subscription fees for cloud services include troubleshooting and technical assistance.",
     "lower their IT costs because the subscription fee", "assistance functions.", None),

    ("q13", "dev", 41, "1.4_security_ethics",
     "What is phishing in computer security?",
     "Phishing lures users to provide personal credentials through hoax emails/sites.",
     "Attempts to get users to interact with an email or website that appears to be legitimate", "called phishing.", None),

    ("q14", "dev", 42, "1.4_security_ethics",
     "What are internet cookies and what do they track?",
     "Cookies are small data files deposited on user hard disks that keep track of browsing and search history.",
     "Small data files that are deposited on user hard disks from websites", "called cookies.", None),

    ("q15", "dev", 44, "1.4_security_ethics",
     "How should a company manage internal security regarding employee access?",
     "A company should establish policies and protocols to ensure data security compliance and limit employee access.",
     "Internally, a company should establish policies and protocols", "abiding by data security measures.", None),

    # Test 16-20
    ("q16", "test", 3, "1.1_history",
     "What was the Jacquard loom an early example of in computing history?",
     "Jacquard's loom performed calculations using a punch card system as an early precursor.",
     "Jacquard’s loom, which performed calculations using a punch card system", "early development", None),

    ("q17", "test", 24, "1.2_hardware_network",
     "What allows users to save information outside of the computer unit for portable use?",
     "External/portable storage drives.",
     "allowing the user to save information outside of the computer unit", "use elsewhere.",
     {"section": "1.2_hardware_network"}),

    ("q18", "test", 38, "1.3_cloud_iot",
     "What older backup media is no longer necessary when using cloud storage?",
     "CDs and flash drives are no longer needed to store backups or transport files.",
     "backups of the system or flash drives to transport", "computer to another.", None),

    ("q19", "test", 41, "1.4_security_ethics",
     "What is spoofing in the context of email and communication scams?",
     "Spoofing is communication that masquerades as coming from a legitimate, trusted source.",
     "Spoofing is communication (usually", "trusted source.",
     {"section": "1.4_security_ethics"}),

    ("q20", "test", 42, "1.4_security_ethics",
     "Why do websites store cookies on a user's computer?",
     "To remember user preferences, track browsing history, and collect marketing information.",
     "They keep track of your browsing and search history", "potential interests", None)
]

questions = []
for qid, split, page, sec, qtext, ans, start_p, end_p, flt in specs:
    quote = get_exact_slice(page, start_p, end_p)
    assert quote in pages[page], f"Strict assertion failed for {qid}"
    questions.append({
        "id": qid,
        "split": split,
        "section": sec,
        "question": qtext,
        "expected_answer": ans,
        "gold_source_id": "openstax-workplace-skills-ch01",
        "gold_page": page,
        "evidence_quote": quote,
        "filter": flt
    })

out_dir = Path("F:/vinai/K5-L3A-DAY06-PhamHuuDuc-03380-DataIngestion/benchmark")
out_dir.mkdir(parents=True, exist_ok=True)
out_file = out_dir / "questions.json"
with open(out_file, "w", encoding="utf-8") as f:
    json.dump(questions, f, ensure_ascii=False, indent=2)

print(f"ALL 20 QUESTIONS PASSED STRICT VERBATIM CHECK! Written to {out_file.resolve()}")
