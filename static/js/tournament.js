// DOM-ready
$(function(){
  $('#id_start_date, #id_end_date').datepicker();

  $('#cancel_button')
    .click(
      function () {
        window.location.href = '/gentlemens_gt';
      });
});
