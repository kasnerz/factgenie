# factgenie

Visualize and annotate errors in LLM outputs.

🚧 **The project is in progress, use at your own risk.** 🚧

<img src="factgenie/static/img/github/browse.png" width="100%" alt="Main screen" />

## Intro
Outputs from large language models (LLMs) may contain factual errors. 

With **factgenie**, you can have the errors highlighted 🌈:
- From humans through a crowdsourcing service.
- From LLMs through an API.

How does **factgenie** help with that?
1. It helps you **create a user-friendly website** for collecting annotations from human crowdworkers.
2. It helps you with **LLM API calls** for collecting equivalent annotations from LLM-based evaluators.
3. It provides you **visualization interface** for inspecting the annotated outputs.

What does factgenie **not help with** is collecting the data or model outputs (we assume that you already have these), starting the crowdsourcing campaign (for that, you need to use a service such as [Prolific.com](https://prolific.com)) or running the LLM evaluators (for that, you need a local framework such as [Ollama](https://ollama.com) or a proprietary API).

---
*Please, keep in mind that this project is a spin-off of our custom code we used for research experiments. It may need additional effort on your side to make everything work as expected :wink:*

----

## Quickstart
Make sure you have Python 3 installed (the project is tested with Python 3.10).

The following commands install the package, start the web server, and open the front page in the browser:

```
pip install -e .
factgenie run --host=127.0.0.1 --port 5000
xdg-open http://127.0.0.1:5000  # for Linux it opens the page for you
```

## Step-by-step guide
Each project is unique. That is why this **framework is partially DIY**: we assume that it will be customized for a particular use-case.

### 1) Gather your inputs and outputs

Make sure you have **input data** and corresponding **model outputs** from the language model. 


By input data, we mean anything that will help the annotators with assessing the factual accuracy of the output. 

See the [factgenie/data](factgenie/data) folder for example inputs and the [factgenie/outputs](factgenie/outputs) folder for example model outputs.

The input data can have any format visualizable in the web interface - anything from plain text to advanced charts. The model outputs are presumably in plain text. 

### 2) Prepare a data loader
Write a data loader class for your dataset. The class needs to subclass the `Dataset` class in [factgenie/loaders/dataset.py](factgenie/loaders/dataset.py) and implement its methods.

Notably, you need to implement:
- `load_data()` for loading the input data,
- `load_generated_outputs()` for loading the model outputs,
- `render()` for rendering the inputs in HTML,
- `get_info()` returning information about your dataset.

You can get inspired by the example datasets in [factgenie/loaders/dataset.py](factgenie/loaders/dataset.py).

### 3) Run the web interface

To check that everything works as expected, fire up the web interface 🔥


First, install the Python package (the project is tested with Python 3.10):
```
pip install -e .
```
Start the local web server:
```
factgenie run --host=127.0.0.1 --port 8890
```

After opening the page http://127.0.0.1:8890 in your browser, you should be able to see the front page:

<img src="factgenie/static/img/github/main.png" width="100%" style="margin-bottom: 10px" alt="Main screen" />

Go to `/browse`. Make sure that you can select your dataset in the navigation bar and browse through the examples.

### 4) Annotate the outputs with LLMs
TODO


### 5) Annotate the outputs with human crowdworkers
For collecting the annotations from human crowdworkers, you typically need to:
- prepare **user-friendly web interface** for collecting the annotations  ,
- **monitor the progress** of the crowdworkers.

👉️ With factgenie, you won't need to spend almost any time with any of these!

#### Starting a campaign
First, we will **start a new campaign**:
- Go to `/crowdsourcing`.
- Click on **New Campaign** and select the campaign identifier.
- In the **Data** section:
  - Select the datasets and splits you want to annotate. 
  - **Examples per batch**: the number of examples the annotator will see,
  - **Group outputs**: whether you want to shuffle all the available outputs (`Random`) or keep the outputs grouped by input examples (`Example-wise (shuffled)`).
- In the **Prolific** section:
  - **Idle time**: number of minutes after which an assigned example will be freed and offered to a new annotator
  - **Prolific completion code**: the code that will appear to the annotator after the annotation is completed.
- In the **Error categories** section:
  - Select which error categories you want the annotators to annotate along with the corresponding colors.

Your campaign should appear in the list:

<img src="factgenie/static/img/github/list.png" width="100%" style="margin-bottom: 10px" alt="Main screen" />

You can now preview the annotation page by clicking on the 👁️‍🗨️ icon. If this page gets opened by a crowdworker, the corresponding batch of examples will get assigned to them.

Since we are using the dummy `PROLIFIC_PID` parameter (`test`), we can preview the page and submit annotations without having this particular batch assigned.

#### Customizing the annotation page
**And now it's your turn.** To customize the annotation page, go to `factgenie/templates/campaigns/<your_campaign_id>` and modify the `annotate.html` file. 

You will typically need to write custom instructions for the crowdworkers, include Javascript libraries necessary for rendering your inputs, or write custom Javascript code.

You can get inspired by the example campaign in `factgenie/templates/campaigns/`.

Make sure that everything works from your point of view by submitting the annotations from the Preview page (and deleting the resulting files).


<img src="factgenie/static/img/github/page.png" width="100%" style="display: flex; margin: auto;" alt="Main screen" />


#### Launch the crowdsourcing campaign
By clicking on the **Details** button, you can get the link that you can paste on Prolific. By now, you need to run the server with a public URL so that it is accessible to the crowdworkers.

On the details page, you can monitor how individual batches get assigned and completed.

### 6) View the results
Once the annotations are collected, you can view them on the `/browse`. The annotations from each campaign can be selected in the drop-down menu above model outputs.

<img src="factgenie/static/img/github/annot.png" width="60%" style="display: flex; margin: auto;" alt="Main screen" />


## Core Developers 

### Optional use of Git Large File Storage (git lfs)
- We use `git lfs` for storing instructional videos and it is useful for storing any large artefacts.
- We would like to keep the `git lfs` completely optional so do not commit any large files which are required for running _factgenie_, i.e. use it just for documentation.
- Links to `git lfs` documentation:
   - [Git LFS configuration](https://docs.github.com/en/repositories/working-with-files/managing-large-files/configuring-git-large-file-storage)
   - [Moving a large file from git to git lfs](https://docs.github.com/en/repositories/working-with-files/managing-large-files/moving-a-file-in-your-repository-to-git-large-file-storage)
   - [Does every user need to use git lfs (no)](https://github.com/git-lfs/git-lfs/discussions/4644)
