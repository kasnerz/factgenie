#!/usr/bin/env python3
import os
import json
import time
import logging
import pandas as pd
import time
import threading
import traceback
import shutil
import datetime
import zipfile
from flask import Flask, render_template, jsonify, request, Response, make_response, redirect, url_for
from collections import defaultdict
import urllib.parse
from slugify import slugify
from io import BytesIO

from factgenie.campaigns import Campaign, ModelCampaign, HumanCampaign
from factgenie.metrics import LLMMetricFactory
import factgenie.utils as utils

DIR_PATH = os.path.dirname(__file__)
TEMPLATES_DIR = os.path.join(DIR_PATH, "templates")
STATIC_DIR = os.path.join(DIR_PATH, "static")
ANNOTATIONS_DIR = os.path.join(DIR_PATH, "annotations")


app = Flask("factgenie", template_folder=TEMPLATES_DIR, static_folder=STATIC_DIR)
app.db = {}
app.db["annotation_index"] = {}
app.db["lock"] = threading.Lock()
app.db["threads"] = {}
app.db["announcers"] = {}

logger = logging.getLogger(__name__)


# -----------------
# Jinja filters
# -----------------
@app.template_filter("ctime")
def timectime(timestamp):
    try:
        s = datetime.datetime.fromtimestamp(timestamp)
        return s.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return timestamp


@app.template_filter("elapsed")
def time_elapsed(timestamp):
    try:
        s = datetime.datetime.fromtimestamp(timestamp)
        diff = str(datetime.datetime.now() - s)
        return diff.split(".")[0]
    except:
        return timestamp


@app.template_filter("annotate_url")
def annotate_url(current_url):
    # get the base url (without any "browse", "crowdsourcing" or "crowdsourcing/campaign" in it)
    parsed = urllib.parse.urlparse(current_url)
    base_url = f"{parsed.scheme}://{parsed.netloc}/"
    return f"{base_url}annotate"


# -----------------
# Decorators
# -----------------


# Very simple decorator to protect routes
def login_required(f):
    def wrapper(*args, **kwargs):
        if app.config["login"]["active"]:
            auth = request.cookies.get("auth")
            if not auth:
                return redirect(url_for("login"))
            username, password = auth.split(":")
            if not utils.check_login(app, username, password):
                return redirect(url_for("login"))

        return f(*args, **kwargs)

    wrapper.__name__ = f.__name__
    return wrapper


# -----------------
# Flask endpoints
# -----------------
@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    logger.info(f"Main page loaded")

    return render_template(
        "index.html",
        host_prefix=app.config["host_prefix"],
    )


@app.route("/about", methods=["GET", "POST"])
@login_required
def about():
    logger.info(f"About page loaded")

    return render_template(
        "about.html",
        host_prefix=app.config["host_prefix"],
    )


@app.route("/annotate", methods=["GET", "POST"])
def annotate():
    logger.info(f"Annotate page loaded")

    utils.generate_campaign_index(app)
    campaign_id = request.args.get("campaign")
    campaign = app.db["campaign_index"]["human"][campaign_id]
    compl_code = campaign.metadata["prolific_code"]
    prolific_pid = request.args.get("PROLIFIC_PID", "test")
    session_id = request.args.get("SESSION_ID", "test")
    study_id = request.args.get("STUDY_ID", "test")

    db = campaign.db
    metadata = campaign.metadata
    annotation_set = utils.get_annotator_batch(app, campaign, db, prolific_pid, session_id, study_id)
    return render_template(
        f"campaigns/{campaign.campaign_id}/annotate.html",
        host_prefix=app.config["host_prefix"],
        annotation_set=annotation_set,
        annotator_id=prolific_pid,
        compl_code=compl_code,
        metadata=metadata,
    )


@app.route("/annotations", methods=["GET", "POST"])
@login_required
def manage_annotations():
    utils.generate_annotation_index(app)

    annotations = app.db["annotation_index"]

    return render_template("manage_annotations.html", annotations=annotations, host_prefix=app.config["host_prefix"])


@app.route("/browse", methods=["GET", "POST"])
@login_required
def browse():
    logger.info(f"Browse page loaded")

    utils.generate_annotation_index(app)

    dataset_name = request.args.get("dataset")
    split = request.args.get("split")
    example_idx = request.args.get("example_idx")

    if dataset_name and split and example_idx:
        display_example = {"dataset": dataset_name, "split": split, "example_idx": int(example_idx)}
        logger.info(f"Serving permalink for {display_example}")
    else:
        display_example = None

    datasets = utils.get_dataset_overview(app)

    return render_template(
        "browse.html",
        display_example=display_example,
        datasets=datasets,
        host_prefix=app.config["host_prefix"],
        annotations=app.db["annotation_index"],
    )


