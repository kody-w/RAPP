/* RAPP site — markdown viewer for pages/docs/viewer.html
 *
 * Loads marked.js from CDN, fetches a markdown file by name, renders into
 * .doc-body. Builds an in-page ToC into .doc-toc. Highlights active heading
 * on scroll.
 *
 * Usage: pages/docs/viewer.html?doc=SPEC  -> fetches ./SPEC.md
 *
 * Allowed doc set is whitelisted to prevent open-redirect-style abuse.
 */
(function(){
  var ALLOWED = ['SPEC','ROADMAP','AGENTS','VERSIONS','skill','rapplication-sdk','README'];

  function $(s, r){ return (r || document).querySelector(s); }
  function param(k){
    var m = location.search.match(new RegExp('[?&]' + k + '=([^&]*)'));
    return m ? decodeURIComponent(m[1]) : null;
  }
  function slugify(text){
    return String(text || '').toLowerCase()
      .replace(/[^a-z0-9\s-]/g,'')
      .trim().replace(/\s+/g,'-');
  }

  function buildToc(rootEl){
    var headings = rootEl.querySelectorAll('h1, h2, h3, h4');
    if(!headings.length) return null;
    var ul = document.createElement('ul');
    headings.forEach(function(h){
      var lvl = Number(h.tagName.slice(1));
      if(lvl > 4) return;
      var id = h.id || slugify(h.textContent);
      h.id = id;

      // anchor link affordance
      var a = document.createElement('a');
      a.className = 'doc-anchor';
      a.href = '#' + id;
      a.setAttribute('aria-label','Permalink');
      a.textContent = '#';
      a.style.cssText = 'opacity:0;margin-left:8px;color:var(--text-dim);text-decoration:none;';
      h.appendChild(a);
      h.addEventListener('mouseenter', function(){ a.style.opacity = '0.6'; });
      h.addEventListener('mouseleave', function(){ a.style.opacity = '0'; });

      var li = document.createElement('li');
      li.className = 'lvl-' + lvl;
      var link = document.createElement('a');
      link.href = '#' + id;
      link.textContent = h.textContent.replace(/#$/, '').trim();
      li.appendChild(link);
      ul.appendChild(li);
    });
    return ul;
  }

  function activateOnScroll(toc, body){
    var headings = body.querySelectorAll('h1, h2, h3, h4');
    if(!headings.length) return;
    var links = toc.querySelectorAll('a');
    var io = new IntersectionObserver(function(entries){
      entries.forEach(function(e){
        if(e.isIntersecting){
          links.forEach(function(l){ l.classList.remove('active'); });
          var match = toc.querySelector('a[href="#' + e.target.id + '"]');
          if(match) match.classList.add('active');
        }
      });
    }, { rootMargin:'-80px 0px -70% 0px' });
    headings.forEach(function(h){ io.observe(h); });
  }

  function loadMarked(){
    return new Promise(function(resolve, reject){
      if(window.marked) return resolve(window.marked);
      var s = document.createElement('script');
      s.src = 'https://cdn.jsdelivr.net/npm/marked@12.0.2/marked.min.js';
      s.onload = function(){ resolve(window.marked); };
      s.onerror = function(){ reject(new Error('marked load failed')); };
      document.head.appendChild(s);
    });
  }

  function render(doc){
    var bodyEl = $('.doc-body');
    var tocEl = $('.doc-toc');
    var headerEl = $('.doc-header h1');
    var subEl = $('.doc-header .doc-sub');
    if(!bodyEl) return;

    var url = './' + doc + '.md';
    Promise.all([loadMarked(), fetch(url).then(function(r){
      if(!r.ok) throw new Error('HTTP ' + r.status);
      return r.text();
    })]).then(function(out){
      var marked = out[0], md = out[1];
      // Default marked options — GFM, breaks off (markdown semantics).
      marked.setOptions({ gfm:true, breaks:false });
      var html = marked.parse(md);
      bodyEl.innerHTML = html;

      // Pull first H1 into the doc header; remove duplicate inside body.
      var firstH1 = bodyEl.querySelector('h1');
      if(firstH1){
        if(headerEl) headerEl.textContent = firstH1.textContent;
        document.title = 'RAPP docs — ' + firstH1.textContent;
        firstH1.remove();
      }

      // Pull first paragraph (often a tagline) into the doc-sub if present.
      var firstP = bodyEl.querySelector('blockquote, p');
      if(firstP && subEl && firstP.tagName === 'BLOCKQUOTE'){
        subEl.innerHTML = firstP.innerHTML;
        firstP.remove();
      }

      var ul = buildToc(bodyEl);
      if(ul && tocEl){
        var heading = document.createElement('h4');
        heading.textContent = 'On this page';
        tocEl.innerHTML = '';
        tocEl.appendChild(heading);
        tocEl.appendChild(ul);
        activateOnScroll(tocEl, bodyEl);
      }
    }).catch(function(err){
      bodyEl.innerHTML = '<div style="padding:24px;border:1px solid var(--border);border-radius:8px">'
        + '<h2>Couldn\'t load <code>' + doc + '.md</code></h2>'
        + '<p style="color:var(--text-dim);margin-top:8px">' + err.message + '</p>'
        + '<p style="margin-top:12px"><a href="./">← Back to docs index</a></p>'
        + '</div>';
    });
  }

  // Boot
  document.addEventListener('DOMContentLoaded', function(){
    var doc = param('doc') || 'README';
    if(ALLOWED.indexOf(doc) === -1){
      doc = 'README';
    }
    render(doc);
  });
})();
