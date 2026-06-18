# Sabatina do Barema - Problema 3

Este roteiro responde pontualmente ao barema do professor. As respostas em
**Resposta oral** foram escritas para serem faladas durante a apresentação.

## Resumo de 30 segundos

**Resposta oral:** "Eu implementei uma blockchain didática própria com três nós
FastAPI independentes. Cada nó mantém seu ledger e storage, valida assinaturas,
saldo, duplo gasto e alocação de drones. As transações e blocos são propagados
por HTTP. O consenso usa Proof of Work e a melhor cadeia válida. Os dados
públicos do laudo ficam no ledger; o conteúdo confidencial fica criptografado
off-chain, com hashes on-chain para auditoria."

Código principal:

- `backend/app/ledger.py`: blockchain, PoW, saldo, validação e consenso.
- `backend/app/network.py`: comunicação entre peers.
- `backend/app/service.py`: créditos, escoltas e laudos.
- `backend/app/crypto.py`: assinatura, hash e criptografia.
- `backend/app/main.py`: endpoints FastAPI.
- `frontend/src/App.tsx` e `frontend/src/components.tsx`: interface.

---

# 1. Arquitetura

## 1.1 Existem múltiplos nós independentes?

**Resposta oral:** "Sim. No modo de laboratório eu subo `node-a`, `node-b` e
`node-c`. Cada instância executa a mesma aplicação, mas recebe um `NODE_ID`, uma
lista de peers, um arquivo de ledger e um volume de storage próprios. Eles não
compartilham banco de dados."

**Onde está no código:**

- `docker-compose.yml:2`, `docker-compose.yml:25`, `docker-compose.yml:48`:
  definição dos três nós.
- `docker-compose.yml:16-17`, `docker-compose.yml:39-40`,
  `docker-compose.yml:62-63`: volumes separados.
- `docker-compose.yml:85-90`: seis volumes independentes.
- `backend/app/config.py:9-29`: configuração individual de cada nó.
- `backend/app/ledger.py:76`: cada processo carrega ou cria seu ledger local.
- `backend/app/ledger.py:89`: persistência local do ledger e mempool.

**Como demonstrar:**

```powershell
docker compose ps
docker volume ls
```

Abra:

- `http://localhost:8001/node/status`
- `http://localhost:8002/node/status`
- `http://localhost:8003/node/status`

## 1.2 Existe banco central, servidor de saldo ou nó mestre?

**Resposta oral:** "Não. O saldo não é consultado em um servidor de saldo. Cada
nó recalcula o saldo percorrendo sua própria cadeia. Qualquer nó pode receber,
validar e minerar transações. A lista de peers é simétrica e não existe uma
função especial de mestre."

**Onde está no código:**

- `backend/app/ledger.py:115`: cálculo de saldo pelo histórico.
- `backend/app/ledger.py:232`: qualquer nó aceita uma transação válida.
- `backend/app/ledger.py:273`: qualquer nó pode minerar.
- `docker-compose.yml:7`, `docker-compose.yml:30`, `docker-compose.yml:53`:
  peers simétricos.
- `backend/app/main.py:222`: `/balances` apenas calcula e expõe o estado local.

## 1.3 O sistema funciona se um nó cair?

**Resposta oral:** "Sim. Os outros dois nós continuam validando, minerando e
respondendo. Quando o nó volta, ele consulta os peers e substitui sua cadeia
pela melhor cadeia válida."

**Onde está no código:**

- `backend/app/network.py:59`: busca cadeias dos peers.
- `backend/app/ledger.py:427`: substituição pela melhor cadeia válida.
- `backend/app/main.py:128-129`: endpoints de sincronização.
- `backend/app/main.py:469`: reparo pela rede.

**Como demonstrar:**

```powershell
docker compose stop node-c
```

Faça uma transferência pelo `node-a`, confirme no `node-b`, depois:

```powershell
docker compose start node-c
```

Selecione `node-c` na interface e use **Sincronizar com peers**.

## 1.4 Por que blockchain própria? Quais os trade-offs?

