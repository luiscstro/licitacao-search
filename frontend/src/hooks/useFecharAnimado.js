import { useState } from "react";

const DURACAO_SAIDA_PAINEL = 160;

// Mesmo idioma já usado no Pipeline (DURACAO_SAIDA): antes de desmontar,
// marca "saindo" pra CSS tocar a animação de saída, só then chama o
// aoFechar de verdade. Evita que overlay/modal sumam sem transição.
export function useFecharAnimado(aoFechar, duracao = DURACAO_SAIDA_PAINEL) {
  const [saindo, setSaindo] = useState(false);

  function fechar() {
    setSaindo(true);
    setTimeout(aoFechar, duracao);
  }

  return [saindo, fechar];
}
