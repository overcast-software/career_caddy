# OrgModeExport

import argparse
import os
import sys
from openai import OpenAI
from jinja2 import Environment, FileSystemLoader
from lib.models import Resume
from lib.handlers.db_handler import DatabaseHandler


class OrgModeExport:

    def __init__(self, ai_client, content, destination=None, example=None):
        self.ai_client = ai_client
        self.content = content
        self.destination = destination  # None means stdout
        self.env = Environment(loader=FileSystemLoader("templates"))
        self.example = example or self.example_resume()

    def process(self) -> str:
        return self.convert_with_ai()

    def convert_with_ai(self):
        template = self.env.get_template("orgmode_export_prompt.j2")
        prompt = template.render(
            example_resume=self.example, resume_string=self.content
        )

        response = self.ai_client.chat.completions.create(
            model="gpt-5",
            messages=[
                {
                    "role": "system",
                    "content": "You input various strings and output org mode syntax",
                },
                {"role": "user", "content": prompt},
            ],
        )
        return response.choices[0].message.content.strip()

    def write_org_mode(self):
        output = self.convert_with_ai()
        if self.destination:
            with open(self.destination, "w", encoding="utf-8") as f:
                f.write(output + "\n")
        else:
            sys.stdout.write(output + "\n")

    def example_resume(self) -> str:
        resume = Resume.get(1)
        if resume:
            return resume.content
        else:
            raise ValueError("could not find resume id: 1")


def parse_arguments():
    parser = argparse.ArgumentParser(description="Convert string to type orgmode.")
    parser.add_argument("-f", "--file", help="Path to file", type=str)
    parser.add_argument(
        "-d",
        "--destination",
        help="Path to the destination org file (defaults to stdout)",
        required=False,
        type=str,
    )
    parser.add_argument("-s", "--stdin", help="Read from stdin", action="store_true")
    return parser.parse_args()


def get_api_key():
    if "OPENAI_API_KEY" in os.environ:
        return os.environ["OPENAI_API_KEY"]
    else:
        print("API key is required. Set OPENAI_API_KEY environment variable.")
        sys.exit(1)


if __name__ == "__main__":
    args = parse_arguments()

    DatabaseHandler()
    api_key = get_api_key()
    ai_client = OpenAI(api_key=api_key)
    writer = None
    if args.stdin:
        content = sys.stdin.read()
        writer = OrgModeExport(ai_client, content, args.destination)
    elif args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            content = f.read()
        writer = OrgModeExport(ai_client, content, args.destination)
    else:
        raise ValueError("Either --file or --stdin must be provided.")

    writer.write_org_mode()