**Resposta oral:** "Escolhi blockchain própria porque o objetivo acadêmico exige
mostrar claramente criação do bloco, PoW, assinatura, validação, propagação,
fork e duplo gasto. Ethereum ou Hyperledger esconderiam parte dessas etapas.
Em troca, minha solução tem menos escalabilidade, descoberta de peers estática,
PoW simples e não possui a segurança econômica de uma rede pública real."

**Onde está documentado:**

- `README.md:15`: arquitetura.
- `README.md:334`: consenso e forks.
- `README.md:501`: limitações didáticas.

## 1.5 E em computadores realmente separados?

**Resposta oral:** "Também existe modo multi-PC. Cada computador sobe somente
um nó, aponta `PEERS` para os IPs dos outros e mantém seus volumes locais."

**Onde está no código:**

- `docker-compose.multi-pc.yml:1-48`.
- `.env.multi-pc.example:4-16`.
- `iniciar-multi-pc.ps1:1-60`.
- `README.md:182-197`.

---

# 2. Comunicação

## 2.1 Como os nós se comunicam?

**Resposta oral:** "Os nós usam HTTP assíncrono. Cada nó conhece URLs de peers.
Ao criar uma transação ou bloco, ele envia o objeto aos demais nós. O receptor
não confia automaticamente: executa a própria validação."

**Onde está no código:**

- `backend/app/network.py:24`: propagação de transações.
- `backend/app/network.py:32`: propagação de blocos.
- `backend/app/main.py:178`: recebimento de transação.
- `backend/app/main.py:198`: recebimento de bloco.
- `backend/app/main.py:116-121`: consulta e cadastro de peers.

## 2.2 Como uma transação é propagada?

**Resposta oral:** "Primeiro ela é validada localmente e incluída no mempool.
Depois é enviada para os peers em `/receive-transaction`. Cada peer verifica
assinatura, saldo, duplicidade e regras de negócio antes de aceitar."

**Onde está no código:**

- `backend/app/service.py:44`: criação e envio de transferência.
- `backend/app/ledger.py:169`: validação da transação.
- `backend/app/ledger.py:232`: inclusão protegida no mempool.
- `backend/app/network.py:24`: envio aos peers.
- `backend/app/main.py:178`: recebimento.

## 2.3 Como um bloco é propagado?

**Resposta oral:** "Depois da mineração, o bloco é enviado a todos os peers.
Cada peer acrescenta o bloco apenas se a altura, o hash, o PoW, o
`previous_hash`, as assinaturas e o estado resultante forem válidos."

**Onde está no código:**

- `backend/app/ledger.py:273`: mineração.
- `backend/app/network.py:32`: propagação.
- `backend/app/ledger.py:306`: validação integral da cadeia.
- `backend/app/ledger.py:413`: aceitação de bloco recebido.

## 2.4 Qual é o consenso?

**Resposta oral:** "Uso Proof of Work com dificuldade configurável. O minerador
incrementa o nonce até o SHA-256 do bloco começar com a quantidade exigida de
zeros. Para convergência, os nós adotam a cadeia válida de maior comprimento."

**Onde está no código:**

- `backend/app/ledger.py:263`: laço de Proof of Work.
- `backend/app/ledger.py:273`: criação do bloco.
- `backend/app/ledger.py:306`: validação do PoW.
- `backend/app/ledger.py:427`: escolha da melhor cadeia.
- `docker-compose.yml`: `POW_DIFFICULTY=3`.

## 2.5 Como resolve forks?

**Resposta oral:** "O nó consulta as cadeias dos peers, descarta qualquer cadeia
inválida e compara o score. A cadeia mais longa vence. Se duas válidas têm a
mesma altura, o hash da ponta é usado como desempate determinístico, para todos
convergirem sem nó mestre."

**Onde está no código:**

- `backend/app/network.py:59`: coleta das cadeias candidatas.
- `backend/app/ledger.py:427`: validação, score e substituição.

## 2.6 Por que o mecanismo do Problema 2 não bastava?

