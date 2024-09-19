// var url_prefix = window.location.href.split(/[?#]/)[0];
var url_prefix = window.url_prefix;
var example_idx = 0;
var total_examples = 1;
var datasets = window.datasets;
var metadata = window.metadata;
// var dataset = null;
var generated_outputs = window.generated_outputs;
var mode = window.mode;
var examples_cached = {};
var sizes = mode == "annotate" ? [50, 50] : [66, 33];
var selected_campaigns = [];
var model_outs = window.model_outs;

if (mode == "annotate") {
    var annotation_set = window.annotation_set;
    var annotator_id = window.annotator_id;
    total_examples = annotation_set.length;
}

if (mode == "annotate" || mode == "browse") {
    // the draggable divider between the main area and the right panel
    var splitInstance = Split(['#centerpanel', '#rightpanel'], {
        sizes: sizes, gutterSize: 1
    });
}

function randInt(max) {
    return Math.floor(Math.random() * max);
}

function mod(n, m) {
    return ((n % m) + m) % m;
}

function nextBtn() {
    goToPage(example_idx + 1);
}

function prevBtn() {
    goToPage(example_idx - 1);
}

function startBtn() {
    goToPage(0);
}

function endBtn() {
    goToPage(total_examples - 1);
}

function randomBtn() {
    goToPage(randInt(total_examples - 1));
}

function goToAnnotation(page) {
    $(".page-link").removeClass("bg-active");
    $(`#page-link-${page}`).addClass("bg-active");
    saveCurrentAnnotations();
    showAnnotation();
}

function goToView(page) {
    const dataset = $('#dataset-select').val();
    const split = $('#split-select').val();

    fetchExample(dataset, split, example_idx);

    $("#page-input").val(example_idx);
}

function goToPage(page) {
    example_idx = page;
    example_idx = mod(example_idx, total_examples);

    if (mode == "annotate") {
        goToAnnotation(example_idx);
    } else {
        goToView(example_idx);
    }
}


function fetchAnnotation(dataset, split, example_idx, annotation_idx) {
    return new Promise((resolve, reject) => {
        // console.log(`fetching ${dataset} ${split} ${example_idx}`);
        $.get(`${url_prefix}/example`, {
            "dataset": dataset,
            "example_idx": example_idx,
            "split": split,
        }, function (data) {
            $('<div>', {
                id: `out-text-${annotation_idx}`,
                class: `annotate-box `,
                style: 'display: none;'
            }).appendTo('#outputarea');

            // filter the data to only include the setup we want
            const setup_id = annotation_set[annotation_idx].setup.id;

            data.generated_outputs = data.generated_outputs.filter(o => o.setup.id == setup_id)[0];

            examples_cached[annotation_idx] = data;

            resolve();
        }).fail(function () {
            reject();
        });
    });
}

function loadAnnotations() {
    $("#dataset-spinner").show();

    const promises = [];
    const annotation_span_categories = metadata.config.annotation_span_categories;

    // prefetch the examples for annotation: we need them for YPet initialization
    for (const [annotation_idx, example] of Object.entries(annotation_set)) {
        const dataset = example.dataset;
        const split = example.split;
        const example_idx = example.example_idx;
        const promise = fetchAnnotation(dataset, split, example_idx, annotation_idx);
        promises.push(promise);
    }
    Promise.all(promises)
        .then(() => {
            YPet.addInitializer(function (options) {
                /* Configure the # and colors of Annotation types (minimum 1 required) */
                YPet.AnnotationTypes = new AnnotationTypeList(annotation_span_categories);
                var regions = {};
                var paragraphs = {};

                for (const [annotation_idx, data] of Object.entries(examples_cached)) {

                    var p = new Paragraph({ 'text': data.generated_outputs.generated, 'granularity': metadata.config.annotation_granularity });

                    paragraphs[`p${annotation_idx}`] = p;
                    regions[`p${annotation_idx}`] = `#out-text-${annotation_idx}`;

                    const li = $('<li>', { class: "page-item" });
                    const a = $('<a>', { class: "page-link bg-incomplete", style: "min-height: 28px;", id: `page-link-${annotation_idx}` }).text(annotation_idx);
                    li.append(a);
                    $("#nav-example-cnt").append(li);

                    // switch to the corresponding example when clicking on the page number
                    $(`#page-link-${annotation_idx}`).click(function () {
                        goToPage(annotation_idx);
                    });
                }
                YPet.addRegions(regions);

                for (const [p, p_obj] of Object.entries(paragraphs)) {
                    YPet[p].show(new WordCollectionView({ collection: p_obj.get('words') }));

                    YPet[p].currentView.collection.parentDocument.get('annotations').on('remove', function (model, collection) {
                        if (collection.length == 0) {
                            collection = [];
                        }
                    });
                    goToAnnotation(example_idx);
                }
            });
            YPet.start();

        })
        .catch(() => {
            // Handle errors if any request fails
            console.error("One or more requests failed.");
        })
        .finally(() => {
            // This block will be executed regardless of success or failure
            $("#dataset-spinner").hide();
        });
}

