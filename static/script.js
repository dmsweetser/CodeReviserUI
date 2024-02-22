document.addEventListener('DOMContentLoaded', function () {
    // Check if there is any state saved in sessionStorage
    var accordionState = sessionStorage.getItem('accordionState');
    if (accordionState) {
        var accordionData = JSON.parse(accordionState);

        // Iterate through each accordion and set its state
        accordionData.forEach(function (item) {
            var accordion = document.getElementById(item.id);
            if (accordion) {
                if (item.isCollapsed) {
                    accordion.classList.remove('show');
                } else {
                    accordion.classList.add('show');
                }
            }
        });
    } else {
        saveAccordionState()
    }

    var accordionButtons = document.querySelectorAll('.accordion-button');
    accordionButtons.forEach(function (accordionButton) {
        accordionButton.addEventListener('click', function () {
            setTimeout(() => saveAccordionState(), 1000);
        });
    });

    // Function to save accordion state in sessionStorage
    function saveAccordionState() {
        var accordions = document.querySelectorAll('.accordion-collapse');
        var accordionData = [];
        accordions.forEach(function (accordion) {
            accordionData.push({
                id: accordion.id,
                isCollapsed: !accordion.classList.contains('show')
            });
        });
        sessionStorage.setItem('accordionState', JSON.stringify(accordionData));
    }
});

document.addEventListener('DOMContentLoaded', function () {
    const editBtns = document.querySelectorAll('.edit-btn');
    editBtns.forEach(btn => btn.addEventListener('click', async function () {
        const file = this.dataset.file;
        const revision = this.dataset.revision;
        const response = await fetch(`/edit_revision/${file}/${revision}`);
        const data = await response.json();
        const codeDiv = document.getElementById(`code_${file}`);
        codeDiv.innerHTML = data.content;
        const editBtn = this;
        codeDiv.nextElementSibling.innerHTML = `<button type="button" class="btn btn-warning btn-sm ms-2 edit-btn" data-bs-toggle="button" data-file="${file}" data-revision="${revision}" data-content="${data.content}" onclick="saveRevision('${file}','${revision}')">Save Changes</button>`;
        this.disabled = true;
    }));
});

async function saveRevision(file, revision) {
    const content = document.getElementById(`code_${file}`).innerHTML;
    const response = await fetch(`/edit_revision/${file}/${revision}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content })
    });
    const data = await response.json();
    if (data.success) {
        window.location.reload();
    }
}