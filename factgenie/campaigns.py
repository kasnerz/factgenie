#!/usr/bin/env python3
import os
import json
import glob
import logging
import pandas as pd
import ast
import coloredlogs

from pathlib import Path

logger = logging.getLogger(__name__)
coloredlogs.install(level="INFO", logger=logger, fmt="%(asctime)s %(levelname)s %(message)s")


DIR_PATH = os.path.dirname(__file__)
CROWDSOURCING_DIR = os.path.join(DIR_PATH, "annotations")


class Campaign:
    @classmethod
    def get_name(cls):
        return cls.__name__

    def __init__(self, campaign_id):
        self.campaign_id = campaign_id
        self.dir = os.path.join(CROWDSOURCING_DIR, campaign_id)
        self.db_path = os.path.join(self.dir, "db.csv")
        self.metadata_path = os.path.join(self.dir, "metadata.json")

        with open(self.db_path) as f:
            self.db = pd.read_csv(f)

        with open(self.metadata_path) as f:
            self.metadata = json.load(f)

    def get_finished_examples(self):
        # load all the JSONL files in the "files" subdirectory
        examples_finished = []

        for jsonl_file in glob.glob(os.path.join(self.dir, "files/*.jsonl")):
            with open(jsonl_file) as f:
                for line in f:
                    example = json.loads(line)
                    examples_finished.append(example)

        return examples_finished

    def update_db(self, db):
        db.to_csv(self.db_path, index=False)

    def update_metadata(self):
        with open(self.metadata_path, "w") as f:
            json.dump(self.metadata, f, indent=4)

    def get_stats(self):
        # group by batch_idx, keep the first row of each group
        batch_stats = self.db.groupby("batch_idx").first()

        return batch_stats["status"].value_counts().to_dict()

    def get_overview(self):
        # pair the examples in db with the finished examples
        # we need to match the examples on (dataset, split, setup, example_idx)
        # add the annotations to the df

        # get the finished examples
        finished_examples = self.get_finished_examples()
        example_index = {
            (ex["dataset"], ex["split"], ex["setup"]["id"], ex["example_idx"]): str(ex) for ex in finished_examples
        }

        overview_db = self.db.copy()
        overview_db["annotations"] = ""

        for i, row in self.db.iterrows():
            key = (row["dataset"], row["split"], row["setup_id"], row["example_idx"])
            example = ast.literal_eval(example_index.get(key, "{}"))

            annotations = example.get("annotations", [])
            overview_db.at[i, "annotations"] = str(annotations)

        return overview_db


class HumanCampaign(Campaign):
    def get_examples_for_batch(self, batch_idx):
        annotator_batch = []

        # find all examples for this batch in self.db
        batch_examples = self.db[self.db["batch_idx"] == batch_idx]

        for _, row in batch_examples.iterrows():
            annotator_batch.append(
                {
                    "dataset": row["dataset"],
                    "split": row["split"],
                    "setup": {"id": row["setup_id"]},
                    "example_idx": row["example_idx"],
                }
            )
        return annotator_batch


class ModelCampaign(Campaign):
    def get_stats(self):
        return self.db["status"].value_counts().to_dict()