**Resposta oral:** "O Problema 2 resolvia exclusão mútua para não alocar o mesmo
drone duas vezes naquele instante. Ele não criava propriedade transferível de
créditos, histórico imutável, assinatura de pagamentos nem prova de
adulteração. O ledger resolve estado econômico e histórico auditável; a regra
de concorrência continua necessária dentro da validação do ledger."

---

# 3. Gestão de Ativos

## 3.1 Como os créditos são criados?

**Resposta oral:** "Os créditos iniciais são emitidos no bloco gênese. O gênese
é determinístico e idêntico em todos os nós. Cada uma das três companhias
recebe 100 Operational Credits."

**Onde está no código:**

- `backend/app/ledger.py:48`: criação do gênese.
- `backend/app/ledger.py:55`: transações `GENESIS_CREDIT`.
- `backend/app/data.py`: companhias e carteiras iniciais.

## 3.2 Como o saldo é calculado?

**Resposta oral:** "O saldo é uma função do histórico: somo valores recebidos e
subtraio valores enviados. Não salvo um campo de saldo como fonte da verdade.
Para validar gasto também incluo os débitos pendentes no mempool."

**Onde está no código:**

- `backend/app/ledger.py:115`: cálculo confirmado e opcionalmente pendente.
- `backend/app/main.py:222`: saldos de todas as companhias.
- `backend/app/main.py:230`: saldo individual.
- `frontend/src/components.tsx:244`: tabela visual de saldos.

## 3.3 Como as transferências são autenticadas?

**Resposta oral:** "Cada carteira possui chave Ed25519. A transação é serializada
de forma canônica e assinada com a chave privada. O nó deriva o endereço da
chave pública e verifica a assinatura antes de consultar o saldo."

**Onde está no código:**

- `backend/app/crypto.py:21`: serialização canônica.
- `backend/app/crypto.py:70`: endereço derivado da chave pública.
- `backend/app/crypto.py:74`: assinatura Ed25519.
- `backend/app/crypto.py:79`: verificação.
- `backend/app/ledger.py:241`: criação de transação assinada.
- `backend/app/ledger.py:169`: validação.

## 3.4 Como mostrar transferência confirmada em outro nó?

**Resposta oral:** "Eu faço a transferência no `node-a`, aguardo o bloco e
seleciono o `node-b` ou `node-c` na interface. O saldo e a transação aparecem
porque o bloco foi propagado, não porque existe banco compartilhado."

**Onde está no código:**

- `backend/app/main.py:257`: endpoint de transferência.
- `backend/app/service.py:44`: fluxo de transferência.
- `backend/app/network.py:24` e `:32`: propagação.
- `frontend/src/components.tsx:312`: formulário.
- `frontend/src/App.tsx:207`: seleção do nó consultado.

---

# 4. Prevenção de Duplo Gasto

## 4.1 Onde o duplo gasto é detectado?

**Resposta oral:** "Ele é detectado antes da entrada no mempool e novamente
antes da mineração. O saldo disponível considera a cadeia confirmada e as
transações pendentes. Assim a primeira requisição reserva economicamente o
valor e a segunda encontra saldo insuficiente."

**Onde está no código:**

- `backend/app/ledger.py:169`: validação.
- `backend/app/ledger.py:179-194`: saldo confirmado mais pendências.
- `backend/app/ledger.py:232`: região crítica com lock.
- `backend/app/ledger.py:273`: revalidação antes da mineração.
- `backend/app/ledger.py:306`: replay completo ao validar uma cadeia.

## 4.2 O bloqueio está somente na interface?

**Resposta oral:** "Não. A interface apenas exibe a resposta. A rejeição ocorre
no backend dentro de `validate_transaction`. Mesmo uma chamada direta à API é
rejeitada."

Mensagem esperada:

```text
Saldo insuficiente ou tentativa de duplo gasto detectada.
```

## 4.3 Como funciona o teste simultâneo?

**Resposta oral:** "O endpoint cria duas transferências, cada uma tentando usar
todo o mesmo saldo, e dispara as duas concorrentemente. O lock serializa a
alteração do mempool; uma entra e a outra é rejeitada."

