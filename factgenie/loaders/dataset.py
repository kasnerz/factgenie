#!/usr/bin/env python3
import logging
import json
from pathlib import Path
from collections import defaultdict
import json2table
from slugify import slugify

logger = logging.getLogger(__name__)


class Dataset:
    def __init__(self, name, base_path="factgenie"):
        self.base_path = base_path
        self.data_path = f"{self.base_path}/data"
        self.output_path = f"{self.base_path}/outputs"
        self.name = name
        self.examples = self.load_data()
        self.outputs = self.load_generated_outputs()
        self.type = "default"

    def get_example(self, split, example_idx):
        example = self.examples[split][example_idx]

        return example

    def get_example_count(self, split=None):
        if split is None:
            return sum([len(exs) for exs in self.examples.values()])

        return len(self.examples[split])

    def has_split(self, split):
        return split in self.examples.keys()

    def get_splits(self):
        return list(self.examples.keys())

    def load_generated_outputs(self):
        outputs = defaultdict(dict)

        for split in self.get_splits():
            outs = Path.glob(Path(self.output_path) / self.name / split, "*.json")

            outputs[split] = defaultdict()

            for out in outs:
                with open(out) as f:
                    j = json.load(f)
                    setup_id = slugify(j["setup"]["id"])
                    outputs[split][setup_id] = j

        return outputs

    def load_data(self):
        """By default loads the data from factgenie/data/{name}/{split}.json.

        Do override it if you want to load the data e.g. from HuggingFace

        Notice it also calls postprocess_data internally!

        """
        splits = Path.glob(Path(self.data_path) / self.name, "*.json")
        splits = [split.stem for split in splits]
        examples = {split: [] for split in splits}

        for split in splits:
            with open(f"{self.data_path}/{self.name}/{split}.json") as f:
                data = json.load(f)

            data = self.postprocess_data(data)
            examples[split] = data

        return examples

    def postprocess_data(self, data):
        return data

    def render(self, example):
        # default function, can be overwritten by dataset classes
        html = json2table.convert(
            example,
            build_direction="LEFT_TO_RIGHT",
            table_attributes={
                "class": "table table-sm caption-top meta-table table-responsive font-mono rounded-3 table-bordered"
            },
        )
        return html

    def add_generated_outputs(self, split, setup_id, model_outputs):
        path = Path(f"{self.output_path}/{self.name}/{split}")
        path.mkdir(parents=True, exist_ok=True)

        model_outputs = model_outputs.strip()
        generated = [{"out": out} for out in model_outputs.split("\n")]

        setup_id = slugify(setup_id)

        if setup_id in self.outputs[split]:
            raise ValueError(f"Output for {setup_id} already exists in {split}")

        if len(generated) != len(self.examples[split]):
            raise ValueError(
                f"Output count mismatch for {setup_id} in {split}: {len(generated)} vs {len(self.examples[split])}"
            )

        j = {
            "dataset": self.name,
            "split": split,
            "setup": {"id": setup_id},
            "generated": generated,
        }
        self.outputs[split][setup_id] = j

        with open(f"{path}/{setup_id}.json", "w") as f:
            json.dump(j, f, indent=4)

    def delete_generated_outputs(self, split, setup):
        path = Path(f"{self.output_path}/{self.name}/{split}/{setup}.json")

        if path.exists():
            path.unlink()

        self.outputs[split].pop(setup, None)

    def get_generated_outputs_for_split(self, split):
        return self.outputs[split]

    def get_generated_output_by_idx(self, split, output_idx, setup_id):
        if setup_id in self.outputs[split]:
            model_out = self.outputs[split][setup_id]

            if output_idx < len(model_out["generated"]):
                return model_out["generated"][output_idx]["out"]

        logger.warning(f"No output found for {setup_id=}, {output_idx=}, {split=}")
        return None

    def get_generated_outputs_for_idx(self, split, output_idx):
        outs_all = []

        for setup_id, outs in self.outputs[split].items():
            if output_idx >= len(outs["generated"]):
                continue

            out = {}
            out["setup"] = {"id": setup_id}
            out["generated"] = outs["generated"][output_idx]["out"]

            outs_all.append(out)

        return outs_all

    def get_info(self):
        return "TODO for you: Override this function and fill relevant info for your particular dataset!"
