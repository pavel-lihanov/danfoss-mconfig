$('input:text[datalist][multiple]').each(function() {
    var elem = $(this),
        list = $(document.getElementById(elem.attr('datalist')));
    elem.autocomplete({
        source: list.children().map(function() {
            return $(this).text();
        }).get()
    });
});                            

