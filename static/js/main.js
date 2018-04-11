console.log('Main.js loaded');

$('#add-option').click(function() {
    $('.option').first().clone().appendTo('#options');
});

$('#remove-option').click(function() {
    $('.option').last().remove();
});
