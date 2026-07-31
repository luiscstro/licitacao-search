// Helpers de data e valor compartilhados entre cartões e painéis de alerta.

export function formatarValor(valor) {
  if (!valor) return "não informado";
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(valor);
}

export function diasAte(dataStr) {
  if (!dataStr) return "—";
  const data = new Date(dataStr);
  const hoje = new Date();
  const diffMs = data.setHours(0, 0, 0, 0) - hoje.setHours(0, 0, 0, 0);
  const dias = Math.round(diffMs / 86400000);
  if (dias < 0) return `venceu há ${Math.abs(dias)}d`;
  if (dias === 0) return "hoje";
  return `em ${dias}d`;
}

export function diasRestantes(dataStr) {
  if (!dataStr) return null;
  const data = new Date(dataStr);
  const hoje = new Date();
  return Math.round((data.setHours(0, 0, 0, 0) - hoje.setHours(0, 0, 0, 0)) / 86400000);
}

export function urgente(dataStr) {
  const dias = diasRestantes(dataStr);
  return dias !== null && dias >= 0 && dias <= 3;
}
