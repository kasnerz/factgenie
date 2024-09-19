#!/usr/bin/env python3

import re
import glob
import json
import random
import os
import argparse
import pandas as pd
from collections import defaultdict
from scipy.stats import pearsonr
import sys
from pathlib import Path
import logging
import coloredlogs
import factgenie.utils as utils

from factgenie.campaigns import ANNOTATIONS_DIR

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

logger = logging.getLogger(__name__)
coloredlogs.install(level="INFO", logger=logger, fmt="%(asctime)s %(levelname)s %(message)s")


def get_example_info(j, campaign_id):
    return {
        "annotator_id": j["annotator_id"],
        "annotator_group": j.get("annotator_group", 0),
        "campaign_id": campaign_id,
        "dataset": j["dataset"],
        "example_idx": j["example_idx"],
        "setup_id": j["setup"]["id"],
        "split": j["split"],
    }


def load_annotations(line, campaign_id):
    j = json.loads(line)
    annotation_records = []

    r = get_example_info(j, campaign_id)

    for annotation in j["annotations"]:
        r["annotation_type"] = annotation["type"]
        r["annotation_start"] = annotation["start"]
        r["annotation_text"] = annotation["text"]

        annotation_records.append(r.copy())

    return annotation_records


def create_example_record(line, campaign_id, annotation_span_categories, annotation_records):
    # a record is created even if there are no annotations
    j = json.loads(line)

    example_record = get_example_info(j, campaign_id)

    for i, category in enumerate(annotation_span_categories):
        example_record["cat_" + str(i)] = 0

        for annotation in j["annotations"]:
            if int(annotation["type"]) == i:
                example_record["cat_" + str(i)] += 1

    example_record["annotations"] = [
        {
            "annotation_type": r["annotation_type"],
            "annotation_start": r["annotation_start"],
            "annotation_text": r["annotation_text"],
        }
        for r in annotation_records
    ]

    return example_record


def load_annotations_for_campaign(campaign):
    annotation_index = []
    example_index = []

    campaign_id = campaign.metadata["id"]
    annotation_span_categories = campaign.metadata["config"]["annotation_span_categories"]

    jsonl_files = glob.glob(os.path.join(ANNOTATIONS_DIR, campaign_id, "files", "*.jsonl"))

    for jsonl_file in jsonl_files:
        with open(jsonl_file) as f:
            lines = f.readlines()
        for line in lines:
            try:
                annotation_records = load_annotations(line, campaign_id)
                annotation_index += annotation_records

                example_record = create_example_record(
                    line, campaign_id, annotation_span_categories, annotation_records
                )
                example_index.append(example_record)
            except Exception as e:
                logger.error(f"Error while processing line: {line}")
                logger.error(e)

    annotation_index = pd.DataFrame(annotation_index)
    example_index = pd.DataFrame(example_index)

    return annotation_index, example_index


def preprocess_annotations(df, campaign):
    # remove lines with nans
    df = df.dropna()

    # remove annotations with type that is not in the correct range (0 - len(annotation_span_categories))
    annotation_span_categories = campaign.metadata["config"]["annotation_span_categories"]

    category_cnt = len(annotation_span_categories)
    df = df[df["annotation_type"].apply(lambda x: x in range(category_cnt))]

    # make annotation_type an integer
    df["annotation_type"] = df["annotation_type"].astype(int)

    return df


def compute_ann_counts(df):
    """
    Compute annotation counts for each annotation type (separately for each dataset, split, setup_id).
    """
    results = []

    all_annotation_types = df["annotation_type"].unique()
    all_annotation_types.sort()

    for dataset in df["dataset"].unique():
        for split in df["split"].unique():
            for setup_id in df["setup_id"].unique():
                # filter the dataframe
                df_filtered = df[(df["dataset"] == dataset) & (df["split"] == split) & (df["setup_id"] == setup_id)]

                # make sure that all annotation types are present in the dataframe, even with zero counts
                ann_counts = (
                    df_filtered.groupby("annotation_type")
                    .size()
                    .reindex(all_annotation_types, fill_value=0)
                    .reset_index(name="ann_count")
                )

                ann_counts["dataset"] = dataset
                ann_counts["split"] = split
                ann_counts["setup_id"] = setup_id

                results.append(ann_counts)

    # concatenate all results into a single dataframe
    results = pd.concat(results, ignore_index=True)

    return results


