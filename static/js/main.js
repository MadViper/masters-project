console.log('Main.js loaded');

$('#add-option').click(function () {
    $('.option').first().clone().appendTo('#options');
});

$('#remove-option').click(function () {
    $('.option').last().remove();
});

function draw() {
    console.log("draw");
    console.log(document.getElementById("vis").dataset.dbconfig);
    var db_config = JSON.parse(document.getElementById("vis").dataset.dbconfig);
    console.log(db_config);

    var config = {
        container_id: "vis",

        server_url: db_config.db_url,
        server_user: db_config.db_username,
        server_password: db_config.db_password,

        labels: {
            "performer": {
                caption: "name",
                size: "pagerank",
                community: "partition"
            }
        },

        relationships: {
            "works_with": {
                caption: "case"
                // caption: false,
                // thickness: "count"
            }
        },

        initial_cypher: "MATCH p=()-[:works_with]->() RETURN p"
    };

    var vis = new NeoVis.default(config);
    vis.render();
}

draw();