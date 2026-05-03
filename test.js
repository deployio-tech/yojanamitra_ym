
    function googleTranslateElementInit() {
      new google.translate.TranslateElement({ pageLanguage: 'en', includedLanguages: 'hi,kn,ta,te,ml,mr,bn,gu,pa', layout: google.translate.TranslateElement.InlineLayout.SIMPLE }, 'google_translate_element');
    }
    function toggleTranslatePanel(e) {
      e.stopPropagation();
      var p = document.getElementById('translate-panel-header');
      p.style.display = p.style.display === 'block' ? 'none' : 'block';
    }
    function setLang(lang, el) {
      document.querySelectorAll('.tp-lang').forEach(function (x) { x.classList.remove('active'); });
      el.classList.add('active');
      document.getElementById('translate-panel-header').style.display = 'none';
      if (lang === 'en') {
        var iframe = document.querySelector('.goog-te-banner-frame');
        if (iframe) { var btn = iframe.contentDocument.querySelector('.goog-te-button button'); if (btn) btn.click(); }
        var sel = document.querySelector('select.goog-te-combo');
        if (sel) { sel.value = ''; sel.dispatchEvent(new Event('change')); }
        return;
      }
      var sel = document.querySelector('select.goog-te-combo');
      if (sel) { sel.value = lang; sel.dispatchEvent(new Event('change')); }
    }
    document.addEventListener('click', function (e) {
      var p = document.getElementById('translate-panel-header');
      if (p && !document.getElementById('header-translate-wrap').contains(e.target)) p.style.display = 'none';
    });
  