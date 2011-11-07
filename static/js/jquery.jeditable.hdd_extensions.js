//
// jeditable text processing
//
var deentify_text = function(text){
    text = text.replace(/<br[\s\/]?>/gi, '\n');
    text = text.replace(/&amp;/gi, '&');
    text = text.replace(/&lt;/gi, '<');
    text = text.replace(/&gt;/gi, '>');
    text = text.replace(/&quot;/gi, '"');
    return text;
}

//
// jeditable onsubmit functions
//
var verify_submit_new_value = function(form_obj, val, orig){
    if (val != orig){
        return true;
    } else {
        // turn off jeditable by calling the reset method on the
        // element that we made jeditable via $(selector).editable()
        $(form_obj).parent()[0].reset();
        return false;
    }
}

var jeditable_validate = function(form_obj, validate_func, err_msg,
        preserve_case){
    var input = $('input[name=value], textarea[name=value]', form_obj);
    var val = input.val();
    val = $.trim(val);
    if (preserve_case && preserve_case != 1){
        val = val.toUpperCase();
    }
    input.val(val);
    var orig = deentify_text( $(form_obj).parent()[0].revert );
    if (validate_func){
        var valid = validate_func(val);
        if (valid){
            return verify_submit_new_value(form_obj, val, orig);
        } else {
            $('label.error', form_obj).html(err_msg);
            return false;
        }
    } else {
        return verify_submit_new_value(form_obj, val, orig);
    }
}

//
// custom jeditable widgets
//

// datepicker
$.editable.addInputType('datepicker', {
        element: function(settings, original) {
                    var input = $('<input name="value" class="datepicker_input"/>')
                                    .datepicker(
                                      {showOn: 'both',
                                       buttonage: '',
                                       buttonImageOnly: false
                                      });
                    $(this).append(input)
                           .append($('<br/><label class="error"></label>'));
                    return(input);
                 },

        buttons: function(settings, original) {
            var default_buttons = $.editable.types['defaults'].buttons;
            default_buttons.apply(this, [settings, original]);

            var third = $('<input type="button" value="Clear">').click(
                    function(){
                        $(this).siblings('.datepicker_input').val('');
                    }
                );
            $(this).append(third);
            }
        }
    );

// autogrow textarea
$.editable.addInputType('autogrow', {
    element: function(settings, original) {
        var textarea = $('<textarea />');
        if (settings.rows) {
            textarea.attr('rows', settings.rows);
        } else {
            textarea.height(settings.height);
        }
        if (settings.cols) {
            textarea.attr('cols', settings.cols);
        } else {
            textarea.width(settings.width);
        }
        $(this).append(textarea);
        return(textarea);
    },
    plugin: function(settings, original) {
        $('textarea', this).autogrow(settings.autogrow);
    }
});

// name
$.editable.addInputType('name', {
    element: function(settings, original) {
        var wrapper = $('<span>');
        var firstname = $('<input type="text" name="firstname" style="width:25%;font-size:.8em;"/>');
        var midname = $('<input type="text" name="midname" style="width:25%;font-size:.8em;"/>');
        var lastname = $('<input type="text" name="lastname" style="width:25%;font-size:.8em;"/>');
        var suffix = $('<input type="text" name="suffix" style="width:10%;font-size:.8em;"/>');
        wrapper.append(firstname)
               .append(midname)
               .append(lastname)
               .append(suffix);
        $(this).append(wrapper);
        // returning a hidden input because jeditable expects a single
        // input field to hold the "final" value
        var hidden_input = $('<input type="hidden"/>');
        $(this).append('<br/>')
               .append(hidden_input);
        return(hidden_input);
    },

    content: function(value, settings, original) {
        var idgriev = $(value).attr('id').split('_')[0];
        var url = SITE_ROOT + 'default/fetch_name?idgriev=' + idgriev;
        var xml_http_req = $.ajax({'async':false,
                                   'dataType':'json',
                                   'url':url});
        var name = eval('(' + xml_http_req.responseText + ')');
        $('[name=firstname]', this).val(name[0]);
        $('[name=midname]', this).val(name[1]);
        $('[name=lastname]', this).val(name[2]);
        $('[name=suffix]', this).val(name[3]);
    },

    submit: function(settings, original) {
        // Transfer data from name inputs to hidden input
        // labeled so that we can properly extract it for db update
        var firstname = $('[name=firstname]', this).val();
        var midname = $('[name=midname]', this).val();
        var lastname = $('[name=lastname]', this).val();
        var suffix = $('[name=suffix]', this).val();
        var nameval = '{"firstname":"' + firstname + '",'
                      + '"midname":"' + midname + '",'
                      + '"lastname":"' + lastname + '",'
                      + '"suffix":"' + suffix + '"}'
                      ;
        $('input[name=value]', this).val(nameval);
    }

});

// autocomplete text input
$.editable.addInputType('autocomplete', {
    element: function(settings, original) {
        var input = $('<input type="text" style="font-size:.8em"/>')
            .autocomplete(settings.ac_url, settings.ac_options);
        $(this).append(input)
               .append($('<br/><label class="error"></label>'));
        return(input);
    }
});

// autocompleteArray text input
$.editable.addInputType('autocompleteArray', {
    element: function(settings, original) {
        var input = $('<input type="text" style="font-size:.8em"/>')
            .autocompleteArray(settings.ac_array, settings.ac_options);
        $(this).append(input)
               .append($('<br/><label class="error"></label>'));
        return(input);
    }
});
