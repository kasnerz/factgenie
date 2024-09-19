function deleteRow(button) {
    $(button).parent().parent().remove();
}

function getSelectedCampaigns() {
    const selectedCampaigns = $('.btn-check-campaign:checked').map(function () {
        return $(this).data('content');
    }).get();
    return selectedCampaigns;
}


function gatherSelectedCombinations() {
    // read all the rows the remained in #selectedDatasetsContent
    var selectedData = [];
    $("#selectedDatasetsContent tr").each(function () {
        var dataset = $(this).find("td:eq(0)").text();
        var split = $(this).find("td:eq(1)").text();
        var setup_id = $(this).find("td:eq(2)").text();
        selectedData.push({ dataset: dataset, split: split, setup_id: setup_id });
    });
    return selectedData;
}

function showAgreement(response) {
    // uncover `agreement-modal`, fill the `agreement-area` with the data

    $("#agreement-spinner").hide();

    var content = '';
    // iterate over the objects in the `response` list
    for (const data of response) {
        const agreement = `
            <h5><code>${data.first_annotator}</code> vs. <code>${data.second_annotator}</code></h5>
            <hr>
            <b>Dataset-level agreement</b>
            <p><small class="text-muted">Pearson <i>r</i> between the annotators computed over a list of average error counts, one number for each (dataset, split, setup_id) combination.</small></p>
            <dl class="row">
            <dt class="col-sm-5">Pearson r (macro)</dt>
                <dd class="col-sm-7">${data.dataset_level_pearson_r_macro.toFixed(2)} (avg. of [${data.dataset_level_pearson_r_macro_categories}])</dd>
                <p><small class="text-muted"> An average of coefficients computed separately for each category.</small></p>
                <dt class="col-sm-5">Pearson r (micro)</dt>
                <dd class="col-sm-7">${data.dataset_level_pearson_r_micro.toFixed(2)}</dd>
                <p><small class="text-muted"> Computed over concatenated results from all the categories.</small></p>
                </dl>
            <hr>
            <b>Example-level agreement</b>
            <p><small class="text-muted">Pearson <i>r</i> between the annotators computed over a list of error counts, one number for each example.</small></p>
            <dl class="row">
                <dt class="col-sm-5">Pearson r (macro)</dt>
                <dd class="col-sm-7">${data.example_level_pearson_r_macro.toFixed(2)} (avg. of [${data.example_level_pearson_r_macro_categories}])</dd>
                <p><small class="text-muted"> An average of coefficients computed separately for each category.</small></p>
                <dt class="col-sm-5">Pearson r (micro)</dt>
                <dd class="col-sm-7">${data.example_level_pearson_r_micro.toFixed(2)}</dd>
                 <p><small class="text-muted"> Computed over concatenated results from all the categories.</small></p>
            </dl>
            <hr>
        `;
        content += agreement;
    }

    $('#agreement-area').html(content);
    $('#agreement-modal').modal('show');
}

function computeAgreement() {
    // get the selected campaigns and ask the backend
    const selectedCombinations = gatherSelectedCombinations();
    const selectedCampaigns = getSelectedCampaigns();

    if (selectedCombinations.length == 0) {
        alert("Please select some data for comparison.");
        return;
    }

    $("#agreement-spinner").show();

    $.post({
        url: `${url_prefix}/compute_agreement`,
        contentType: 'application/json', // Specify JSON content type
        data: JSON.stringify({
            selectedCampaigns: selectedCampaigns,
            combinations: selectedCombinations,
        }),
        success: function (response) {
            console.log(response);

            if (response.error !== undefined) {
                alert(response.error);
            } else {
                showAgreement(response);
            }
        }
    });
}



