console.log('Main.js loaded');

$('#add-option').click(function () {
    $('.option').first().clone().appendTo('#options');
});

$('#remove-option').click(function () {
    $('.option').last().remove();
});

function draw() {
    var container_id = "vis";
    var config_as_string = document.getElementById(container_id).dataset.config;
    console.log(config_as_string);
    var config = JSON.parse(config_as_string);

    config.container_id = container_id;
    config.trust = "TRUST_CUSTOM_CA_SIGNED_CERTIFICATES";
    config.initial_cypher = "MATCH p=()-[:works_with]->() RETURN p";

    config.labels = {
        "performer": {
            caption: "name",
            size: "pagerank",
            community: "partition"
        }
    };

    config.relationships = {
        "works_with": {
            caption: "case"
            // caption: false,
            // thickness: "count"
        }
    };

    // noinspection JSPotentiallyInvalidConstructorUsage
    new NeoVis.default(config).render();
}

draw();