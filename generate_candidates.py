from faker import Faker
import csv
import random
fake = Faker()
subjects = [
    "Python",
    "Java",
    "C++",
    "Data Structures",
    "Database",
    "Artificial Intelligence"
]
with open("sample_candidates.csv", "w", newline="") as file:
    writer = csv.writer(file)
    writer.writerow([
        "Candidate ID",
        "Name",
        "Email",
        "Age",
        "Exam Subject"
    ])
    for i in range(1, 21):
        writer.writerow([
            f"CAND{i:03}",
            fake.name(),
            fake.email(),
            random.randint(18, 30),
            random.choice(subjects)
        ])
print("20 Sample Candidate Records Generated Successfully!")