**Onde está no código:**

- `backend/app/service.py:258`: cenário de duplo gasto.
- `backend/app/main.py:474`: endpoint `/demo/double-spend`.
- `backend/tests/test_system.py:47`: teste automatizado.
- `frontend/src/components.tsx:734`: painel de demonstrações.

**Como demonstrar:** tela **Demonstrações** → **Duplo gasto**.

---

# 5. Requisição e Pagamento de Escoltas

## 5.1 O drone só é despachado depois do pagamento?

**Resposta oral:** "Sim. O sistema cria `ESCORT_PAYMENT` e
`DRONE_DISPATCH` no mesmo bloco, nessa ordem. O despacho referencia
explicitamente o ID do pagamento. A API só retorna estado `DISPATCHED` depois
que o bloco foi minerado."

**Onde está no código:**

- `backend/app/service.py:59`: fluxo de escolta.
- `backend/app/service.py:95`: despacho referencia `payment_tx_id`.
- `backend/app/ledger.py:169`: valida vínculo entre pagamento e despacho.
- `backend/app/main.py:322`: endpoint.

## 5.2 O que ocorre sem saldo?

**Resposta oral:** "O `ESCORT_PAYMENT` passa pela mesma validação financeira de
uma transferência. Se o saldo confirmado menos pendências for menor que o
custo, a missão não entra no mempool e nenhum despacho é criado."

**Onde está no código:**

- `backend/app/ledger.py:179-194`.

## 5.3 Como evita duas companhias alocarem o mesmo drone?

**Resposta oral:** "A ocupação é reconstruída a partir de `ESCORT_PAYMENT` e
`MISSION_COMPLETE` do ledger e do mempool. Antes de aceitar novo pagamento, o
nó verifica se o drone já aparece ativo. A operação também usa uma região
crítica assíncrona."

**Onde está no código:**

- `backend/app/ledger.py:129`: reconstrução das missões ativas.
- `backend/app/ledger.py:196-204`: rejeição de drone ocupado.
- `backend/app/service.py:59`: lock e confirmação.
- `backend/app/service.py:289`: corrida simultânea.
- `backend/tests/test_system.py:56`: teste automatizado.

## 5.4 O pagamento fica auditável?

**Resposta oral:** "Sim. `ESCORT_PAYMENT` permanece dentro do bloco com
companhia, valor, drone, rota e missão. Pode ser consultado pelo explorer,
`/transactions` ou histórico da carteira."

**Onde está no código:**

- `backend/app/main.py:157`: transações.
- `backend/app/main.py:243-244`: histórico da companhia/carteira.
- `frontend/src/components.tsx:213`: lista visual.

---

# 6. Log de Operações Imutável

## 6.1 O que é registrado quando a missão termina?

**Resposta oral:** "O ledger recebe uma `MISSION_COMPLETE`, com resultado e
risco, e uma `MISSION_REPORT_PROOF`, com companhia, drone, rota, resultado,
ponteiro, hash do laudo original, hash do arquivo criptografado e chave de
acesso encapsulada."

**Onde está no código:**

- `backend/app/service.py:159`: conclusão.
- `backend/app/service.py:201`: criação da prova.
- `backend/app/service.py:126`: reconstrução pública das missões.

## 6.2 O laudo completo fica na blockchain?

**Resposta oral:** "Não. Dados grandes e estratégicos ficam criptografados
off-chain. O ledger guarda a prova pública e metadados relevantes. Isso mantém
auditoria pública sem expor descrição, evidências e observações estratégicas."

**Onde está no código:**

- `backend/app/crypto.py:97`: criptografia híbrida X25519 + AES-256-GCM.
- `backend/app/storage.py:21`: gravação do envelope criptografado.
- `backend/app/network.py:39`: replicação do ciphertext aos peers.
- `backend/app/service.py:234`: descriptografia somente pela dona.
- `frontend/src/components.tsx:512`: visualização e bloqueio.

## 6.3 O que garante a imutabilidade?

