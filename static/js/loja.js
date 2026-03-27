// Script de ordenar
function redirectToPage() {
  var selectElement = document.getElementsByClassName('produtos__select')[0];
  var selectedOption = selectElement.options[selectElement.selectedIndex].value;
  if (selectedOption) {
    window.location.href = selectedOption;
  }
}

// Scripts do Menu Lateral
function setupCheckboxHighlight(containerClass, checkboxSelector, targetSelector, getTarget, styles) {
  var checkboxes = document.querySelectorAll(containerClass + ' ' + checkboxSelector);

  checkboxes.forEach(function(checkbox) {
    checkbox.addEventListener('change', function() {
      var allTargets = document.querySelectorAll(containerClass + ' ' + targetSelector);
      allTargets.forEach(function(el) {
        el.classList.remove('menu__item--selecionado');
      });

      var target = getTarget(this);
      if (this.checked && target) {
        target.classList.add('menu__item--selecionado');
      }
    });
  });
}

setupCheckboxHighlight(
  '.menu__tamanho',
  '.menu__checkbox',
  '.menu__tamanho-quadrado',
  function(cb) { return cb.previousElementSibling; }
);

setupCheckboxHighlight(
  '.menu__categoria',
  '.menu__checkbox',
  '.menu__categoria-quadrado',
  function(cb) { return cb.previousElementSibling.previousElementSibling; }
);

var elemsMenuCabecalho = document.querySelectorAll(
  ".menu__expansivel-cabecalho"
);

elemsMenuCabecalho.forEach(function (ele) {
  ele.addEventListener("click", function () {
    ele.parentElement.classList.toggle("menu__expansivel--aberto");
  });
});

// Script para abrir e fechar a tela de filtro
var elemFecharFiltro = document.querySelector(".menu__fechar-filtro");
var elemAbrirFiltro = document.querySelector(".produtos__cabecalho-filtrar");

if (elemFecharFiltro) {
  elemFecharFiltro.addEventListener("click", function () {
    document.body.classList.remove("filtro-aberto");
  });
}

if (elemAbrirFiltro) {
  elemAbrirFiltro.addEventListener("click", function () {
    document.body.classList.add("filtro-aberto");
  });
}
