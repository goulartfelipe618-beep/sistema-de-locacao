/**
 * Botão flutuante de atendimento (quadrado + telefone) e formulário por etapas.
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
      '<button type="button" class="chat-fab" id="chat-fab" data-i18n-aria="chat.open" aria-label="Abrir atendimento">' +
      PHONE_ICON +
      '</button>'
    );
  }

  function modalHtml() {
    return (
      '<div class="modal" id="chat-modal" aria-hidden="true" role="dialog" aria-labelledby="chat-modal-title" aria-modal="true">' +
      '<div class="modal__backdrop" data-close-modal="chat-modal"></div>' +
      '<div class="modal__panel modal__panel--chat">' +
      '<button type="button" class="modal__close" data-close-modal="chat-modal" data-i18n-aria="modal.close" aria-label="Fechar">×</button>' +
      '<h2 class="modal__title" id="chat-modal-title" data-i18n="chat.title">Atendimento Rodavia</h2>' +
      '<p class="chat-wizard__progress" id="chat-wizard-progress" aria-live="polite"></p>' +
      '<form class="chat-wizard" id="chat-wizard-form" novalidate>' +
      '<p class="form-message chat-wizard__error" id="chat-wizard-error" role="alert" hidden></p>' +
      '<div class="chat-wizard__step is-active" data-chat-step="1">' +
      '<div class="form-field">' +
      '<label for="chat-nome" data-i18n="chat.step_name_label">Nome completo</label>' +
      '<input type="text" id="chat-nome" name="nome" required autocomplete="name" />' +
      '</div>' +
      '<div class="chat-wizard__actions">' +
      '<button type="button" class="btn btn--primary chat-wizard__next" data-i18n="chat.continue">Continuar</button>' +
      '</div>' +
      '</div>' +
      '<div class="chat-wizard__step" data-chat-step="2" hidden>' +
      '<div class="form-field">' +
      '<label for="chat-email" data-i18n="chat.step_email_label">E-mail</label>' +
      '<input type="email" id="chat-email" name="email" required autocomplete="email" />' +
      '</div>' +
      '<div class="chat-wizard__actions">' +
      '<button type="button" class="btn btn--ghost chat-wizard__back" data-i18n="chat.back">Voltar</button>' +
      '<button type="button" class="btn btn--primary chat-wizard__next" data-i18n="chat.continue">Continuar</button>' +
      '</div>' +
      '</div>' +
      '<div class="chat-wizard__step" data-chat-step="3" hidden>' +
      '<div class="form-field">' +
      '<label for="chat-telefone" data-i18n="chat.step_phone_label">Telefone</label>' +
      '<input type="tel" id="chat-telefone" name="telefone" required autocomplete="tel" inputmode="tel" />' +
      '</div>' +
      '<div class="chat-wizard__actions">' +
      '<button type="button" class="btn btn--ghost chat-wizard__back" data-i18n="chat.back">Voltar</button>' +
      '<button type="button" class="btn btn--primary chat-wizard__next" data-i18n="chat.continue">Continuar</button>' +
      '</div>' +
      '</div>' +
      '<div class="chat-wizard__step" data-chat-step="4" hidden>' +
      '<div class="form-field">' +
      '<label for="chat-duvida" data-i18n="chat.step_message_label">Digite a sua dúvida</label>' +
      '<textarea id="chat-duvida" name="duvida" rows="4" required></textarea>' +
      '</div>' +
      '<div class="chat-wizard__actions">' +
      '<button type="button" class="btn btn--ghost chat-wizard__back" data-i18n="chat.back">Voltar</button>' +
      '<button type="submit" class="btn btn--primary" data-i18n="chat.send">Enviar</button>' +
      '</div>' +
      '</div>' +
      '</form>' +
      '<div class="chat-wizard__success" id="chat-wizard-success" hidden>' +
      '<p class="chat-wizard__success-text" data-i18n="chat.success">Em breve um atendente entrará em contato.</p>' +
      '<button type="button" class="btn btn--primary" id="chat-wizard-close" data-i18n="chat.close">Fechar</button>' +
      '</div>' +
      '</div>' +
      '</div>'
    );
  }

  function ensureWidgets() {
    if (!$('#chat-fab')) {
      document.body.insertAdjacentHTML('beforeend', fabHtml());
    } else {
      var fab = $('#chat-fab');
      fab.classList.add('chat-fab');
      fab.innerHTML = PHONE_ICON;
    }
    if (!$('#chat-modal')) {
      document.body.insertAdjacentHTML('beforeend', modalHtml());
    }
    if (global.SiteI18n && typeof global.SiteI18n.apply === 'function') {
      global.SiteI18n.apply($('#chat-modal') || document);
      global.SiteI18n.apply($('#chat-fab') || document);
    }
  }

  function updateProgress() {
    var el = $('#chat-wizard-progress');
    if (el) {
      el.textContent = t('chat.step_progress', { current: currentStep, total: TOTAL_STEPS });
    }
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
        if (input) setTimeout(function () { input.focus(); }, 80);
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

  function openModal() {
    ensureWidgets();
    resetWizard();
    var modal = $('#chat-modal');
    modal?.classList.add('is-open');
    modal?.setAttribute('aria-hidden', 'false');
  }

  function closeModal() {
    var modal = $('#chat-modal');
    modal?.classList.remove('is-open');
    modal?.setAttribute('aria-hidden', 'true');
    resetWizard();
  }

  function showSuccess() {
    var form = $('#chat-wizard-form');
    var success = $('#chat-wizard-success');
    if (form) form.hidden = true;
    if (success) success.hidden = false;
    var progress = $('#chat-wizard-progress');
    if (progress) progress.textContent = '';
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
      showSuccess();
    });

    $('#chat-wizard-close')?.addEventListener('click', closeModal);
  }

  function init() {
    ensureWidgets();
    bindWizard();

    var fab = $('#chat-fab');
    if (fab && fab.dataset.chatFabBound !== '1') {
      fab.dataset.chatFabBound = '1';
      fab.addEventListener('click', openModal);
    }

    document.querySelectorAll('[data-close-modal="chat-modal"]').forEach(function (btn) {
      if (btn.dataset.chatCloseBound === '1') return;
      btn.dataset.chatCloseBound = '1';
      btn.addEventListener('click', closeModal);
    });
  }

  global.SiteChat = {
    fabHtml: fabHtml,
    modalHtml: modalHtml,
    ensureWidgets: ensureWidgets,
    init: init,
    open: openModal,
    close: closeModal,
  };
})(window);
