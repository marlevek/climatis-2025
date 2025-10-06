const botaoAceitarCookies = document.getElementById('btn-cookies');
const avisoCookies = document.getElementById('aviso-cookies');
const fundoCookies = document.getElementById('fundo-aviso-cookies');

if (!localStorage.getItem('cookies-aceitos')) {
    avisoCookies.classList.add('activo');
    fundoCookies.classList.add('activo');
}

botaoAceitarCookies.addEventListener('click', () => {
    avisoCookies.classList.remove('activo');
    fundoCookies.classList.remove('activo');

    localStorage.setItem('cookies-aceitos', true);

});