/**
 * Internacionalização do site público (pt-BR, en-US, es-ES).
 * Carregue antes dos demais scripts. Expõe window.SiteI18n.
 */
(function (global) {
  'use strict';

  var STORAGE_KEY = 'rodavia_site_lang';
  var DEFAULT_LANG = 'pt-BR';

  var LOCALES = {
    'pt-BR': { flag: '\uD83C\uDDE7\uD83C\uDDF7', label: 'Brasil', menu: 'Portugu\u00eas (Brasil)' },
    'en-US': { flag: '\uD83C\uDDFA\uD83C\uDDF8', label: 'USA', menu: 'English (USA)' },
    'es-ES': { flag: '\uD83C\uDDEA\uD83C\uDDF8', label: 'ESP', menu: 'Espa\u00f1ol (ESP)' },
  };

  var MESSAGES = {
    'pt-BR': {
      'meta.index.title': 'LOCADORA RODAVIA | Aluguel de carros',
      'meta.index.description':
        'LOCADORA RODAVIA — aluguel de carros com retirada r\u00e1pida, frota diversificada e as melhores condi\u00e7\u00f5es para sua viagem.',
      'meta.grupos.title': 'Grupos de Carros | LOCADORA RODAVIA',
      'meta.grupos.description':
        'Grupos de carros LOCADORA RODAVIA — escolha a categoria ideal e alugue com as melhores condi\u00e7\u00f5es.',
      'skip.main': 'Ir para conte\u00fado principal',
      'topbar.business': 'Neg\u00f3cios Rodavia',
      'topbar.rental': 'Aluguel de carros',
      'topbar.fleet': 'Gest\u00e3o de frotas',
      'topbar.used': 'Seminovos',
      'topbar.subscription': 'Carro por assinatura',
      'topbar.app': 'Carro para app',
      'locale.choose': 'Escolher idioma',
      'nav.home_page': 'P\u00e1gina inicial {name}',
      'nav.toggle': 'Abrir menu',
      'nav.groups': 'Grupos de carros',
      'nav.agencies': 'Rede de ag\u00eancias',
      'nav.about': 'Sobre n\u00f3s',
      'nav.offers': 'Ofertas',
      'nav.loyalty': 'Fidelidade',
      'nav.business': 'Para empresas',
      'nav.faq': 'D\u00favidas',
      'nav.main': 'Menu principal',
      'hero.label': 'Destaques',
      'hero.loading': 'Carregando destaques\u2026',
      'hero.prev': 'Slide anterior',
      'hero.next': 'Pr\u00f3ximo slide',
      'hero.dots': 'Slides do hero',
      'search.hidden_title': 'Busca de ve\u00edculos Rodavia',
      'search.pickup': 'Local de retirada',
      'search.pickup_prompt': 'Onde voc\u00ea quer retirar o carro?',
      'search.date': 'Data',
      'search.time': 'Hora',
      'search.return': 'Devolu\u00e7\u00e3o',
      'search.monthly': 'Economize com o aluguel mensal',
      'search.submit': 'Buscar',
      'search.checking_api': 'Verificando API\u2026',
      'fleet.title': 'Conhe\u00e7a a nossa Frota',
      'fleet.subtitle': 'As melhores condi\u00e7\u00f5es para voc\u00ea reservar e aproveitar',
      'fleet.prev': 'Grupo anterior',
      'fleet.next': 'Pr\u00f3ximo grupo',
      'fleet.empty':
        'Fa\u00e7a uma busca no topo para ver os grupos dispon\u00edveis no per\u00edodo escolhido.',
      'fleet.all_groups': 'Confira todos os grupos',
      'service.fast_title': 'Fast Retirada Digital',
      'service.fast_text':
        'Retire seu carro em at\u00e9 5 minutos com check-in digital, contrato eletr\u00f4nico e chaves liberadas na hora \u2014 menos fila, mais viagem.',
      'service.extras_title': 'Adicionais',
      'service.extras_text':
        'Pra que sua viagem seja ainda mais simples: GPS, cadeirinha, prote\u00e7\u00e3o extra e outros servi\u00e7os para personalizar seu aluguel.',
      'service.portal_title': 'Portal do Cliente',
      'service.portal_text':
        'Tudo que voc\u00ea precisa em um s\u00f3 lugar: reservas, faturas, hist\u00f3rico de loca\u00e7\u00f5es e benef\u00edcios do programa de fidelidade Rodavia.',
      'service.learn_more': 'Saiba mais',
      'dest.title': 'Destinos para descobrir e se inspirar',
      'dest.subtitle':
        'Do litoral \u00e0s montanhas, explore o Brasil com a liberdade de um carro Rodavia. Inspire-se com roteiros selecionados e planeje sua pr\u00f3xima escapada.',
      'dest.all': 'Conferir todos os destinos',
      'dest.rio': 'Rio de Janeiro \u2014 RJ',
      'dest.gramado': 'Gramado \u2014 RS',
      'dest.salvador': 'Salvador \u2014 BA',
      'dest.foz': 'Foz do Igua\u00e7u \u2014 PR',
      'dest.floripa': 'Florian\u00f3polis \u2014 SC',
      'dest.brasilia': 'Bras\u00edlia \u2014 DF',
      'carousel.prev': 'Anterior',
      'carousel.next': 'Pr\u00f3ximo',
      'footer.app_title': 'Aplicativo Rodavia',
      'footer.app_text':
        'Baixe o app fict\u00edcio para gerenciar reservas e fidelidade (em breve nas lojas).',
      'footer.institutional': 'Institucional',
      'footer.about': 'Sobre a Rodavia',
      'footer.sustainability': 'Sustentabilidade',
      'footer.press': 'Imprensa',
      'footer.careers': 'Trabalhe conosco',
      'footer.business': 'Neg\u00f3cios',
      'footer.partnerships': 'Parcerias',
      'footer.business_rental': 'Rodavia empresas',
      'footer.for_you': 'Para voc\u00ea',
      'footer.faq': 'D\u00favidas frequentes',
      'footer.cookies_pref': 'Prefer\u00eancia de cookies',
      'footer.contacts': 'Contatos',
      'footer.rights': '\u00a9 LOCADORA RODAVIA. Todos os direitos reservados.',
      'footer.version': 'Vers\u00e3o do site v1.0.0',
      'cookie.title': 'Cookies',
      'cookie.text':
        'Este site utiliza cookies para garantir que voc\u00ea obtenha a melhor experi\u00eancia durante sua navega\u00e7\u00e3o, melhorar continuamente nossos servi\u00e7os e lhe ofertar publicidade relevante aos seus interesses. Clique em Rejeitar se n\u00e3o desejar receber ofertas direcionadas.',
      'cookie.text_short':
        'Este site utiliza cookies para melhorar sua experi\u00eancia. Clique em Rejeitar se n\u00e3o desejar ofertas direcionadas.',
      'cookie.learn': 'Saiba mais',
      'cookie.accept': 'Manter cookies',
      'cookie.reject': 'Rejeitar',
      'cookie.prefs': 'Prefer\u00eancia de Cookies',
      'cookie.prefs_title': 'Prefer\u00eancia de cookies',
      'cookie.prefs_text':
        'Sua escolha \u00e9 salva no navegador (localStorage). Voc\u00ea pode alter\u00e1-la limpando os dados do site.',
      'chat.open': 'Abrir atendimento',
      'chat.fab_label': 'Reserve direto conosco',
      'chat.title': 'Atendimento Rodavia',
      'chat.subtitle': 'Online · respondemos em breve',
      'chat.prompt_name': 'Para começar, informe seu nome completo.',
      'chat.prompt_email': 'Qual e-mail podemos usar para retorno?',
      'chat.prompt_phone': 'Informe um telefone com DDD para contato.',
      'chat.prompt_message': 'Descreva sua dúvida com o máximo de detalhes.',
      'chat.footer_note': 'Seus dados são usados apenas para retorno deste atendimento.',
      'chat.text':
        'Chat em breve. Enquanto isso, ligue para <strong>0800 123 4567</strong> ou envie e-mail para contato@rodavia.com.br.',
      'chat.step_progress': 'Etapa {current} de {total}',
      'chat.step_name_label': 'Nome completo',
      'chat.step_email_label': 'E-mail',
      'chat.step_phone_label': 'Telefone',
      'chat.step_message_label': 'Digite a sua dúvida',
      'chat.continue': 'Continuar',
      'chat.back': 'Voltar',
      'chat.send': 'Enviar',
      'chat.close': 'Fechar',
      'chat.success': 'Em breve um atendente entrará em contato.',
      'chat.error_name': 'Informe seu nome completo.',
      'chat.error_email': 'Informe um e-mail válido.',
      'chat.error_phone': 'Informe um telefone válido com DDD.',
      'chat.error_message': 'Descreva sua dúvida com pelo menos 5 caracteres.',
      'chat.sending': 'Enviando…',
      'chat.error_submit': 'Não foi possível enviar sua mensagem. Tente novamente em instantes.',
      'modal.close': 'Fechar',
      'scroll.top': 'Voltar ao topo',
      'reserve.title': 'Confirmar reserva',
      'reserve.name': 'Nome completo',
      'reserve.email': 'E-mail',
      'reserve.cpf': 'CPF',
      'reserve.phone': 'Telefone',
      'reserve.submit': 'Enviar reserva',
      'breadcrumb.trail': 'Trilha',
      'breadcrumb.home': 'Home',
      'groups.title': 'Grupos de Carros',
      'groups.loading': 'Carregando\u2026',
      'groups.empty':
        'Informe retirada e devolu\u00e7\u00e3o na barra acima e clique em Buscar para listar apenas grupos dispon\u00edveis no per\u00edodo (dados do ERP).',
      'groups.rentals': 'Reservas',
      'groups.my_reservations': 'Minhas reservas',
      'groups.prepay': 'Pr\u00e9-pagamento',
      'groups.support': 'Atendimento',
      'groups.whatsapp': 'WhatsApp',
      'groups.contact': 'Fale conosco',
      'groups.app_short': 'Gerencie reservas pelo celular.',
      'groups.footer_legal':
        '\u00a9 LOCADORA RODAVIA \u2014 CNPJ 00.000.000/0001-00 \u2014 Vers\u00e3o do site v1.0.0',
      'groups.rent_now': 'Alugar agora',
      'groups.view_details': 'Ver detalhes',
      'feature.ac': 'Ar',
      'feature.no_ac': 'Sem ar',
      'branches.loading': 'Carregando filiais\u2026',
      'branches.none': 'Nenhuma filial dispon\u00edvel',
      'bff.checking': 'Verificando API\u2026',
      'bff.connected': 'API conectada',
      'bff.offline': 'API offline',
      'search.error.pickup': 'Selecione o local de retirada.',
      'search.error.invalid_dates': 'Informe datas v\u00e1lidas.',
      'search.error.return_after': 'A devolu\u00e7\u00e3o deve ser posterior \u00e0 retirada.',
      'search.status.searching': 'Buscando grupos\u2026',
      'search.status.no_vehicles': 'Nenhum ve\u00edculo dispon\u00edvel neste per\u00edodo.',
      'search.status.groups': '{count} grupo(s) dispon\u00edvel(is) no per\u00edodo.',
      'search.status.groups_page': '{count} grupo(s) dispon\u00edvel(is).',
      'search.error.load_fleet': 'N\u00e3o foi poss\u00edvel carregar a frota. Tente novamente.',
      'search.error.load_groups': 'N\u00e3o foi poss\u00edvel carregar os grupos.',
      'search.error.generic': 'Erro ao buscar.',
      'search.error.before_reserve': 'Fa\u00e7a uma busca antes de reservar.',
      'search.error.boot': 'Erro ao iniciar integra\u00e7\u00e3o',
      'quote.calculating': 'Calculando cota\u00e7\u00e3o\u2026',
      'quote.on_confirm': 'Cota\u00e7\u00e3o dispon\u00edvel na confirma\u00e7\u00e3o.',
      'reserve.sending': 'Enviando reserva\u2026',
      'reserve.sending_short': 'Enviando\u2026',
      'reserve.success':
        'Reserva enviada com sucesso! Em breve voc\u00ea receber\u00e1 a confirma\u00e7\u00e3o.',
      'reserve.success_short': 'Reserva enviada com sucesso!',
      'reserve.error': 'N\u00e3o foi poss\u00edvel concluir a reserva.',
      'reserve.error_short': 'Erro ao reservar.',
      'groups.loading_groups': 'Carregando grupos\u2026',
      'hero.promo': 'Destaque promocional',
      'fleet.vehicle_alt': 'Ve\u00edculo {title}',
      'fleet.subtitle_default': 'Modelo representativo da categoria',
      'fleet.similar': '{model} ou similar',
    },
    'en-US': {
      'meta.index.title': 'RODAVIA RENT A CAR | Car rental',
      'meta.index.description':
        'RODAVIA RENT A CAR — car rental with fast pickup, diverse fleet and the best conditions for your trip.',
      'meta.grupos.title': 'Car Groups | RODAVIA RENT A CAR',
      'meta.grupos.description':
        'RODAVIA car groups — choose the ideal category and rent with the best conditions.',
      'skip.main': 'Skip to main content',
      'topbar.business': 'Rodavia businesses',
      'topbar.rental': 'Car rental',
      'topbar.fleet': 'Fleet management',
      'topbar.used': 'Pre-owned cars',
      'topbar.subscription': 'Car subscription',
      'topbar.app': 'Rideshare cars',
      'locale.choose': 'Choose language',
      'nav.home_page': 'Home page {name}',
      'nav.toggle': 'Open menu',
      'nav.groups': 'Car groups',
      'nav.agencies': 'Branch network',
      'nav.about': 'About us',
      'nav.offers': 'Offers',
      'nav.loyalty': 'Loyalty',
      'nav.business': 'For business',
      'nav.faq': 'Help',
      'nav.main': 'Main menu',
      'hero.label': 'Highlights',
      'hero.loading': 'Loading highlights\u2026',
      'hero.prev': 'Previous slide',
      'hero.next': 'Next slide',
      'hero.dots': 'Hero slides',
      'search.hidden_title': 'Rodavia vehicle search',
      'search.pickup': 'Pickup location',
      'search.pickup_prompt': 'Where do you want to pick up the car?',
      'search.date': 'Date',
      'search.time': 'Time',
      'search.return': 'Return',
      'search.monthly': 'Save with monthly rental',
      'search.submit': 'Search',
      'search.checking_api': 'Checking API\u2026',
      'fleet.title': 'Discover our Fleet',
      'fleet.subtitle': 'The best conditions for you to book and enjoy',
      'fleet.prev': 'Previous group',
      'fleet.next': 'Next group',
      'fleet.empty': 'Search at the top to see available groups for your selected dates.',
      'fleet.all_groups': 'See all groups',
      'service.fast_title': 'Fast Digital Pickup',
      'service.fast_text':
        'Pick up your car in up to 5 minutes with digital check-in, electronic contract and keys ready on the spot — less waiting, more travel.',
      'service.extras_title': 'Add-ons',
      'service.extras_text':
        'Make your trip even easier: GPS, child seat, extra protection and other services to customize your rental.',
      'service.portal_title': 'Customer Portal',
      'service.portal_text':
        'Everything you need in one place: bookings, invoices, rental history and Rodavia loyalty benefits.',
      'service.learn_more': 'Learn more',
      'dest.title': 'Destinations to discover and get inspired',
      'dest.subtitle':
        'From the coast to the mountains, explore Brazil with the freedom of a Rodavia car. Get inspired by selected routes and plan your next getaway.',
      'dest.all': 'See all destinations',
      'dest.rio': 'Rio de Janeiro \u2014 RJ',
      'dest.gramado': 'Gramado \u2014 RS',
      'dest.salvador': 'Salvador \u2014 BA',
      'dest.foz': 'Foz do Igua\u00e7u \u2014 PR',
      'dest.floripa': 'Florian\u00f3polis \u2014 SC',
      'dest.brasilia': 'Bras\u00edlia \u2014 DF',
      'carousel.prev': 'Previous',
      'carousel.next': 'Next',
      'footer.app_title': 'Rodavia App',
      'footer.app_text':
        'Download the app to manage bookings and loyalty (coming soon to stores).',
      'footer.institutional': 'Company',
      'footer.about': 'About Rodavia',
      'footer.sustainability': 'Sustainability',
      'footer.press': 'Press',
      'footer.careers': 'Careers',
      'footer.business': 'Business',
      'footer.partnerships': 'Partnerships',
      'footer.business_rental': 'Rodavia for business',
      'footer.for_you': 'For you',
      'footer.faq': 'FAQ',
      'footer.cookies_pref': 'Cookie preferences',
      'footer.contacts': 'Contact',
      'footer.rights': '\u00a9 RODAVIA RENT A CAR. All rights reserved.',
      'footer.version': 'Site version v1.0.0',
      'cookie.title': 'Cookies',
      'cookie.text':
        'This site uses cookies to ensure the best browsing experience, continuously improve our services and offer relevant advertising. Click Reject if you do not want targeted offers.',
      'cookie.text_short':
        'This site uses cookies to improve your experience. Click Reject if you do not want targeted offers.',
      'cookie.learn': 'Learn more',
      'cookie.accept': 'Accept cookies',
      'cookie.reject': 'Reject',
      'cookie.prefs': 'Cookie Preferences',
      'cookie.prefs_title': 'Cookie preferences',
      'cookie.prefs_text':
        'Your choice is saved in the browser (localStorage). You can change it by clearing site data.',
      'chat.open': 'Open support',
      'chat.fab_label': 'Book directly with us',
      'chat.title': 'Rodavia Support',
      'chat.subtitle': 'Online · we reply shortly',
      'chat.prompt_name': 'To get started, enter your full name.',
      'chat.prompt_email': 'Which email should we use to reply?',
      'chat.prompt_phone': 'Enter a phone number with area code.',
      'chat.prompt_message': 'Describe your question in as much detail as you can.',
      'chat.footer_note': 'Your data is used only to follow up on this request.',
      'chat.text':
        'Chat coming soon. Meanwhile, call <strong>0800 123 4567</strong> or email contato@rodavia.com.br.',
      'chat.step_progress': 'Step {current} of {total}',
      'chat.step_name_label': 'Full name',
      'chat.step_email_label': 'Email',
      'chat.step_phone_label': 'Phone',
      'chat.step_message_label': 'Type your question',
      'chat.continue': 'Continue',
      'chat.back': 'Back',
      'chat.send': 'Send',
      'chat.close': 'Close',
      'chat.success': 'An agent will contact you shortly.',
      'chat.error_name': 'Please enter your full name.',
      'chat.error_email': 'Please enter a valid email.',
      'chat.error_phone': 'Please enter a valid phone number with area code.',
      'chat.error_message': 'Please describe your question (at least 5 characters).',
      'chat.sending': 'Sending…',
      'chat.error_submit': 'Could not send your message. Please try again shortly.',
      'modal.close': 'Close',
      'scroll.top': 'Back to top',
      'reserve.title': 'Confirm booking',
      'reserve.name': 'Full name',
      'reserve.email': 'Email',
      'reserve.cpf': 'Tax ID (CPF)',
      'reserve.phone': 'Phone',
      'reserve.submit': 'Submit booking',
      'breadcrumb.trail': 'Breadcrumb',
      'breadcrumb.home': 'Home',
      'groups.title': 'Car Groups',
      'groups.loading': 'Loading\u2026',
      'groups.empty':
        'Enter pickup and return dates above and click Search to list only groups available for the period (ERP data).',
      'groups.rentals': 'Bookings',
      'groups.my_reservations': 'My bookings',
      'groups.prepay': 'Prepayment',
      'groups.support': 'Support',
      'groups.whatsapp': 'WhatsApp',
      'groups.contact': 'Contact us',
      'groups.app_short': 'Manage bookings on your phone.',
      'groups.footer_legal':
        '\u00a9 RODAVIA RENT A CAR \u2014 Tax ID 00.000.000/0001-00 \u2014 Site version v1.0.0',
      'groups.rent_now': 'Rent now',
      'groups.view_details': 'View details',
      'feature.ac': 'A/C',
      'feature.no_ac': 'No A/C',
      'branches.loading': 'Loading branches\u2026',
      'branches.none': 'No branches available',
      'bff.checking': 'Checking API\u2026',
      'bff.connected': 'API connected',
      'bff.offline': 'API offline',
      'search.error.pickup': 'Select a pickup location.',
      'search.error.invalid_dates': 'Enter valid dates.',
      'search.error.return_after': 'Return must be after pickup.',
      'search.status.searching': 'Searching groups\u2026',
      'search.status.no_vehicles': 'No vehicles available for this period.',
      'search.status.groups': '{count} group(s) available for the period.',
      'search.status.groups_page': '{count} group(s) available.',
      'search.error.load_fleet': 'Could not load fleet. Please try again.',
      'search.error.load_groups': 'Could not load groups.',
      'search.error.generic': 'Search error.',
      'search.error.before_reserve': 'Search first before booking.',
      'search.error.boot': 'Failed to start integration',
      'quote.calculating': 'Calculating quote\u2026',
      'quote.on_confirm': 'Quote available at confirmation.',
      'reserve.sending': 'Sending booking\u2026',
      'reserve.sending_short': 'Sending\u2026',
      'reserve.success': 'Booking sent successfully! You will receive confirmation soon.',
      'reserve.success_short': 'Booking sent successfully!',
      'reserve.error': 'Could not complete the booking.',
      'reserve.error_short': 'Booking error.',
      'groups.loading_groups': 'Loading groups\u2026',
      'hero.promo': 'Promotional highlight',
      'fleet.vehicle_alt': 'Vehicle {title}',
      'fleet.subtitle_default': 'Representative model for this category',
      'fleet.similar': '{model} or similar',
    },
    'es-ES': {
      'meta.index.title': 'LOCADORA RODAVIA | Alquiler de coches',
      'meta.index.description':
        'LOCADORA RODAVIA — alquiler de coches con retirada r\u00e1pida, flota diversificada y las mejores condiciones para su viaje.',
      'meta.grupos.title': 'Grupos de Coches | LOCADORA RODAVIA',
      'meta.grupos.description':
        'Grupos de coches LOCADORA RODAVIA — elija la categor\u00eda ideal y alquile con las mejores condiciones.',
      'skip.main': 'Ir al contenido principal',
      'topbar.business': 'Negocios Rodavia',
      'topbar.rental': 'Alquiler de coches',
      'topbar.fleet': 'Gesti\u00f3n de flotas',
      'topbar.used': 'Seminuevos',
      'topbar.subscription': 'Coche por suscripci\u00f3n',
      'topbar.app': 'Coche para app',
      'locale.choose': 'Elegir idioma',
      'nav.home_page': 'P\u00e1gina inicial {name}',
      'nav.toggle': 'Abrir men\u00fa',
      'nav.groups': 'Grupos de coches',
      'nav.agencies': 'Red de agencias',
      'nav.about': 'Sobre nosotros',
      'nav.offers': 'Ofertas',
      'nav.loyalty': 'Fidelidad',
      'nav.business': 'Para empresas',
      'nav.faq': 'Dudas',
      'nav.main': 'Men\u00fa principal',
      'hero.label': 'Destacados',
      'hero.loading': 'Cargando destacados\u2026',
      'hero.prev': 'Diapositiva anterior',
      'hero.next': 'Siguiente diapositiva',
      'hero.dots': 'Diapositivas del hero',
      'search.hidden_title': 'B\u00fasqueda de veh\u00edculos Rodavia',
      'search.pickup': 'Lugar de recogida',
      'search.pickup_prompt': '\u00bfD\u00f3nde desea recoger el coche?',
      'search.date': 'Fecha',
      'search.time': 'Hora',
      'search.return': 'Devoluci\u00f3n',
      'search.monthly': 'Ahorre con alquiler mensual',
      'search.submit': 'Buscar',
      'search.checking_api': 'Verificando API\u2026',
      'fleet.title': 'Conozca nuestra Flota',
      'fleet.subtitle': 'Las mejores condiciones para reservar y disfrutar',
      'fleet.prev': 'Grupo anterior',
      'fleet.next': 'Siguiente grupo',
      'fleet.empty':
        'Realice una b\u00fasqueda arriba para ver los grupos disponibles en el per\u00edodo elegido.',
      'fleet.all_groups': 'Ver todos los grupos',
      'service.fast_title': 'Retirada Digital R\u00e1pida',
      'service.fast_text':
        'Recoja su coche en hasta 5 minutos con check-in digital, contrato electr\u00f3nico y llaves listas al instante — menos fila, m\u00e1s viaje.',
      'service.extras_title': 'Adicionales',
      'service.extras_text':
        'Para que su viaje sea a\u00fan m\u00e1s simple: GPS, silla infantil, protecci\u00f3n extra y otros servicios para personalizar su alquiler.',
      'service.portal_title': 'Portal del Cliente',
      'service.portal_text':
        'Todo lo que necesita en un solo lugar: reservas, facturas, historial de alquileres y beneficios del programa de fidelidad Rodavia.',
      'service.learn_more': 'Saber m\u00e1s',
      'dest.title': 'Destinos para descubrir e inspirarse',
      'dest.subtitle':
        'De la costa a las monta\u00f1as, explore Brasil con la libertad de un coche Rodavia. Insp\u00edrese con rutas seleccionadas y planee su pr\u00f3xima escapada.',
      'dest.all': 'Ver todos los destinos',
      'dest.rio': 'Rio de Janeiro \u2014 RJ',
      'dest.gramado': 'Gramado \u2014 RS',
      'dest.salvador': 'Salvador \u2014 BA',
      'dest.foz': 'Foz do Igua\u00e7u \u2014 PR',
      'dest.floripa': 'Florian\u00f3polis \u2014 SC',
      'dest.brasilia': 'Bras\u00edlia \u2014 DF',
      'carousel.prev': 'Anterior',
      'carousel.next': 'Siguiente',
      'footer.app_title': 'Aplicaci\u00f3n Rodavia',
      'footer.app_text':
        'Descargue la app para gestionar reservas y fidelidad (pr\u00f3ximamente en las tiendas).',
      'footer.institutional': 'Institucional',
      'footer.about': 'Sobre Rodavia',
      'footer.sustainability': 'Sostenibilidad',
      'footer.press': 'Prensa',
      'footer.careers': 'Trabaje con nosotros',
      'footer.business': 'Negocios',
      'footer.partnerships': 'Alianzas',
      'footer.business_rental': 'Rodavia empresas',
      'footer.for_you': 'Para usted',
      'footer.faq': 'Preguntas frecuentes',
      'footer.cookies_pref': 'Preferencia de cookies',
      'footer.contacts': 'Contactos',
      'footer.rights': '\u00a9 LOCADORA RODAVIA. Todos los derechos reservados.',
      'footer.version': 'Versi\u00f3n del sitio v1.0.0',
      'cookie.title': 'Cookies',
      'cookie.text':
        'Este sitio utiliza cookies para garantizar la mejor experiencia de navegaci\u00f3n, mejorar continuamente nuestros servicios y ofrecer publicidad relevante. Haga clic en Rechazar si no desea ofertas dirigidas.',
      'cookie.text_short':
        'Este sitio utiliza cookies para mejorar su experiencia. Haga clic en Rechazar si no desea ofertas dirigidas.',
      'cookie.learn': 'Saber m\u00e1s',
      'cookie.accept': 'Mantener cookies',
      'cookie.reject': 'Rechazar',
      'cookie.prefs': 'Preferencia de Cookies',
      'cookie.prefs_title': 'Preferencia de cookies',
      'cookie.prefs_text':
        'Su elecci\u00f3n se guarda en el navegador (localStorage). Puede cambiarla borrando los datos del sitio.',
      'chat.open': 'Abrir atención',
      'chat.fab_label': 'Reserve directo con nosotros',
      'chat.title': 'Atenci\u00f3n Rodavia',
      'chat.subtitle': 'En l\u00ednea \u00b7 respondemos pronto',
      'chat.prompt_name': 'Para comenzar, indique su nombre completo.',
      'chat.prompt_email': '\u00bfQu\u00e9 correo podemos usar para responder?',
      'chat.prompt_phone': 'Indique un tel\u00e9fono con c\u00f3digo de \u00e1rea.',
      'chat.prompt_message': 'Describa su consulta con el mayor detalle posible.',
      'chat.footer_note': 'Sus datos se usan solo para dar seguimiento a esta solicitud.',
      'chat.text':
        'Chat pr\u00f3ximamente. Mientras tanto, llame al <strong>0800 123 4567</strong> o escriba a contato@rodavia.com.br.',
      'chat.step_progress': 'Paso {current} de {total}',
      'chat.step_name_label': 'Nombre completo',
      'chat.step_email_label': 'Correo electr\u00f3nico',
      'chat.step_phone_label': 'Tel\u00e9fono',
      'chat.step_message_label': 'Escriba su consulta',
      'chat.continue': 'Continuar',
      'chat.back': 'Volver',
      'chat.send': 'Enviar',
      'chat.close': 'Cerrar',
      'chat.success': 'Pronto un agente se pondr\u00e1 en contacto.',
      'chat.error_name': 'Ingrese su nombre completo.',
      'chat.error_email': 'Ingrese un correo v\u00e1lido.',
      'chat.error_phone': 'Ingrese un tel\u00e9fono v\u00e1lido con c\u00f3digo de \u00e1rea.',
      'chat.error_message': 'Describa su consulta con al menos 5 caracteres.',
      'chat.sending': 'Enviando…',
      'chat.error_submit': 'No se pudo enviar su mensaje. Inténtelo de nuevo en unos instantes.',
      'modal.close': 'Cerrar',
      'scroll.top': 'Volver arriba',
      'reserve.title': 'Confirmar reserva',
      'reserve.name': 'Nombre completo',
      'reserve.email': 'Correo electr\u00f3nico',
      'reserve.cpf': 'CPF',
      'reserve.phone': 'Tel\u00e9fono',
      'reserve.submit': 'Enviar reserva',
      'breadcrumb.trail': 'Ruta',
      'breadcrumb.home': 'Inicio',
      'groups.title': 'Grupos de Coches',
      'groups.loading': 'Cargando\u2026',
      'groups.empty':
        'Indique recogida y devoluci\u00f3n arriba y haga clic en Buscar para listar solo grupos disponibles en el per\u00edodo (datos del ERP).',
      'groups.rentals': 'Reservas',
      'groups.my_reservations': 'Mis reservas',
      'groups.prepay': 'Prepago',
      'groups.support': 'Atenci\u00f3n',
      'groups.whatsapp': 'WhatsApp',
      'groups.contact': 'Cont\u00e1ctenos',
      'groups.app_short': 'Gestione reservas desde el m\u00f3vil.',
      'groups.footer_legal':
        '\u00a9 LOCADORA RODAVIA \u2014 CNPJ 00.000.000/0001-00 \u2014 Versi\u00f3n del sitio v1.0.0',
      'groups.rent_now': 'Alquilar ahora',
      'groups.view_details': 'Ver detalles',
      'feature.ac': 'Aire',
      'feature.no_ac': 'Sin aire',
      'branches.loading': 'Cargando sucursales\u2026',
      'branches.none': 'Ninguna sucursal disponible',
      'bff.checking': 'Verificando API\u2026',
      'bff.connected': 'API conectada',
      'bff.offline': 'API desconectada',
      'search.error.pickup': 'Seleccione el lugar de recogida.',
      'search.error.invalid_dates': 'Indique fechas v\u00e1lidas.',
      'search.error.return_after': 'La devoluci\u00f3n debe ser posterior a la recogida.',
      'search.status.searching': 'Buscando grupos\u2026',
      'search.status.no_vehicles': 'Ning\u00fan veh\u00edculo disponible en este per\u00edodo.',
      'search.status.groups': '{count} grupo(s) disponible(s) en el per\u00edodo.',
      'search.status.groups_page': '{count} grupo(s) disponible(s).',
      'search.error.load_fleet': 'No fue posible cargar la flota. Int\u00e9ntelo de nuevo.',
      'search.error.load_groups': 'No fue posible cargar los grupos.',
      'search.error.generic': 'Error al buscar.',
      'search.error.before_reserve': 'Realice una b\u00fasqueda antes de reservar.',
      'search.error.boot': 'Error al iniciar integraci\u00f3n',
      'quote.calculating': 'Calculando cotizaci\u00f3n\u2026',
      'quote.on_confirm': 'Cotizaci\u00f3n disponible en la confirmaci\u00f3n.',
      'reserve.sending': 'Enviando reserva\u2026',
      'reserve.sending_short': 'Enviando\u2026',
      'reserve.success':
        '\u00a1Reserva enviada con \u00e9xito! Pronto recibir\u00e1 la confirmaci\u00f3n.',
      'reserve.success_short': '\u00a1Reserva enviada con \u00e9xito!',
      'reserve.error': 'No fue posible completar la reserva.',
      'reserve.error_short': 'Error al reservar.',
      'groups.loading_groups': 'Cargando grupos\u2026',
      'hero.promo': 'Destacado promocional',
      'fleet.vehicle_alt': 'Veh\u00edculo {title}',
      'fleet.subtitle_default': 'Modelo representativo de la categor\u00eda',
      'fleet.similar': '{model} o similar',
    },
  };

  function getStoredLang() {
    try {
      var stored = localStorage.getItem(STORAGE_KEY);
      if (stored && LOCALES[stored]) return stored;
    } catch (e) {
      /* ignore */
    }
    return DEFAULT_LANG;
  }

  var currentLang = getStoredLang();

  function interpolate(text, vars) {
    if (!vars) return text;
    return String(text).replace(/\{(\w+)\}/g, function (_, key) {
      return vars[key] != null ? String(vars[key]) : '';
    });
  }

  function t(key, vars) {
    if (!key) return '';
    var lang = currentLang;
    var table = MESSAGES[lang] || MESSAGES[DEFAULT_LANG];
    var fallback = MESSAGES[DEFAULT_LANG];
    var text = table[key] != null ? table[key] : fallback[key] != null ? fallback[key] : null;
    if (text == null) {
      console.warn('[SiteI18n] missing key:', key);
      return '';
    }
    return interpolate(text, vars);
  }

  function applyMeta(root) {
    var scope = root || document;
    var page = document.documentElement.getAttribute('data-page');
    if (page) {
      var titleKey = 'meta.' + page + '.title';
      var descKey = 'meta.' + page + '.description';
      if (MESSAGES[currentLang][titleKey] || MESSAGES[DEFAULT_LANG][titleKey]) {
        document.title = t(titleKey);
      }
      var meta = scope.querySelector('meta[name="description"]');
      if (meta && (MESSAGES[currentLang][descKey] || MESSAGES[DEFAULT_LANG][descKey])) {
        meta.setAttribute('content', t(descKey));
      }
    }
  }

  function apply(root) {
    var scope = root || document;
    document.documentElement.lang = currentLang;

    scope.querySelectorAll('[data-i18n]').forEach(function (el) {
      if (!el.dataset.i18nDefault) {
        el.dataset.i18nDefault = el.textContent.trim();
      }
      var translated = t(el.getAttribute('data-i18n'));
      el.textContent = translated || el.dataset.i18nDefault || '';
    });

    scope.querySelectorAll('[data-i18n-html]').forEach(function (el) {
      el.innerHTML = t(el.getAttribute('data-i18n-html'));
    });

    scope.querySelectorAll('[data-i18n-placeholder]').forEach(function (el) {
      el.setAttribute('placeholder', t(el.getAttribute('data-i18n-placeholder')));
    });

    scope.querySelectorAll('[data-i18n-aria]').forEach(function (el) {
      el.setAttribute('aria-label', t(el.getAttribute('data-i18n-aria')));
    });

    scope.querySelectorAll('[data-i18n-title]').forEach(function (el) {
      el.setAttribute('title', t(el.getAttribute('data-i18n-title')));
    });

    scope.querySelectorAll('option[data-i18n]').forEach(function (el) {
      el.textContent = t(el.getAttribute('data-i18n'));
    });

    applyMeta(scope);
    updateLangSelectorUI();
  }

  function updateLangSelectorUI() {
    var info = LOCALES[currentLang] || LOCALES[DEFAULT_LANG];
    var flagEl = document.querySelector('[data-locale-flag]');
    var labelEl = document.querySelector('[data-locale-label]');
    if (flagEl) flagEl.textContent = info.flag;
    if (labelEl) labelEl.textContent = info.label;

    document.querySelectorAll('[data-lang-option]').forEach(function (btn) {
      var lang = btn.getAttribute('data-lang-option');
      var active = lang === currentLang;
      btn.classList.toggle('is-active', active);
      btn.setAttribute('aria-selected', active ? 'true' : 'false');
    });
  }

  function closeLangMenu() {
    var menu = document.getElementById('locale-menu');
    var btn = document.getElementById('country-selector');
    if (menu) menu.hidden = true;
    if (btn) btn.setAttribute('aria-expanded', 'false');
  }

  function openLangMenu() {
    var menu = document.getElementById('locale-menu');
    var btn = document.getElementById('country-selector');
    if (menu) menu.hidden = false;
    if (btn) btn.setAttribute('aria-expanded', 'true');
  }

  function initLangSelector() {
    var wrap = document.getElementById('locale-selector');
    var btn = document.getElementById('country-selector');
    var menu = document.getElementById('locale-menu');
    if (!wrap || !btn || !menu) return;

    btn.addEventListener('click', function (e) {
      e.stopPropagation();
      var open = btn.getAttribute('aria-expanded') === 'true';
      if (open) closeLangMenu();
      else openLangMenu();
    });

    menu.querySelectorAll('[data-lang-option]').forEach(function (optionBtn) {
      optionBtn.addEventListener('click', function (e) {
        e.preventDefault();
        var lang = optionBtn.getAttribute('data-lang-option');
        if (lang && LOCALES[lang]) setLang(lang);
        closeLangMenu();
      });
    });

    document.addEventListener('click', function (e) {
      if (!wrap.contains(e.target)) closeLangMenu();
    });

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') closeLangMenu();
    });
  }

  function setLang(lang) {
    if (!LOCALES[lang]) return;
    currentLang = lang;
    try {
      localStorage.setItem(STORAGE_KEY, lang);
    } catch (e) {
      /* ignore */
    }
    apply();
    document.dispatchEvent(
      new CustomEvent('site:langchange', { detail: { lang: lang } })
    );
  }

  function getLang() {
    return currentLang;
  }

  function init() {
    apply();
    initLangSelector();
  }

  try {
    document.documentElement.lang = currentLang;
  } catch (e) {
    /* ignore */
  }

  function mergeLocale(lang, entries) {
    if (!entries) return;
    if (!MESSAGES[lang]) MESSAGES[lang] = {};
    Object.assign(MESSAGES[lang], entries);
  }

  global.SiteI18n = {
    t: t,
    getLang: getLang,
    setLang: setLang,
    apply: apply,
    init: init,
    mergeLocale: mergeLocale,
    _mergeLocale: mergeLocale,
    STORAGE_KEY: STORAGE_KEY,
    LOCALES: LOCALES,
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})(window);
