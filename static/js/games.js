var zebra_stripe_tables = function () {
    $('.tablerow:even').addClass('highlight');
}

//
// DOM-ready
//
$(function(){
  zebra_stripe_tables();

  $('#id_round_number')
    .change(
      function () {
        var tournament_id = $('#id_tournament').val();
        var round_number = $(this).val();
        window.location.href = '/gentlemens_gt/games/' + tournament_id + '/' + round_number;
      });

  $('[id^=delete_round]')
    .click(
      function () {
        var round = $(this).attr('id').split('_').slice(2);
        if (confirm('Really delete Round ' + round + ' and all of its games?')){
          var tournament_id = $('#id_tournament').val();
          window.location.href = '/gentlemens_gt/games/' + tournament_id + '/' + round + '/delete';
        }
        });

  $('.editable_mission_points')
    .editable('/gentlemens_gt/games/update');

  $('input[name^=sports_]')
    .click(
      function () {
        var element = $(this);
        var id_pieces = element.attr('name').split('_');
        var player_id = id_pieces[1];
        var rated_by_id = id_pieces[2];
        var score = element.val();
        $.post(
          '/gentlemens_gt/sports/' + player_id + '/' + rated_by_id + '/edit',
          {score:score}
          );
      });

  $('[id^=printable_games]')
    .click(
      function () {
        var id_pieces = $(this).attr('id').split('_');
        var tournament_id = id_pieces[2];
        var round_number = id_pieces[3];
        window.open('/gentlemens_gt/games/' + tournament_id + '/' + round_number + '/printable',
                    'PrintableGames',
                    'width=600,height=600,scrollbars=yes,left=200,top=200');
      });

});
