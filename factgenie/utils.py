#!/usr/bin/env python3
import os
import datetime
import json
import glob
import time
import logging
from typing import Dict
import pandas as pd
import random
import time
import coloredlogs
import traceback
import yaml
import queue
import shutil
import inspect
import importlib
import zipfile

from io import BytesIO
from slugify import slugify
from flask import jsonify, make_response
from collections import defaultdict
from pathlib import Path
from factgenie.campaigns import Campaign, HumanCampaign, ModelCampaign
from factgenie.metrics import LLMMetric, LLMMetricFactory
from factgenie.loaders.dataset import Dataset, DATA_DIR

DIR_PATH = os.path.dirname(__file__)
TEMPLATES_DIR = os.path.join(DIR_PATH, "templates")
STATIC_DIR = os.path.join(DIR_PATH, "static")
ANNOTATIONS_DIR = os.path.join(DIR_PATH, "annotations")
LLM_CONFIG_DIR = os.path.join(DIR_PATH, "config", "llm-eval")
LLM_D2T_DIR = os.path.join(DIR_PATH, "config", "llm-d2t")
CROWDSOURCING_CONFIG_DIR = os.path.join(DIR_PATH, "config", "crowdsourcing")

DATASET_CONFIG_PATH = "factgenie/loaders/datasets.yml"

file_handler = logging.FileHandler("error.log")
file_handler.setLevel(logging.ERROR)


logger = logging.getLogger(__name__)


# https://maxhalford.github.io/blog/flask-sse-no-deps/
class MessageAnnouncer:
    def __init__(self):
        self.listeners = []

    def listen(self):
        self.listeners.append(queue.Queue(maxsize=5))
        return self.listeners[-1]

    def announce(self, msg):
        # We go in reverse order because we might have to delete an element, which will shift the
        # indices backward
        for i in reversed(range(len(self.listeners))):
            try:
                self.listeners[i].put_nowait(msg)
            except queue.Full:
                del self.listeners[i]


def format_sse(data: str, event=None) -> str:
    """Formats a string and an event name in order to follow the event stream convention.

    >>> format_sse(data=json.dumps({'abc': 123}), event='Jackson 5')
    'event: Jackson 5\\ndata: {"abc": 123}\\n\\n'

    """
    msg = f"data: {data}\n\n"
    if event is not None:
        msg = f"event: {event}\n{msg}"
    return msg


def success():
    resp = jsonify(success=True)
    return resp


def error(j):
    resp = jsonify(success=False, error=j)
    return resp


def get_dataset(app, dataset_id):
    return app.db["datasets_obj"].get(dataset_id)


def load_configs(mode):
    """
    Goes through all the files in the LLM_CONFIG_DIR
    instantiate the LLMMetric class
    and inserts the object in the metrics dictionary

    Returns:
        metrics: dictionary of LLMMetric objects with keys of metric names
    """
    configs = {}

    if mode == "llm_eval":
        config_dir = LLM_CONFIG_DIR
    elif mode == "llm_d2t":
        config_dir = LLM_D2T_DIR
    else:
        config_dir = CROWDSOURCING_CONFIG_DIR

    #config_dir = LLM_CONFIG_DIR if mode == "llm_eval" else CROWDSOURCING_CONFIG_DIR

    for file in os.listdir(config_dir):
        if file.endswith(".yaml"):
            try:
                with open(os.path.join(config_dir, file)) as f:
                    config = yaml.safe_load(f)
                    configs[file] = config
            except Exception as e:
                logger.error(f"Error while loading metric {file}")
                traceback.print_exc()
                continue
    return configs


def generate_campaign_index(app):
    campaigns = defaultdict(dict)

    # find all subdirs in CROWDSOURCING_DIR
    for campaign_dir in Path(ANNOTATIONS_DIR).iterdir():
        try:
            if not campaign_dir.is_dir():
                continue

            metadata = json.load(open(os.path.join(campaign_dir, "metadata.json")))
            campaign_source = metadata.get("source")
            campaign_id = metadata["id"]

            if campaign_source == "crowdsourcing":
                campaign = HumanCampaign(campaign_id=campaign_id)
            elif campaign_source == "llm_eval":
                campaign = ModelCampaign(campaign_id=campaign_id)
            elif campaign_source == 'llm_d2t':
                campaign = ModelCampaign(campaign_id=campaign_id)
            elif campaign_source == "hidden":
                continue
            else:
                logger.warning(f"Unknown campaign source: {campaign_source}")
                continue

            campaigns[campaign_source][campaign_id] = campaign
        except:
            logger.error(f"Error while loading campaign {campaign_dir}")

    app.db["campaign_index"] = campaigns


