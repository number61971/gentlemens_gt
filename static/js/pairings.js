// DOM-ready
$(function(){
  $('#id_round_number')
    .change(
      function () {
        var tournament_id = $('#id_tournament').val();
        var round_number = $(this).val();
        window.location.href = '/gentlemens_gt/games/' + tournament_id + '/' + round_number + '/pairings';
      });

  $('#tables').sortable();

  $('#players_1, #players_2')
    .sortable({connectWith: '.connectedSortable'});

  $('#pairings_form')
    .submit(
      function () {
        var tplayers_1_items = $('#players_1 li');
        var tplayers_2_items = $('#players_2 li');
        if (tplayers_1_items.length == tplayers_2_items.length) {
          var tables_items = $('#tables li');
          var pairings = new Array();
          for (var i=0; i<tplayers_1_items.length; i++) {
            var table = $(tables_items[i]).attr('id').split('_').slice(1);
            var p1 = $(tplayers_1_items[i]).attr('id').split('_').slice(1);
            var p2 = $(tplayers_2_items[i]).attr('id').split('_').slice(1);
            pairings.push(table + ':' + p1 + 'v' + p2);
          }
          $('#id_pairings').val(pairings.join(','));
          return true;
        } else {
          alert('ERROR: Pairings are unbalanced!');
          return false;
        }
        });

  });
