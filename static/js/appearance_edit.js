var summarize_appearance = function () {
  var appearance_widgets = $('#appearance_edit select');
  var total = 0;
  for (var i=0; i<appearance_widgets.length; i++){
    total = total + parseInt(appearance_widgets[i].value);
  }
  $('#appearance_total').html(total);
  $('#favorite_votes_total').html('+' + $('#id_favorite_army_votes').val() + ' favorite army votes');
}

// DOM-ready
$(function(){
  summarize_appearance();

  $('#appearance_edit select, #id_favorite_army_votes')
    .change(
      function () {
        summarize_appearance();
      });

  $('#cancel_button')
    .click(
      function () {
        var tournament_id = $('#tournament_id').val();
        window.location.href = '/gentlemens_gt/appearance/' + tournament_id;
      });
});
