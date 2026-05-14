function showError(message) {
    // Remove existing JS alerts
    $('#js-alerts .alert').remove();

    // Add a JS alert container if not existed
    if ($('#js-alerts').length === 0) {
        $('form').before('<div id="js-alerts"></div>');
    }

    // Add a bootstrap-style alert 
    $('#js-alerts').append(
        '<div class="alert alert-danger alert-dismissible fade show" role="alert">' +
        message +
        '<button type="button" class="close" data-dismiss="alert" aria-label="Close">' +
        '<span aria-hidden="true">&times;</span>' +
        '</button>' +
        '</div>'
    );
}