## 🪙 Economia Virtual (Sistema de Créditos)
Para incentivar o *crowdsourcing* e evitar o problema de "Cold Start", o sistema opera sob uma economia de créditos que condiciona o uso da plataforma à colaboração do usuário.

* **Onboarding:** Todo novo usuário recebe **20 créditos** ao criar a conta.
* **Custo de Uso (Consumo):** Cada requisição para "Otimizar Cesta de Compras" custa **1 crédito**.
* **Recompensa (Ingestão):** Cada leitura de NFC-e (QR Code) processada com sucesso e validada concede **5 créditos** ao usuário.

**Regras Antifraude (Validação de Cupons):**
1. **Unicidade:** Cupons com a mesma Chave de Acesso da SEFAZ já existentes no banco não geram créditos.
2. **Validade Temporal:** Apenas cupons emitidos nos **últimos 7 dias** são válidos para pontuação e armazenamento. Cupons mais antigos são descartados para não poluir o motor de precificação.
3. **Rate Limit:** Limitado ao processamento de **3 cupons por usuário/dia** para evitar abusos.