def generate_annotation_index(app):
    # contains annotations for each generated output
    annotations = defaultdict(list)

    # for all subdirectories in ANNOTATIONS_DIR, load content of all the jsonl files
    for subdir in os.listdir(ANNOTATIONS_DIR):
        try:
            # find metadata for the campaign
            metadata_path = os.path.join(ANNOTATIONS_DIR, subdir, "metadata.json")
            if not os.path.exists(metadata_path):
                continue

            with open(metadata_path) as f:
                metadata = json.load(f)

            jsonl_files = glob.glob(os.path.join(ANNOTATIONS_DIR, subdir, "files/*.jsonl"))

            for jsonl_file in jsonl_files:
                with open(jsonl_file) as f:
                    for line in f:
                        annotation = json.loads(line)
                        annotation["metadata"] = metadata

                        key = (
                            slugify(annotation["dataset"]),
                            slugify(annotation["split"]),
                            annotation["example_idx"],
                            slugify(annotation["setup"]["id"]),
                        )
                        annotations[key].append(annotation)
        except:
            # if app.config["debug"]:
            traceback.print_exc()
            logger.error(f"Error while loading annotations for {subdir}")
            # raise
    app.db["annotation_index"] = annotations

    return annotations


def export_annotations(app, campaign_id):
    zip_buffer = BytesIO()

    with zipfile.ZipFile(zip_buffer, "w") as zip_file:
        for root, dirs, files in os.walk(os.path.join(ANNOTATIONS_DIR, campaign_id)):
            for file in files:
                zip_file.write(
                    os.path.join(root, file),
                    os.path.relpath(os.path.join(root, file), os.path.join(ANNOTATIONS_DIR, campaign_id)),
                )

    # Set response headers for download
    timestamp = int(time.time())
    response = make_response(zip_buffer.getvalue())
    response.headers["Content-Type"] = "application/zip"
    response.headers["Content-Disposition"] = f"attachment; filename={campaign_id}_{timestamp}.zip"
    return response


def get_annotations(app, dataset_id, split, example_idx, setup_id):
    annotation_index = app.db["annotation_index"]
    key = (slugify(dataset_id), slugify(split), example_idx, slugify(setup_id))

    return annotation_index.get(key, [])


def get_example_data(app, dataset_id, split, example_idx):
    dataset = get_dataset(app=app, dataset_id=dataset_id)

    example = dataset.get_example(split=split, example_idx=example_idx)
    html = dataset.render(example=example)

    # temporary solution for external files
    # prefix all the "/files" calls with "app.config["host_prefix"]"
    html = html.replace('src="/files', f'src="{app.config["host_prefix"]}/files')

    generated_outputs = dataset.get_generated_outputs_for_idx(split=split, output_idx=example_idx)

    for i, output in enumerate(generated_outputs):
        setup_id = output["setup"]["id"]
        annotations = get_annotations(app, dataset_id, split, example_idx, setup_id)

        generated_outputs[i]["annotations"] = annotations

    return {
        "html": html,
        "raw_data": example,
        "total_examples": dataset.get_example_count(split),
        "generated_outputs": generated_outputs,
    }


def get_model_outputs_overview(app, datasets):
    model_outputs = {}

    for dataset_id, dataset_config in datasets.items():
        dataset = get_dataset(app=app, dataset_id=dataset_id)
        splits = dataset.get_splits()

        model_outputs[dataset_id] = {}

        for split in splits:
            # model_outputs[dataset_id][split] = {}
            outputs = dataset.get_generated_outputs_for_split(split)

            for setup_id, output in outputs.items():
                output_info = {}
                output_info["split"] = split
                output_info["setup_id"] = setup_id
                output_info["example_count"] = len(outputs[setup_id]["generated"])

                model_outputs[dataset_id][setup_id] = output_info

    return model_outputs


def free_idle_examples(db):
    start = int(time.time())

    # check if there are annotations which are idle for more than 2 hours: set them to free
    idle_examples = db[(db["status"] == "assigned") & (db["start"] < start - 2 * 60 * 60)]
    for i in idle_examples.index:
        db.loc[i, "status"] = "free"
        db.loc[i, "start"] = ""
        db.loc[i, "annotator_id"] = ""

    return db


