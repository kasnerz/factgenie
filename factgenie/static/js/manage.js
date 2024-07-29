const url_prefix = window.url_prefix;
const modelOutputs = window.model_outputs;


function createUploadDatasetSplitElem() {
    const newSplit = $(`
        <div class="row mt-1">
        <div class="col-6">
        <input type="text" class="form-control" name="split-name" placeholder="Split name">
        </div>
        <div class="col-5">
        <input class="form-control" type="file" name="split-file" accept=".txt" required>
        </div>
        <div class="col-1">
        <button type="button" class="btn btn-danger" onclick="deleteRow(this);">x</button>
        </div>
        </div>
    `);
    return newSplit;
}

function deleteRow(button) {
    $(button).parent().parent().remove();
}

function addDatasetSplit() {
    const datasetSplits = $("#dataset-files");
    const newSplit = createUploadDatasetSplitElem();
    datasetSplits.append(newSplit);
}

function showModelOutputs(dataset, split) {
    // add a row to #model-out-table for each model output
    const outputs = modelOutputs[dataset][split];
    const table = $('#model-out-table tbody');
    table.empty();

    for (const setup in outputs) {
        const examples = outputs[setup].example_count;
        const row = `<tr>
            <td><a class="blue-link" href="${url_prefix}/browse?dataset=${dataset}&split=${split}&example_idx=0">${setup}</a></td>
            <td>${examples}</td>
            <td>
                <a onclick="deleteOutput('${dataset}', '${split}', '${setup}')" class="btn btn-outline-danger"
                data-bs-toggle="tooltip" title="Delete the output">
                <i class="fa fa-trash"></i>
                </a>
            </td>
        </tr>`;
        table.append(row);
    }
}

function deleteOutput(dataset, split, setup) {
    // ask for confirmation
    if (!confirm(`Are you sure you want to delete the output for ${setup}?`)) {
        return;
    }
    $.post({
        url: `${url_prefix}/delete_model_outputs`,
        contentType: 'application/json', // Specify JSON content type
        data: JSON.stringify({
            dataset: dataset,
            split: split,
            setup: setup
        }),
        success: function (response) {
            console.log(response);

            if (response.success !== true) {
                alert(response.error);
            } else {
                // reload
                location.reload();
            }
        }
    });
}


function uploadDataset() {
    const dataset_id = $("#dataset-id").val();
    const description = $("#dataset-description").val();
    const format = $("#dataset-format").val();

    // for each split in #dataset-files, read split-name and split-file
    const dataset = {}
    $("#dataset-files").children().each(function () {
        const splitName = $(this).find("input[name='split-name']").val();
        const splitFile = $(this).find("input[name='split-file']")[0].files[0];

        // upload the dataset
        const reader = new FileReader();
        reader.readAsText(splitFile);
        const splitData = reader.result;

        dataset[splitName] = splitData;
    });
    // send by post request to /upload_dataset
    reader.onload = function (e) {
        $.post({
            url: `${url_prefix}/upload_dataset`,
            contentType: 'application/json', // Specify JSON content type
            data: JSON.stringify({
                id: dataset_id,
                description: description,
                format: format,
                dataset: dataset,
            }),
            success: function (response) {
                console.log(response);

                if (response.success !== true) {
                    alert(response.error);
                } else {
                    // reload
                    location.reload();
                }
            }
        });
    }
}

function uploadModelOutputs() {
    const dataset = $("#dataset-select").val();
    const split = $("#split-select").val();
    const setup_id = $("#setup-id").val();

    // read the file from #model-output-upload form
    const file = $("#model-output-upload")[0].files[0];
    const reader = new FileReader();
    reader.readAsText(file);

    // send by post request to /upload_model_outputs
    reader.onload = function (e) {
        $.post({
            url: `${url_prefix}/upload_model_outputs`,
            contentType: 'application/json', // Specify JSON content type
            data: JSON.stringify({
                outputs: e.target.result,
                dataset: dataset,
                split: split,
                setup_id: setup_id,
            }),
            success: function (response) {
                console.log(response);

                if (response.success !== true) {
                    alert(response.error);
                } else {
                    // reload
                    location.reload();
                }
            }
        });
    }
}

function changeDataset() {
    const dataset = $('#dataset-select').val();

    // set available splits in #split-select
    $('#split-select').empty();
    for (const split of datasets[dataset].splits) {
        $('#split-select').append(`<option value="${split}">${split}</option>`);
    }
    const split = $('#split-select').val();

    showModelOutputs(dataset, split);
}

function changeSplit() {
    const dataset = $('#dataset-select').val();
    const split = $('#split-select').val();

    showModelOutputs(dataset, split);
}


function updateDatasetFormat() {
    // change "accept" for the "#dataset-file" input based on the value of "#dataset-format" select: text (.txt), json (.json), csv (.csv), html (.zip)
    const format = $("#dataset-format").val();
    let txt = "";
    let accept = "";
    if (format === "text") {
        accept = ".txt";
    } else if (format === "jsonl") {
        accept = ".jsonl";
    } else if (format === "csv") {
        accept = ".csv";
    } else if (format === "html") {
        accept = ".zip";
    }
    $("#dataset-file").attr("accept", accept);
    // $("#dataset-upload-info").text(txt);
}


function setDatasetEnabled(name, enabled) {
    $.post({
        url: `${url_prefix}/set_dataset_enabled`,
        contentType: 'application/json', // Specify JSON content type
        data: JSON.stringify({
            datasetName: name,
            enabled: enabled
        }),
        success: function (response) {
            console.log(response);

            if (response.success !== true) {
                alert(response.error);
            } else {
                // reload
                location.reload();
            }
        }
    });
}

$("#dataset-select").on("change", changeDataset);
$("#split-select").on("change", changeSplit);

function enableTooltips() {
    // enable tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    })
}


$(document).ready(function () {
    if (window.mode == "outputs") {
        $("#dataset-select").val(Object.keys(datasets)[0]).trigger("change");
    }
    // $("#page-input").val(example_idx);
    enableTooltips();
});

