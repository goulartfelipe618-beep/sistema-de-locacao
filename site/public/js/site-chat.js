/**
 * Botão flutuante + painel lateral de atendimento (drawer à direita; tela cheia no mobile).
 * Exposes window.SiteChat
 */
(function (global) {
  'use strict';

  var TOTAL_STEPS = 4;
  var currentStep = 1;

  var PHONE_ICON =
    '<svg class="chat-fab__icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
    '<path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/>' +
    '</svg>';

  var CLOSE_ICON =
    '<svg class="chat-fab__icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true">' +
    '<path d="M18 6L6 18M6 6l12 12"/>' +
    '</svg>';

  function $(sel, root) {
    return (root || document).querySelector(sel);
  }

  function t(key, vars) {
    if (global.SiteI18n && typeof global.SiteI18n.t === 'function') {
      return global.SiteI18n.t(key, vars);
    }
    return key;
  }

  function fabHtml() {
    return (
      '<button type="button" class="chat-fab" id="chat-fab" data-i18n-aria="chat.open" aria-label="Abrir atendimento" aria-controls="chat-drawer" aria-expanded="false">' +
      PHONE_ICON +
      '</button>'
    );
  }

  function drawerHtml() {
    var steps = '';
    for (var i = 1; i <= TOTAL_STEPS; i += 1) {
      steps +=
        '<span class="chat-drawer__step-dot" data-step-dot="' +
        i +
        '" aria-hidden="true"></span>';
    }
    return (
      '<div class="chat-drawer" id="chat-drawer" aria-hidden="true">' +
      '<div class="chat-drawer__backdrop" data-chat-close tabindex="-1"></div>' +
      '<aside class="chat-drawer__panel" role="dialog" aria-modal="true" aria-labelledby="chat-drawer-title" tabindex="-1">' +
      '<header class="chat-drawer__header">' +
      '<div class="chat-drawer__header-main">' +
      '<span class="chat-drawer__avatar" aria-hidden="true">' +
      '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><path d="M12 2a3 3 0 0 0-3 3v1H8a2 2 0 0 0-2 2v11a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-1V5a3 3 0 0 0-3-3z"/><circle cx="12" cy="14" r="2"/></svg>' +
      '</span>' +
      '<div class="chat-drawer__header-text">' +
      '<h2 class="chat-drawer__title" id="chat-drawer-title" data-i18n="chat.title">Atendimento Rodavia</h2>' +
      '<p class="chat-drawer__subtitle"><span class="chat-drawer__status-dot" aria-hidden="true"></span><span data-i18n="chat.subtitle">Online · respondemos em breve</span></p>' +
      '</div>' +
      '</div>' +
      '<button type="button" class="chat-drawer__close" data-chat-close data-i18n-aria="modal.close" aria-label="Fechar">' +
      '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M18 6L6 18M6 6l12 12"/></svg>' +
      '</button>' +
      '</header>' +
      '<div class="chat-drawer__progress-wrap">' +
      '<div class="chat-drawer__progress-track" aria-hidden="true">' +
      steps +
      '</div>' +
      '<p class="chat-drawer__progress-label" id="chat-wizard-progress" aria-live="polite"></p>' +
      '</div>' +
      '<div class="chat-drawer__body">' +
      '<form class="chat-wizard" id="chat-wizard-form" novalidate>' +
      '<p class="form-message chat-wizard__error" id="chat-wizard-error" role="alert" hidden></p>' +
      '<div class="chat-wizard__step is-active" data-chat-step="1">' +
      '<p class="chat-wizard__prompt" data-i18n="chat.prompt_name">Para começar, informe seu nome completo.</p>' +
      '<div class="form-field chat-wizard__field">' +
      '<label for="chat-nome" data-i18n="chat.step_name_label">Nome completo</label>' +
      '<input type="text" id="chat-nome" name="nome" required autocomplete="name" />' +
      '</div>' +
      '<div class="chat-wizard__actions">' +
      '<button type="button" class="btn btn--primary chat-wizard__next" data-i18n="chat.continue">Continuar</button>' +
      '</div>' +
      '</div>' +
      '<div class="chat-wizard__step" data-chat-step="2" hidden>' +
      '<p class="chat-wizard__prompt" data-i18n="chat.prompt_email">Qual e-mail podemos usar para retorno?</p>' +
      '<div class="form-field chat-wizard__field">' +
      '<label for="chat-email" data-i18n="chat.step_email_label">E-mail</label>' +
      '<input type="email" id="chat-email" name="email" required autocomplete="email" />' +
      '</div>' +
      '<div class="chat-wizard__actions">' +
      '<button type="button" class="btn btn--ghost chat-wizard__back" data-i18n="chat.back">Voltar</button>' +
      '<button type="button" class="btn btn--primary chat-wizard__next" data-i18n="chat.continue">Continuar</button>' +
      '</div>' +
      '</div>' +
      '<div class="chat-wizard__step" data-chat-step="3" hidden>' +
      '<p class="chat-wizard__prompt" data-i18n="chat.prompt_phone">Informe um telefone com DDD para contato.</p>' +
      '<div class="form-field chat-wizard__field">' +
      '<label for="chat-telefone" data-i18n="chat.step_phone_label">Telefone</label>' +
      '<input type="tel" id="chat-telefone" name="telefone" required autocomplete="tel" inputmode="tel" />' +
      '</div>' +
      '<div class="chat-wizard__actions">' +
      '<button type="button" class="btn btn--ghost chat-wizard__back" data-i18n="chat.back">Voltar</button>' +
      '<button type="button" class="btn btn--primary chat-wizard__next" data-i18n="chat.continue">Continuar</button>' +
      '</div>' +
      '</div>' +
      '<div class="chat-wizard__step" data-chat-step="4" hidden>' +
      '<p class="chat-wizard__prompt" data-i18n="chat.prompt_message">Descreva sua dúvida com o máximo de detalhes.</p>' +
      '<div class="form-field chat-wizard__field">' +
      '<label for="chat-duvida" data-i18n="chat.step_message_label">Digite a sua dúvida</label>' +
      '<textarea id="chat-duvida" name="duvida" rows="5" required></textarea>' +
      '</div>' +
      '<div class="chat-wizard__actions">' +
      '<button type="button" class="btn btn--ghost chat-wizard__back" data-i18n="chat.back">Voltar</button>' +
      '<button type="submit" class="btn btn--primary" data-i18n="chat.send">Enviar</button>' +
      '</div>' +
      '</div>' +
      '</form>' +
      '<div class="chat-wizard__success" id="chat-wizard-success" hidden>' +
      '<div class="chat-wizard__success-icon" aria-hidden="true">' +
      '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>' +
      '</div>' +
      '<p class="chat-wizard__success-text" data-i18n="chat.success">Em breve um atendente entrará em contato.</p>' +
      '<button type="button" class="btn btn--primary" id="chat-wizard-close" data-i18n="chat.close">Fechar</button>' +
      '</div>' +
      '</div>' +
      '<footer class="chat-drawer__footer">' +
      '<p class="chat-drawer__footer-note" data-i18n="chat.footer_note">Seus dados são usados apenas para retorno deste atendimento.</p>' +
      '</footer>' +
      '</aside>' +
      '</div>'
    );
  }

  function ensureWidgets() {
    if (!$('#chat-fab')) {
      document.body.insertAdjacentHTML('beforeend', fabHtml());
    } else {
      var fab = $('#chat-fab');
      fab.classList.add('chat-fab');
      if (!fab.classList.contains('is-open')) fab.innerHTML = PHONE_ICON;
    }
    var legacy = $('#chat-modal');
    if (legacy) legacy.remove();
    if (!$('#chat-drawer')) {
      document.body.insertAdjacentHTML('beforeend', drawerHtml());
    }
    if (global.SiteI18n && typeof global.SiteI18n.apply === 'function') {
      global.SiteI18n.apply($('#chat-drawer') || document);
      global.SiteI18n.apply($('#chat-fab') || document);
    }
  }

  function updateProgress() {
    var el = $('#chat-wizard-progress');
    if (el) {
      el.textContent = t('chat.step_progress', { current: currentStep, total: TOTAL_STEPS });
    }
    var drawer = $('#chat-drawer');
    drawer?.querySelectorAll('[data-step-dot]').forEach(function (dot) {
      var n = Number(dot.getAttribute('data-step-dot'));
      dot.classList.toggle('is-done', n < currentStep);
      dot.classList.toggle('is-active', n === currentStep);
    });
  }

  function showStep(step) {
    currentStep = step;
    var form = $('#chat-wizard-form');
    var success = $('#chat-wizard-success');
    if (form) form.hidden = false;
    if (success) success.hidden = true;

    form?.querySelectorAll('[data-chat-step]').forEach(function (block) {
      var n = Number(block.getAttribute('data-chat-step'));
      var active = n === step;
      block.hidden = !active;
      block.classList.toggle('is-active', active);
      if (active) {
        var input = block.querySelector('input, textarea');
        if (input) setTimeout(function () { input.focus(); }, 120);
      }
    });

    clearError();
    updateProgress();
  }

  function clearError() {
    var err = $('#chat-wizard-error');
    if (err) {
      err.hidden = true;
      err.textContent = '';
      err.classList.remove('is-error');
    }
  }

  function showError(message) {
    var err = $('#chat-wizard-error');
    if (!err) return;
    err.textContent = message;
    err.hidden = false;
    err.classList.add('is-error');
  }

  function validateStep(step) {
    if (step === 1) {
      var nome = $('#chat-nome')?.value?.trim() || '';
      if (nome.length < 3) return t('chat.error_name');
      return null;
    }
    if (step === 2) {
      var email = $('#chat-email')?.value?.trim() || '';
      if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return t('chat.error_email');
      return null;
    }
    if (step === 3) {
      var tel = $('#chat-telefone')?.value?.replace(/\D/g, '') || '';
      if (tel.length < 10) return t('chat.error_phone');
      return null;
    }
    if (step === 4) {
      var msg = $('#chat-duvida')?.value?.trim() || '';
      if (msg.length < 5) return t('chat.error_message');
      return null;
    }
    return null;
  }

  function resetWizard() {
    var form = $('#chat-wizard-form');
    form?.reset();
    showStep(1);
  }

  function setFabOpen(open) {
    var fab = $('#chat-fab');
    if (!fab) return;
    fab.classList.toggle('is-open', open);
    fab.setAttribute('aria-expanded', open ? 'true' : 'false');
    fab.innerHTML = open ? CLOSE_ICON : PHONE_ICON;
    fab.setAttribute('aria-label', open ? t('modal.close') : t('chat.open'));
  }

  function openDrawer() {
    ensureWidgets();
    resetWizard();
    var drawer = $('#chat-drawer');
    drawer?.classList.add('is-open');
    drawer?.setAttribute('aria-hidden', 'false');
    document.body.classList.add('chat-drawer-open');
    setFabOpen(true);
    drawer?.querySelector('.chat-drawer__panel')?.focus();
  }

  function closeDrawer() {
    var drawer = $('#chat-drawer');
    drawer?.classList.remove('is-open');
    drawer?.setAttribute('aria-hidden', 'true');
    document.body.classList.remove('chat-drawer-open');
    setFabOpen(false);
    resetWizard();
  }

  function toggleDrawer() {
    if ($('#chat-drawer')?.classList.contains('is-open')) closeDrawer();
    else openDrawer();
  }

  function showSuccess() {
    var form = $('#chat-wizard-form');
    var success = $('#chat-wizard-success');
    if (form) form.hidden = true;
    if (success) success.hidden = false;
    var progress = $('#chat-wizard-progress');
    if (progress) progress.textContent = '';
    $('#chat-drawer')?.querySelectorAll('[data-step-dot]').forEach(function (dot) {
      dot.classList.add('is-done');
      dot.classList.remove('is-active');
    });
  }

  function bindWizard() {
    var form = $('#chat-wizard-form');
    if (!form || form.dataset.chatBound === '1') return;
    form.dataset.chatBound = '1';

    form.querySelectorAll('.chat-wizard__next').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var err = validateStep(currentStep);
        if (err) {
          showError(err);
          return;
        }
        clearError();
        if (currentStep < TOTAL_STEPS) showStep(currentStep + 1);
      });
    });

    form.querySelectorAll('.chat-wizard__back').forEach(function (btn) {
      btn.addEventListener('click', function () {
        clearError();
        if (currentStep > 1) showStep(currentStep - 1);
      });
    });

    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var err = validateStep(4);
      if (err) {
        showError(err);
        return;
      }
      clearError();
      var submitBtn = form.querySelector('[type="submit"]');
      var submitLabel = submitBtn ? submitBtn.textContent : '';
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = t('chat.sending');
      }
      var payload = {
        nome: $('#chat-nome')?.value?.trim() || '',
        email: $('#chat-email')?.value?.trim() || '',
        telefone: $('#chat-telefone')?.value?.trim() || '',
        mensagem: $('#chat-duvida')?.value?.trim() || '',
        origem: 'chat',
        pagina: (global.location && global.location.pathname) || 'index.html',
      };
      var send =
        global.RodaviaAPI && typeof global.RodaviaAPI.atendimento === 'function'
          ? global.RodaviaAPI.atendimento(payload)
          : Promise.reject(new Error(t('chat.error_submit')));
      send
        .then(function () {
          showSuccess();
        })
        .catch(function (submitErr) {
          showError(submitErr && submitErr.message ? submitErr.message : t('chat.error_submit'));
        })
        .finally(function () {
          if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = submitLabel || t('chat.send');
          }
        });
    });

    $('#chat-wizard-close')?.addEventListener('click', closeDrawer);
  }

  function bindDrawer() {
    var drawer = $('#chat-drawer');
    if (!drawer || drawer.dataset.bound === '1') return;
    drawer.dataset.bound = '1';

    drawer.querySelectorAll('[data-chat-close]').forEach(function (btn) {
      btn.addEventListener('click', closeDrawer);
    });

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && drawer.classList.contains('is-open')) closeDrawer();
    });
  }

  function init() {
    ensureWidgets();
    bindWizard();
    bindDrawer();

    var fab = $('#chat-fab');
    if (fab && fab.dataset.chatFabBound !== '1') {
      fab.dataset.chatFabBound = '1';
      fab.addEventListener('click', toggleDrawer);
    }
  }

  global.SiteChat = {
    fabHtml: fabHtml,
    modalHtml: drawerHtml,
    drawerHtml: drawerHtml,
    ensureWidgets: ensureWidgets,
    init: init,
    open: openDrawer,
    close: closeDrawer,
    toggle: toggleDrawer,
  };
})(window);
