var zebra_stripe_tables = function () {
    $('.tablerow:even').addClass('highlight');
    $('.column1').css('background-color','black');
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
        window.location.href = '/gentlemens_gt/standings/' + tournament_id + '/' + round_number;
      });

  $('[id^=show_results_]')
    .click(
      function () {
        var element = $(this);
        var id = element.attr('id').split('_')[2];
        $('#results_' + id).toggle();
        if (element.html() == '+'){
          element.html('&ndash;');
        } else {
          element.html('+');
        }
      });

  $('[id^=printable_standings]')
    .click(
      function () {
        var id_pieces = $(this).attr('id').split('_');
        if (id_pieces[2] == 'inactives'){
          var tournament_id = id_pieces[3];
          var round_number = id_pieces[4];
          var include_inactives = '?include_inactives=True';
        } else {
          var tournament_id = id_pieces[2];
          var round_number = id_pieces[3];
          var include_inactives = '';
        }
        window.open('/gentlemens_gt/standings/' + tournament_id + '/' + round_number + '/printable' + include_inactives,
                    'PrintableStandings',
                    'width=600,height=600,scrollbars=yes,left=200,top=200');
      });
});
