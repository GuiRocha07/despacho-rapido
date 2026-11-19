// Contagem regressiva da atualização automática da fila.
const painel = document.querySelector(".atualizacao");
if (painel) {
  const segundos = Number(painel.dataset.segundos) || 120;
  const agora = new Date();
  document.getElementById("ultima").textContent = agora.toLocaleTimeString("pt-BR");
  let restante = segundos;
  const contagem = document.getElementById("contagem");
  const mostrar = () => {
    const m = String(Math.floor(restante / 60)).padStart(2, "0");
    const s = String(restante % 60).padStart(2, "0");
    contagem.textContent = `${m}:${s}`;
  };
  mostrar();
  setInterval(() => {
    restante -= 1;
    if (restante <= 0) location.reload();
    mostrar();
  }, 1000);
}

// Botão "Copiar mensagem".
document.querySelectorAll(".copiar").forEach((botao) => {
  botao.addEventListener("click", async () => {
    await navigator.clipboard.writeText(botao.dataset.texto);
    botao.textContent = "Copiado ✓";
    setTimeout(() => (botao.textContent = "Copiar mensagem"), 2000);
  });
});
