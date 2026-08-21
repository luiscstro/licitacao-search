// Helpers de data e valor compartilhados entre cartões e painéis de alerta.

export function formatarValor(valor) {
  if (!valor) return "não informado";
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(valor);
}

export function formatarDataHora(dataStr) {
  if (!dataStr) return "sem prazo informado";
  const data = new Date(dataStr);
  if (Number.isNaN(data.getTime())) return "sem prazo informado";
  const dataFormatada = data.toLocaleDateString("pt-BR");
  const horaFormatada = data.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
  return `${dataFormatada} às ${horaFormatada}`;
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

export function tempoRelativo(dataStr) {
  if (!dataStr) return "";
  const data = new Date(dataStr);
  if (Number.isNaN(data.getTime())) return "";
  const diffMin = Math.floor((Date.now() - data.getTime()) / 60000);
  if (diffMin < 1) return "agora mesmo";
  if (diffMin < 60) return `há ${diffMin} min`;
  const diffH = Math.floor(diffMin / 60);
  if (diffH < 24) return `há ${diffH}h`;
  const diffD = Math.floor(diffH / 24);
  if (diffD < 30) return `há ${diffD}d`;
  return data.toLocaleDateString("pt-BR");
}

export function iniciais(email) {
  if (!email) return "?";
  const nome = email.split("@")[0];
  const partes = nome.split(/[._-]/).filter(Boolean);
  if (partes.length >= 2) return (partes[0][0] + partes[1][0]).toUpperCase();
  return nome.slice(0, 2).toUpperCase();
}