**Resposta oral:** "O hash do bloco cobre todo o conteúdo, cada bloco referencia
o hash anterior e o PoW precisa continuar válido. Alterar um registro muda o
hash e quebra o encadeamento. Além disso, transações têm assinatura digital."

**Onde está no código:**

- `backend/app/crypto.py:27`: SHA-256.
- `backend/app/ledger.py:306`: valida hash, PoW e `previous_hash`.
- `backend/app/crypto.py:79`: assinatura.

Observação correta para a arguição: tecnicamente os bits locais ainda podem ser
editados; "imutabilidade" significa que a adulteração é detectável e que a
cópia inválida é rejeitada/reparada pela rede.

## 6.4 Como detectar adulteração do arquivo off-chain?

**Resposta oral:** "O nó recalcula o SHA-256 do ciphertext e compara com
`encrypted_file_hash` registrado na blockchain. Não precisa descriptografar o
arquivo para auditar a integridade."

**Onde está no código:**

- `backend/app/storage.py:51`: comparação.
- `backend/app/main.py:373`: endpoint público.
- `backend/app/storage.py:76`: adulteração intencional.

## 6.5 Como demonstrar adulteração e reparo?

**Onde está no código:**

- `backend/app/main.py:443`: verificar cadeia.
- `backend/app/main.py:449`: adulterar cadeia.
- `backend/app/main.py:458`: adulterar storage.
- `backend/app/main.py:469`: reparar.
- `backend/tests/test_system.py:95`: teste automatizado.

**Como demonstrar:** tela **Auditoria** → adulterar → verificar → sincronizar.

---

# 7. Transparência e Auditabilidade

## 7.1 O que qualquer participante consegue consultar?

**Resposta oral:** "Sem descriptografar dados confidenciais, qualquer
participante consulta blocos, transações, saldos, carteiras públicas, drones,
missões, resultado público, hashes e ponteiro do laudo."

**Endpoints:**

- `backend/app/main.py:134`: `/ledger`.
- `backend/app/main.py:144`: `/blocks`.
- `backend/app/main.py:157`: `/transactions`.
- `backend/app/main.py:209-230`: companhias e saldos.
- `backend/app/main.py:272`: carteiras públicas.
- `backend/app/main.py:304`: drones.
- `backend/app/main.py:335-340`: missões públicas.

## 7.2 Por que os detalhes exigem login?

**Resposta oral:** "Transparência não significa publicar informação
estratégica. Todos auditam existência, resultado, hash e integridade. Somente a
companhia dona possui a chave para descriptografar o conteúdo completo."

**Onde está no código:**

- `backend/app/auth.py:35-85`: sessão assinada.
- `backend/app/main.py:62-83`: login e identidade.
- `backend/app/main.py:362`: endpoint autenticado.
- `backend/app/service.py:234`: confere a companhia dona.
- `frontend/src/components.tsx:602`: botão de detalhes.
- `frontend/src/components.tsx:618`: bloqueio visual.

## 7.3 Como consultar o mesmo dado em dois nós?

**Resposta oral:** "A interface possui seletor de nó. Eu posso mostrar o saldo,
altura e hash no `node-a`, trocar para `node-b` e obter o mesmo resultado a
partir de outra API e outro arquivo de ledger."

**Onde está no código:**

- `frontend/src/App.tsx:48`: nó selecionado.
- `frontend/src/App.tsx:207`: seletor.
- `backend/app/main.py:491`: comparação entre nós.

## 7.4 Como rastrear a origem dos créditos?

**Resposta oral:** "A origem é o `GENESIS_CREDIT`. Depois, o histórico da
carteira mostra todas as entradas, saídas e pagamentos. Como o saldo é derivado,
qualquer valor pode ser recomposto até o gênese."

**Onde está no código:**

- `backend/app/ledger.py:48`: gênese.
- `backend/app/main.py:243-244`: histórico.
- `frontend/src/App.tsx:275`: tela Carteiras.

## 7.5 Como rastrear todas as missões de um drone?