def select_batch_idx(db, seed):
    free_examples = db[db["status"] == "free"]
    assigned_examples = db[db["status"] == "assigned"]

    if len(free_examples) == 0 and len(assigned_examples) == 0:
        raise ValueError("No examples available")

    # if no free examples but still assigned examples, take the oldest assigned example
    if len(free_examples) == 0 and len(assigned_examples) > 0:
        free_examples = assigned_examples
        free_examples = free_examples.sort_values(by=["start"])
        free_examples = free_examples.head(1)

        logger.info(f"Annotating extra example {free_examples.index[0]}")

    example = free_examples.sample(random_state=seed)
    batch_idx = int(example.batch_idx.values[0])
    logger.info(f"Selecting batch {batch_idx}")

    return batch_idx


def get_annotator_batch(app, campaign, db, prolific_pid, session_id, study_id):
    # simple locking over the CSV file to prevent double writes
    with app.db["lock"]:
        logging.info(f"Acquiring lock for {prolific_pid}")
        start = int(time.time())

        seed = random.seed(str(start) + prolific_pid + session_id + study_id)

        try:
            batch_idx = select_batch_idx(db, seed)
        except ValueError:
            # no available batches
            return []

        if prolific_pid != "test":
            db = free_idle_examples(db)

            # update the CSV
            db.loc[batch_idx, "status"] = "assigned"
            db.loc[batch_idx, "start"] = start
            db.loc[batch_idx, "annotator_id"] = prolific_pid

            campaign.update_db(db)

        annotator_batch = campaign.get_examples_for_batch(batch_idx)

        for example in annotator_batch:
            example.update(
                {
                    "campaign_id": campaign.campaign_id,
                    "batch_idx": batch_idx,
                    "annotator_id": prolific_pid,
                    "session_id": session_id,
                    "study_id": study_id,
                    "start_timestamp": start,
                }
            )

        logging.info(f"Releasing lock for {prolific_pid}")

    return annotator_batch


def generate_llm_eval_db(datasets: Dict[str, Dataset], campaign_data):
    # load all outputs
    all_examples = []

    for c in campaign_data:
        dataset = datasets[c["dataset"]]
        for i in range(dataset.get_example_count(c["split"])):
            all_examples.append(
                {
                    "dataset": c["dataset"],
                    "split": c["split"],
                    "example_idx": i,
                    "setup_id": c["setup_id"],
                }
            )

    df = pd.DataFrame.from_records(all_examples)

    # create a column for batch index and assign each example to a batch
    df["annotator_id"] = ""
    df["status"] = "free"
    df["start"] = ""

    return df


def generate_campaign_db(app, campaign_data, config):
    # load all outputs
    all_examples = []

    examples_per_batch = config["examples_per_batch"]
    sort_order = config["sort_order"]

    for c in campaign_data:
        dataset = app.db["datasets_obj"][c["dataset"]]
        for i in range(dataset.get_example_count(c["split"])):
            all_examples.append(
                {
                    "dataset": c["dataset"],
                    "split": c["split"],
                    "example_idx": i,
                    "setup_id": c["setup_id"],
                }
            )

    if sort_order == "example-level":
        random.seed(42)
        random.shuffle(all_examples)
        # group outputs by example ids, dataset and split
        all_examples = sorted(all_examples, key=lambda x: (x["example_idx"], x["dataset"], x["split"]))
    elif sort_order == "dataset-level":
        random.seed(42)
        random.shuffle(all_examples)
    elif sort_order == "default":
        pass
    else:
        raise ValueError(f"Unknown sort order {sort_order}")
    df = pd.DataFrame.from_records(all_examples)

    # create a column for batch index and assign each example to a batch
    df["batch_idx"] = df.index // examples_per_batch
    df["annotator_id"] = ""
    df["status"] = "free"
    df["start"] = ""

    return df


def load_dataset_config():
    with open(DATASET_CONFIG_PATH) as f:
        config = yaml.safe_load(f)

    return config


def save_dataset_config(config):
    with open(DATASET_CONFIG_PATH, "w") as f:
        yaml.dump(config, f, indent=2, allow_unicode=True)


