/* RAPP site — chrome injector + nav highlight.
 * Pages declare `<div id="site-header"></div>` and (optionally)
 * `<div id="site-footer"></div>`. This script fetches the partials
 * and injects them, then highlights the current section in the nav.
 *
 * Loaded with `defer`, so the DOM is parsed before this runs.
 *
 * Path resolution: every page lives at some depth under /pages/.
 *   pages/index.html               -> _site/  (depth 0)
 *   pages/about/leadership.html    -> ../_site/  (depth 1)
 *   pages/docs/viewer.html         -> ../_site/  (depth 1)
 *   pages/vault/...                -> the vault has its own SPA, doesn't use this
 *
 * The script auto-detects depth from its own <script src> attribute.
 */
(function(){
  function $(sel, root){ return (root || document).querySelector(sel); }

  // Find this script's src to derive the _site/ base.
  var thisScript = document.currentScript
    || Array.from(document.scripts).find(function(s){ return /\/_site\/js\/site\.js/.test(s.src); });
  if(!thisScript){ return; }
  var srcUrl = new URL(thisScript.src, document.baseURI);
  var siteBase = srcUrl.pathname.replace(/\/js\/site\.js$/, '/');   // ".../_site/"
  // Convert site base into a relative URL string from the current document.
  function rel(absPath){
    var here = new URL('.', document.baseURI);
    var target = new URL(absPath, document.baseURI);
    var hereParts = here.pathname.replace(/\/$/, '').split('/');
    var targetParts = target.pathname.split('/');
    var i = 0;
    while(i < hereParts.length && i < targetParts.length && hereParts[i] === targetParts[i]) i++;
    var ups = hereParts.slice(i).map(function(){ return '..'; });
    var down = targetParts.slice(i);
    var result = ups.concat(down).join('/');
    return result || './';
  }
  var siteRel = rel(siteBase);                     // e.g. "../_site/"
  var pagesRel = rel(siteBase.replace(/_site\/$/, ''));  // e.g. "../"

  // Inject header + footer if their placeholders exist.
  function inject(slotId, partialName){
    var slot = document.getElementById(slotId);
    if(!slot) return Promise.resolve();
    return fetch(siteRel + 'partials/' + partialName, { credentials:'omit' })
      .then(function(r){ return r.ok ? r.text() : ''; })
      .then(function(html){
        if(!html) return;
        // Rewrite href="@/foo" tokens to the page-relative URL.
        // @/ means "relative to pages/".
        html = html.replace(/(\shref|\ssrc)="@\/([^"]*)"/g, function(_, attr, p){
          return attr + '="' + pagesRel + p + '"';
        });
        slot.innerHTML = html;
        if(slotId === 'site-header') wireHeader();
      })
      .catch(function(){ /* offline/file:// — degrade silently */ });
  }

  function wireHeader(){
    // Theme toggle
    var btn = $('.theme-toggle');
    if(btn && window.RAPP && window.RAPP.toggleTheme){
      btn.addEventListener('click', window.RAPP.toggleTheme);
    }

    // Mobile nav toggle
    var navBtn = $('.nav-toggle');
    var nav = $('.site-nav');
    if(navBtn && nav){
      navBtn.addEventListener('click', function(){
        nav.classList.toggle('open');
      });
    }

    // Highlight current section.
    // The current page's pathname tells us which top-level section under /pages/ we're in.
    var path = location.pathname;
    var section = (function(){
      var m = path.match(/\/pages\/([^/]+)\//);
      if(m) return m[1];
      // landing page (pages/index.html or pages/)
      if(/\/pages\/?(index\.html)?$/.test(path)) return '_home';
      return null;
    })();
    if(section){
      var match = $('.site-nav a[data-section="' + section + '"]');
      if(match) match.setAttribute('aria-current','page');
    }
  }

  // Auto-inject on DOM ready (defer guarantees DOM is parsed already).
  inject('site-header', 'header.html');
  inject('site-footer', 'footer.html');
})();
