# Sentinel Ledger

Sistema web desenvolvido para o **Problema 3: Economia e Auditoria de
Guerra**, da disciplina TEC502 - Concorrência e Conectividade.

A aplicação coordena pagamentos e escoltas de drones no Estreito de Ormuz por
meio de uma blockchain didática distribuída. Cada nó mantém sua própria cópia
do ledger e do armazenamento off-chain. Não existe banco de saldos, nó mestre
ou autoridade central.

> A blockchain não guarda o segredo; ela guarda a prova. O conteúdo fica
> off-chain e criptografado. A companhia acessa com sua chave, e a rede audita
> com o hash.

## Arquitetura

```text
                    transações e blocos via HTTP
        ┌──────────────┐  <──────────────────>  ┌──────────────┐
        │    node-a    │                         │    node-b    │
        │ ledger-a.json│  <──────────────────>  │ ledger-b.json│
        │ storage-a/   │                         │ storage-b/   │
        └──────┬───────┘                         └──────┬───────┘
               │                 ▲                       │
               └─────────────────┼───────────────────────┘
                                 ▼
                         ┌──────────────┐
                         │    node-c    │
                         │ ledger-c.json│
                         │ storage-c/   │
                         └──────────────┘
                                 ▲
                                 │ APIs reais
                         ┌───────┴────────┐
                         │ React + Vite UI│
                         └────────────────┘
```

Cada instância FastAPI possui:

- arquivo de ledger independente;
- mempool próprio;
- lista própria de peers;
- pasta off-chain independente;
- validação local de transações e blocos;
- mineração Proof of Work;
- propagação e resolução de divergências;
- capacidade de continuar operando quando outro nó fica offline.

Os volumes `ledger-a`, `ledger-b`, `ledger-c`, `storage-a`, `storage-b` e
`storage-c` são separados no Docker Compose. Nenhuma base é compartilhada.

## Tecnologias e decisões

- **FastAPI:** API HTTP e comunicação entre peers.
- **React, Vite e TypeScript:** interface de operação e apresentação.
- **Blockchain própria:** torna explícitas as etapas de criação, validação,
  propagação e confirmação de blocos.
- **Proof of Work:** dificuldade baixa, com hash iniciado por `000`.
- **Maior cadeia válida:** conflitos são resolvidos por altura e, em empate,
  pelo menor hash da ponta, criando desempate determinístico.
- **Ed25519:** assinatura digital de transações.
- **X25519 + AES-256-GCM:** criptografia híbrida dos laudos.
- **JSON local:** persistência simples e inspecionável em laboratório.

O principal trade-off é privilegiar clareza didática sobre desempenho. A
solução demonstra propriedades fundamentais de um ledger distribuído, mas não
pretende substituir uma blockchain de produção com milhares de validadores.

## Execução com Docker

Pré-requisitos: Docker Desktop com Docker Compose.

```powershell
docker compose up --build
```

No Windows, também é possível iniciar tudo com:

```powershell
.\iniciar.ps1
```

O terminal precisa permanecer apenas até o Docker confirmar que os serviços
foram iniciados. Os containers continuam executando em segundo plano.

Acessos:

- Interface: <http://localhost:5173>
- node-a: <http://localhost:8001/docs>
- node-b: <http://localhost:8002/docs>
- node-c: <http://localhost:8003/docs>

Credenciais didáticas das companhias:

| Companhia | Usuário | Senha |
|---|---|---|
| Gulf Shipping Co. | `gulf` | `Gulf@2026` |
| Atlas Maritime | `atlas` | `Atlas@2026` |
| Orion Logistics | `orion` | `Orion@2026` |

O login emite uma sessão assinada compartilhada pelos três nós. A sessão
define a única carteira autorizada a transferir créditos, solicitar escoltas,
concluir missões e descriptografar laudos. As senhas são apenas para
demonstração acadêmica; uma implantação real usaria armazenamento seguro de
credenciais e autenticação multifator.

