# Roteiro para o relatório no formato SBC

Este arquivo organiza o conteúdo técnico já implementado. Ele deve ser
transferido para o template oficial da SBC e complementado com referências
bibliográficas antes da entrega.

## Título sugerido

**Sentinel Ledger: coordenação descentralizada de créditos e auditoria de
missões autônomas**

## Resumo

Apresentar o problema de confiança entre participantes, duplo gasto e
adulteração de laudos. Resumir a blockchain própria, o consenso PoW, as
assinaturas e a separação entre prova on-chain e conteúdo off-chain.

## 1. Introdução

- Contexto do Estreito de Ormuz.
- Limitações da arquitetura anterior.
- Objetivo da nova solução.
- Contribuições: créditos, consenso, auditoria e confidencialidade.

## 2. Arquitetura anterior e comparação

| Aspecto | Problema 2 | Problema 3 |
|---|---|---|
| Estado | Brokers/setores | Ledger replicado por nó |
| Confiança | Servidores conhecidos | Validação criptográfica |
| Concorrência | Coordenação de alocação | Estado confirmado no ledger |
| Falha | Dependência dos brokers | Continuidade com peers restantes |
| Auditoria | Logs locais alteráveis | Hashes encadeados e assinados |

Explicar por que somente reutilizar o mecanismo de concorrência anterior não
resolveria fraude de saldo e adulteração histórica.

## 3. Projeto da solução

- Três nós FastAPI independentes.
- Modelo de bloco e transação.
- Gênese determinístico.
- Operational Credit.
- Endereços e assinaturas Ed25519.
- Propagação HTTP.
- PoW e regra da melhor cadeia.

## 4. Prevenção de duplo gasto e concorrência

Descrever a validação contra cadeia confirmada e mempool, lock atômico local,
revalidação durante a mineração e validação completa ao receber blocos.

Explicar que `ESCORT_PAYMENT` e `DRONE_DISPATCH` são confirmados atomicamente no
mesmo bloco, impedindo despacho sem pagamento.

## 5. Auditoria e confidencialidade

- Laudo público resumido.
- Conteúdo confidencial off-chain.
- AES-256-GCM.
- Encapsulamento da chave com X25519.
- `report_hash` e `encrypted_file_hash`.
- Detecção e reparo de cópia local adulterada.

## 6. Avaliação

Relatar os experimentos:

1. transferência observada em dois nós;
2. nó derrubado durante operação;
3. duplo gasto concorrente;
4. corrida pelo mesmo drone;
5. adulteração do bloco;
6. adulteração do arquivo;
7. abertura com carteira correta e rejeição da errada.

Incluir capturas da interface e respostas das APIs.

## 7. Trade-offs e limitações

Discutir clareza didática versus escalabilidade, peers estáticos, PoW simples,
armazenamento local replicado, ausência de TLS interno e custódia simulada das
chaves.

## 8. Conclusão

Retomar como descentralização, encadeamento de hashes, consenso, assinaturas e
criptografia atendem aos requisitos de economia e auditoria.

## Referências a incluir

- artigo original do Bitcoin;
- documentação Ed25519/X25519;
- referência sobre AES-GCM;
- documentação FastAPI;
- literatura sobre ledgers distribuídos e double spending.

