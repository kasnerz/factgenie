#!/usr/bin/env python3
import logging

logger = logging.getLogger(__name__)

from factgenie.loaders.dataset import Dataset
from pathlib import Path
import json
import json2table


class PlainTextDataset(Dataset):
    def load_examples(self, split, data_path):
        examples = []

        with open(f"{data_path}/{split}.txt") as f:
            lines = f.readlines()
            for line in lines:
                examples.append(line.strip())

        return examples

    def render(self, example):
        html = "<div class='font-mono'>"
        html += "<p>"
        html += "<br>".join(example)
        html += "</p>"
        html += "</div>"

        return html


class JSONDataset(Dataset):
    def load_examples(self, split, data_path):
        examples = []

        with open(f"{data_path}/{split}.json") as f:
            examples = json.load(f)

        return examples

    def render(self, example):
        # default method, can be overwritten by dataset classes
        html = json2table.convert(
            example,
            build_direction="LEFT_TO_RIGHT",
            table_attributes={
                "class": "table table-sm caption-top meta-table table-responsive font-mono rounded-3 table-bordered"
            },
        )
        return html


class JSONLDataset(Dataset):
    def load_examples(self, split, data_path):
        examples = []

        with open(f"{data_path}/{split}.jsonl") as f:
            for line in f:
                examples.append(json.loads(line))

        return examples

    def render(self, example):
        # default method, can be overwritten by dataset classes
        html = json2table.convert(
            example,
            build_direction="LEFT_TO_RIGHT",
            table_attributes={
                "class": "table table-sm caption-top meta-table table-responsive font-mono rounded-3 table-bordered"
            },
        )
        return html


class CSVDataset(Dataset):
    def load_examples(self, split, data_path):
        # load the corresponding CSV file
        # each example will be a key-value pair where the key is the column name and the value is the value in the row
        examples = []

        with open(f"{data_path}/{split}.csv") as f:
            lines = f.readlines()
            header = lines[0].strip().split(",")
            for line in lines[1:]:
                values = line.strip().split(",")
                example = dict(zip(header, values))
                examples.append(example)

        return examples

    def render(self, example):
        html = (
            "<table class='table table-sm caption-top meta-table table-responsive font-mono rounded-3 table-bordered'>"
        )
        html += "<caption>Example</caption>"
        html += "<tbody>"

        for key, value in example.items():
            html += f"<tr><th>{key}</th><td>{value}</td></tr>"

        html += "</tbody>"
        html += "</table>"

        return html


class HTMLDataset(Dataset):
    def load_examples(self, split, data_path):
        # load the HTML files in the directory, sorted by filename numerically
        examples = []
        split_dir = Path(f"{data_path}/{split}")
        filenames = sorted(split_dir.iterdir(), key=lambda x: int(x.stem))

        for filename in filenames:
            with open(filename) as f:
                examples.append(f.read())

        return examples

    def render(self, example):
        return example