Para encerrar sem apagar os ledgers:

```powershell
docker compose down
```

ou:

```powershell
.\parar.ps1
```

Para reiniciar todo o ambiente do zero:

```powershell
docker compose down -v
docker compose up --build
```

## Execução distribuída em vários computadores

O arquivo `docker-compose.yml` continua sendo o modo rápido para executar os
três nós no mesmo computador. Para executar a rede em máquinas distintas, use
`docker-compose.multi-pc.yml`: cada computador executa um nó com ledger e
storage próprios e se comunica com os outros por seus endereços IP da rede
local.

### Topologia de exemplo

| Computador | Endereço IP | Nó | Porta |
|---|---|---|---|
| PC A | `192.168.1.10` | `node-a` | `8000` |
| PC B | `192.168.1.11` | `node-b` | `8000` |
| PC C | `192.168.1.12` | `node-c` | `8000` |

Os computadores precisam estar na mesma rede e conseguir acessar uns aos
outros. Recomenda-se reservar os endereços IP no roteador para evitar que eles
mudem durante a execução.

### Opção 1: iniciar pelo script

Copie o projeto para os três computadores e execute:

No PC A, que também hospedará a interface:

```powershell
.\iniciar-multi-pc.ps1 `
  -NodeId "node-a" `
  -Peers "http://192.168.1.11:8000,http://192.168.1.12:8000" `
  -AuthSecret "uma-chave-compartilhada-forte" `
  -WithFrontend `
  -NodeUrls "http://192.168.1.10:8000,http://192.168.1.11:8000,http://192.168.1.12:8000"
```

No PC B:

```powershell
.\iniciar-multi-pc.ps1 `
  -NodeId "node-b" `
  -Peers "http://192.168.1.10:8000,http://192.168.1.12:8000" `
  -AuthSecret "uma-chave-compartilhada-forte"
```

No PC C:

```powershell
.\iniciar-multi-pc.ps1 `
  -NodeId "node-c" `
  -Peers "http://192.168.1.10:8000,http://192.168.1.11:8000" `
  -AuthSecret "uma-chave-compartilhada-forte"
```

Todos os nós devem usar exatamente o mesmo `AUTH_SECRET`, pois uma sessão
iniciada em um nó precisa ser reconhecida pelos outros. Cada nó deve possuir
um `NODE_ID` diferente.

A interface ficará disponível em:

```text
http://192.168.1.10:5173
```

Ela pode ser aberta por qualquer computador da rede. As URLs passadas em
`NodeUrls` precisam ser endereços alcançáveis pelo navegador; não use
`localhost`, pois ele apontaria para o computador de quem abriu a página.

### Opção 2: iniciar com arquivo de ambiente

Copie `.env.multi-pc.example` para `.env.multi-pc` em cada computador e ajuste
`NODE_ID`, `PEERS` e os IPs:

```powershell
Copy-Item .env.multi-pc.example .env.multi-pc
docker compose --env-file .env.multi-pc -f docker-compose.multi-pc.yml up --build -d
```

No computador que também hospedará a interface, inclua o perfil `frontend`:

```powershell
docker compose --env-file .env.multi-pc -f docker-compose.multi-pc.yml --profile frontend up --build -d
```

Para conferir a comunicação:

```powershell
Invoke-RestMethod http://192.168.1.10:8000/node/network
Invoke-RestMethod http://192.168.1.11:8000/node/network
Invoke-RestMethod http://192.168.1.12:8000/node/network
```

Cada resposta deve mostrar os outros dois peers como `online: true`.

### Firewall do Windows

Em um PowerShell executado como administrador, libere a API em cada
computador:

```powershell
New-NetFirewallRule `
  -DisplayName "Sentinel Ledger API" `
  -Direction Inbound `
  -Protocol TCP `
  -LocalPort 8000 `
  -Action Allow `
  -Profile Private
