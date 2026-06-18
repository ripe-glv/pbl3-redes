# Sabatina do Barema - Problema 3

Este roteiro responde pontualmente ao barema do professor. As respostas em
**Resposta oral** foram escritas para serem faladas durante a apresentação.

## Resumo de 30 segundos

**Resposta oral:** "O projeto possui dois modos comparáveis. No modo principal,
eu implementei uma blockchain didática própria com três nós FastAPI
independentes, ledgers separados, Proof of Work, propagação HTTP e escolha da
melhor cadeia válida. No modo alternativo, as mesmas regras de créditos,
escoltas e provas são executadas por um smart contract Solidity em uma rede
Ethereum local Ganache, acessada pelo backend com Web3 e JSON-RPC. Nos dois
modos, o laudo completo fica criptografado off-chain e somente hashes e
metadados públicos ficam on-chain."

Código principal:

- `backend/app/ledger.py`: blockchain, PoW, saldo, validação e consenso.
- `backend/app/network.py`: comunicação entre peers.
- `backend/app/service.py`: créditos, escoltas e laudos.
- `backend/app/crypto.py`: assinatura, hash e criptografia.
- `backend/app/main.py`: endpoints FastAPI.
- `evm/contracts/SentinelLedger.sol`: regras do smart contract.
- `backend/app/evm.py`: gateway Web3, eventos, blocos e recibos EVM.
- `backend/app/evm_main.py`: API compatível do modo Ganache.
- `evm/scripts/deploy.mjs`: compilação e deploy automático do contrato.
- `docker-compose.ganache.yml`: Ganache, deploy, três APIs e frontend.
- `frontend/src/App.tsx` e `frontend/src/components.tsx`: interface.

## Qual modo está sendo apresentado?

Antes da demonstração, diga explicitamente qual ambiente está aberto:

- **Manual:** interface `http://localhost:5173`, APIs `8001`, `8002` e `8003`.
- **Ganache/EVM:** interface `http://localhost:5183`, APIs `8011`, `8012` e
  `8013`, JSON-RPC `8545`.

**Resposta oral curta:** "A blockchain manual demonstra como os mecanismos
internos foram construídos. O modo Ganache demonstra como a aplicação seria
implementada sobre uma plataforma Ethereum e um smart contract."

| Aspecto | Blockchain manual | Ganache/EVM |
|---|---|---|
| Ledger | JSON independente por nó | Estado mantido pelo Ganache |
| Regras | Python em `ledger.py` | Solidity em `SentinelLedger.sol` |
| Nós blockchain | Três peers independentes | Um nó EVM local |
| APIs | Três APIs, cada uma com ledger próprio | Três gateways para o mesmo contrato |
| Consenso | PoW e melhor cadeia válida | Gerenciado pelo Ganache local |
| Comunicação | HTTP entre peers | JSON-RPC entre Web3 e Ganache |
| Assinatura | Ed25519 implementada na aplicação | Contas e transações Ethereum |
| Custo computacional | Dificuldade e nonce | Gas |
| Fork e reparo | Implementados no projeto | Não demonstrados entre validadores |
| Objetivo | Ensinar o interior da blockchain | Ensinar DApp e smart contract |

---

# 1. Arquitetura

## 1.1 Existem múltiplos nós independentes?

**Resposta oral:** "No modo manual, sim. Eu subo `node-a`, `node-b` e `node-c`.
Cada instância recebe um `NODE_ID`, peers, ledger e storage próprios. Elas não
compartilham banco. No modo Ganache também existem três APIs, mas elas são
gateways da aplicação conectados ao mesmo nó Ethereum local e ao mesmo
contrato; portanto não afirmo que sejam três validadores EVM independentes."

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

No modo Ganache:

- `docker-compose.ganache.yml:48-103`: três gateways FastAPI.
- `docker-compose.ganache.yml:54`, `:73`, `:92`: mesmo JSON-RPC Ganache.
- `docker-compose.ganache.yml:61`, `:80`, `:99`: mesmo artefato do contrato.
- `backend/app/evm.py:20-35`: conexão Web3 e instanciação do contrato.

Abra:

- `http://localhost:8011/node/status`
- `http://localhost:8012/node/status`
- `http://localhost:8013/node/status`

As respostas devem ter `node_id` diferente, mas o mesmo `chain_id`, altura e
`contract_address`.

## 1.2 Existe banco central, servidor de saldo ou nó mestre?

