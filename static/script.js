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