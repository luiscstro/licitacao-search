import { useEffect, useRef, useState } from "react";

const semAnimacao =
  typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

// Anima a contagem de um número inteiro do valor anterior até o novo,
// pra pastilhas de indicadores não trocarem "secas" quando os dados chegam.
export default function NumeroAnimado({ valor, duracao = 650, formatar }) {
  const numero = Number(valor) || 0;
  // começa em 0 mesmo na primeira montagem — a contagem subindo é parte
  // da vida da tela, não só das atualizações depois
  const [exibido, setExibido] = useState(semAnimacao ? numero : 0);
  const anterior = useRef(semAnimacao ? numero : 0);
  const quadro = useRef(null);

  useEffect(() => {
    const de = anterior.current;
    const para = numero;
    if (de === para) return undefined;
    if (semAnimacao) {
      setExibido(para);
      anterior.current = para;
      return undefined;
    }
    const inicio = performance.now();
    function passo(agora) {
      const t = Math.min(1, (agora - inicio) / duracao);
      const facilitado = 1 - Math.pow(1 - t, 3);
      setExibido(Math.round(de + (para - de) * facilitado));
      if (t < 1) {
        quadro.current = requestAnimationFrame(passo);
      } else {
        anterior.current = para;
      }
    }
    quadro.current = requestAnimationFrame(passo);
    return () => cancelAnimationFrame(quadro.current);
  }, [numero, duracao]);

  return <>{formatar ? formatar(exibido) : exibido}</>;
}