**Resposta oral:** "Não. O saldo não é consultado em um servidor de saldo. Cada
nó recalcula o saldo percorrendo sua própria cadeia. Qualquer nó pode receber,
validar e minerar transações. A lista de peers é simétrica e não existe uma
função especial de mestre. Essa resposta descreve o modo manual. No Ganache, o
estado autoritativo fica no contrato executado por um único nó EVM local."

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
pela melhor cadeia válida. Isso vale para o modo manual. No Ganache, derrubar
uma das APIs não interrompe as outras, mas derrubar o container Ganache
interrompe o acesso ao ledger EVM porque ele é o único nó blockchain desse
ambiente."

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
Depois implementei também o modo Ganache para comparar: nele eu removo a
implementação manual da infraestrutura e concentro as regras em Solidity. Em
troca, a demonstração EVM ganha smart contract, eventos, gas e JSON-RPC, mas
deixa de mostrar internamente mempool, PoW e resolução de forks."

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

**Resposta oral:** "No modo manual, os peers usam HTTP assíncrono e propagam
transações e blocos diretamente. No modo Ganache, o frontend ainda fala HTTP
com o FastAPI, mas o backend fala JSON-RPC com o nó Ethereum por meio do
Web3.py. Nesse segundo modo, a validação das regras ocorre no smart contract e
a inclusão em blocos é responsabilidade do Ganache."

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
zeros. Para convergência, os nós adotam a cadeia válida de maior comprimento.
Isso descreve o modo manual. No modo Ganache, não implementei consenso entre
três validadores: existe um único nó Ethereum local que cria blocos
automaticamente para desenvolvimento."

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
recebe 100 Operational Credits. No modo Ganache, o construtor do smart contract
atribui os mesmos 100 créditos às três contas Ethereum e emite eventos
`GenesisCredit`."

**Onde está no código:**

- `backend/app/ledger.py:48`: criação do gênese.
- `backend/app/ledger.py:55`: transações `GENESIS_CREDIT`.
- `backend/app/data.py`: companhias e carteiras iniciais.
- `evm/contracts/SentinelLedger.sol:53-72`: créditos iniciais no construtor.

## 3.2 Como o saldo é calculado?

**Resposta oral:** "O saldo é uma função do histórico: somo valores recebidos e
subtraio valores enviados. Não salvo um campo de saldo como fonte da verdade.
Para validar gasto também incluo os débitos pendentes no mempool."

**Onde está no código:**

- `backend/app/ledger.py:115`: cálculo confirmado e opcionalmente pendente.
- `backend/app/main.py:222`: saldos de todas as companhias.
- `backend/app/main.py:230`: saldo individual.
- `frontend/src/components.tsx:244`: tabela visual de saldos.

**Diferença no Ganache:** o saldo de Operational Credits fica no estado do
contrato, no mapping `credits`. O backend consulta esse mapping com uma chamada
somente leitura.

- `evm/contracts/SentinelLedger.sol:23`: mapping de créditos.
- `backend/app/evm.py:44-49`: leitura do saldo via Web3.

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

**Diferença no Ganache:** a transação parte de uma conta Ethereum desbloqueada
pelo Ganache. O contrato usa `msg.sender` para identificar a companhia e
rejeita saldo insuficiente com `require`.

- `evm/contracts/SentinelLedger.sol:75-90`: autorização e transferência.
- `backend/app/evm.py:51-55`: chamada do contrato.
- `backend/app/evm.py:87-98`: envio, recibo e `gas_used`.

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

**No modo Ganache:** cada chamada de `transferCredits` executa de forma atômica
na EVM. A primeira transação altera o mapping `credits`; quando a segunda é
executada, ela lê o novo saldo e pode ser revertida por `require`.

- `evm/contracts/SentinelLedger.sol:80-90`: regra atômica de saldo.
- `backend/app/evm_main.py:385-404`: demonstração EVM.

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

**No modo Ganache:** pagamento e reserva do drone acontecem dentro da mesma
execução de `requestEscort`. Se qualquer `require` falhar, toda a transação é
revertida; não existe estado parcial com crédito descontado e drone livre, ou
drone ocupado sem pagamento.

- `evm/contracts/SentinelLedger.sol:93-131`: operação atômica.
- `backend/app/evm_main.py:199-228`: endpoint EVM.

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

**No modo Ganache:** `droneBusy[droneId]` fica no estado do contrato. Como as
transações são executadas sequencialmente pela EVM, a primeira marca o drone e
a segunda encontra `Drone unavailable` e reverte.

- `evm/contracts/SentinelLedger.sol:26-27`: estado dos drones.
- `evm/contracts/SentinelLedger.sol:99-106`: validação e reserva.
- `backend/app/evm_main.py:407-437`: demonstração da corrida.

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