def compute_avg_ann_counts(ann_counts, example_index):
    # for each line in ann_counts, find the corresponding dataset in datasets and add the number of examples
    # then compute the average annotation count

    # add a column with the number of examples for each dataset, split
    ann_counts["example_count"] = 0

    for i, row in ann_counts.iterrows():
        dataset = row["dataset"]
        split = row["split"]
        setup_id = row["setup_id"]
        ann_counts.loc[i, "example_count"] = (
            example_index[
                (example_index["dataset"] == dataset)
                & (example_index["split"] == split)
                & (example_index["setup_id"] == setup_id)
            ]
            .example_idx.unique()
            .shape[0]
        )

    ann_counts["avg_count"] = ann_counts["ann_count"] / ann_counts["example_count"]

    # round to three decimal places
    ann_counts["avg_count"] = ann_counts["avg_count"].round(3)

    return ann_counts


def compute_prevalence(ann_counts, example_index):
    # for each combination of dataset, split, setup_id, annotation_type, compute the percentage of examples that are affected by the annotation type and add it to the `ann_counts` dataframe
    for i, row in ann_counts.iterrows():
        dataset = row["dataset"]
        split = row["split"]
        setup_id = row["setup_id"]
        annotation_type = row["annotation_type"]

        examples = example_index[
            (example_index["dataset"] == dataset)
            & (example_index["split"] == split)
            & (example_index["setup_id"] == setup_id)
            & (example_index["cat_" + str(annotation_type)] > 0)
        ]

        ann_counts.loc[i, "prevalence"] = examples.shape[0] / row["example_count"]

        # round to three decimal places
        ann_counts["prevalence"] = ann_counts["prevalence"].round(3)

    return ann_counts


def aggregate_ann_counts(ann_counts, groupby):
    if groupby == "span":
        aggregated = (
            ann_counts.groupby("annotation_type")
            .agg({"avg_count": "mean", "ann_count": "sum", "example_count": "sum", "prevalence": "mean"})
            .reset_index()
            .to_dict(orient="records")
        )

    elif groupby == "setup":
        # keep individual annotation categories, but aggregate setup_ids for each dataset, split
        aggregated = (
            ann_counts.groupby(["setup_id", "annotation_type"])
            .agg({"avg_count": "mean", "ann_count": "sum", "example_count": "sum", "prevalence": "mean"})
            .reset_index()
            .to_dict(orient="records")
        )

    elif groupby == "dataset":
        # keep individual annotation categories, but aggregate datasets for each split, setup_id
        aggregated = (
            ann_counts.groupby(["dataset", "split", "annotation_type"])
            .agg({"avg_count": "mean", "ann_count": "sum", "example_count": "sum", "prevalence": "mean"})
            .reset_index()
            .to_dict(orient="records")
        )

    # round to three decimal places
    for a in aggregated:
        a["avg_count"] = round(a["avg_count"], 3)
        a["prevalence"] = round(a["prevalence"], 3)

    return aggregated


def compute_statistics(app, campaign, datasets):
    statistics = {}

    annotation_index, example_index = load_annotations_for_campaign(campaign)

    if annotation_index.empty:
        return None

    annotation_index = preprocess_annotations(annotation_index, campaign)

    annotation_counts = compute_ann_counts(annotation_index)
    annotation_counts = compute_avg_ann_counts(annotation_counts, example_index)
    annotation_counts = compute_prevalence(annotation_counts, example_index)

    statistics["ann_counts"] = {
        "full": annotation_counts.to_dict(orient="records"),
        "span": aggregate_ann_counts(annotation_counts, "span"),
        "setup": aggregate_ann_counts(annotation_counts, "setup"),
        "dataset": aggregate_ann_counts(annotation_counts, "dataset"),
    }

    return statistics


