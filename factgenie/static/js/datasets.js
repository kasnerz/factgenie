function getSelectedDatasets() {
    const selectedDatasets = $('.btn-check-dataset:checked').map(function () {
        return $(this).data('content');
    }).get();
    return selectedDatasets;
}

function getSelectedSplits() {
    const selectedSplits = $('.btn-check-split:checked').map(function () {
        return $(this).data('content');
    }).get();
    return selectedSplits;
}

function addSplitButton(split) {
    if ($('#splits-container').find(`#btn-check-split-${split}`).length > 0) {
        return;
    }
    $('#splits-container').append(`
    <div class="form-check form-switch">
        <input class="form-check-input btn-check-split" type="checkbox" role="switch"
            id="btn-check-split-${split}" data-content="${split}">
        <label class="form-check-label btn-check-split-label" for="btn-check-split-${split}">${split}</label>
    </div>
`);
}

function addOutputButton(output) {
    if ($('#outputs-container').find(`#btn-check-output-${output}`).length > 0) {
        return;
    }
    $('#outputs-container').append(`
        <div class="form-check form-switch">
            <input class="form-check-input btn-check-output" type="checkbox" role="switch"
                id="btn-check-output-${output}" data-content="${output}">
            <label class="form-check-label btn-check-output-label" for="btn-check-output-${output}">${output}</label>
        </div>
    `);
}

function sortCheckboxes(container) {
    // Sort all the checkboxes in the given container alphabetically
    const checkboxes = container.find('.form-check-input');
    checkboxes.sort(function (a, b) {
        return $(a).data('content').localeCompare($(b).data('content'));
    });
    container.empty();
    checkboxes.each(function () {
        container.append($(this).parent());
    });
}

function updateComparisonData() {
    const selectedDatasets = getSelectedDatasets();
    const selectedSplits = getSelectedSplits();

    if (selectedDatasets.length === 0) {
        $('#splits-column').hide();
        $('#outputs-column').hide();
    } else {
        $('#splits-column').show();
    }
    if (selectedSplits.length === 0 || selectedDatasets.length === 0) {
        $('#outputs-column').hide();
    } else if (window.mode != "llm_gen") {
        $('#outputs-column').show();
    }

    // Store the current checked states of the split buttons
    const splitCheckedStates = {};
    $('.btn-check-split').each(function () {
        splitCheckedStates[$(this).data('content')] = $(this).is(':checked');
    });

    // Store the current checked states of the output buttons
    const outputCheckedStates = {};
    $('.btn-check-output').each(function () {
        outputCheckedStates[$(this).data('content')] = $(this).is(':checked');
    });

    $('#splits-container').empty();
    $('#outputs-container').empty();

    for (const dataset of selectedDatasets) {
        Object.keys(model_outs[dataset]).forEach(split => addSplitButton(split));

        for (const split of selectedSplits) {
            // if the split is not available in the dataset, skip
            if (!model_outs[dataset][split]) {
                continue;
            }
            Object.keys(model_outs[dataset][split]).forEach(output => addOutputButton(output));
        }
    }
    // Sort all the checkboxes alphabetically
    sortCheckboxes($('#splits-container'));
    sortCheckboxes($('#outputs-container'));

    // Restore the checked states of the split buttons
    $('.btn-check-split').each(function () {
        const split = $(this).data('content');
        if (splitCheckedStates[split]) {
            $(this).prop('checked', true);
        }
    });
    // Restore the checked states of the output buttons
    $('.btn-check-output').each(function () {
        const output = $(this).data('content');
        if (outputCheckedStates[output]) {
            $(this).prop('checked', true);
        }
    });
}


$(document).on('change', '.btn-check-dataset', updateComparisonData);
$(document).on('change', '.btn-check-split', updateComparisonData);
