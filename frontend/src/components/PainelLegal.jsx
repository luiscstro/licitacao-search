import { X } from "lucide-react";
import { useFecharAnimado } from "../hooks/useFecharAnimado";

const CONTEUDO = {
  termos: {
    titulo: "Termos de Uso",
    corpo: (
      <>
        <p>
          O LicitTracker é uma ferramenta de monitoramento de licitações públicas, construída a partir de
          dados abertos do Portal Nacional de Contratações Públicas (PNCP). Ao usar a plataforma, você
          concorda com o seguinte:
        </p>
        <ul>
          <li>
            A conta e os dados cadastrados pertencem à empresa que os criou — outras contas não têm acesso.
          </li>
          <li>
            As informações de licitações vêm de fontes públicas oficiais e podem conter imprecisões ou atrasos
            em relação ao PNCP; sempre confira o edital original antes de qualquer decisão.
          </li>
          <li>
            O uso é de sua responsabilidade — não nos responsabilizamos por decisões de negócio tomadas com
            base nos dados exibidos.
          </li>
          <li>
            Contas usadas de forma abusiva (ex: automação não autorizada, tentativa de acesso a dados de outra
            empresa) podem ser suspensas.
          </li>
        </ul>
        <p>Dúvidas sobre esses termos podem ser enviadas pelo e-mail cadastrado na sua conta.</p>
      </>
    ),
  },
  privacidade: {
    titulo: "Política de Privacidade",
    corpo: (
      <>
        <p>
          Levamos a sério os dados que você compartilha. Esta política explica, em linguagem simples, o que
          coletamos e por quê — em linha com a LGPD (Lei Geral de Proteção de Dados).
        </p>
        <p>
          <strong>O que coletamos:</strong> e-mail e senha (a senha nunca é guardada em texto puro), dados
          cadastrais da empresa (CNPJ, endereço, representante legal — quando você preenche), critérios de
          busca, favoritos e comentários que você registra na plataforma.
        </p>
        <p>
          <strong>Por que coletamos:</strong> exclusivamente para operar a plataforma — autenticar seu acesso,
          filtrar licitações relevantes pros seus critérios, e (se você optar) enviar o resumo diário por
          e-mail.
        </p>
        <p>
          <strong>Com quem compartilhamos:</strong> com ninguém para fins comerciais. Dados de CNPJ podem ser
          consultados em APIs públicas de dados abertos (BrasilAPI/MinhaReceita) só quando você aciona a
          sincronização manualmente.
        </p>
        <p>
          <strong>Onde fica armazenado:</strong> em um banco de dados próprio da aplicação, sem uso de
          rastreadores de terceiros ou venda de dados a anunciantes.
        </p>
        <p>
          Você pode pedir a exclusão da sua conta e dos dados associados a qualquer momento, pelo e-mail
          cadastrado.
        </p>
      </>
    ),
  },
  cookies: {
    titulo: "Política de Cookies",
    corpo: (
      <>
        <p>
          O LicitTracker{" "}
          <strong>não usa cookies de rastreamento, publicidade ou analytics de terceiros</strong>.
        </p>
        <p>
          A sessão de login é mantida via <code>localStorage</code> do navegador (um token de acesso guardado
          localmente no seu dispositivo, não em um cookie) — ele só é enviado pra nossa própria API, nunca pra
          terceiros, e some ao fazer logout ou limpar os dados do site no navegador.
        </p>
        <p>Não há banner de consentimento de cookies porque, tecnicamente, não usamos cookies.</p>
      </>
    ),
  },
};

export default function PainelLegal({ tipo, aoFechar }) {
  const [saindo, fechar] = useFecharAnimado(aoFechar);
  const conteudo = CONTEUDO[tipo];
  if (!conteudo) return null;

  return (
    <div className={`painel-overlay ${saindo ? "saindo" : ""}`} onClick={fechar}>
      <div
        className={`painel-modal painel-legal card-formulario ${saindo ? "saindo" : ""}`}
        onClick={(e) => e.stopPropagation()}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
            marginBottom: 6,
          }}
        >
          <div>
            <span className="eyebrow">Legal</span>
            <h2 style={{ marginBottom: 0 }}>{conteudo.titulo}</h2>
          </div>
          <button
            className="botao fantasma"
            onClick={fechar}
            style={{ padding: 8, borderRadius: "50%", width: 32, height: 32, flexShrink: 0 }}
            aria-label="Fechar"
          >
            <X size={15} strokeWidth={2.2} />
          </button>
        </div>
        <div className="painel-legal-corpo">{conteudo.corpo}</div>
      </div>
    </div>
  );
}
