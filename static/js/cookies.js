// Functions for setting, deleting, and reading cookies.

var setCookie = function ( name, value, exp_y, exp_m, exp_d, path, domain, secure ){
    var cookie_string = name + "=" + escape( value );
    if ( exp_y ){
        var expires = new Date ( exp_y, exp_m, exp_d );
        cookie_string += "; expires=" + expires.toGMTString();
    }
    if ( ! path ){
        // set cookie to be valid throughout entire domain by default
        path = '/';
    }
    cookie_string += "; path=" + escape( path );
    if ( domain ){
        cookie_string += "; domain=" + escape( domain );
    }
    if ( secure ){
        cookie_string += "; secure";
    }
    document.cookie = cookie_string;
}

var deleteCookie = function ( cookie_name ){
    // deletion is accomplished by setting an expiry date in the past
    setCookie(cookie_name, '', 1970, 1, 1);
}

var getCookie = function ( cookie_name ){
    var results = document.cookie.match ( cookie_name + '=(.*?)(;|$)' );
    if ( results ){
        return ( unescape ( results[1] ) );
    } else {
        return null;
    }
}