**No modo Ganache:** `completeMission` atualiza a struct `Mission` no contrato
com resultado, risco, ponteiro e hashes. O contrato também libera o drone e
emite `MissionCompleted`. O laudo completo continua fora da cadeia.

- `evm/contracts/SentinelLedger.sol:134-165`: conclusão on-chain.
- `backend/app/evm_main.py:243-300`: criptografia e envio ao contrato.

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

**No modo Ganache:** blocos confirmados não são editados pelos endpoints da
aplicação. O histórico e o estado são mantidos pelo cliente Ethereum. O
endpoint de adulteração da cadeia retorna conflito porque não há edição direta
do ledger EVM pela API.

- `backend/app/evm_main.py:339-356`: verificação e bloqueio da adulteração.

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

No explorer, o bloco detectado passa a aparecer em vermelho, com animação e
selo **COMPROMETIDO**. Ao selecioná-lo, a interface mostra o motivo da falha e
compara o hash calculado com o hash registrado. Depois do reparo, a marcação
desaparece automaticamente.

- A tela de Auditoria possui um seletor explícito de nó alvo.
- O nó escolhido também passa a ser o nó consultado pelo explorer.
- Os logs registram a ação junto com a URL do nó adulterado.
- `frontend/src/App.tsx`: consulta `/audit/verify-chain` durante a atualização.
- `frontend/src/components.tsx`: selo visual do bloco comprometido.
- `frontend/src/styles.css`: alerta vermelho e animação de integridade.

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
partir de outra API. No modo manual, isso ocorre por propagação entre ledgers
independentes. No Ganache, ocorre porque as três APIs consultam o mesmo contrato
e a mesma rede EVM. O resultado visual é parecido, mas a arquitetura é
diferente."

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

**Resposta oral:** "Sim. O README explica os dois modos. O Compose original sobe
a blockchain manual com três ledgers independentes. O Compose Ganache sobe a
rede EVM, publica o contrato automaticamente e inicia três gateways FastAPI.
Também há teste de fumaça EVM para transferência, missão, contrato e laudo."

**Onde está:**

- `README.md:70`: execução Docker.
- `README.md:299`: funcionamento do ledger.
- `README.md:380`: roteiro do barema.
- `README.md:501`: limitações.
- `iniciar.ps1` e `parar.ps1`: execução local.
- `iniciar-multi-pc.ps1`: execução distribuída em computadores diferentes.
- `docker-compose.ganache.yml`: ambiente EVM completo.
- `scripts/smoke-evm.py`: teste ponta a ponta do modo Ganache.

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

# 9. Modo Ganache, Ethereum e Smart Contract

## 9.1 O que foi implementado no modo Ganache?

**Resposta oral:** "Foi criada uma segunda implementação da mesma aplicação
sobre uma rede Ethereum local. O Ganache mantém o ledger EVM e cria os blocos.
O contrato `SentinelLedger.sol` mantém créditos, missões e ocupação dos drones.
O FastAPI usa Web3.py para chamar o contrato e traduz eventos Ethereum para o
formato exibido pelo frontend."

**Onde está no código:**

- `evm/contracts/SentinelLedger.sol`: contrato Solidity.
- `evm/scripts/deploy.mjs`: compilação, deploy e geração de ABI.
- `backend/app/evm.py`: integração Web3.
- `backend/app/evm_main.py`: endpoints do modo EVM.
- `docker-compose.ganache.yml`: ambiente completo.

## 9.2 O que é Solidity?

**Resposta oral:** "Solidity é a linguagem usada para escrever programas que
rodam na Ethereum Virtual Machine. Ela permite declarar estado persistente,
funções, eventos e condições `require`. O código é compilado para bytecode,
publicado em um endereço e executado pela EVM."

No projeto:

- `mapping(address => uint256) credits`: saldo dos créditos operacionais.
- `mapping(string => bool) droneBusy`: ocupação dos drones.
- `mapping(string => Mission) missions`: estado das missões.
- `transferCredits`, `requestEscort` e `completeMission`: regras de negócio.

## 9.3 O que é um smart contract?

**Resposta oral:** "É um programa publicado na blockchain. Depois do deploy,
ele possui endereço e estado próprios. As funções que alteram estado são
executadas como transações. Todos os participantes usam o mesmo código, e uma
regra inválida reverte toda a operação."

Exemplo do projeto:

```solidity
require(credits[msg.sender] >= amount, "Insufficient credits");
credits[msg.sender] -= amount;
credits[recipient] += amount;
```

O `require` impede saldo negativo. Se falhar, nenhuma alteração daquela chamada
é confirmada.

## 9.4 O que é EVM?

**Resposta oral:** "EVM significa Ethereum Virtual Machine. É o ambiente
determinístico que executa o bytecode do contrato. Para a mesma transação e o
mesmo estado inicial, a execução precisa produzir o mesmo resultado. No
projeto, o Ganache fornece essa EVM local."

Fluxo:

```text
Solidity → compilador solc → bytecode + ABI → deploy → EVM
```

## 9.5 O que é o ledger EVM?

**Resposta oral:** "É o estado e o histórico mantidos pela rede Ethereum:
blocos, transações, contas, contratos, recibos, logs e dados persistentes dos
contratos. No modo Ganache, não existe `ledger.json` da aplicação; o estado
autoritativo está no Ganache e no contrato."

O volume `evm-chain` persiste os dados da rede local:

- `docker-compose.ganache.yml:19-24`.

## 9.6 O que é ABI?

**Resposta oral:** "ABI é a descrição da interface binária do contrato. Ela diz
ao Web3 quais funções e eventos existem, seus parâmetros e tipos. O backend usa
a ABI junto com o endereço do contrato para montar chamadas JSON-RPC e
decodificar resultados."

**Onde está no código:**

- `evm/scripts/deploy.mjs`: salva endereço, ABI, chain ID e contas.
- `backend/app/evm.py:27-35`: carrega artefato e cria o objeto do contrato.

## 9.7 O que é JSON-RPC?

**Resposta oral:** "É o protocolo usado para conversar com o nó Ethereum. As
mensagens são objetos JSON contendo método, parâmetros e identificador. Web3.py
abstrai chamadas como consultar bloco, executar `eth_call`, enviar transação e
buscar recibo."

Fluxo do projeto:

```text
Frontend → HTTP → FastAPI → Web3.py → JSON-RPC → Ganache → EVM
```

Exemplos conceituais:

- `eth_chainId`: identifica a rede;
- `eth_blockNumber`: consulta a altura;
- `eth_call`: leitura sem alterar o estado;
- `eth_sendTransaction`: envia operação que altera o estado;
- `eth_getTransactionReceipt`: consulta confirmação, status e gas.

## 9.8 O que é gas?

**Resposta oral:** "Gas mede o trabalho computacional executado pela EVM.
Leituras, cálculos e principalmente escritas no estado têm custos diferentes.
Em uma rede pública, o usuário paga `gas usado × preço do gas` em ETH. No
Ganache o ETH é fictício, mas o recibo continua informando `gas_used`."

**Onde está no código:**

- `backend/app/evm.py:87-98`: envio e leitura do recibo.

O limite configurado pelo backend é `4_000_000`, mas a cobrança corresponde ao
que foi efetivamente usado, disponível em `receipt.gasUsed`.

## 9.9 Os créditos operacionais são ETH?

**Resposta oral:** "Não. ETH é a moeda nativa usada para pagar gas. Os
Operational Credits são números mantidos no mapping `credits` do contrato. Uma
companhia pode ter ETH para executar transações e, separadamente, possuir uma
quantidade de créditos operacionais."

## 9.10 Como as três companhias viram contas Ethereum?

**Resposta oral:** "O Ganache cria contas determinísticas a partir de uma
mnemonic fixa. No deploy, as três primeiras contas são associadas a `gulf`,
`atlas` e `orion`. O endereço e a ABI são salvos no artefato consumido pelos
três backends."

**Onde está no código:**

- `docker-compose.ganache.yml:13-16`: mnemonic e quantidade de contas.
- `evm/scripts/deploy.mjs`: seleção das contas e deploy.
- `backend/app/evm_main.py:27-34`: associação com as companhias.

## 9.11 Como o contrato é publicado automaticamente?

**Resposta oral:** "O serviço `deploy-contract` espera o healthcheck do
Ganache, compila o Solidity com `solc`, publica o contrato com ethers e grava
endereço e ABI no volume `evm-artifacts`. Os três backends só iniciam depois
que esse serviço termina com sucesso. Se o contrato já existe na cadeia
persistida, o script reutiliza o endereço."

**Onde está no código:**

- `docker-compose.ganache.yml:25-46`: healthcheck e dependência.
- `evm/scripts/deploy.mjs`: espera, compilação, deploy e reutilização.

## 9.12 Existem três nós Ethereum no modo Ganache?