@app.route("/crowdsourcing", methods=["GET", "POST"])
@login_required
def crowdsourcing():
    logger.info(f"Crowdsourcing page loaded")

    datasets = app.db["datasets_obj"]
    model_outs = {x: [] for x in ["datasets", "splits", "setup_ids", "valid_triplets"]}

    for dataset_name, dataset in datasets.items():
        splits = dataset.get_splits()
        model_outs["datasets"].append(dataset_name)

        for split in splits:
            output_setups = dataset.outputs[split].keys()
            model_outs["splits"].append(split)

            for setup_id in output_setups:
                model_outs["setup_ids"].append(setup_id)
                model_outs["valid_triplets"].append(
                    {
                        "dataset": dataset_name,
                        "split": split,
                        "setup_id": setup_id,
                        "example_count": dataset.get_example_count(split),
                    }
                )

    for key in ["datasets", "splits", "setup_ids"]:
        model_outs[key] = sorted(list(set(model_outs[key])))

    utils.generate_campaign_index(app)

    campaign_index = app.db["campaign_index"]["human"]
    campaigns = defaultdict(dict)

    for campaign_id, campaign in campaign_index.items():
        campaigns[campaign_id]["metadata"] = campaign.metadata
        campaigns[campaign_id]["stats"] = campaign.get_stats()

    default_campaign_id = utils.generate_default_id(campaign_index=campaign_index, prefix="campaign")

    return render_template(
        "crowdsourcing.html",
        model_outs=model_outs,
        campaigns=campaigns,
        default_campaign_id=default_campaign_id,
        is_password_protected=app.config["login"]["active"],
        host_prefix=app.config["host_prefix"],
    )


@app.route("/crowdsourcing/detail", methods=["GET", "POST"])
@login_required
def crowdsourcing_detail():
    utils.generate_campaign_index(app)

    campaign_id = request.args.get("campaign")
    db = app.db["campaign_index"]["human"][campaign_id].db
    # replace NaN with empty string
    db = db.where(pd.notnull(db), "")

    # group by batch idx
    # add a column with the number of examples for each batch
    # for other columns keep first item
    db = db.groupby("batch_idx").agg(
        {
            "dataset": "first",
            "split": "first",
            "example_idx": "count",
            "setup_id": "first",
            "status": "first",
            "start": "first",
            "annotator_id": "first",
        }
    )
    db = db.rename(columns={"example_idx": "example_cnt"}).reset_index()
    db = db.to_dict(orient="records")

    return render_template(
        "crowdsourcing_detail.html",
        campaign_id=campaign_id,
        db=db,
        host_prefix=app.config["host_prefix"],
    )


@app.route("/crowdsourcing/new", methods=["POST"])
@login_required
def crowdsourcing_new():
    data = request.get_json()

    campaign_id = slugify(data.get("campaignId"))
    examples_per_batch = int(data.get("examplesPerBatch"))
    idle_time = int(data.get("idleTime"))
    prolific_code = data.get("prolificCode")
    campaign_data = data.get("campaignData")
    annotation_span_categories = data.get("annotationSpanCategories")
    sort_order = data.get("sortOrder")

    # create a new directory
    if os.path.exists(os.path.join(ANNOTATIONS_DIR, campaign_id)):
        return jsonify({"error": "Campaign already exists"})

    os.makedirs(os.path.join(ANNOTATIONS_DIR, campaign_id, "files"), exist_ok=True)

    # create the annotation CSV
    db = utils.generate_campaign_db(app, campaign_data, examples_per_batch, sort_order)
    db.to_csv(os.path.join(ANNOTATIONS_DIR, campaign_id, "db.csv"), index=False)

    # save metadata
    with open(os.path.join(ANNOTATIONS_DIR, campaign_id, "metadata.json"), "w") as f:
        json.dump(
            {
                "id": campaign_id,
                "idle_time": idle_time,
                "prolific_code": prolific_code,
                # "data": campaign_data,
                "sort_order": sort_order,
                "source": "human",
                "annotation_span_categories": annotation_span_categories,
                "created": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            },
            f,
            indent=4,
        )

    # copy templates/campaigns/annotate_default.html into templates/campaigns/{campaign_id} as "annotate.html"
    os.makedirs(os.path.join(TEMPLATES_DIR, "campaigns", campaign_id), exist_ok=True)

    shutil.copy(
        os.path.join(TEMPLATES_DIR, "campaigns", "annotate_default.html"),
        os.path.join(TEMPLATES_DIR, "campaigns", campaign_id, "annotate.html"),
    )

    # create the campaign object
    campaign = HumanCampaign(campaign_id=campaign_id)

    app.db["campaign_index"]["human"][campaign_id] = campaign

    return utils.success()