function populateTable(tableId, data, columns) {
    var table = $(`#${tableId} tbody`);
    table.empty(); // Clear existing rows

    for (const obj of data) {
        let row = '<tr>';
        for (const col of columns) {
            if (col === 'annotation_type') {
                row += `<td>
                    <span class="badge" style="background-color: ${metadata.config.annotation_span_categories[obj[col]].color}; color: rgb(60, 65, 73);">
                        ${metadata.config.annotation_span_categories[obj[col]].name}
                    </span>
                </td>`;
            } else {
                row += `<td>${obj[col]}</td>`;
            }
        }
        row += '</tr>';
        table.append(row);
    }
    $(`#${tableId}`).bootstrapTable();
}

function updateComparisonData() {
    const selectedCampaigns = getSelectedCampaigns();

    $('#common-categories').html("None");
    $('#common-examples').html("0");
    $("#selectedDatasetsContent").empty();
    $("#agreement-btn").addClass("disabled")

    if (selectedCampaigns.length < 2) {
        // TODO make it also work for multiple annotators within the same campaign
        return;
    }
    // find which category label names are common to all campaigns
    const campaignCategories = selectedCampaigns.map(c => campaigns[c].metadata.config.annotation_span_categories).map(c => c.map(cat => cat.name));
    const commonCategories = campaignCategories.reduce((acc, val) => {
        return acc.filter(x => val.some(y => y === x));
    });

    $('#common-categories').html(
        commonCategories.map(c => `<span class="badge bg-secondary">${c}</span>`).join("\n")
    );

    // find examples that are common to all selected campaigns and that have a status `finished`
    const combinations = selectedCampaigns.map(c => campaigns[c].data);
    const commonExamples = combinations.reduce((acc, val) => {
        return acc.filter(x => val.some(y => y.dataset === x.dataset && y.split === x.split && y.setup_id === x.setup_id));
    });
    const finishedExamples = commonExamples.filter(e => e.status === 'finished');

    // for every (dataset, split, setup_id) combination, compute the number of examples
    const exampleCounts = finishedExamples.reduce((acc, val) => {
        const key = `${val.dataset}|${val.split}|${val.setup_id}`;
        acc[key] = (acc[key] || 0) + 1;
        return acc;
    }, {});

    const comparisonData = Object.entries(exampleCounts).map(([key, count]) => {
        const [dataset, split, setup_id] = key.split('|');
        return { dataset, split, setup_id, example_count: count };
    });

    $("#selectedDatasetsContent").html(
        comparisonData.map(d =>
            `<tr>
                <td>${d.dataset}</td>
                <td>${d.split}</td>
                <td>${d.setup_id}</td>
                <td>${d.example_count}</td>
                <td><button type="button" class="btn btn-sm btn-secondary" onclick="deleteRow(this);">x</button></td>
            </tr>`
        ).join("\n")
    );

    $('#common-examples').html(finishedExamples.length);
    $("#agreement-btn").removeClass("disabled");

    return combinations;
}



const fullTableColumns = ['dataset', 'split', 'setup_id', 'example_count', 'annotation_type', 'ann_count', 'avg_count', 'prevalence'];
const spanTableColumns = ['example_count', 'annotation_type', 'ann_count', 'avg_count', 'prevalence'];
const setupTableColumns = ['setup_id', 'example_count', 'annotation_type', 'ann_count', 'avg_count', 'prevalence'];
const datasetTableColumns = ['dataset', 'split', 'example_count', 'annotation_type', 'ann_count', 'avg_count', 'prevalence'];


$(document).ready(function () {
    // if we are on a detail page, populate the tables
    if ($('#full-table').length > 0) {
        const statistics = window.statistics;
        const ann_counts = statistics.ann_counts;

        populateTable('full-table', ann_counts.full, fullTableColumns);
        populateTable('span-table', ann_counts.span, spanTableColumns);
        populateTable('setup-table', ann_counts.setup, setupTableColumns);
        populateTable('dataset-table', ann_counts.dataset, datasetTableColumns);
    }
});


$(document).on('change', '.btn-check-campaign', updateComparisonData);