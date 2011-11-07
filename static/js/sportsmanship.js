var zebra_stripe_tables = function () {
    $('.tablerow:even').addClass('highlight');
    $('.column1').css('background-color','black');
}

//
// DOM-ready
//
$(function(){
  zebra_stripe_tables();

  $('.editable_favorite_opponent_votes')
    .editable('/gentlemens_gt/sports/update');

  $('[id^=show_base_sports_]')
    .click(
      function () {
        var element = $(this);
        var id = element.attr('id').split('_')[3];
        $('#results_' + id).toggle();
        if (element.html() == '+'){
          element.html('&ndash;');
        } else {
          element.html('+');
        }
      });

  $('[id^=printable_sportsmanship]')
    .click(
      function () {
        var id_pieces = $(this).attr('id').split('_');
        if (id_pieces[2] == 'inactives'){
          var tournament_id = id_pieces[3];
          var include_inactives = '?include_inactives=True';
        } else {
          var tournament_id = id_pieces[2];
          var include_inactives = '';
        }
        window.open('/gentlemens_gt/sports/' + tournament_id + '/printable' + include_inactives,
                    'PrintableSportsmanship',
                    'width=600,height=600,scrollbars=yes,left=200,top=200');
      });
});
