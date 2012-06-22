var offset=0;
var keyword="";
var dontload = false;

new_article = function(art) {
    article = $('<div/>', {
        'class': 'issue1',
        id: 'aid'+art.ID
    }).append(
        $('<a/>', {
            href: art.link,
            target: "_blank"
        }).append(
            $('<h2/>', {
                'class': 'issue_head',
                text: art.title,
                name: art.ID
            })
        )
    );
    if(art.media && art.media != "") {
        article.append(
            $('<div/>', {
                'class': 'media',
                html: art.media
            })
        );
    } else if(art.image && art.image.filename != "") {
        article.append(
            $('<div/>', {
                'class': 'image'
            }).append(
                $('<img/>', {
                    src: art.image.filename,
                    alt: art.image.filename
                })
            )
        );
    }
    return article.append(
        $('<div/>', {
            'class': 'issue_content',
            html: art.content
        })
    ).append(
        $('<div/>', {
            'class': 'small'
        }).append(
            $('<span/>', {
                text: Humanize.naturalDay(parseInt(art.datestr)),
            })
        ).append(
            $('<span/>', {
                html: '<a target="_blank" href="'+art.link+'">Read the original</a>'
            })
        ).append(
            $('<span/>', {
                html: '<a href="http://bufferapp.com/add" class="buffer-add-button" data-text="'+
                        art.title+
                        '" data-url="'+
                        art.link+
                        '" data-count="horizontal" >Buffer</a><script type="text/javascript" src="http://static.bufferapp.com/js/button.js"></script>'
            })
        )
    );
}

load_and_inc_offset = function(keyword, n) {
    if(n <= 0 || dontload) return;
    $.getJSON('/json/latest/articles/by/keyword/'+keyword+'/'+offset+'/'+n, function(data) {
        if(data.articles.length > 0) {
            $.each(data.articles, function(i, art) {
                new_article(art).appendTo("#content");
            });
        } else dontload = true;
    });
    offset++;
}

fill_up = function(kid, initially) {
  if($(window).scrollTop() >= $(document).height() - $(window).height()) {
      load_and_inc_offset(kid, 1);
  }
  if(!initially)
      setTimeout("fill_up("+kid+", false)", 500);
}

$('document').ready(function() {
  setup();
  kid = $("#keyword").attr('title');
  fill_up(kid, true);
  fill_up(kid, true);
  fill_up(kid, true);

  $(window).scroll(function() {
    fill_up(kid, false);
  });
});