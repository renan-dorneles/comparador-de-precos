# Diretrizes de Arquitetura Técnica

## 1. Módulo de Créditos e Transações (Ledger)
A gestão de saldo dos usuários não deve ser feita apenas sobrescrevendo um valor no banco. O assistente de IA deve implementar um sistema de "Ledger" (livro-razão) para rastreabilidade:

* **Tabela `users`:** Deve conter o campo `credit_balance` (Integer, default 20).
* **Tabela `credit_transactions`:** Deve registrar todas as movimentações. 
  * Colunas: `id`, `user_id`, `amount` (positivo para ganho, negativo para gasto), `transaction_type` (Enum: 'SCAN_REWARD', 'SEARCH_COST', 'ONBOARDING'), `reference_id` (ID da nota fiscal ou da busca, opcional), `created_at`.
* **Atomicidade (ACID):** Toda operação de inserção de nota fiscal ou busca de cesta deve usar transações de banco de dados (`db.commit()` no SQLAlchemy apenas após inserir o registro principal E registrar a transação de crédito).

## 2. Fluxo Técnico de Ingestão de NFC-e
Quando a rota de recebimento do QR Code for acionada, o fluxo obrigatório da API é:
1. **Decode & Extract:** Extrair a Chave de Acesso de 44 dígitos da URL.
2. **Check Duplication:** Consultar a tabela de notas fiscais. Se existir, retornar HTTP 200 (com status amigável de "Nota já cadastrada") e abortar processamento sem dar crédito.
3. **Scrape HTML:** Fazer a requisição à SEFAZ-RS.
4. **Time Validation:** Extrair a data de emissão. Se `(data_atual - data_emissao) > 7 dias`, retornar HTTP 200 ("Nota muito antiga") e abortar inserção.
5. **AI Processing:** Enviar os itens para o LLM/SLM mapear para o catálogo genérico.
6. **Database Commit:** Em uma única transação no SQLAlchemy: 
   - Salvar a nota e os itens.
   - Inserir +5 na tabela `credit_transactions`.
   - Atualizar `credit_balance` do usuário.

## 3. Fluxo Técnico de Otimização (Busca)
1. **Check Balance:** Verificar se `users.credit_balance >= 1`. Se não, retornar HTTP 403 Forbidden ("Saldo insuficiente").
2. **Process Search:** Rodar o algoritmo de completude geolocalizado usando PostGIS.
3. **Database Commit:** Em uma única transação:
   - Inserir -1 na tabela `credit_transactions`.
   - Subtrair 1 do `credit_balance`.
   - Retornar o JSON com os mercados sugeridos.