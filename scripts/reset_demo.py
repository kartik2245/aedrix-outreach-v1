"""
reset_demo.py
CLI script to safely reset only demo records (environment='DEMO').
Guarantees production records remain 100% untouched.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.demo.demo_service import DemoService


def main():
    print("===================================================================")
    print(" AEDRIX DEMO DATASET RESET TOOL")
    print("===================================================================")
    service = DemoService()
    res = service.reset_demo_dataset()
    print("Reset completed successfully:")
    print(f"  Deleted demo records: {res['deleted_demo_records']}")
    print(f"  Message:              {res['message']}")
    print("===================================================================")


if __name__ == "__main__":
    main()