**Resposta oral obrigatória:** "Não. Existem três instâncias FastAPI chamadas
`node-a`, `node-b` e `node-c`, mas todas acessam o mesmo Ganache e o mesmo smart
contract. Elas são três gateways da aplicação, não três validadores Ethereum.
Os três nós realmente independentes, com ledgers e consenso próprios, existem
no modo manual."

Essa distinção evita afirmar uma descentralização que o ambiente Ganache não
possui.

## 9.13 Por que manter três APIs no modo Ganache?

**Resposta oral:** "Para preservar a interface de seleção de nós, demonstrar
que diferentes instâncias da aplicação enxergam o mesmo estado on-chain e
permitir comparar arquiteturas. Porém, a consistência vem do ledger EVM
compartilhado, não de propagação entre essas APIs."

## 9.14 Como os eventos do contrato aparecem no explorer?

**Resposta oral:** "O contrato emite eventos para gênese, transferência,
solicitação de escolta e conclusão. O gateway Web3 busca os logs desde o bloco
zero, decodifica pela ABI e os converte para o formato de transação usado pela
interface."

**Onde está no código:**

- `evm/contracts/SentinelLedger.sol:31-51`: eventos.
- `backend/app/evm.py:12-17`: mapeamento dos tipos.
- `backend/app/evm.py:140-184`: consulta e conversão dos logs.

## 9.15 Como os blocos Ethereum aparecem na interface antiga?

**Resposta oral:** "O backend consulta os blocos reais do Ganache e adapta
campos como número, timestamp, parent hash, hash e nonce para a estrutura que o
frontend já conhecia. Os eventos decodificados são agrupados pelo número do
bloco."

**Onde está no código:**

- `backend/app/evm.py:187-210`: adaptação dos blocos.
- `backend/app/evm_main.py:117-138`: endpoints de ledger e transações.

## 9.16 O Ganache usa o mesmo Proof of Work manual?

**Resposta oral:** "Não. O Proof of Work com busca de nonce pertence à
blockchain manual. O Ganache minera blocos instantaneamente para
desenvolvimento. Também não afirmo que essa configuração reproduz o consenso
Proof of Stake da Ethereum pública."

## 9.17 Qual versão é mais simples?

**Resposta oral:** "A blockchain manual é conceitualmente simples porque o
escopo é pequeno, mas exige implementar hash, mempool, PoW, validação,
propagação, forks e persistência. Ganache simplifica essa infraestrutura, porém
introduz Solidity, ABI, EVM, gas, deploy, eventos e integração Web3. Então ele
reduz a complexidade da blockchain e aumenta a complexidade da integração."

## 9.18 Por que Ganache se ele foi descontinuado?

**Resposta oral:** "Foi usado por compatibilidade com o ambiente solicitado e
para comparação acadêmica. A implementação está isolada em um Compose
alternativo. Para um projeto novo eu consideraria Anvil ou Hardhat Network,
mantendo o mesmo contrato e uma integração EVM semelhante."

## 9.19 Como executar cada modo?

Blockchain manual:

```powershell
docker compose -f docker-compose.yml up --build -d
```

Ganache/EVM:

```powershell
docker compose -f docker-compose.ganache.yml up --build -d
```

Os projetos têm nomes e portas diferentes, portanto podem rodar ao mesmo tempo.

## 9.20 Como validar o modo Ganache?

```powershell
python scripts/smoke-evm.py
```

O teste realiza login, transferência, solicitação de escolta, conclusão,
descriptografia e verificação dos hashes. O resultado esperado contém:

```text
report_valid: true
file_valid: true
```

---

# 10. Perguntas extras prováveis

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
propriedade de não depender de um storage único. Isso descreve o modo manual.
No Compose Ganache, as três APIs compartilham o volume `evm-storage`; portanto,
nesse modo específico o storage é redundante apenas no nível de acesso, não em
cópias independentes."

## Qual a diferença entre `report_hash` e `encrypted_file_hash`?

**Resposta oral:** "`report_hash` prova o conteúdo original canônico antes da
criptografia. `encrypted_file_hash` prova que o arquivo ciphertext armazenado
não foi modificado. O primeiro é verificado após descriptografar; o segundo
pode ser verificado publicamente."

---

# 11. Ordem recomendada para os 30 minutos

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
12. Trocar para o modo Ganache e mostrar o mesmo domínio no smart contract.
13. Mostrar `contract_address`, `gas_used` e eventos no explorer.
14. Explicar que as três APIs EVM compartilham um único Ganache.
15. Encerrar com trade-offs e limitações.
