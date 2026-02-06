
# Iracema – Front-end (Presentation/GUI)

Este diretório contém o **front-end web** do projeto **Iracema**, responsável pela interface conversacional de exploração do catálogo e consulta aos dados.

## Visão Geral

O front-end foi projetado para **parecer um assistente de dados (estilo GPT)**, e não um chatbot tradicional.
Ele interpreta comandos em linguagem natural, sugere ações possíveis e orquestra os fluxos de:
- Busca no catálogo
- Seleção de tabelas
- Consulta ao backend (ask)

## Stack Tecnológica

- React + Vite
- JavaScript moderno (ES6+)
- Axios para integração com API
- Hooks customizados para estado e fluxo
- Motor local de NLU (Natural Language Understanding)

## Estrutura de Pastas

Presentation/GUI/src
- assets (imagens e estilos)
- config (axios e configurações)
- features/Chat
  - components
  - domain
  - hooks
  - nlu (motor de intenções)
  - catalogEngine.js
  - helpers.js
  - service.js
- App.jsx
- main.jsx

## NLU – Natural Language Understanding

O NLU interpreta comandos como:
- "detalhar"
- "usar pan_icmbio_2021"
- "trocar tabela"
- "ano: 2022"

E os transforma em intenções como:
- DETAILS
- SELECT
- SWITCH_TABLE
- ASK_QUESTION
- CATALOG_SEARCH

Isso permite comandos livres sem depender de botões fixos.

## Fluxo de Conversa

### Modo Catálogo
- O usuário descreve o que procura
- O sistema sugere tabelas próximas
- Pode detalhar ou selecionar

### Modo Consulta
- Após selecionar uma tabela
- Qualquer texto vira pergunta ao backend
- Pode trocar tabela a qualquer momento

## Execução Local

1. Instalar dependências:
npm install

2. Configurar variáveis de ambiente:
VITE_API_BASE_URL=http://localhost:9090

3. Rodar:
npm run dev

## Build

npm run build

O output será gerado em dist/.

## Integração com Backend

O front consome:
- /chat/start
- /chat/ask
- /chat/ask/fc
- /chat/ask/ai

O controle de fallback entre estratégias ocorre no hook useAskFlow.

## Experiência do Usuário

- Sugestões do que você pode escrever (atalhos opcionais)
- Sem follow-ups obrigatórios
- Mensagens sempre textuais (sem respostas vazias)
- Feedback claro em erros

## Objetivo

Facilitar o acesso aos dados da PEDEA por meio de uma experiência conversacional técnica, transparente e auditável.
