# Comparador de Preços

Plataforma de comparação de preços que incentiva o *crowdsourcing* de dados NFC-e com um
sistema de **créditos** baseado em *ledger*, ingestão de NFC-e via QR Code e busca
geolocalizada otimizada com PostGIS.

## 📋 Status atual

Implementado conforme as **Fases 0, 1 e 2** do [`docs/PLAN.md`](docs/PLAN.md), mais a tarefa
**3.1** (decoder de QR Code NFC-e):

- ✅ Estrutura de pastas: `src/`, `tests/`, `alembic/`
- ✅ Dependências: FastAPI, SQLAlchemy 2.0 (async), Pydantic v2, Alembic, GeoAlchemy2/PostGIS, Redis, JWT, bcrypt
- ✅ Modelos SQLAlchemy: `User`, `CreditTransaction`, `Invoice`, `InvoiceItem`, `ProductCatalog`, `Store`, `StorePrice`
- ✅ Migração inicial `20240115_001_initial_schema.py` (habilita a extensão PostGIS, com índice GIST em `stores.location`)
- ✅ Serviço de **Ledger** com atomicidade ACID (`credit_balance` + `credit_transactions` na mesma transação, com lock `FOR UPDATE`)
- ✅ Rotas `/auth/register`, `/auth/login`, `/auth/refresh`, `/auth/me` e `/me/credits`
- ✅ Rate limiting com Redis (janela diária)
- ✅ **Decoder de QR Code NFC-e** (extração e validação da chave de acesso de 44 dígitos)
- ✅ Docker Compose (PostgreSQL + PostGIS, Redis), Dockerfile e CI (GitHub Actions + pre-commit)
- ✅ 29 testes unitários (segurança e decoder NFC-e) + validação do schema no CI (`alembic upgrade`/`downgrade`)

**Em andamento:** Fase 3 (pipeline de ingestão NFC-e: scraper SEFAZ-RS, mapeamento IA de catálogo e
`POST /invoices/scan`), Fase 4 (busca geolocalizada PostGIS) e Fase 5 (testes de integração e deploy).

## 🚀 Começando

### 1. Dependências

```bash
pip install -r requirements.txt
# ou, com extras de desenvolvimento:
pip install -e .[dev]
```

### 2. Infraestrutura (PostgreSQL/PostGIS + Redis)

```bash
docker compose up -d
```

### 3. Variáveis de ambiente

Crie um arquivo `.env` na raiz:

```env
DATABASE_URL=postgresql+asyncpg://comparador_user:comparador_pass@localhost:5432/comparador_precos
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=troque-esta-chave-em-producao
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### 4. Migrações

```bash
alembic upgrade head
```

### 5. Subindo a API

```bash
uvicorn src.comparador_precos.main:app --reload
```

Documentação interativa (Swagger): <http://localhost:8000/docs>
Health check: <http://localhost:8000/health>

### 6. Testes e qualidade

```bash
pytest                    # toda a suíte
pytest tests/unit         # apenas unitários
ruff check src            # lint
black src                 # formatação
mypy src                  # tipagem
pre-commit install        # hooks locais (black, ruff, mypy)
```

## 📁 Estrutura

```
comparador-de-precos/
├── docs/
│   ├── PLAN.md            # plano de desenvolvimento (Fases 0-5)
│   ├── ARCHITECTURE.md    # diretrizes técnicas
│   └── README.md          # regras de negócio
├── src/comparador_precos/
│   ├── core/              # config, database, security, dependencies, rate_limit
│   ├── models/            # modelos SQLAlchemy
│   ├── schemas/           # schemas Pydantic v2
│   ├── services/          # regras de negócio (ledger)
│   ├── api/routes/        # rotas FastAPI
│   └── main.py            # app FastAPI
├── tests/
│   ├── unit/
│   └── integration/
├── alembic/               # migrações
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
└── requirements.txt
```

## 🪙 Regras de negócio

| Evento | Créditos |
|---|---|
| Onboarding (novo cadastro) | **+20** |
| NFC-e processada com sucesso | **+5** |
| Otimização de cesta de compras | **-1** |

Antifraude: unicidade da chave de acesso SEFAZ, validade de **7 dias** e rate limit de
**3 scans por usuário/dia**.

## 📄 Documentação

- [`docs/PLAN.md`](docs/PLAN.md) — plano de desenvolvimento por fases
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — arquitetura e fluxos técnicos
- [`docs/README.md`](docs/README.md) — regras da economia de créditos

## 📄 Licença

MIT
