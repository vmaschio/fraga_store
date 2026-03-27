document.addEventListener('DOMContentLoaded', function() {
    const radiosTamanho = document.querySelectorAll('input[type="radio"][name="tamanho"]');
    let wasChecked = false;
  
    radiosTamanho.forEach(function(radio) {
        radio.addEventListener('mousedown', function() {
            wasChecked = this.checked;
        });
        radio.addEventListener('click', function() {
            if (wasChecked) {
                this.checked = false;
            }
            atualizarVisualSelecao();
        });
    });
  
    function atualizarVisualSelecao() {
        radiosTamanho.forEach(function(radio) {
            const label = document.querySelector(`label[for="${radio.id}"]`);
            if (label) {
                if (radio.checked) {
                    label.classList.add('s-produto__tamanhos-item--selecionado');
                } else {
                    label.classList.remove('s-produto__tamanhos-item--selecionado');
                }
            }
        });
    }
    atualizarVisualSelecao();
    var elemsCarrosselBotao = document.querySelectorAll(".s-produto__carrossel-botao");
    var elemCarrosselImagens = document.querySelector(".s-produto__carrossel-itens");
  
    if (elemCarrosselImagens) {
        elemsCarrosselBotao.forEach(function (elem, i) {
            elem.addEventListener("click", function () {
                elemCarrosselImagens.style.transform = "translateX(-" + i * 100 + "%)";
        
                elemsCarrosselBotao.forEach(function (ele) {
                    if (ele != elem) {
                        ele.classList.remove("s-produto__carrossel-botao--selecionado");
                    } else {
                        ele.classList.add("s-produto__carrossel-botao--selecionado");
                    }
                });
            });
        });
    }
});