function submitAnnotations(campaign_id) {
    // remove `words` from the annotations: they are only used by the YPet library
    for (const example of annotation_set) {
        for (const annotation of example.annotations) {
            delete annotation.words;
        }
    }

    $.post({
        url: `${url_prefix}/submit_annotations`,
        contentType: 'application/json', // Specify JSON content type
        data: JSON.stringify({
            campaign_id: metadata.id,
            annotator_id: annotator_id,
            annotation_set: annotation_set
        }
        ),
        success: function (data) {
            window.onbeforeunload = null;
            $("#overlay-end").show();
        }
    });
}

function collectFlags() {
    // collect values of all checkboxes within divs of class `flag-checkbox`, save values sequentially (for each id)
    const flags = [];
    $(".flag-checkbox").each(function () {
        const value = $(this).find("input[type='checkbox']").prop("checked");
        flags.push(value);
    });
    return flags;
}

function collectOptions() {
    const options = [];

    // for all ".crowdsourcing-option" div's, see whether is has the "option-select" or "option-slider" class
    // and collect the value of the select or the slider, respectively
    // save it along with the value of the label

    $(".crowdsourcing-option").each(function (x) {
        if ($(this).hasClass("option-select")) {
            const type = "select";
            const label = $(this).find("label").text();
            const index = $(this).find("select").val();
            const value = $(this).find("select option:selected").text();
            options.push({ type: type, label: label, index: index, value: value });
        } else if ($(this).hasClass("option-slider")) {
            const type = "slider";
            const label = $(this).find("label").text();
            const index = $(this).find("input[type='range']").val();
            const value = $(this).find("datalist option")[index].value;
            options.push({ type: type, label: label, index: index, value: value });
        }
    });
    return options;
}




function saveCurrentAnnotations() {
    var collection = YPet[`p${example_idx}`].currentView.collection.parentDocument.get('annotations').toJSON();
    annotation_set[example_idx]["annotations"] = collection;
}


function markAnnotationAsComplete() {
    saveCurrentAnnotations();
    annotation_set[example_idx]["flags"] = collectFlags();
    annotation_set[example_idx]["options"] = collectOptions();

    $('#page-link-' + example_idx).removeClass("bg-incomplete");
    $('#page-link-' + example_idx).addClass("bg-complete");

    // uncheck all checkboxes
    $(".flag-checkbox input[type='checkbox']").prop("checked", false);

    // if all the examples are annotated, post the annotations
    if ($(".bg-incomplete").length == 0) {
        // show the `submit` button
        $("#submit-annotations-btn").show();

        // scroll to the top
        $('html, body').animate({
            scrollTop: $("#submit-annotations-btn").offset().top
        }, 500);

    } else if (example_idx < total_examples - 1) {
        nextBtn();
    }
}

function showRawData(data) {
    var rawDataStr = JSON.stringify(data.raw_data, null, 2).replace(/\\n/g, '<br>');

    if (rawDataStr[0] == '"') {
        // remove the first and last double quotes
        rawDataStr = rawDataStr.slice(1, -1);
    }
    rawDataStr = rawDataStr.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    $("#rawarea").html(`<pre>${rawDataStr}</pre>`);
}

function showAnnotation() {
    $(".annotate-box").hide();
    $(`#out-text-${example_idx}`).show();

    const data = examples_cached[example_idx];
    const flags = annotation_set[example_idx].flags;
    const options = annotation_set[example_idx].options;

    if (flags !== undefined) {
        // flags are an array
        $(".flag-checkbox").each(function (i) {
            $(this).find("input[type='checkbox']").prop("checked", flags[i]);
        });
    } else {
        // uncheck all checkboxes
        $(".flag-checkbox input[type='checkbox']").prop("checked", false);
    }

    if (options !== undefined) {
        // options is an array of objects
        for (const [i, option] of Object.entries(options)) {
            const div = $(`#options div:eq(${i})`);
            div.find("select[name='optionType']").val(option.type);
            div.find("input[name='optionLabel']").val(option.label);
            div.find("input[name='optionValues']").val(option.values.join(", "));
        }
    } else {
        // clear all options
        $("#options").empty();
    }

    $("#examplearea").html(data.html);
    // $(".text-type").html(`${type}`);
}

