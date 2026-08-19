# Instruções para agentes de IA neste repositório

Este arquivo documenta o padrão de trabalho combinado para este projeto
(LicitTracker). Ele vale para **qualquer agente de IA** (Claude, Copilot,
Cursor, ChatGPT, etc.) que for fazer alterações neste repositório — não é
específico do Claude.

## Workflow obrigatório: Issue → Branch → PR

Antes de fazer qualquer commit que represente uma tarefa real — uma
**Correção** (bug fix), uma **Melhoria** (enhancement/refactor) ou uma
**Nova função** (feature) — siga estes passos, nessa ordem:

1. **Crie uma Issue no GitHub** descrevendo a tarefa (`gh issue create`).
   - Título curto e direto.
   - Corpo com "Problema" e "Correção proposta" (ou "O que muda"), o
     suficiente para alguém entender o motivo sem ler o código primeiro.
   - Use uma label existente do repo quando fizer sentido: `bug`,
     `enhancement`, `documentation`.
2. **Crie uma branch a partir de `main`** com prefixo que indique o tipo:
   `fix/…`, `feat/…`, `chore/…` ou `docs/…`.
3. **Faça a alteração e o commit** nessa branch. Só inclua no commit os
   arquivos relacionados àquela tarefa específica — não misture com outras
   mudanças que estejam soltas na árvore de trabalho.
4. **Abra um Pull Request** (`gh pr create`) da branch para `main`.
   - **A descrição do PR deve mencionar a Issue correspondente**
     (ex.: `Closes #12` ou `Refs #12`) para linkar automaticamente.
   - Descreva o que mudou e por quê, e um plano de teste quando fizer
     sentido.
5. **Não faça merge direto em `main` sem PR.** O merge do PR (deploy) fica
   a critério do usuário, a menos que ele peça explicitamente para o
   agente mesclar.

## Por quê

- Cada mudança fica rastreável: Issue explica o "porquê", PR mostra o
  "o quê" e liga de volta pro "porquê".
- PRs funcionam como o portão de controle antes de qualquer deploy —
  nada vai para `main` sem passar por essa revisão.
- Qualquer pessoa (ou agente) que entrar no projeto depois consegue
  reconstruir o histórico de decisões pelas Issues/PRs, sem depender de
  contexto perdido em conversas.

## Exceções

- Correções triviais de digitação/formatação sem impacto funcional podem
  dispensar Issue, mas ainda devem ir por PR.
- Nunca pule esse fluxo para mudanças em autenticação, segredos/env vars,
  banco de dados ou dependências — essas sempre precisam de Issue + PR.