def compute_pearson_correlation(dataset_level_counts, example_level_counts, annotator_count, annotator_group_ids):
    results = []

    for a in range(annotator_count):
        for b in range(a + 1, annotator_count):
            a_group_id = annotator_group_ids[a]
            b_group_id = annotator_group_ids[b]

            r_data, _ = pearsonr(dataset_level_counts[a], dataset_level_counts[b])
            logger.info(
                f"Annotators {a_group_id} and {b_group_id} have a dataset-level Pearson correlation coefficient of {r_data:.3f}"
            )

            r_example, _ = pearsonr(example_level_counts[a], example_level_counts[b])
            logger.info(
                f"Annotators {a_group_id} and {b_group_id} have an example-level Pearson correlation coefficient of {r_example:.3f}"
            )

            results.append(
                {
                    "first_annotator": a_group_id,
                    "second_annotator": b_group_id,
                    "dataset_level_pearson_r": r_data,
                    "example_level_pearson_r": r_example,
                }
            )

    return results


def compute_span_counts(example_index, annotator_count, combinations, cat_columns):
    dataset_level_counts = [[] for _ in range(annotator_count)]
    example_level_counts = [[] for _ in range(annotator_count)]

    for dataset, split, setup_id in combinations:
        example_index_subset = example_index[
            (example_index["dataset"] == dataset)
            & (example_index["split"] == split)
            & (example_index["setup_id"] == setup_id)
        ]

        error_counts = [{"cat_" + str(i): [] for i in range(len(cat_columns))} for _ in range(annotator_count)]

        for i, row in example_index_subset.iterrows():
            for a in range(annotator_count):
                for j, c in enumerate(cat_columns):
                    error_counts[a]["cat_" + str(j)].append(row[c][a])

        # for each pair of annotators, compute the Pearson correlation coefficient between the average number of errors for each category

        for a in range(annotator_count):
            for j, c in enumerate(cat_columns):
                if len(error_counts[a][c]) > 0:
                    avg = sum(error_counts[a][c]) / len(error_counts[a][c])
                else:
                    avg = 0

                dataset_level_counts[a].append(avg)
                example_level_counts[a] += error_counts[a][c]

    return dataset_level_counts, example_level_counts


def prepare_example_index(combinations, selected_campaigns, campaigns):
    # gather a list of all examples with some annotations
    example_index = pd.DataFrame()

    for campaign_id in selected_campaigns:
        campaign = campaigns[campaign_id]

        _, ei = load_annotations_for_campaign(campaign)
        example_index = pd.concat([example_index, ei], ignore_index=True)

    # a combination is a tuple (dataset, split, setup_id)
    # leave only examples in example_index that are in the combinations selected by the user
    example_index = example_index[
        example_index.apply(lambda x: (x["dataset"], x["split"], x["setup_id"]) in combinations, axis=1)
    ]

    # add a column "annotator_group_id" to example_index, concatenating the campaign_id with str(annotator_group)
    example_index["annotator_group_id"] = (
        example_index["campaign_id"] + "-anngroup-" + example_index["annotator_group"].astype(str)
    )

    # get the number of annotators we are considering
    annotator_group_ids = list(example_index["annotator_group_id"].unique())
    annotator_count = len(annotator_group_ids)

    # group examples by dataset, split, setup_id, example_idx
    # aggregate annotations, annotator_ids, and counts for each category into a list
    aggregations = {"annotations": list, "annotator_group_id": list}
    cat_columns = [x for x in example_index.columns if x.startswith("cat_")]

    for c in cat_columns:
        aggregations[c] = list

    example_index = (
        example_index.groupby(["dataset", "split", "setup_id", "example_idx"]).agg(aggregations).reset_index()
    )
    # remove all examples that do not have annotations from all annotators
    example_index = example_index[example_index["annotator_group_id"].apply(lambda x: len(x) == annotator_count)]

    return example_index, annotator_count, annotator_group_ids, cat_columns


def compute_inter_annotator_agreement(app, selected_campaigns, combinations, campaigns, datasets):
    combinations = [(c["dataset"], c["split"], c["setup_id"]) for c in combinations]

    example_index, annotator_count, annotator_group_ids, cat_columns = prepare_example_index(
        combinations=combinations, selected_campaigns=selected_campaigns, campaigns=campaigns
    )

    dataset_level_counts, example_level_counts = compute_span_counts(
        example_index=example_index, annotator_count=annotator_count, combinations=combinations, cat_columns=cat_columns
    )

    results = compute_pearson_correlation(
        dataset_level_counts=dataset_level_counts,
        example_level_counts=example_level_counts,
        annotator_count=annotator_count,
        annotator_group_ids=annotator_group_ids,
    )

    return results