```

No computador que executa o frontend, libere também:

```powershell
New-NetFirewallRule `
  -DisplayName "Sentinel Ledger Frontend" `
  -Direction Inbound `
  -Protocol TCP `
  -LocalPort 5173 `
  -Action Allow `
  -Profile Private
```

Use somente uma rede confiável marcada como `Privada`. O modo acadêmico usa
HTTP sem TLS e não deve ser exposto diretamente à internet.

Para parar o nó sem apagar seus dados:

```powershell
.\parar-multi-pc.ps1
```

Para apagar também o ledger e o storage persistidos naquele computador:

```powershell
docker compose --env-file .env.multi-pc -f docker-compose.multi-pc.yml down -v
```

## Execução manual

### Backend

Crie um ambiente virtual e instale as dependências:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Abra três terminais. Exemplo para o primeiro nó:

```powershell
$env:NODE_ID="node-a"
$env:PORT="8001"
$env:PEERS="http://localhost:8002,http://localhost:8003"
$env:LEDGER_FILE="../data/ledger-node-a.json"
$env:STORAGE_DIR="../storage/node-a"
python run.py
```

Repita para `node-b`/porta `8002` e `node-c`/porta `8003`, alterando os peers e
os caminhos para que cada nó tenha arquivos próprios.

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

Acesse <http://localhost:5173>.

## Funcionamento do ledger

### Créditos e saldos

O bloco gênese determinístico concede 100 Operational Credits (OC) a cada
companhia:

- Gulf Shipping Co.;
- Atlas Maritime;
- Orion Logistics.

Não existe coluna ou variável definitiva de saldo. Para consultar um saldo, o
nó percorre as transações confirmadas e soma entradas menos saídas. O mempool é
considerado apenas na validação, impedindo que duas transações pendentes gastem
o mesmo valor.

### Assinaturas

Cada companhia possui uma chave Ed25519 determinística para a simulação. O
endereço é derivado da chave pública. O nó confirma:

1. se a chave pública produz o endereço remetente;
2. se a assinatura corresponde ao conteúdo canônico da transação;
3. se o saldo e as regras específicas continuam válidos.

**Em produção, a chave privada nunca deve permanecer no backend.** Assinatura e
descriptografia ocorreriam no cliente, hardware wallet ou serviço de custódia.

### Pagamento e despacho

`ESCORT_PAYMENT` e `DRONE_DISPATCH` entram no mesmo bloco e nesta ordem. Assim,
o despacho só se torna efetivo junto com a confirmação do pagamento. A
ocupação do drone é reconstruída a partir do ledger, e não de uma variável
local definitiva.

### Consenso e forks

Cada bloco contém índice, timestamp, hash anterior, nonce, transações e nó
criador. Um bloco só é aceito se:

- seu hash corresponde exatamente ao conteúdo;
- satisfaz a dificuldade PoW;
- aponta para o hash anterior correto;
- todas as assinaturas são válidas;
- não produz saldo negativo ou duplo gasto;
- não aloca um drone já ocupado.

Ao sincronizar, o nó procura a melhor cadeia válida entre os peers. Cadeias de
mesma altura usam o hash da ponta como desempate determinístico. Uma cópia
local inválida pode ser substituída por uma cópia válida de mesma altura.

## Transparência não significa exposição total dos dados

A blockchain torna pública a existência da missão, o pagamento, horário,
companhia, drone, rota, resultado resumido, hashes, ponteiro do arquivo e
status. Essas informações satisfazem a auditoria do consórcio.

Descrição detalhada, evidências e observações estratégicas ficam em um arquivo
off-chain criptografado. Qualquer participante consegue provar que a missão
existiu e verificar se o arquivo mudou. Somente a companhia dona possui a
chave X25519 capaz de recuperar a chave AES e ler o conteúdo confidencial.

Isso equilibra transparência, auditabilidade e sigilo operacional.

## Armazenamento off-chain e prova on-chain

Ao concluir uma missão:

1. o laudo completo é serializado de forma canônica;
2. `report_hash` é calculado antes da criptografia;
3. uma chave AES-256 aleatória criptografa o laudo com AES-GCM;
4. a chave AES é encapsulada usando X25519 e a chave pública da companhia;
5. o envelope criptografado é salvo e replicado entre os storages dos peers;
6. `encrypted_file_hash` é calculado sobre o arquivo salvo;
7. a blockchain recebe somente metadados públicos, hashes, ponteiro e chave
   encapsulada.

O hash prova que o laudo existia naquele estado. Se o arquivo externo mudar,
`encrypted_file_hash` não corresponde. Se um bloco mudar, seu hash e o
encadeamento deixam de corresponder.

## Conceitos fundamentais do projeto

### Ledger distribuído

O ledger é o registro ordenado de todos os blocos confirmados. Ele funciona
como a fonte da verdade para créditos, pagamentos, despachos e missões.

Cada nó possui uma cópia independente do ledger. Não existe uma API central
responsável por armazenar o estado global. Quando um nó recebe uma nova
transação ou um novo bloco, ele executa suas próprias validações antes de
alterar sua cópia local.

O estado atual é reconstruído a partir do histórico:

- o saldo é calculado somando créditos recebidos e subtraindo créditos gastos;
- a ocupação dos drones é calculada a partir de pagamentos de escolta e
  conclusões de missão;
- o histórico de uma companhia é obtido filtrando as transações relacionadas
  à sua carteira;
- as missões públicas são reconstruídas a partir das transações registradas
  nos blocos.

Essa abordagem evita que uma variável local de saldo ou disponibilidade se
torne uma segunda fonte da verdade.

### Transações

Uma transação representa uma mudança de estado solicitada à rede. Os tipos
utilizados são:

| Tipo | Finalidade |
|---|---|
| `GENESIS_CREDIT` | Distribui os créditos iniciais no bloco gênese |
| `TRANSFER_CREDIT` | Transfere créditos entre companhias |
| `ESCORT_PAYMENT` | Debita o custo de uma escolta |
| `DRONE_DISPATCH` | Registra o despacho associado a um pagamento |
| `MISSION_COMPLETE` | Registra o resultado público da missão |
| `MISSION_REPORT_PROOF` | Registra hashes e o ponteiro do laudo criptografado |

Cada transação comum contém remetente, destinatário, valor, timestamp, payload,
chave pública e assinatura. O identificador da transação impede que o mesmo
registro seja aceito duas vezes.

Antes de ser aceita, uma transação passa por verificações de:

- assinatura digital;
- correspondência entre chave pública e endereço da carteira;
- identificador duplicado;
- saldo disponível;
- débitos já pendentes;
- disponibilidade do drone;
- vínculo entre pagamento, despacho e missão;
- autorização da companhia dona da operação.

### Mempool

O mempool é a lista local de transações válidas que ainda não foram incluídas
em um bloco.

O fluxo de uma transação é:

1. a API recebe a solicitação;
2. o nó valida assinatura e regras de estado;
3. a transação válida entra no mempool local;
4. ela é propagada para os peers;
5. o nó minerador seleciona as transações pendentes;
6. todas são validadas novamente contra o estado confirmado;
7. as transações válidas entram no novo bloco;
8. após a confirmação, elas são removidas do mempool.

O mempool também participa da prevenção de duplo gasto. Ao calcular quanto uma
carteira ainda pode gastar, o nó considera os débitos pendentes. Portanto, duas
requisições concorrentes não podem reservar o mesmo saldo antes da mineração.

Cada nó mantém seu próprio mempool. Ele é uma área temporária de preparação e
não substitui o ledger confirmado.

### Estrutura dos blocos

Cada bloco possui:

- `index`: posição na cadeia;
- `timestamp`: momento de criação;
- `previous_hash`: hash do bloco anterior;
- `hash`: SHA-256 do conteúdo do bloco;
- `nonce`: valor alterado durante o Proof of Work;
- `transactions`: transações confirmadas;
- `node_id`: nó que criou o bloco.

O `previous_hash` forma o encadeamento. Se uma transação de um bloco antigo for
alterada, o hash daquele bloco muda e deixa de corresponder ao
`previous_hash` armazenado no bloco seguinte.

### Bloco gênese

O bloco gênese é o primeiro bloco da cadeia. Ele usa timestamp, transações e
ordenação determinísticos, produzindo o mesmo conteúdo em todos os nós.

Nele são criados 100 OC para cada companhia por meio de transações
`GENESIS_CREDIT`. Novas transações desse tipo são rejeitadas fora do gênese,
impedindo emissão arbitrária de créditos durante a operação.

### Proof of Work

O Proof of Work é o mecanismo utilizado para produzir um bloco válido. O nó
calcula repetidamente o SHA-256 do bloco, incrementando o `nonce`, até que o
hash comece com a quantidade configurada de zeros.

Com dificuldade `3`, por exemplo:

```text
000a21f4c8...
```

O PoW torna a substituição de blocos mais custosa, pois qualquer mudança exige
recalcular o trabalho daquele bloco e dos blocos posteriores. A dificuldade é
baixa neste projeto para manter a criação de blocos rápida no ambiente
acadêmico.

### Mineração e confirmação

Mineração é o processo de transformar transações pendentes em um bloco
confirmado.

O nó minerador:

1. lê o mempool;
2. revalida cada transação na ordem em que será aplicada;
3. descarta transações que deixaram de ser válidas;
4. cria um bloco apontando para o hash atual da cadeia;
5. executa o Proof of Work;
6. persiste o bloco no ledger local;
7. remove as transações confirmadas do mempool;
8. propaga o bloco aos peers.

Um pagamento ou transferência só altera o estado confirmado depois de aparecer
em um bloco aceito.

### Validação da cadeia

Ao verificar uma cadeia, o nó recalcula todo o estado desde o gênese. São
verificados:

- conteúdo e hash de cada bloco;
- dificuldade do Proof of Work;
- encadeamento por `previous_hash`;
- unicidade das transações;
- assinaturas digitais;
- saldos e ausência de duplo gasto;
- disponibilidade dos drones;
- propriedade e sequência das missões;
- existência de pagamento antes do despacho;
- conclusão antes da prova do laudo.

Uma cadeia que falha em qualquer etapa é considerada inválida.

### Consenso e resolução de divergências

Os nós podem divergir temporariamente quando criam blocos concorrentes ou
quando um deles permanece offline.

Para resolver a divergência, o nó consulta as cadeias dos peers e considera
somente candidatas que passam pela validação completa. A cadeia válida de maior
comprimento é escolhida. Em caso de mesma altura, o hash da ponta é usado como
desempate determinístico.

Não existe um nó mestre escolhendo a cadeia. Cada participante executa
localmente a mesma regra de consenso.

### Propagação entre peers

A comunicação entre os nós ocorre por HTTP:

- transações são enviadas para `/receive-transaction`;
- blocos são enviados para `/receive-block`;
- cadeias podem ser consultadas em `/ledger`;
- divergências são tratadas por `/node/resolve-conflicts`;
- arquivos criptografados são replicados por `/storage/replica`.

Receber uma mensagem de outro peer não implica confiança automática. O nó
destinatário valida o conteúdo antes de armazená-lo.

### Prevenção de duplo gasto

O duplo gasto é tratado em três momentos:

1. na entrada da transação, considerando ledger e mempool;
2. novamente durante a seleção das transações para mineração;
3. durante o replay completo ao validar uma cadeia recebida.

Além disso, a alteração do mempool é protegida por uma região crítica local,
impedindo que duas requisições simultâneas sejam aceitas usando o mesmo saldo.

### Estado e concorrência dos drones

A disponibilidade de um drone não é mantida como um campo definitivo.

Um `ESCORT_PAYMENT` torna o drone ocupado e uma `MISSION_COMPLETE` encerra a
ocupação. Ao receber nova solicitação, o nó reconstrói as missões ativas usando
o ledger e o mempool.

`ESCORT_PAYMENT` e `DRONE_DISPATCH` são incluídos no mesmo bloco. O despacho
referencia o identificador do pagamento, garantindo que não exista despacho
confirmado sem pagamento associado.

### Carteiras, login e autorização

Cada companhia possui uma carteira com endereço, chave pública de assinatura e
chave pública de criptografia.

O login cria uma sessão assinada que identifica a companhia ativa. Essa
identidade é utilizada para autorizar transferências, solicitações de escolta,
conclusões de missão e acesso aos detalhes confidenciais.

A autenticação não participa do consenso e não determina saldos. Ela apenas
controla quem pode solicitar operações em nome de uma carteira.

### Persistência

O ledger e o mempool são persistidos em JSON. A gravação ocorre primeiro em um
arquivo temporário, que depois substitui o arquivo principal. Isso reduz o
risco de deixar um arquivo parcialmente escrito caso o processo seja
interrompido durante a persistência.

No Docker, cada nó utiliza volumes próprios para ledger e storage. No modo
multi-PC, cada computador mantém os dados em seus próprios volumes locais.

### Integridade e recuperação

Existem dois níveis de integridade:

- **on-chain:** hashes, `previous_hash`, PoW e assinaturas protegem o ledger;
- **off-chain:** `encrypted_file_hash` protege o arquivo criptografado.

Se a cópia local de um ledger for adulterada, ela falha na validação e pode ser
substituída por uma cadeia válida obtida dos peers. Se um arquivo off-chain for
alterado, seu hash deixa de corresponder à prova registrada na blockchain.

## Endpoints principais

| Grupo | Endpoints |
|---|---|
| Nó | `/node/status`, `/node/peers`, `/node/sync`, `/node/resolve-conflicts` |
| Ledger | `/ledger`, `/blocks`, `/transactions`, `/mine`, `/receive-block` |
| Créditos | `/balances`, `/companies/{id}/balance`, `/credits/transfer` |
| Carteiras | `/wallets`, `/wallets/{id}`, `/wallets/{id}/sign` |
| Escoltas | `/drones`, `/escort/request`, `/drones/{id}/missions` |
| Missões | `/missions`, `/missions/{id}/complete`, `/missions/{id}/decrypt` |
| Auditoria | `/audit/verify-chain`, `/audit/tamper-chain`, `/audit/repair` |
| Demos | `/demo/double-spend`, `/demo/drone-race`, `/demo/compare-nodes` |

A documentação OpenAPI completa está disponível em `/docs` de qualquer nó.

## Testes

```powershell
cd backend
pytest -q
```

Os testes automatizados cobrem:

- gênese determinístico e saldo derivado;
- rejeição de duplo gasto;
- corrida concorrente pelo mesmo drone;
- criptografia e acesso exclusivo da companhia;
- adulteração de bloco e arquivo off-chain.

## Estrutura

```text
backend/
  app/
    crypto.py       assinaturas, hashes e criptografia híbrida
    ledger.py       blockchain, PoW, saldos e validação
    network.py      propagação e resolução de conflitos
    service.py      fluxos de negócio e demonstrações
    storage.py      arquivos off-chain
    main.py         API FastAPI
  tests/
frontend/
  src/
docker-compose.yml
docs/
```

## Limitações didáticas

- peers são configurados estaticamente;
- o consenso usa maior cadeia e não tolerância bizantina avançada;
- as chaves de demonstração são determinísticas;
- a rede HTTP não usa TLS dentro do ambiente local;
- o PoW é intencionalmente fácil para permitir apresentação rápida;
- os arquivos off-chain são replicados entre nós, sem IPFS externo.

Essas escolhas tornam a implementação reproduzível e permitem explicar cada
propriedade técnica sem esconder o funcionamento atrás de uma plataforma
pronta.