def set_dataset_enabled(app, dataset_id, enabled):
    config = load_dataset_config()
    config["datasets"][dataset_id]["enabled"] = enabled

    if enabled:
        dataset = instantiate_dataset(dataset_id, config["datasets"][dataset_id])
        app.db["datasets_obj"][dataset_id] = dataset
    else:
        app.db["datasets_obj"].pop(dataset_id, None)

    save_dataset_config(config)


def get_dataset_overview(app):
    config = load_dataset_config()
    overview = {}

    for dataset_id, dataset_config in config["datasets"].items():
        class_name = dataset_config["class"]
        params = dataset_config.get("params", {})
        is_enabled = dataset_config.get("enabled", True)
        description = dataset_config.get("description", "")
        splits = dataset_config.get("splits", [])
        dataset_type = dataset_config.get("type", "default")

        if is_enabled:
            dataset = app.db["datasets_obj"].get(dataset_id)
            example_count = {split: dataset.get_example_count(split) for split in dataset.get_splits()}
        else:
            example_count = {}

        overview[dataset_id] = {
            "class": class_name,
            "params": params,
            "enabled": is_enabled,
            "splits": splits,
            "description": description,
            "example_count": example_count,
            "type": dataset_type,
        }

    return overview


def get_dataset_classes():
    module_name = "factgenie.loaders"
    module = importlib.import_module(module_name)

    classes = {}

    # for each submodule, find all classes subclassing `Dataset`
    # then do { "submodule.class": class }
    for name, obj in inspect.getmembers(module):
        if inspect.ismodule(obj):
            submodule = obj
            for name, obj in inspect.getmembers(submodule):
                if inspect.isclass(obj) and issubclass(obj, Dataset) and obj != Dataset:
                    submodule_name = obj.__module__[len(module_name) + 1 :]
                    classes[f"{submodule_name}.{obj.__name__}"] = obj

    return classes


def delete_dataset(app, dataset_id):
    config = load_dataset_config()
    config["datasets"].pop(dataset_id, None)
    save_dataset_config(config)

    # remove the data directory
    shutil.rmtree(f"factgenie/data/{dataset_id}", ignore_errors=True)

    app.db["datasets_obj"].pop(dataset_id, None)


def export_dataset(app, dataset_id):
    zip_buffer = BytesIO()
    data_path = f"{DATA_DIR}/{dataset_id}"

    with zipfile.ZipFile(zip_buffer, "w") as zip_file:
        for root, dirs, files in os.walk(data_path):
            for file in files:
                zip_file.write(
                    os.path.join(root, file),
                    os.path.relpath(os.path.join(root, file), data_path),
                )

    # Set response headers for download
    response = make_response(zip_buffer.getvalue())
    response.headers["Content-Type"] = "application/zip"
    response.headers["Content-Disposition"] = f"attachment; filename={dataset_id}.zip"

    return response


def instantiate_dataset(dataset_id, dataset_config):
    submodule, class_name = dataset_config["class"].split(".")

    # Dynamically import the class
    module = importlib.import_module("factgenie.loaders")
    submodule = getattr(module, submodule)
    dataset_class = getattr(submodule, class_name)

    return dataset_class(dataset_id, **dataset_config)


def instantiate_datasets():
    config = load_dataset_config()
    datasets = {}
    for dataset_id, dataset_config in config["datasets"].items():
        is_enabled = dataset_config.get("enabled", True)

        if not is_enabled:
            continue

        datasets[dataset_id] = instantiate_dataset(dataset_id, dataset_config)

    return datasets


def upload_dataset(dataset_id, dataset_description, dataset_format, dataset_data):
    params = {
        "text": {"suffix": "txt", "class": "base.PlainTextDataset", "type": "default"},
        "jsonl": {"suffix": "jsonl", "class": "base.JSONLDataset", "type": "json"},
        "csv": {"suffix": "csv", "class": "base.CSVDataset", "type": "table"},
        "html": {"suffix": "zip", "class": "base.HTMLDataset", "type": "default"},
    }
    dataset_id = slugify(dataset_id)
    data_dir = f"factgenie/data/{dataset_id}"
    os.makedirs(data_dir, exist_ok=True)

    if dataset_format in ["text", "jsonl", "csv"]:
        # save each split in a separate file
        for split, data in dataset_data.items():
            with open(f"{data_dir}/{split}.{params[dataset_format]['suffix']}", "w") as f:
                f.write(data)

    elif dataset_format == "html":
        # dataset_data is the file object
        for split, data in dataset_data.items():
            binary_file = BytesIO(bytes(data))
            with zipfile.ZipFile(binary_file, "r") as zip_ref:
                zip_ref.extractall(f"{data_dir}/{split}")

    # add an entry in the dataset config
    config = load_dataset_config()
    config["datasets"][dataset_id] = {
        "class": params[dataset_format]["class"],
        "description": dataset_description,
        "type": params[dataset_format]["type"],
        "splits": list(dataset_data.keys()),
        "enabled": False,
    }
    save_dataset_config(config)


