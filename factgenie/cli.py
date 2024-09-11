#!/usr/bin/env python3

# The cli is CLI entry point.
# The local imports in individual functions make CLI way faster.
# Use them as much as possible and minimize imports at the top of the file.
import click

from flask.cli import FlaskGroup


@click.command()
def list_datasets():
    import yaml
    from factgenie.utils import DATASET_CONFIG_PATH

    """List all available datasets."""
    with open(DATASET_CONFIG_PATH) as f:
        config = yaml.safe_load(f)

    for dataset_id, _ in config["datasets"].items():
        print(dataset_id)


@click.command()
@click.option("--campaign_id", required=True, type=str)
@click.option("--dataset_id", required=True, type=str)
@click.option("--split", required=True, type=str)
@click.option("--setup_id", required=True, type=str)
@click.option(
    "--llm_metric_config", required=True, type=str, help="Path to the metric config file or just the metric name."
)
@click.option("--overwrite", is_flag=True, default=False, help="Remove existing campaign if it exists.")
def run_llm_eval(campaign_id: str, dataset_id: str, split: str, setup_id: str, llm_metric_config: str, overwrite: bool):
    """Runs the LLM evaluation from CLI with no web server."""
    from slugify import slugify
    from factgenie import utils
    from factgenie.metrics import LLMMetricFactory

    campaign_id = slugify(campaign_id)
    campaign_data = [{"dataset": dataset_id, "split": split, "setup_id": setup_id}]

    config = utils.load_dataset_config()
    dataset_config = config["datasets"][dataset_id]
    datasets = {dataset_id: utils.instantiate_dataset(dataset_id, dataset_config)}

    configs = utils.load_configs("llm_eval")  # Loads all metrics configs factgenie/llm-evals/*.yaml
    metric_config = configs[llm_metric_config]
    campaign = utils.llm_eval_new(campaign_id, metric_config, campaign_data, datasets, overwrite=overwrite)

    # mockup objects useful for interactivity
    threads = {campaign_id: {"running": True}}
    announcer = None

    metric = LLMMetricFactory.from_config(metric_config)

    return utils.run_llm_eval(campaign_id, announcer, campaign, datasets, metric, threads)

@click.option("--overwrite", is_flag=True, default=False, help="Remove existing campaign if it exists.")
def run_llm_d2t(campaign_id: str, dataset_id: str, split: str, llm_metric_config: str, overwrite: bool):
    """Runs the LLM generation from CLI with no web server."""
    from slugify import slugify
    from factgenie import utils
    from factgenie.metrics import LLMMetricFactory

    campaign_id = slugify(campaign_id)
    campaign_data = [{"dataset": dataset_id, "split": split}]

    config = utils.load_dataset_config()
    dataset_config = config["datasets"][dataset_id]
    datasets = {dataset_id: utils.instantiate_dataset(dataset_id, dataset_config)}

    configs = utils.load_configs("llm_d2t")  # Loads all metrics configs factgenie/llm-evals/*.yaml
    metric_config = configs[llm_metric_config]
    campaign = utils.llm_d2t_new(campaign_id, metric_config, campaign_data, datasets, overwrite=overwrite)

    # mockup objects useful for interactivity
    threads = {campaign_id: {"running": True}}
    announcer = None

    metric = LLMMetricFactory.from_config(metric_config)

    return utils.run_llm_d2t(campaign_id, announcer, campaign, datasets, metric, threads)



def create_app(**kwargs):
    import yaml
    import logging
    import coloredlogs
    import os
    from factgenie.main import app
    from factgenie import utils

    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yml")) as f:
        config = yaml.safe_load(f)

    app.config.update(config)
    app.config["root_dir"] = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir)

    app.db["datasets_obj"] = utils.instantiate_datasets()

    if config["debug"] is False:
        logging.getLogger("werkzeug").disabled = True

    logger = logging.getLogger(__name__)
    logger.info("Application ready")

    file_handler = logging.FileHandler("error.log")
    file_handler.setLevel(logging.ERROR)

    logging.basicConfig(
        format="%(levelname)s (%(filename)s:%(lineno)d) - %(message)s",
        level=app.config.get("logging_level", "INFO"),
        handlers=[file_handler, logging.StreamHandler()],
    )
    logger = logging.getLogger(__name__)
    coloredlogs.install(
        level=app.config.get("logging_level", "INFO"),
        logger=logger,
        fmt="%(asctime)s %(levelname)s %(filename)s:%(lineno)d %(message)s",
    )

    app.config.update(SECRET_KEY=os.urandom(24))

    # register CLI commands
    app.cli.add_command(run_llm_eval)
    #app.cli.add_command(run_llm_d2t)
    app.cli.add_command(list_datasets)

    return app


@click.group(cls=FlaskGroup, create_app=create_app)
def run():
    pass
