"""
seed_demo.py
CLI script to seed the realistic UK B2B construction demo dataset.
"""

import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

from src.demo.demo_service import DemoService


def main():
    print("===================================================================")
    print(" AEDRIX DEMO DATASET SEEDER")
    print("===================================================================")
    service = DemoService()
    res = service.seed_demo_dataset()
    print("Demo dataset seeded successfully:")
    print(f"  Campaigns seeded:    {res['campaigns']}")
    print(f"  ICPs seeded:         {res['icps']}")
    print(f"  Leads seeded:        {res['leads']}")
    print(f"  Email drafts seeded: {res['email_drafts']}")
    print(f"  Approvals seeded:    {res['approvals']}")
    print("===================================================================")


if __name__ == "__main__":
    main()
