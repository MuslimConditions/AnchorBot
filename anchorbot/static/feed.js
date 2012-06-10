var offset=0;
var keyword="";
var dontload=false;

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
                text: art.title
            })
        )
    );
    if(art.image && art.image.filename != "") {
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
            html: art.content //TODO make it safe
        })
    ).append(
        $('<div/>', {
            'class': 'small'
        }).append(
            $('<span/>', {
                text: art.datestr
            })
        )
    );
}

load_and_inc_offset = function(keyword, n) {
    if(n <= 0 || dontload) return;
    $.getJSON('/json/art/'+keyword+'/'+offset+'/'+n, function(data) {
        if(data.articles.length > 0) {
            $.each(data.articles, function(i, art) {
                new_article(art).appendTo("#content");
            });
        } else dontload = true;
    });
    offset++;
}

fill_up = function(kid) {
  load_and_inc_offset(kid, 1);
  if(!dontload && $(window).scrollTop() >= $(document).height() - $(window).height()) {
    setTimeout("fill_up("+kid+")", 500);
  }
}

$('document').ready(function() {setup();
  kid = $("#keyword").attr('title');
  fill_up(kid);

  $(window).scroll(function() {
    if(1.2*$(window).scrollTop() >= $(document).height() - $(window).height()) {
      fill_up(kid);
    }
  });
});