# Plano de Desenvolvimento - Comparador de Preços

> **Visão Geral**: Sistema de comparação de preços com economia baseada em créditos, ingestão de NFC-e via QR Code e busca geolocalizada otimizada com PostGIS.

---

## 📊 Status Atual (Out 2026)

| Item | Estado |
|------|--------|
| **Fase 0** (fundação) | ✅ Concluída — estrutura, dependências, Docker Compose, CI |
| **Fase 1** (modelos/BD) | ✅ Concluída — 7 modelos, migração inicial, sessão async, ledger ACID |
| **Fase 2** (auth/créditos) | ✅ Concluída — JWT (register/login/refresh/me), onboarding +20, `/me/credits`, rate limit Redis |
| **Fase 3** (ingestão NFC-e) | 🔄 Parcial — 3.1 (decoder QR) ✅; 3.2–3.7 pendentes |
| **Fase 4** (busca PostGIS) | ⏳ Não iniciada |
| **Fase 5** (testes/deploy) | 🔄 Parcial — 29 testes unitários; falta integração, observabilidade e `docker-compose.prod.yml` |
| **Infraestrutura** | ✅ Docker Compose (PostGIS 16-3.5 + Redis), Dockerfile, CI com validação de schema |
| **Git** | ✅ `main` com Fases 0–2 mergeadas (PR #1); token de CI exposto — **revogar** |

---

## 🏗️ Arquitetura Alvo (do `/docs`)

- **Economia de créditos** para crowdsourcing (solução de cold start)
- **Contabilidade via ledger** (`credit_transactions` + `credit_balance` em users)
- **Pipeline NFC-e**: QR Code → Scrape SEFAZ-RS → Mapeamento IA → BD (ACID)
- **Busca geolocalizada**: PostGIS-powered "otimizar cesta de compras" com custo de 1 crédito
- **Prevenção de fraude**: Unicidade (chave SEFAZ), validade 7 dias, rate limit 3 scans/dia

---

## 🚀 Plano de Desenvolvimento (Fases)

---

### **Fase 0: Fundação & Setup do Projeto** (Semana 1)

| Tarefa | Descrição |
|--------|-----------|
| 0.1 | Inicializar git repo corretamente, criar commit inicial |
| 0.2 | Criar estrutura: `src/`, `tests/`, `alembic/` (migrações) |
| 0.3 | Adicionar dependências ao `pyproject.toml`: **FastAPI**, **SQLAlchemy 2.0**, **Alembic**, **Pydantic v2**, **PostGIS/GeoAlchemy2**, **httpx**, **python-dotenv**, **pydantic-settings** |
| 0.4 | Configurar **Docker Compose**: PostgreSQL + PostGIS, Redis (rate limiting) |
| 0.5 | Configurar CI básico: pre-commit (black, ruff, mypy), pytest config |

---

### **Fase 1: Modelos de Domínio & Banco de Dados** (Semana 1-2)

| Tarefa | Descrição |
|--------|-----------|
| 1.1 | **Modelos SQLAlchemy** conforme ARCHITECTURE.md:<br>• `User` (id, email, hashed_password, credit_balance default=20, created_at)<br>• `CreditTransaction` (id, user_id, amount, type enum, reference_id, created_at)<br>• `Invoice` (id, access_key unique, issue_date, total_value, user_id, raw_html, created_at)<br>• `InvoiceItem` (id, invoice_id, description, quantity, unit, price, catalog_product_id nullable)<br>• `ProductCatalog` (id, generic_name, brand **nullable**, category, unit_of_measure)<br>• `Store` (id, name, cnpj, address, location `Geometry(POINT)`, city, state)<br>• `StorePrice` (id, store_id, catalog_product_id, price, captured_at, invoice_item_id FK) |
| 1.2 | **Migrações Alembic** para todas as tabelas com índices adequados (access_key unique, location GIST para PostGIS) |
| 1.3 | **Gerenciamento de sessão BD** (async SQLAlchemy com dependency injection) |
| 1.4 | **Serviço de Ledger** - operações atômicas de crédito (débito/crédito com registro de transação em única transação BD) |

---

### **Fase 2: Autenticação & API de Créditos** (Semana 2)

| Tarefa | Descrição |
|--------|-----------|
| 2.1 | **JWT Auth**: registro, login, refresh tokens, hash de senha (bcrypt/argon2) |
| 2.2 | **Onboarding**: conceder 20 créditos automaticamente no registro (ledger entry type=ONBOARDING) |
| 2.3 | **Endpoints de crédito**: GET `/me/credits` (saldo + transações recentes) |
| 2.4 | **Middleware de rate limiting** (Redis): 3 scans NFC-e/usuário/dia |

---

### **Fase 3: Pipeline de Ingestão NFC-e** (Semana 3-4) *Diferencial Principal*

| Tarefa | Descrição |
|--------|-----------|
| 3.1 | **Decoder de QR Code**: extrair chave de acesso SEFAZ de 44 dígitos da URL |
| 3.2 | **Verificação de duplicidade**: consultar `Invoice` por access_key → retornar 200 "já registrada" se existir |
| 3.3 | **Scraper SEFAZ-RS** (httpx + BeautifulSoup/lxml): buscar HTML da nota, parsear itens (descrição, qtd, unidade, preço), data emissão, CNPJ/nome/endereço da loja, total. **Fallback**: Playwright (headless browser) caso a SEFAZ bloqueie requisições simples via anti-bot/Cloudflare |
| 3.4 | **Validação temporal**: rejeitar se `issue_date < now() - 7 dias` → 200 "muito antiga" |
| 3.5 | **Mapeamento IA para Catálogo**: enviar itens extraídos → mapear para `ProductCatalog` (criar novo se necessário) via chamadas de API (Open Router / LLMs gratuitos) |
| 3.6 | **Commit atômico BD**: Invoice + Items + StorePrice + CreditTransaction(+5, SCAN_REWARD) + User.credit_balance += 5 |
| 3.7 | **Endpoint**: `POST /invoices/scan` (multipart imagem QR code ou JSON com URL) |

---

### **Fase 4: Busca Geolocalizada & Otimização** (Semana 4-5)

| Tarefa | Descrição |
|--------|-----------|
| 4.1 | **Setup PostGIS**: Habilitar extensão, `Store.location` como `Geometry(POINT, 4326)`, índice GIST |
| 4.2 | **Algoritmo de busca**: Dado lat/lon do usuário + lista de `catalog_product_id` + quantidades → encontrar lojas no raio que tenham TODOS itens (ou max completude) com menor preço total |
| 4.3 | **Scoring de completude**: % da cesta coberta, preço total estimado, distância |
| 4.4 | **Verificação de saldo**: exigir `credit_balance >= 1` → HTTP 403 se insuficiente |
| 4.5 | **Commit atômico**: CreditTransaction(-1, SEARCH_COST) + User.credit_balance -= 1 |
| 4.6 | **Endpoint**: `POST /search/optimize` → retorna lojas ranqueadas com preços, links de mapa |

---

### **Fase 5: Testes, Polish & Deploy** (Semana 5-6)

| Tarefa | Descrição |
|--------|-----------|
| 5.1 | **Testes automatizados Backend/API**: pytest (unitários + integração) — ledger atomicidade, fluxos de crédito, regras validação NFC-e, lógica de busca |
| 5.2 | **Testes manuais Mobile**: validação do app via **Expo Go (React Native)** em dispositivo físico |
| 5.3 | **Documentação API**: OpenAPI/Swagger auto-gerada |
| 5.4 | **Observabilidade**: logging estruturado, métricas básicas (Prometheus), health checks |
| 5.5 | **Dockerfile** para API, docker-compose.prod.yml |
| 5.6 | **README** com setup, run, test instructions |

---

## 🎯 Decisões Arquiteturais Principais

| Decisão | Escolha | Justificativa |
|---------|---------|---------------|
| **Mapeamento Catálogo IA** | **API Open Router (LLMs gratuitos)** — sem modelo local | Evita esgotamento de RAM/VRAM no servidor inicial; custo zero; flexível para trocar modelo |
| **Scraping SEFAZ** | httpx + BeautifulSoup (MVP) + **Playwright headless (fallback)** | Resiliência contra anti-bot/Cloudflare; controle total, sem custo API terceiros |
| **Geoespacial** | PostGIS nativo | Mais poderoso para queries "lojas com TODOS itens" |
| **Frontend** | API-first → **React Native (Expo)** depois | Valida backend primeiro; Expo Go permite teste físico imediato sem build nativo |
| **Hospedagem** | Railway/Render (inicial) | PostGIS gerenciado, deploy simples |
| **Testes Mobile** | **Manuais via Expo Go em dispositivo físico** | Elimina complexidade de AVD/emulador/CI mobile no MVP; foco no backend |

---

## ✅ Próximos Passos Imediatos (Act Mode)

1. ✅ **Criar PLAN.md** ← *CONCLUÍDO*
2. ✅ **Executar Fase 0**: Setup projeto, dependências, Docker Compose (PostgreSQL+PostGIS, Redis) ← *CONCLUÍDO*
3. ✅ **Executar Fase 1**: Modelos SQLAlchemy + Migrações Alembic ← *CONCLUÍDO*
4. ✅ **Executar Fase 2**: Auth JWT + Sistema de Créditos ← *CONCLUÍDO*
5. ⏳ **Executar Fase 3**: Pipeline NFC-e (core) — scraper SEFAZ-RS (httpx/BeautifulSoup) + Playwright fallback + Open Router IA + `POST /invoices/scan`
6. ⏳ **Executar Fase 4**: Busca PostGIS + Otimização (`POST /search/optimize`)
7. ⏳ **Executar Fase 5**: Testes backend (pytest) + Deploy + Validação manual mobile (Expo Go)

---

## 📁 Estrutura de Pastas Alvo

```
comparador-de-precos/
├── docs/
│   ├── ARCHITECTURE.md
│   ├── SPEC.md
│   └── PLAN.md          ← Este arquivo
├── src/
│   ├── api/             # FastAPI routes
│   ├── core/            # Config, security, database
│   ├── models/          # SQLAlchemy models
│   ├── schemas/         # Pydantic schemas
│   ├── services/        # Business logic (ledger, nfce, search)
│   └── tasks/           # Background jobs
├── tests/
│   ├── unit/
│   └── integration/
├── alembic/             # Migrações BD
├── docker-compose.yml
├── docker-compose.prod.yml
├── Dockerfile
├── pyproject.toml
├── pytest.ini
└── README.md
```

---

## 🔧 Comandos Úteis

```bash
# Subir infraestrutura local
docker-compose up -d

# Rodar migrações
alembic upgrade head

# Iniciar API
uvicorn src.main:app --reload

# Rodar testes (backend)
pytest

# Rodar app mobile (desenvolvimento)
cd mobile-app && npx expo start
# Escanear QR Code com Expo Go no celular físico
```

---

**Documento criado em**: 05/10/2026  
**Versão**: 2.0 (Revisão Arquitetural MVP)  
**Status**: Aprovado para implementação (Act Mode)