def upload_model_outputs(dataset, split, setup_id, model_outputs):
    path = Path(f"{dataset.output_path}/{split}")
    path.mkdir(parents=True, exist_ok=True)

    model_outputs = model_outputs.strip()
    generated = [{"out": out} for out in model_outputs.split("\n")]

    setup_id = slugify(setup_id)

    if setup_id in dataset.outputs[split]:
        raise ValueError(f"Output for {setup_id} already exists in {split}")

    if len(generated) != len(dataset.examples[split]):
        raise ValueError(
            f"Output count mismatch for {setup_id} in {split}: {len(generated)} vs {len(dataset.examples[split])}"
        )

    j = {
        "dataset": dataset.id,
        "split": split,
        "setup": {"id": setup_id},
        "generated": generated,
    }
    dataset.outputs[split][setup_id] = j

    with open(f"{path}/{setup_id}.json", "w") as f:
        json.dump(j, f, indent=4)


def delete_model_outputs(dataset, split, setup_id):
    path = Path(f"{dataset.output_path}/{split}/{setup_id}.json")

    if path.exists():
        path.unlink()

    dataset.outputs[split].pop(setup_id, None)


def llm_eval_new(campaign_id, config, campaign_data, datasets, overwrite=False):
    campaign_id = slugify(campaign_id)

    # create a new directory
    if os.path.exists(os.path.join(ANNOTATIONS_DIR, campaign_id)):
        if not overwrite:
            raise ValueError(f"Campaign {campaign_id} already exists")
        else:
            shutil.rmtree(os.path.join(ANNOTATIONS_DIR, campaign_id))

    os.makedirs(os.path.join(ANNOTATIONS_DIR, campaign_id, "files"), exist_ok=True)

    # create the annotation CSV
    db = generate_llm_eval_db(datasets, campaign_data)
    db_path = os.path.join(ANNOTATIONS_DIR, campaign_id, "db.csv")
    logger.info(f"DB with {len(db)} free examples created for {campaign_id} at {db_path}")
    db.to_csv(db_path, index=False)

    # save metadata
    metadata_path = os.path.join(ANNOTATIONS_DIR, campaign_id, "metadata.json")
    logger.info(f"Metadata for {campaign_id} saved at {metadata_path}")
    with open(metadata_path, "w") as f:
        json.dump(
            {
                "id": campaign_id,
                "created": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "source": "llm_eval",
                "status": "new",
                "config": config,
            },
            f,
            indent=4,
        )

    # create the campaign object
    campaign = ModelCampaign(campaign_id=campaign_id)
    return campaign

def llm_d2t_new(campaign_id, config, campaign_data, datasets, overwrite=False):
    campaign_id = slugify(campaign_id)

    # create a new directory
    if os.path.exists(os.path.join(ANNOTATIONS_DIR, campaign_id)):
        if not overwrite:
            raise ValueError(f"Campaign {campaign_id} already exists")
        else:
            shutil.rmtree(os.path.join(ANNOTATIONS_DIR, campaign_id))

    os.makedirs(os.path.join(ANNOTATIONS_DIR, campaign_id, "files"), exist_ok=True)

    # create the annotation CSV
    db = generate_llm_eval_db(datasets, campaign_data)
    db_path = os.path.join(ANNOTATIONS_DIR, campaign_id, "db.csv")
    logger.info(f"DB with {len(db)} free examples created for {campaign_id} at {db_path}")
    db.to_csv(db_path, index=False)

    # save metadata
    metadata_path = os.path.join(ANNOTATIONS_DIR, campaign_id, "metadata.json")
    logger.info(f"Metadata for {campaign_id} saved at {metadata_path}")
    with open(metadata_path, "w") as f:
        json.dump(
            {
                "id": campaign_id,
                "created": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "source": "llm_d2t",
                "status": "new",
                "config": config,
            },
            f,
            indent=4,
        )

    # create the campaign object
    campaign = ModelCampaign(campaign_id=campaign_id)
    return campaign


