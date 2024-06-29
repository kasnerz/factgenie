#!/usr/bin/env python3

# The cli is CLI entry point.
# The local imports in individual functions make CLI way faster.
# Use them as much as possible and minimize imports at the top of the file.
import click
from flask.cli import FlaskGroup



@click.command()
def list_datasets():
    """List all available datasets."""
    from factgenie.loaders import DATASET_CLASSES

    for dataset_name in DATASET_CLASSES.keys():
        print(dataset_name)


@click.command()
@click.option("--campaign_name", required=True, type=str)
@click.option("--dataset_name", required=True, type=str)
@click.option("--split", required=True, type=str)
@click.option("--llm_output_name", required=True, type=str)
@click.option("--llm_metric_config", required=True, type=str, help="Path to the metric config file or just the metric name.")
def run_llm_eval(campaign_name: str, dataset_name: str, split: str, llm_output_name: str, llm_metric_config: str):
    """Runs the LLM evaluation from CLI wit no web server."""
    from pathlib import Path
    import yaml
    from slugify import slugify
    from factgenie import utils
    from factgenie.loaders import DATASET_CLASSES
    from factgenie.evaluate import LLMMetricFactory

    campaign_id = slugify(campaign_name)
    campaign_data = [{"dataset": dataset_name, "split": split, "setup_id":llm_output_name}]

    if Path(llm_metric_config).exists():
        with open(llm_metric_config) as f:
            config = yaml.safe_load(f)
            metric_name = LLMMetricFactory.get_metric_name(config)
    else:
        # Validates that directly given metric name makes sense. It is possible just to use the name 
        # metric_index loads all existing metric configs: factgenie/llm-evals/*.yaml
        metric_name = LLMMetricFactory.get_metric_name({"metric_name": llm_metric_config})


    DATASETS = dict((name, cls()) for name, cls in DATASET_CLASSES.items())  # instantiate all datasets
    metrics_index = utils.generate_metric_index()  # Loads all metrics configs factgenie/llm-evals/*.yaml
    metric = metrics_index[metric_name]
    campaign = utils.llm_eval_new(campaign_id, metric, campaign_data, DATASETS)

    # mockup objects useful for interactivity
    threads = {campaign_id: {"running": True}}
    announcer = None

    return utils.run_llm_eval(campaign_id, announcer, campaign, DATASETS, metric, threads, metric_name)

from .main import app


def create_app(**kwargs):
    from factgenie.loaders import DATASET_CLASSES
    import yaml
    import logging
    import coloredlogs
    import os
    from .main import app

    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yml")) as f:
        config = yaml.safe_load(f)

    app.config.update(config)
    app.config["root_dir"] = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir)

    app.db["datasets_obj"] = {}

    for dataset_name in DATASET_CLASSES.keys():
        app.db["datasets_obj"][dataset_name] = DATASET_CLASSES[dataset_name]()

    if config["debug"] is False:
        logging.getLogger("werkzeug").disabled = True

    logger = logging.getLogger(__name__)
    logger.info("Application ready")

    file_handler = logging.FileHandler("error.log")
    file_handler.setLevel(logging.ERROR)

    logging.basicConfig(
        format="%(levelname)s - %(message)s",
        level=app.config.get("logging_level", "INFO"),
        handlers=[file_handler, logging.StreamHandler()],
    )
    logger = logging.getLogger(__name__)
    coloredlogs.install(level=app.config.get("logging_level", "INFO"), logger=logger, fmt="%(asctime)s %(levelname)s %(message)s")

    app.config.update(SECRET_KEY=os.urandom(24))

    # register CLI commands 
    app.cli.add_command(run_llm_eval)
    app.cli.add_command(list_datasets)

    return app


@click.group(cls=FlaskGroup, create_app=create_app)
def run():
    pass