**Resposta oral:** "O endpoint filtra as missões reconstruídas do ledger pelo
`drone_id`. Não depende de uma tabela local de missões."

**Onde está no código:**

- `backend/app/main.py:317`: `/drones/{drone_id}/missions`.
- `backend/app/service.py:126`: reconstrução a partir dos blocos.

---

# 8. Documentação

## 8.1 O projeto é reproduzível?

**Resposta oral:** "Sim. O README explica Docker, execução manual, três nós,
multi-PC, endpoints, consenso, saldo, criptografia e cada teste do barema."

**Onde está:**

- `README.md:70`: execução Docker.
- `README.md:299`: funcionamento do ledger.
- `README.md:380`: roteiro do barema.
- `README.md:501`: limitações.
- `iniciar.ps1` e `parar.ps1`: execução local.
- `iniciar-multi-pc.ps1`: execução distribuída em computadores diferentes.

## 8.2 O código está no GitHub?

**Resposta oral:** "Sim. O repositório possui `origin` em
`https://github.com/ripe-glv/pbl3-redes.git`, e a branch `main` está sincronizada
com `origin/main`."

Antes da apresentação confirme:

```powershell
git status -sb
git log --oneline -3
```

## 8.3 O relatório SBC está pronto?

**Resposta oral honesta:** "Existe um roteiro técnico em
`docs/RELATORIO_SBC.md`, com comparação do Problema 2, arquitetura, duplo gasto,
auditoria e trade-offs. Ele ainda precisa ser transferido e finalizado no
template oficial da SBC com referências e resultados."

Esse é o principal item documental que ainda não deve ser apresentado como
concluído se o artigo final não tiver sido produzido.

---

# 9. Perguntas extras prováveis

## O login não virou um servidor central?

**Resposta oral:** "Não há um servidor exclusivo de autenticação. Qualquer nó
emite e valida a sessão. O token é assinado com o mesmo segredo configurado nos
nós, então continua funcionando ao trocar de nó. Essa autenticação é apenas
controle didático de acesso; ela não decide saldos, blocos ou consenso."

Trade-off: em produção seria melhor usar identidade descentralizada, certificados
ou assinatura de desafio pela própria carteira, evitando senha compartilhada.

## Por que HTTP pode ser chamado de P2P?

**Resposta oral:** "P2P descreve a topologia lógica, não exige um protocolo de
transporte específico. Os nós são equivalentes, conectam-se diretamente e
trocam transações e blocos sem coordenador. HTTP é o protocolo escolhido para
essas mensagens."

## A maior cadeia sempre é segura?

**Resposta oral:** "Ela é adequada para a demonstração, mas uma rede pequena
continua suscetível a maioria maliciosa e reorganizações. Uma implantação real
usaria mais participantes, dificuldade/trabalho acumulado e possivelmente PoA,
PBFT ou uma plataforma consolidada."

## O arquivo off-chain também é descentralizado?

**Resposta oral:** "Nesta solução o ciphertext é replicado entre os storages
dos peers. Cada nó tem sua cópia independente. Não uso IPFS, mas mantenho a
propriedade de não depender de um storage único."

## Qual a diferença entre `report_hash` e `encrypted_file_hash`?

**Resposta oral:** "`report_hash` prova o conteúdo original canônico antes da
criptografia. `encrypted_file_hash` prova que o arquivo ciphertext armazenado
não foi modificado. O primeiro é verificado após descriptografar; o segundo
pode ser verificado publicamente."

---

# 10. Ordem recomendada para os 30 minutos

1. Dashboard e três nós.
2. Explorer e bloco gênese.
3. Transferência e confirmação em outro nó.
4. Teste de duplo gasto.
5. Solicitação de escolta e corrida pelo mesmo drone.
6. Conclusão da missão e prova pública.
7. Login correto e abertura do laudo.
8. Login de outra companhia e acesso bloqueado.
9. Adulteração da cadeia e reparo.
10. Adulteração do arquivo e divergência de hash.
11. Derrubar um nó e continuar operando.
12. Encerrar com trade-offs e limitações.