def generate_default_id(campaign_index, prefix):
    i = 1
    default_campaign_id = f"{prefix}-{i}"
    while default_campaign_id in campaign_index:
        default_campaign_id = f"{prefix}-{i}"
        i += 1

    return default_campaign_id


def get_model_outs(app):
    datasets = app.db["datasets_obj"]
    model_outs = {x: [] for x in ["datasets", "splits", "setup_ids", "valid_triplets"]}

    for dataset_id, dataset in datasets.items():
        splits = dataset.get_splits()
        model_outs["datasets"].append(dataset_id)

        for split in splits:
            output_setups = dataset.outputs[split].keys()
            model_outs["splits"].append(split)

            for setup_id in output_setups:
                model_outs["setup_ids"].append(setup_id)
                model_outs["valid_triplets"].append(
                    {
                        "dataset": dataset_id,
                        "split": split,
                        "setup_id": setup_id,
                        "example_count": dataset.get_example_count(split),
                    }
                )

    for key in ["datasets", "splits", "setup_ids"]:
        model_outs[key] = sorted(list(set(model_outs[key])))

    return model_outs


def check_login(app, username, password):
    return username == app.config["login"]["username"] and password == app.config["login"]["password"]


def save_annotation(save_dir, metric, dataset_id, split, setup_id, example_idx, annotation_set, start_time):
    # save the annotation
    annotator_id = metric.get_annotator_id()

    annotation = {
        "annotator_id": annotator_id,
        "dataset": dataset_id,
        "setup": {"id": setup_id, "model": setup_id},
        "split": split,
        "example_idx": example_idx,
        "annotations": annotation_set,
    }

    # save the annotation
    with open(os.path.join(save_dir, f"{annotator_id}-{dataset_id}-{split}-{start_time}.jsonl"), "a") as f:
        f.write(json.dumps(annotation) + "\n")
    return annotation


def duplicate_eval(app, campaign_id, new_campaign_id):
    # copy the directory except for the annotations
    old_campaign_dir = os.path.join(ANNOTATIONS_DIR, campaign_id)
    new_campaign_dir = os.path.join(ANNOTATIONS_DIR, new_campaign_id)

    # if new campaign dir exists, return error
    if os.path.exists(new_campaign_dir):
        return error("Campaign already exists")

    shutil.copytree(old_campaign_dir, new_campaign_dir, ignore=shutil.ignore_patterns("files"))

    # copy the db
    old_db = pd.read_csv(os.path.join(old_campaign_dir, "db.csv"))
    new_db = old_db.copy()
    new_db["status"] = "free"

    new_db.to_csv(os.path.join(new_campaign_dir, "db.csv"), index=False)

    # update the metadata
    metadata_path = os.path.join(new_campaign_dir, "metadata.json")
    with open(metadata_path) as f:
        metadata = json.load(f)

    metadata["id"] = new_campaign_id
    metadata["created"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    metadata["status"] = "new"

    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=4)

    return success()


def save_config(filename, config, mode):
    # https://github.com/yaml/pyyaml/issues/121#issuecomment-1018117110
    def yaml_multiline_string_pipe(dumper, data):
        text_list = [line.rstrip() for line in data.splitlines()]
        fixed_data = "\n".join(text_list)
        if len(text_list) > 1:
            return dumper.represent_scalar("tag:yaml.org,2002:str", fixed_data, style="|")
        return dumper.represent_scalar("tag:yaml.org,2002:str", fixed_data)

    yaml.add_representer(str, yaml_multiline_string_pipe)

    if mode == "llm_eval":
        save_dir = LLM_CONFIG_DIR
    elif mode == "llm_d2t":
        save_dir = LLM_D2T_DIR
    else:
        save_dir = CROWDSOURCING_CONFIG_DIR

    #save_dir = LLM_CONFIG_DIR if mode == "llm_eval" else CROWDSOURCING_CONFIG_DIR

    with open(os.path.join(save_dir, filename), "w") as f:
        yaml.dump(config, f, indent=2, allow_unicode=True)


def parse_llm_config(config):
    config = {
        "type": config.get("metricType"),
        "model": config.get("modelName"),
        "prompt_template": config.get("promptTemplate"),
        "system_msg": config.get("systemMessage"),
        "api_url": config.get("apiUrl"),
        "model_args": config.get("modelArguments"),
        "extra_args": config.get("extraArguments"),
        "annotation_span_categories": config.get("annotationSpanCategories"),
    }
    return config


