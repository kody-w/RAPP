/* RAPP site — theme init + toggle.
 * Loaded SYNCHRONOUSLY in <head> on every page so the theme attribute lands
 * before paint (no flash of wrong-theme content).
 *
 * Pages that use this should NOT also have an inline IIFE doing the same job.
 */
(function(){
  try{
    var saved = localStorage.getItem('rapp-theme');
    var prefersLight = window.matchMedia
      && window.matchMedia('(prefers-color-scheme: light)').matches;
    var theme = saved || (prefersLight ? 'light' : 'dark');
    if(theme === 'light') document.documentElement.setAttribute('data-theme','light');
  }catch(e){}

  // Expose a toggle for the header button (site.js wires this up).
  window.RAPP = window.RAPP || {};
  window.RAPP.toggleTheme = function(){
    var current = document.documentElement.getAttribute('data-theme') === 'light' ? 'light' : 'dark';
    var next = current === 'light' ? 'dark' : 'light';
    if(next === 'light'){
      document.documentElement.setAttribute('data-theme','light');
    }else{
      document.documentElement.removeAttribute('data-theme');
    }
    try{ localStorage.setItem('rapp-theme', next); }catch(e){}
  };
})();