@app.route("/datasets", methods=["GET", "POST"])
@login_required
def manage_datasets():
    datasets = utils.get_dataset_overview(app)

    return render_template("manage_datasets.html", datasets=datasets, host_prefix=app.config["host_prefix"])


@app.route("/delete_campaign", methods=["POST"])
@login_required
def delete_campaign():
    data = request.get_json()
    campaign_name = data.get("campaignId")
    source = data.get("source")

    shutil.rmtree(os.path.join(ANNOTATIONS_DIR, campaign_name))

    if os.path.exists(os.path.join(TEMPLATES_DIR, "campaigns", campaign_name)):
        shutil.rmtree(os.path.join(TEMPLATES_DIR, "campaigns", campaign_name))

    del app.db["campaign_index"][source][campaign_name]

    return utils.success()


@app.route("/example", methods=["GET", "POST"])
def render_example():
    dataset_name = request.args.get("dataset")
    split = request.args.get("split")
    example_idx = int(request.args.get("example_idx"))

    try:
        example_data = utils.get_example_data(app, dataset_name, split, example_idx)
    except Exception as e:
        traceback.print_exc()
        logger.error(f"Error while getting example data: {e}")
        example_data = {}

    return jsonify(example_data)


@app.route("/export_annotations", methods=["GET", "POST"])
@login_required
def export_annotations():
    zip_buffer = BytesIO()
    campaign_id = request.args.get("campaign")

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


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if utils.check_login(app, username, password):
            # redirect to the home page ("/")
            resp = make_response(redirect("/"))
            resp.set_cookie("auth", f"{username}:{password}")
            return resp
        else:
            return "Login failed", 401
    return render_template("login.html")


@app.route("/llm_eval", methods=["GET", "POST"])
@login_required
def llm_eval():
    logger.info(f"LLM eval page loaded")

    utils.generate_campaign_index(app)

    campaign_index = app.db["campaign_index"]["model"]
    campaigns = defaultdict(dict)

    for campaign_id, campaign in campaign_index.items():
        campaigns[campaign_id]["metadata"] = campaign.metadata
        campaigns[campaign_id]["stats"] = campaign.get_stats()

    return render_template(
        "llm_eval.html",
        campaigns=campaigns,
        host_prefix=app.config["host_prefix"],
    )


@app.route("/llm_eval/create", methods=["GET", "POST"])
@login_required
def llm_eval_create():
    data = request.get_json()

    llm_config = data.get("llmConfig")
    campaign_id = data.get("campaignId")
    campaign_data = data.get("campaignData")

    app.db["metric_index"] = utils.generate_metric_index()

    metric = app.db["metric_index"][llm_config]
    datasets = app.db["datasets_obj"]

    campaign = utils.llm_eval_new(campaign_id, metric, campaign_data, datasets)
    app.db["campaign_index"][campaign_id] = campaign

    return utils.success()


@app.route("/llm_eval/detail", methods=["GET", "POST"])
@login_required
def llm_eval_detail():
    utils.generate_campaign_index(app)

    campaign_id = request.args.get("campaign")
    campaign = app.db["campaign_index"]["model"][campaign_id]

    if campaign.metadata["status"] == "running" and not app.db["announcers"].get(campaign_id):
        campaign.metadata["status"] = "paused"
        campaign.update_metadata()

    overview = campaign.get_overview()
    finished_examples = overview[overview["status"] == "finished"]

    overview = overview.to_dict(orient="records")
    finished_examples = finished_examples.to_dict(orient="records")

    return render_template(
        "llm_eval_detail.html",
        campaign_id=campaign_id,
        overview=overview,
        finished_examples=finished_examples,
        metadata=campaign.metadata,
        host_prefix=app.config["host_prefix"],
    )