def parse_crowdsourcing_config(config):
    config = {
        "examples_per_batch": int(config.get("examplesPerBatch")),
        "idle_time": int(config.get("idleTime")),
        "completion_code": config.get("completionCode"),
        "sort_order": config.get("sortOrder"),
        "annotation_span_categories": config.get("annotationSpanCategories"),
    }

    return config


def run_llm_eval(campaign_id, announcer, campaign, datasets, metric, threads):
    start_time = int(time.time())

    save_dir = os.path.join(ANNOTATIONS_DIR, campaign_id, "files")
    os.makedirs(save_dir, exist_ok=True)

    # set metadata status
    campaign.metadata["status"] = "running"
    campaign.update_metadata()
    db = campaign.db

    logger.info(f"Starting LLM evaluation for {campaign_id}")

    for i, row in db.iterrows():
        if threads[campaign_id]["running"] == False:
            break

        if row["status"] == "finished":
            continue

        dataset_id = row["dataset"]
        split = row["split"]
        setup_id = row["setup_id"]
        example_idx = row["example_idx"]

        dataset = datasets[dataset_id]
        example = dataset.get_example(split, example_idx)

        output = dataset.get_generated_output_by_idx(split=split, output_idx=example_idx, setup_id=setup_id)

        annotation_set = metric.annotate_example(example, output)

        if "error" in annotation_set:
            return error(annotation_set["error"])

        annotation = save_annotation(
            save_dir, metric, dataset_id, split, setup_id, example_idx, annotation_set, start_time
        )

        db.loc[i, "status"] = "finished"
        campaign.update_db(db)

        # overview = campaign.get_overview()
        # finished_examples = overview[overview["status"] == "finished"]

        finished_examples_cnt = len(campaign.get_finished_examples())
        payload = {"finished_examples_cnt": finished_examples_cnt, "annotation": annotation}

        msg = format_sse(data=json.dumps(payload))
        if announcer is not None:
            announcer.announce(msg=msg)
        logger.info(f"{campaign_id}: {finished_examples_cnt}/{len(db)} examples")

    # if all fields are finished, set the metadata to finished
    if len(db.status.unique()) == 1 and db.status.unique()[0] == "finished":
        campaign.metadata["status"] = "finished"
        campaign.update_metadata()

    return jsonify(success=True, status=campaign.metadata["status"])


def run_llm_d2t(campaign_id, announcer, campaign, datasets, metric, threads):
    start_time = int(time.time())

    save_dir = os.path.join(ANNOTATIONS_DIR, campaign_id, "files")
    os.makedirs(save_dir, exist_ok=True)

    # set metadata status
    campaign.metadata["status"] = "running"
    campaign.update_metadata()
    db = campaign.db

    logger.info(f"Starting LLM generation for {campaign_id}")

    for i, row in db.iterrows():
        if threads[campaign_id]["running"] == False:
            break

        if row["status"] == "finished":
            continue

        dataset_id = row["dataset"]
        split = row["split"]
        setup_id = row["setup_id"]
        example_idx = row["example_idx"]

        dataset = datasets[dataset_id]
        example = dataset.get_example(split, example_idx)

        output = dataset.get_generated_output_by_idx(split=split, output_idx=example_idx, setup_id=setup_id)

        annotation_set = metric.annotate_example(example, output)

        #if "error" in annotation_set:
        #    return error(annotation_set["error"])

        annotation = save_annotation(
            save_dir, metric, dataset_id, split, setup_id, example_idx, annotation_set, start_time
        )

        db.loc[i, "status"] = "finished"
        campaign.update_db(db)

        # overview = campaign.get_overview()
        # finished_examples = overview[overview["status"] == "finished"]

        finished_examples_cnt = len(campaign.get_finished_examples())
        payload = {"finished_examples_cnt": finished_examples_cnt, "annotation": annotation}

        msg = format_sse(data=json.dumps(payload))
        if announcer is not None:
            announcer.announce(msg=msg)
        logger.info(f"{campaign_id}: {finished_examples_cnt}/{len(db)} examples")

    # if all fields are finished, set the metadata to finished
    if len(db.status.unique()) == 1 and db.status.unique()[0] == "finished":
        campaign.metadata["status"] = "finished"
        campaign.update_metadata()

    return jsonify(success=True, status=campaign.metadata["status"])