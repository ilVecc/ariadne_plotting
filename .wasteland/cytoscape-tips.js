document.addEventListener("DOMContentLoaded", function () {
        let cy = document.getElementById("automaton-graph");

        function makePopper(ele) {
            let ref = ele.popperRef(); // used only for positioning

            ele.tippy = tippy(ref, { // tippy options:
                content: () => {
                    let content = document.createElement('div');
                    content.innerHTML = ele.id();
                    return content;
                },
                trigger: 'manual' // probably want manual mode
            });
        }

        cy.ready(function () {
            cy.elements().forEach(function (ele) {
                makePopper(ele);
            });
        });

        cy.elements().unbind('mouseover');
        cy.elements().bind('mouseover', (event) => event.target.tippy.show());

        cy.elements().unbind('mouseout');
        cy.elements().bind('mouseout', (event) => event.target.tippy.hide());

    }
);