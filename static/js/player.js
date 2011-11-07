// DOM-ready
$(function () {
  $('#id_phone').change(function(){
      this.value = format_phone(this.value);
    });

  $('#cancel_button')
    .click(
      function () {
        var tournament_id = $('#tournament_id').val();
        window.location.href = '/gentlemens_gt/players/' + tournament_id;
      });
});
