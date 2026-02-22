# ⚛️ QUANTTECH SYSTEM — Web App

Análise fundamentalista de ações brasileiras. Acesse pelo navegador, inclusive pelo celular.

## Deploy no Railway

1. Crie um repositório no GitHub chamado `quanttech-system`
2. Faça upload dos 3 arquivos: `app.py`, `requirements.txt`, `Procfile`
3. Acesse [railway.app](https://railway.app) e conecte com sua conta GitHub
4. Clique em **New Project → Deploy from GitHub repo**
5. Selecione `quanttech-system`
6. Aguarde o deploy (~2 minutos)
7. Clique em **Settings → Generate Domain** para obter sua URL pública

## Arquivos

- `app.py` — aplicação Flask completa
- `requirements.txt` — dependências Python
- `Procfile` — instrução de execução para Railway

## Funcionalidades

- Análise fundamentalista completa via Fundamentus
- Score 0-100 por categoria (Qualidade, Valuation, Crescimento, Solidez)
- Valuation Graham com preço justo e preço teto
- Simulação de R$1.000 investidos com reinvestimento de dividendos
- Oscilações históricas de preço
- Análise técnica (EMA50)
- Limite de 30 usuários simultâneos
- Responsivo para celular
