#!/usr/bin/env python3

import argparse
import json
import sys
from datetime import datetime

class OrgModeWriter:
    def __init__(self, json_data=None, json_file=None, destination_file=None):
        if json_data:
            self.data = json.loads(json_data)
        elif json_file:
            self.data = self.read_json_file(json_file)
        else:
            raise ValueError("Either json_data or json_file must be provided.")
        self.destination_file = destination_file

    @staticmethod
    def read_json_file(file_path):
        with open(file_path, 'r') as file:
            data = json.load(file)
        return data

    def write_org_mode(self):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(self.destination_file, 'a') as file:
            file.write(f"* {timestamp}\n")
            file.write(f"** Title: {self.data['title']}\n")
            file.write(f"** Description: {self.data['description']}\n")
            file.write(f"** Company: {self.data['company']}\n")

def parse_arguments():
    parser = argparse.ArgumentParser(description='Process JSON input for org-mode.')
    parser.add_argument('-f', '--file', help='Path to the JSON file', type=str)
    parser.add_argument('-d', '--destination', help='Path to the destination org file', required=True, type=str)
    parser.add_argument('-s', '--stdin', help='Read JSON from stdin', action='store_true')
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_arguments()

    if args.stdin:
        json_data = sys.stdin.read()
        writer = OrgModeWriter(json_data=json_data, destination_file=args.destination)
    elif args.file:
        writer = OrgModeWriter(json_file=args.file, destination_file=args.destination)
    else:
        raise ValueError("Either --file or --stdin must be provided.")

    writer.write_org_mode()