@app.route("/llm_eval/new", methods=["GET", "POST"])
@login_required
def llm_eval_new():
    datasets = app.db["datasets_obj"]
    model_outs = {x: [] for x in ["datasets", "splits", "setup_ids", "valid_triplets"]}

    for dataset_name, dataset in datasets.items():
        splits = dataset.get_splits()
        model_outs["datasets"].append(dataset_name)

        for split in splits:
            output_setups = dataset.outputs[split].keys()
            model_outs["splits"].append(split)

            for setup_id in output_setups:
                model_outs["setup_ids"].append(setup_id)
                model_outs["valid_triplets"].append(
                    {
                        "dataset": dataset_name,
                        "split": split,
                        "setup_id": setup_id,
                        "example_count": dataset.get_example_count(split),
                    }
                )

    for key in ["datasets", "splits", "setup_ids"]:
        model_outs[key] = sorted(list(set(model_outs[key])))

    # get a list of available metrics
    app.db["metric_index"] = utils.generate_metric_index()
    llm_metrics = {metric: metrics.get_config() for metric, metrics in app.db["metric_index"].items()}

    metric_types = list(LLMMetricFactory.metric_classes().keys())

    utils.generate_campaign_index(app)
    campaign_index = app.db["campaign_index"]["model"]

    default_campaign_id = utils.generate_default_id(campaign_index=campaign_index, prefix="llm-eval")

    return render_template(
        "llm_eval_new.html",
        default_campaign_id=default_campaign_id,
        model_outs=model_outs,
        llm_metrics=llm_metrics,
        metric_types=metric_types,
        host_prefix=app.config["host_prefix"],
    )


@app.route("/llm_eval/run", methods=["POST"])
@login_required
def llm_eval_run():
    data = request.get_json()
    campaign_id = data.get("campaignId")

    app.db["announcers"][campaign_id] = announcer = utils.MessageAnnouncer()

    # TODO: so far it seems that the app is actually more responsive without threads :-O
    # from threading import Thread
    # thread = Thread(target=utils.run_llm_eval, args=(app, campaign_id))
    # thread.daemon = True
    # thread.start()

    app.db["threads"][campaign_id] = {
        "running": True,
    }
    # return utils.run_llm_eval(app, campaign_id)
    app.db["metric_index"] = utils.generate_metric_index()

    campaign = app.db["campaign_index"]["model"][campaign_id]

    threads = app.db["threads"]
    datasets = app.db["datasets_obj"]

    metric_name = campaign.metadata["metric"]
    metric = app.db["metric_index"][metric_name]

    return utils.run_llm_eval(campaign_id, announcer, campaign, datasets, metric, threads, metric_name)


@app.route("/llm_eval/progress/<campaign_id>", methods=["GET"])
@login_required
def listen(campaign_id):
    if not app.db["announcers"].get(campaign_id):
        return Response(status=404)

    def stream():
        messages = app.db["announcers"][campaign_id].listen()
        while True:
            msg = messages.get()
            yield msg

    return Response(stream(), mimetype="text/event-stream")


@app.route("/llm_eval/pause", methods=["POST"])
@login_required
def llm_eval_pause():
    data = request.get_json()
    campaign_id = data.get("campaignId")
    app.db["threads"][campaign_id]["running"] = False

    campaign = app.db["campaign_index"]["model"][campaign_id]
    campaign.metadata["status"] = "paused"
    campaign.update_metadata()

    resp = jsonify(success=True, status=campaign.metadata["status"])
    return resp


@app.route("/submit_annotations", methods=["POST"])
def submit_annotations():
    logger.info(f"Received annotations")
    data = request.get_json()
    campaign_id = data["campaign_id"]
    annotation_set = data["annotation_set"]
    annotator_id = data["annotator_id"]
    now = int(time.time())

    save_dir = os.path.join(ANNOTATIONS_DIR, campaign_id, "files")
    os.makedirs(save_dir, exist_ok=True)
    campaign = app.db["campaign_index"]["human"][campaign_id]

    with app.db["lock"]:
        db = campaign.db
        batch_idx = annotation_set[0]["batch_idx"]

        with open(os.path.join(save_dir, f"{batch_idx}-{annotator_id}-{now}.jsonl"), "w") as f:
            for row in annotation_set:
                f.write(json.dumps(row) + "\n")

        # db[db["batch_idx"] == batch_idx]["status"] = "finished"

        # we cannot do that anymore:
        # A value is trying to be set on a copy of a slice from a DataFrame.
        # Try using .loc[row_indexer,col_indexer] = value instead

        # See the caveats in the documentation: https://pandas.pydata.org/pandas-docs/stable/user_guide/indexing.html#returning-a-view-versus-a-copy
        #   db[db["batch_idx"] == batch_idx]["status"] = "finished"

        db.loc[db["batch_idx"] == batch_idx, "status"] = "finished"

        db.to_csv(os.path.join(ANNOTATIONS_DIR, campaign_id, "db.csv"), index=False)
        logger.info(f"Annotations for {campaign_id} (batch {batch_idx}) saved")

    return jsonify({"status": "success"})
