var zebra_stripe_tables = function () {
    $('.tablerow:even').addClass('highlight');
}

//
// DOM-ready
//
$(function(){
  zebra_stripe_tables();

  $('[id^=printable_overall]')
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
        window.open('/gentlemens_gt/overall/' + tournament_id + '/printable' + include_inactives,
                    'PrintableOverall',
                    'width=600,height=600,scrollbars=yes,left=200,top=200');
      });
});
