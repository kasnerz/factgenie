const url_prefix = window.url_prefix;
const modelOutputs = window.model_outputs;


function createUploadDatasetSplitElem() {
    const newSplit = $(`
        <div class="row mt-1">
        <div class="col-4">
        <input type="text" class="form-control split-name" name="split-name" placeholder="Split name">
        </div>
        <div class="col-7">
        <input class="form-control split-file" type="file" name="split-file" required>
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

$("#dataset-select-overview").on("change", showModelOutputs);

function showModelOutputs() {
    // add a row to #model-out-table for each model output

    const dataset = $('#dataset-select-overview').val();
    const outputs = modelOutputs[dataset];
    const table = $('#model-out-table tbody');
    table.empty();

    for (const setup in outputs) {
        const examples = outputs[setup].example_count;
        const split = outputs[setup].split;
        const row = `<tr>
            <td>${dataset}</td>
            <td>${split}</td>
            <td>${setup}</td>
            <td>${examples}</td>
            <td>
                <a href="${url_prefix}/browse?dataset=${dataset}&split=${split}&example_idx=0" class="btn btn-outline-secondary"
                    data-bs-toggle="tooltip" title="Show the outputs">
                    <i class="fa fa-eye"></i>
                </a>
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
    const dataset = {};
    var filesToRead = $("#dataset-files").children().length;

    // Function to send the POST request
    function sendRequest() {
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
    // Read each file
    $("#dataset-files").children().each(function () {
        const splitName = $(this).find("input[name='split-name']").val();
        const splitFile = $(this).find("input[name='split-file']")[0].files[0];
        const reader = new FileReader();

        reader.onload = function (e) {
            dataset[splitName] = e.target.result;
            filesToRead--;

            // If all files are read, send the request
            if (filesToRead === 0) {
                sendRequest();
            }
        };
        reader.readAsText(splitFile);
    });
}

function deleteDataset(datasetId) {
    // ask for confirmation
    if (!confirm(`Are you sure you want to delete the dataset ${datasetId}? All the data will be lost!`)) {
        return;
    }

    $.post({
        url: `${url_prefix}/delete_dataset`,
        contentType: 'application/json', // Specify JSON content type
        data: JSON.stringify({
            datasetId: datasetId,
        }),
        success: function (response) {
            console.log(response);

            if (response.success !== true) {
                alert(response.error);
            } else {
                // reload the page
                location.reload();
            }
        }
    });
}

function uploadModelOutputs() {
    const dataset = $("#dataset-select").val();
    const split = $("#split-select").val();
    const setup_id = $("#setup-id").val();

    if (setup_id === "") {
        alert("Please enter the setup id");
        return;
    }

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
                if (response.success !== true) {
                    alert(response.error);
                } else {
                    // reload
                    // location.reload();
                    // set the selectbox to the corresponding dataset and split
                    $("#dataset-select").val(dataset).trigger("change");
                    $("#split-select").val(split).trigger("change");
                }
            }
        });
    }
}



//   // set available splits in #split-select
//   $('#split-select').empty();
//   for (const split of datasets[dataset].splits) {
//       $('#split-select').append(`<option value="${split}">${split}</option>`);
//   }
//   const split = $('#split-select').val();


// function changeSplit() {
//     const dataset = $('#dataset-select').val();
//     const split = $('#split-select').val();

//     showModelOutputs(dataset, split);
// }


// function updateDatasetFormat() {
//     const format = $("#dataset-format").val();
//     let accept = "";
//     if (format === "text") {
//         accept = ".txt";
//     } else if (format === "jsonl") {
//         accept = ".jsonl";
//     } else if (format === "csv") {
//         accept = ".csv";
//     } else if (format === "html") {
//         accept = ".zip";
//     }
//     $(".split-file").attr("accept", accept);
// }


function setDatasetEnabled(name, enabled) {
    $.post({
        url: `${url_prefix}/set_dataset_enabled`,
        contentType: 'application/json', // Specify JSON content type
        data: JSON.stringify({
            datasetId: name,
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


function enableTooltips() {
    // enable tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    })
}


$(document).ready(function () {
    if (window.mode == "outputs") {
        $("#dataset-select-overview").val(Object.keys(datasets)[0]).trigger("change");
    }
    // $("#page-input").val(example_idx);
    enableTooltips();
});