function permalinkBtn() {
    const dataset = $('#dataset-select').val();
    const split = $('#split-select').val();

    const url_prefix = window.location.href.split(/[?#]/)[0];

    let permalink = `${url_prefix}?dataset=${dataset}&split=${split}&example_idx=${example_idx}`;

    popover = bootstrap.Popover.getOrCreateInstance("#permalink-btn", options = { html: true });
    popover.setContent({
        '.popover-body': permalink
    });
    $('#permalink-btn').popover('show');
}

function goToBtn() {
    var n = $("#page-input").val();
    goToPage(n);
}

function toggleRaw() {
    // toggle display: none on rawarea and examplearea
    $("#rawarea").toggle();
    $("#examplearea").toggle();
}


function changeDataset() {
    $("#dataset-spinner").show();
    const dataset = $('#dataset-select').val();

    // set available splits in #split-select
    $('#split-select').empty();
    for (const split of datasets[dataset].splits) {
        $('#split-select').append(`<option value="${split}">${split}</option>`);
    }
    const split = $('#split-select').val();

    example_idx = 0;
    fetchExample(dataset, split, example_idx);
    $("#page-input").val(example_idx);
}

function changeSplit() {
    $("#dataset-spinner").show();
    const dataset = $('#dataset-select').val();
    const split = $('#split-select').val();
    example_idx = 0;
    fetchExample(dataset, split, example_idx);
    $("#page-input").val(example_idx);
}

function changeExample(dataset, split, example_idx) {
    // used only for direct links
    $("#dataset-spinner").show();
    $('#dataset-select').val(dataset);
    $('#split-select').empty();
    for (const split of datasets[dataset].splits) {
        $('#split-select').append(`<option value="${split}">${split}</option>`);
    }
    $('#split-select').val(split);
    example_idx = example_idx;
    fetchExample(dataset, split, example_idx);
    $("#page-input").val(example_idx);
}

function getAnnotatedOutput(output, campaign_id) {
    const setup_id = output.setup.id;
    // replace newlines with any spaces around them with <br>
    const content = output.generated.replace(/\\n/g, '<br>');

    // if the campaign_id is in output.annotations, show the annotated content
    const annotations_campaign = output.annotations.filter(a => a.metadata.id == campaign_id);

    var placeholder = $('<pre>', { id: `out-${setup_id}-${campaign_id}-placeholder`, class: `font-mono out-placeholder out-${campaign_id}-placeholder` });
    var annotated_content;

    if (annotations_campaign.length > 0) {
        const annotations = annotations_campaign[0];
        const annotation_span_categories = annotations.metadata.config.annotation_span_categories;

        annotated_content = annotateContent(content, annotations, annotation_span_categories);
    } else {
        // we do not have outputs for the particular campaign -> grey out the text
        if (campaign_id != "original") {
            placeholder.css("color", "#c2c2c2");
        }
        annotated_content = content;
    }
    placeholder.html(annotated_content);
    // placeholder.hide();
    return placeholder;
}

// Our custom function to highlight the text spans using the collected annotations
// Here we do *not* use the YPet library, but directly work with HTML
function annotateContent(content, annotations, annotation_span_categories) {
    let offset = 0; // Track cumulative offset
    const annotationSet = annotations.annotations;

    // sort by start
    annotationSet.sort(function (a, b) {
        return a.start - b.start;
    });
    var html = content;

    annotationSet.forEach(annotation => {
        const annotationType = annotation.type;

        if (!(annotationType in annotation_span_categories)) {
            console.log("Warning: annotation type not found in annotation_span_categories: " + annotationType);
            return;
        }
        const color = annotation_span_categories[annotationType].color;
        const text = annotation.text.trimEnd();

        const start = annotation.start + offset;
        const end = start + text.length;

        const error_name = annotation_span_categories[annotationType].name;
        const reason = annotation.reason;
        let tooltip_text;

        if (annotation.reason !== undefined) {
            tooltip_text = `${error_name} (${reason})`;
        } else {
            tooltip_text = `${error_name}`;
        }

        const spanId = `span-${start}-${end}`;
        const spanContent = `<span id="${spanId}" style="margin-right: 0px;background-color: ${color};" data-bs-toggle="tooltip" data-bs-placement="top" title="${tooltip_text}">${text}</span>`;

        html = html.slice(0, start) + spanContent + html.slice(end);
        // Update the offset
        offset += spanContent.length - text.length;
    });
    return html;
}

function updateDisplayedAnnotations() {
    const activeButtons = $('.btn-ann-select.active');
    selected_campaigns = activeButtons.map(function () {
        return $(this).data('ann');
    }).get();
    // hide all placeholders
    $(".output-box").hide();

    // if no campaign ids, show the original output
    if (selected_campaigns.length == 0) {
        $(".box-original").show();
    }
    for (const campaign_id of selected_campaigns) {
        // show the selected annotator
        $(`.box-${campaign_id}`).show();
    }
    enableTooltips();
}


function createOutputBox(content, campaign_id, setup) {
    const setup_id = setup.id;
    const model = setup.model;

    var card = $('<div>', { class: `card output-box generated-output-box box-${setup_id} box-${campaign_id} box-${setup_id}-${campaign_id}` });

    var annotationBadge = (campaign_id !== "original") ? `<span class="small"><i class="fa fa-pencil"></i> ${campaign_id}</span>` : ""
    var headerHTML = `<div class="d-flex justify-content-between">
    <span class="small">${setup_id}</span>
    ${annotationBadge}
    </div>
    `

    var cardHeader = $('<div>', { class: "card-header small" }).html(headerHTML);
    var cardBody = $('<div>', { class: "card-body" });
    var cardTitle = $('<h5>', { class: "card-title" }).text(model);
    var cardText = $('<div>', { class: "card-text" }).html(content);

    cardBody.append(cardTitle);
    cardBody.append(cardText);
    card.append(cardHeader);
    card.append(cardBody);
    return card;
}

function createOutputBoxes(generated_outputs) {
    // clear the output area
    $("#outputarea").empty();

    // sort outputs by setup id
    generated_outputs.sort(function (a, b) {
        return a.setup.id.localeCompare(b.setup.id);
    });

    // find all campaign ids in output annotations
    const campaign_ids = new Set();

    generated_outputs.forEach(output => {
        output.annotations.forEach(annotation => {
            campaign_ids.add(annotation.metadata.id);
        });
    });
    const selectBox = $("#annotations-select");
    // clear the selectbox
    selectBox.empty();

    // add an option for each campaign id
    for (const campaign_id of campaign_ids) {
        const button = $(`<button type="button" class="btn btn-sm btn-light btn-ann-select" data-ann="${campaign_id}">${campaign_id}</button>`);
        button.on('click', function () {
            $(this).toggleClass('active');
            updateDisplayedAnnotations();
        });
        selectBox.append(button);
    }

    if (campaign_ids.size > 0) {
        $("#setuparea").show();
    } else {
        $("#setuparea").hide();
    }

    // add the annotated outputs
    for (const output of generated_outputs) {
        groupDiv = $('<div>', { class: `output-group box-${output.setup.id} d-inline-flex gap-2` });
        groupDiv.appendTo("#outputarea");

        plain_output = getAnnotatedOutput(output, "original");
        card = createOutputBox(plain_output, "original", output.setup);
        card.appendTo(groupDiv);

        for (const campaign_id of campaign_ids) {
            const annotated_output = getAnnotatedOutput(output, campaign_id);
            card = createOutputBox(annotated_output, campaign_id, output.setup);
            card.appendTo(groupDiv);
            card.hide();
        }
    }

}

function showSelectedCampaigns() {
    // if the annotator is still among the values, restore it
    // prevent resetting to the first annotation when switching examples
    $(".btn-ann-select").each(function () {
        if (selected_campaigns.includes($(this).data('ann'))) {
            $(this).addClass("active").trigger("change");
        } else {
            $(this).removeClass("active");
        }
    });
}

function fetchExample(dataset, split, example_idx) {
    $.get(`${url_prefix}/example`, {
        "dataset": dataset,
        "example_idx": example_idx,
        "split": split,
    }, function (data) {
        $("#dataset-spinner").hide();
        $("#examplearea").html(data.html);
        showRawData(data);

        total_examples = data.total_examples;
        $("#total-examples").html(total_examples - 1);

        createOutputBoxes(data.generated_outputs);
        showSelectedCampaigns();
        updateDisplayedAnnotations();
    });
}


$("#dataset-select").on("change", changeDataset);
$("#split-select").on("change", changeSplit);

if (mode == "annotate") {
    $('.btn-check').on('change', function () {
        $('.btn-check').each(function () {
            const label = $(`label[for=${this.id}]`);
            if (this.checked) {
                label.addClass('active');
            } else {
                label.removeClass('active');
            }
        });
    });
}


$(document).keydown(function (event) {
    const key = event.key;

    if (mode == "browse") {
        if (key === "ArrowRight") {
            event.preventDefault();
            nextBtn();
        } else if (key === "ArrowLeft") {
            event.preventDefault();
            prevBtn();
        }
    }
});

$('#page-input').keypress(function (event) {
    // Enter = Go to page
    if (event.keyCode == 13) {
        goToBtn();
    }
});

$("#hideOverlayBtn").click(function () {
    $("#overlay-start").fadeOut();
});

$(document).on('change', "#data-select-area input[type='checkbox']", function () {
    updateSelectedDatasets();
});

$(".btn-err-cat").change(function () {
    if (this.checked) {
        const cat_idx = $(this).attr("data-cat-idx");
        YPet.setCurrentAnnotationType(cat_idx);
    }
});

function updateSelectedDatasets() {
    var selectedData = gatherComparisonData();

    if (mode == 'llm_eval' || mode == 'crowdsourcing') {
        $("#selectedDatasetsContent").html(
            selectedData.map(d =>
                `<tr>
                <td>${d.dataset}</td>
                <td>${d.split}</td>
                <td>${d.setup_id}</td>
                <td>${d.example_cnt}</td>
                <td><button type="button" class="btn btn-sm btn-secondary" onclick="deleteRow(this);">x</button></td>
            </tr>`
            ).join("\n")
        );
    } else if (mode == 'llm_gen') {
        $("#selectedDatasetsContent").html(
            selectedData.map(d =>
                `<tr>
                <td>${d.dataset}</td>
                <td>${d.split}</td>
                <td>${d.example_cnt}</td>
                <td><button type="button" class="btn btn-sm btn-secondary" onclick="deleteRow(this);">x</button></td>
            </tr>`
            ).join("\n")
        );
    }
}

function gatherSelectedCombinations() {
    // read all the rows the remained in #selectedDatasetsContent
    var selectedData = [];
    $("#selectedDatasetsContent tr").each(function () {
        var dataset = $(this).find("td:eq(0)").text();
        var split = $(this).find("td:eq(1)").text();
        if (mode != "llm_gen") {
            var setup_id = $(this).find("td:eq(2)").text();
            selectedData.push({ dataset: dataset, split: split, setup_id: setup_id });
        } else {
            selectedData.push({ dataset: dataset, split: split });
        }
    });
    return selectedData;
}


function gatherComparisonData() {
    var campaign_datasets = [];
    var campaign_splits = [];
    var campaign_outputs = [];

    $(".btn-check-dataset").each(function () {
        if ($(this).prop("checked")) {
            campaign_datasets.push($(this).attr("data-content"));
        }
    });
    $(".btn-check-split").each(function () {
        if ($(this).prop("checked")) {
            campaign_splits.push($(this).attr("data-content"));
        }
    });
    $(".btn-check-output").each(function () {
        if ($(this).prop("checked")) {
            campaign_outputs.push($(this).attr("data-content"));
        }
    });
    var combinations = [];

    if (mode == "llm_eval" || mode == "crowdsourcing") {
        // get all available combinations of datasets, splits, and outputs
        for (const dataset of campaign_datasets) {
            for (const split of campaign_splits) {
                for (const output of campaign_outputs) {
                    if (model_outs[dataset][split] !== undefined &&
                        model_outs[dataset][split][output] !== undefined) {
                        combinations.push({ dataset: dataset, split: split, setup_id: output, example_cnt: datasets[dataset].example_count[split] });
                    }
                }
            }
        }
    } else if (mode == "llm_gen") {
        // get all available combinations of datasets and splits
        for (const dataset of campaign_datasets) {
            for (const split of campaign_splits) {
                if (model_outs[dataset][split] !== undefined) {
                    combinations.push({ dataset: dataset, split: split, example_cnt: datasets[dataset].example_count[split] });
                }
            }
        }
    }

    return combinations;

}

function gatherConfig() {
    var config = {};

    if (window.mode == "crowdsourcing") {
        config.annotatorInstructions = annotatorInstructionsMDE.value();
        config.annotatorPrompt = $("#annotatorPrompt").val();
        config.finalMessage = finalMessageMDE.value();
        config.hasDisplayOverlay = $("#displayOverlay").is(":checked");
        config.examplesPerBatch = $("#examplesPerBatch").val();
        config.idleTime = $("#idleTime").val();
        config.annotationGranularity = $("#annotationGranularity").val();
        config.sortOrder = $("#sortOrder").val();
        config.annotationSpanCategories = getAnnotationSpanCategories();
        config.flags = getKeys($("#flags"));
        config.options = getOptions();
    } else if (window.mode == "llm_eval" || window.mode == "llm_gen") {
        config.metricType = $("#metric-type").val();
        config.modelName = $("#model-name").val();
        config.promptTemplate = $("#prompt-template").val();
        config.systemMessage = $("#system-message").val();
        config.apiUrl = $("#api-url").val();
        config.modelArguments = getKeysAndValues($("#model-arguments"));
        config.extraArguments = getKeysAndValues($("#extra-arguments"));

        if (window.mode == "llm_eval") {
            config.annotationSpanCategories = getAnnotationSpanCategories();
        }
        if (window.mode == "llm_gen") {
            config.startWith = $("#start-with").val();
        }
    }
    return config;
}


function createLLMCampaign() {
    const campaignId = $('#campaignId').val();
    // const llmConfig = $('#llmConfig').val();

    const config = gatherConfig();
    var campaignData = gatherSelectedCombinations();

    // if no datasets are selected, show an alert
    if (campaignData.length == 0) {
        alert("Please select at least one existing combination of dataset, split, and output.");
        return;
    }

    $.post({
        url: `${url_prefix}/llm_campaign/create?mode=${mode}`,
        contentType: 'application/json', // Specify JSON content type
        data: JSON.stringify({
            campaignId: campaignId,
            campaignData: campaignData,
            config: config
        }),
        success: function (response) {
            console.log(response);

            if (response.success !== true) {
                alert(response.error);
            } else {
                window.location.href = `${url_prefix}/llm_campaign?mode=${mode}`;
            }
        }
    });
}



function getAnnotationSpanCategories() {
    var annotationSpanCategories = [];

    $("#annotation-span-categories").children().each(function () {
        const name = $(this).find("input[name='annotationSpanCategoryName']").val();
        const color = $(this).find("input[name='annotationSpanCategoryColor']").val();
        annotationSpanCategories.push({ name: name, color: color });
    });
    return annotationSpanCategories;
}

function getKeysAndValues(div) {
    var args = {};
    div.children().each(function () {
        const key = $(this).find("input[name='argName']").val();
        const value = $(this).find("input[name='argValue']").val();
        args[key] = value;
    });
    return args;
}

function getKeys(div) {
    var keys = [];
    div.children().each(function () {
        const key = $(this).find("input[name='argName']").val();
        keys.push(key);
    });
    return keys;
}

function getOptions() {
    var options = [];

    $("#options").children().each(function () {
        const type = $(this).find("select[name='optionType']").val();
        const label = $(this).find("input[name='optionLabel']").val();
        const values = $(this).find("input[name='optionValues']").val().split(",").map(v => v.trim());
        options.push({ type: type, label: label, values: values });
    });
    return options;
}

function createHumanCampaign() {
    const campaignId = $('#campaignId').val();
    const config = gatherConfig();
    var campaignData = gatherSelectedCombinations();

    // if no datasets are selected, show an alert
    if (campaignData.length == 0) {
        alert("Please select at least one existing combination of dataset, split, and output.");
        return;
    }

    $.post({
        url: `${url_prefix}/crowdsourcing/create`,
        contentType: 'application/json', // Specify JSON content type
        data: JSON.stringify({
            campaignId: campaignId,
            config: config,
            campaignData: campaignData
        }),
        success: function (response) {
            console.log(response);

            if (response.success !== true) {
                alert(response.error);
            } else {
                window.location.href = `${url_prefix}/crowdsourcing`;
            }
        }
    });
}


function startLLMCampaignListener(campaignId) {
    var source = new EventSource(`${url_prefix}/llm_campaign/progress/${campaignId}`);
    console.log("Listening for progress events");

    source.onmessage = function (event) {
        // update the progress bar
        var payload = JSON.parse(event.data);
        var finished_examples = payload.finished_examples_cnt;
        var progress = Math.round((finished_examples / window.llm_examples) * 100);
        $("#llm-progress-bar").css("width", `${progress}%`);
        $("#llm-progress-bar").attr("aria-valuenow", progress);
        $("#metadata-example-cnt").html(`${finished_examples} / ${window.llm_examples}`);
        console.log(`Received progress: ${progress}%`);

        // update the annotation button
        const example = payload.annotation;
        const dataset = example.dataset;
        const split = example.split;
        const setup_id = example.setup.id;
        const example_idx = example.example_idx;
        const rowId = `${dataset}-${split}-${setup_id}-${example_idx}`;
        const annotation_button = $(`#annotBtn${rowId}`);
        annotation_button.show();

        // update the annotation content
        const annotation_content = example.output;
        const annotation_div = $(`#annotPre${rowId}`);

        // if annotation_content is a dict, convert it to a string
        if (typeof annotation_content === 'object') {
            annotation_div.text(JSON.stringify(annotation_content));
        } else {
            annotation_div.text(annotation_content);
        }

        // update the status
        const status_button = $(`#statusBtn${rowId}`);
        status_button.text("finished");

        if (progress == 100) {
            source.close();
            console.log("Closing the connection");

            if (window.mode == "llm_gen") {
                $("#save-generations-button").show();
            }
        }

    };
}

function runLLMCampaign(campaignId) {
    $("#run-button").hide();
    $("#stop-button").show();
    $("#llm-progress").show();
    $("#metadata-status").html("running");

    startLLMCampaignListener(campaignId);

    $.post({
        url: `${url_prefix}/llm_campaign/run?mode=${mode}`,
        contentType: 'application/json',
        data: JSON.stringify({
            campaignId: campaignId
        }),
        success: function (response) {
            if (response.success !== true) {
                $("#log-area").text(JSON.stringify(response.error));
                console.log(JSON.stringify(response));

                $("#metadata-status").html("error");
                $("#run-button").show();
                $("#stop-button").hide();
                $("#llm-progress").hide();
            } else {
                console.log(response);

                if (response.status == "finished") {
                    $("#metadata-status").html("finished");
                    $("#run-button").hide();
                    $("#download-button").show();
                    $("#stop-button").hide();
                    $("#llm-progress").hide();

                    $("#log-area").text(response.final_message);
                }
            }
        }
    });
}

function pauseLLMCampaign(campaignId) {
    $("#run-button").show();
    $("#stop-button").hide();
    $("#download-button").show();
    $("#llm-progress").hide();

    $.post({
        url: `${url_prefix}/llm_campaign/pause?mode=${mode}`,
        contentType: 'application/json',
        data: JSON.stringify({
            campaignId: campaignId
        }),
        success: function (response) {
            console.log(response);
        }
    });
}

function deleteCampaign(campaignId, source) {
    // ask for confirmation
    if (!confirm(`Are you sure you want to delete the campaign ${campaignId}? All the data will be lost!`)) {
        return;
    }

    $.post({
        url: `${url_prefix}/delete_campaign`,
        contentType: 'application/json', // Specify JSON content type
        data: JSON.stringify({
            campaignId: campaignId,
            source: source,
            mode: window.mode
        }),
        success: function (response) {
            console.log(response);

            if (response.success !== true) {
                alert(response.error);
            } else {
                // remove the campaign from the list
                $(`#campaign-${campaignId}`).remove();

                // reload the page
                location.reload();
            }
        }
    });
}

function addAnnotationSpanCategory() {
    const annotationSpanCategories = $("#annotation-span-categories");
    const randomColor = '#' + Math.floor(Math.random() * 16777215).toString(16);
    const newCategory = createAnnotationSpanCategoryElem("", randomColor);
    annotationSpanCategories.append(newCategory);
}

function addModelArgument() {
    const modelArguments = $("#model-arguments");
    const newArg = createArgElem("", "");
    modelArguments.append(newArg);
}

function addExtraArgument() {
    const modelArguments = $("#extra-arguments");
    const newArg = createArgElem("", "");
    modelArguments.append(newArg);
}

function addFlag() {
    const flags = $("#flags");
    const newFlag = createFlagElem("");
    flags.append(newFlag);
}

function addOption() {
    const options = $("#options");
    const newOption = createOptionElem("select", "", "");
    options.append(newOption);
}


function deleteRow(button) {
    $(button).parent().parent().remove();
}

function createFlagElem(key) {
    // text area and selectbox for the flag ("checked" or "unchecked" based on the value)
    const newFlag = $(`
        <div class="row mt-1">
        <div class="col-11">
        <input type="text" class="form-control" name="argName" value="${key}" placeholder="Question or statement">
        </div>
        <div class="col-1">
        <button type="button" class="btn btn-danger" onclick="deleteRow(this);">x</button>
        </div>
        </div>
    `);
    return newFlag;
}

function createOptionElem(type, label, values) {
    // three columns: option type (selectbox, slider) text input for the label, and text input for comma-separated values
    const newOption = $(`
        <div class="row mt-1">
        <div class="col-3">
        <select class="form-select" name="optionType">
            <option value="select" ${type === 'select' ? 'selected' : ''}>Select box</option>
            <option value="slider" ${type === 'slider' ? 'selected' : ''}>Slider</option>
        </select>
        </div>
        <div class="col-3">
        <input type="text" class="form-control" name="optionLabel" value="${label}" placeholder="Label">
        </div>
        <div class="col-5">
        <input type="text" class="form-control" name="optionValues" value="${values}" placeholder="Comma-separated values">
        </div>
        <div class="col-1">
        <button type="button" class="btn btn-danger" onclick="deleteRow(this);">x</button>
        </div>
        `);
    return newOption;
}

function createArgElem(key, value) {
    // escape quotes in the value
    if (typeof value === 'string') {
        value = value.replace(/"/g, "&quot;");
    }
    const newArg = $(`
        <div class="row mt-1">
        <div class="col-6">
        <input type="text" class="form-control"  name="argName" value="${key}" placeholder="Key">
        </div>
        <div class="col-5">
        <input type="text" class="form-control" name="argValue" value="${value}" placeholder="Value">
        </div>
        <div class="col-1">
        <button type="button" class="btn btn-danger" onclick="deleteRow(this);">x</button>
        </div>
        </div>
    `);
    return newArg;
}

function createAnnotationSpanCategoryElem(name, color) {
    const newCategory = $(`
        <div class="row mt-1">
        <div class="col-6">
        <input type="text" class="form-control" name="annotationSpanCategoryName" value="${name}" placeholder="Category name">
        </div>
        <div class="col-5">
        <input type="color" class="form-control" name="annotationSpanCategoryColor" value="${color}">
        </div>
        <div class="col-1">
        <button type="button" class="btn btn-danger" onclick="deleteRow(this);">x</button>
        </div>
        </div>
    `);
    return newCategory;
}


function duplicateConfig(btnElem, filenameElemId, modeTo, campaignId) {
    const filename = $("#" + filenameElemId).val() + ".yaml";
    const modeFrom = window.mode;

    // TODO warn overwrite
    $.post({
        url: `${url_prefix}/duplicate_config`,
        contentType: 'application/json', // Specify JSON content type
        data: JSON.stringify({
            campaignId: campaignId,
            modeFrom: modeFrom,
            modeTo: modeTo,
            filename: filename,
        }),
        success: function (response) {
            console.log(response);

            if (response.success !== true) {
                alert(response.error);
            } else {
                // change color of the button save-cfg-submit to green for a second with the label "Saved!", then back to normal
                const origText = $(btnElem).text();
                $(btnElem).removeClass("btn-primary").addClass("btn-success").text("Saved!");
                setTimeout(function () {
                    $('#save-cfg-modal').modal('hide');
                    $(btnElem).removeClass("btn-success").addClass("btn-primary").text(origText);
                }, 1500);
            }
        }
    });
}

function duplicateEval(inputDuplicateId, campaignId) {
    newCampaignId = $(`#${inputDuplicateId}`).val();

    $.post({
        url: `${url_prefix}/duplicate_eval`,
        contentType: 'application/json', // Specify JSON content type
        data: JSON.stringify({
            campaignId: campaignId,
            newCampaignId: newCampaignId,
            mode: window.mode
        }),
        success: function (response) {
            console.log(response);

            if (response.success !== true) {
                alert(response.error);
            } else {
                // hide the modal and reload the page
                $('#duplicate-eval-modal').modal('hide');
                location.reload();
            }
        }
    });
}

function saveGenerationOutputs(campaignId) {
    modelName = $("#save-generations-model-name").val();

    $.post({
        url: `${url_prefix}/save_generation_outputs`,
        contentType: 'application/json', // Specify JSON content type
        data: JSON.stringify({
            campaignId: campaignId,
            modelName: modelName
        }),
        success: function (response) {
            console.log(response);

            if (response.success !== true) {
                alert(response.error);
            } else {
                // change color of the button save-cfg-submit to green for a second with the label "Saved!", then back to normal
                $("#save-generations-submit").removeClass("btn-primary").addClass("btn-success").text("Saved!");
                setTimeout(function () {
                    $('#save-generations-modal').modal('hide');
                    $("#save-generations-submit").removeClass("btn-success").addClass("btn-primary").text("Save");
                }, 1500);
            }
        }
    });
}


function saveConfig(mode) {
    const filename = $("#config-save-filename").val() + ".yaml";
    const config = gatherConfig();

    if (filename in window.configs) {
        if (!confirm(`The configuration with the name ${filename} already exists. Do you want to overwrite it?`)) {
            return;
        }
    }
    $.post({
        url: `${url_prefix}/save_config`,
        contentType: 'application/json', // Specify JSON content type
        data: JSON.stringify({
            mode: mode,
            filename: filename,
            config: config
        }),
        success: function (response) {
            console.log(response);

            if (response.success !== true) {
                alert(response.error);
            } else {
                // change color of the button save-cfg-submit to green for a second with the label "Saved!", then back to normal
                $("#save-cfg-submit").removeClass("btn-primary").addClass("btn-success").text("Saved!");
                setTimeout(function () {
                    $('#save-cfg-modal').modal('hide');
                    $("#save-cfg-submit").removeClass("btn-success").addClass("btn-primary").text("Save");
                }, 1500);
            }
        }
    });

}
function updateCrowdsourcingConfig() {
    const crowdsourcingConfig = $('#crowdsourcingConfig').val();

    if (crowdsourcingConfig === "[None]") {
        annotatorInstructionsMDE.value("");
        $("#annotatorPrompt").val("");
        finalMessageMDE.value("");
        $("#examplesPerBatch").val("");
        $("#idleTime").val("");
        $("#annotation-span-categories").empty();
        $("#flags").empty();
        $("#options").empty();
        return;
    }
    const cfg = window.configs[crowdsourcingConfig];

    const annotatorInstructions = cfg.annotator_instructions;
    const annotatorPrompt = cfg.annotator_prompt;
    const finalMessage = cfg.final_message;
    const examplesPerBatch = cfg.examples_per_batch;
    const idleTime = cfg.idle_time;
    const annotationGranularity = cfg.annotation_granularity;
    const sortOrder = cfg.sort_order;
    const annotationSpanCategories = cfg.annotation_span_categories;
    const flags = cfg.flags;
    const options = cfg.options;

    annotatorInstructionsMDE.value(annotatorInstructions);
    $("#annotatorPrompt").val(annotatorPrompt);
    finalMessageMDE.value(finalMessage);
    $("#examplesPerBatch").val(examplesPerBatch);
    $("#idleTime").val(idleTime);
    $("#annotationGranularity").val(annotationGranularity);
    $("#sortOrder").val(sortOrder);
    $("#annotation-span-categories").empty();

    annotationSpanCategories.forEach((annotationSpanCategory) => {
        const newCategory = createAnnotationSpanCategoryElem(annotationSpanCategory.name, annotationSpanCategory.color);
        $("#annotation-span-categories").append(newCategory);
    });
    $("#flags").empty();

    if (flags !== undefined) {
        flags.forEach((flag) => {
            const newFlag = createFlagElem(flag);
            $("#flags").append(newFlag);
        });
    }

    $("#options").empty();

    if (options !== undefined) {
        options.forEach((option) => {
            const newOption = createOptionElem(option.type, option.label, option.values.join(", "));
            $("#options").append(newOption);
        });
    }
}


function updateLLMMetricConfig() {
    const llmConfigValue = $('#llmConfig').val();

    if (llmConfigValue === "[None]") {
        $("#model-name").html("");
        $("#prompt-template").html("");
        $("#system-message").html("");
        $("#api-url").html("");
        $("#model-arguments").empty();
        $("#annotation-span-categories").empty();
        $("#extra-arguments").empty();
        return;
    }
    const cfg = window.configs[llmConfigValue];

    const metric_type = cfg.type;
    const model_name = cfg.model;
    const prompt_template = cfg.prompt_template;
    const system_msg = cfg.system_msg;
    const api_url = cfg.api_url;
    const model_args = cfg.model_args;
    const extra_args = cfg.extra_args;

    // for metric, we need to select the appropriate one from the values in the select box
    $("#metric-type").val(metric_type);
    $("#model-name").html(model_name);
    $("#prompt-template").html(prompt_template);
    $("#system-message").html(system_msg);
    $("#api-url").html(api_url);
    $("#model-arguments").empty();
    $("#extra-arguments").empty();

    $.each(model_args, function (key, value) {
        const newArg = createArgElem(key, value);
        $("#model-arguments").append(newArg);
    });

    $.each(extra_args, function (key, value) {
        const newArg = createArgElem(key, value);
        $("#extra-arguments").append(newArg);
    });

    if (mode == "llm_eval") {
        const annotationSpanCategories = cfg.annotation_span_categories;
        $("#annotation-span-categories").empty();

        annotationSpanCategories.forEach((annotationSpanCategory) => {
            const newCategory = createAnnotationSpanCategoryElem(annotationSpanCategory.name, annotationSpanCategory.color);
            $("#annotation-span-categories").append(newCategory);
        });
    }
    if (mode == "llm_gen") {
        const start_with = cfg.start_with;
        $("#start-with").val(start_with);
    }
}


function enableTooltips() {
    // enable tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    })
}


$(document).ready(function () {
    if (mode == "annotate") {
        loadAnnotations();

        $("#total-examples").html(total_examples - 1);
    } else if (mode == "browse") {
        if (window.display_example != null) {
            const e = window.display_example;
            changeExample(e.dataset, e.split, e.example_idx);
        }
        else {
            // select the first dataset from the selectbox
            $("#dataset-select").val(
                $("#dataset-select option:first").val()
            ).trigger("change");
            $("#page-input").val(example_idx);
        }
    }

    enableTooltips();
});

if (mode == "annotate") {
    window.onbeforeunload = function () {
        return "Are you sure you want to reload the page? Your work will be lost.";
    }
}
