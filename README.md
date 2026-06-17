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
- **Blockchain própria:** permite demonstrar cada etapa do consenso e da
  validação durante a arguição.
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

Para reiniciar toda a demonstração do zero:

```powershell
docker compose down -v
docker compose up --build
```

## Execução distribuída em vários computadores

O arquivo `docker-compose.yml` continua sendo o modo rápido para executar os
três nós no mesmo computador. Para demonstrar distribuição física, use
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
mudem durante a demonstração.

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

## Roteiro de demonstração do barema

Antes de apresentar, abra a tela **Demonstrações**. Ela executa cenários reais
e mostra o JSON retornado pelas APIs.

### 1. Arquitetura descentralizada

1. Mostre no dashboard três nós com alturas e peers.
2. Execute uma transferência e selecione outro nó para consultar o saldo.
3. Derrube um nó:

   ```powershell
   docker compose stop node-c
   ```

4. Atualize a interface e execute uma transação em `node-a`.
5. Suba novamente:

   ```powershell
   docker compose start node-c
   ```

6. Use **Sincronizar com peers** no nó recuperado.

### 2. Comunicação e consenso

Faça uma transferência e mostre a mesma transação no explorer de outro nó.
Abra um bloco para exibir `previous_hash`, PoW, nonce, criador e transações.

### 3. Gestão de ativos

Na tela **Créditos operacionais**, transfira OC entre duas companhias. Mostre
que o saldo muda em outro nó e que a origem permanece rastreável desde o bloco
gênese.

### 4. Duplo gasto

Execute **Teste: Duplo gasto**. Duas transações usam simultaneamente todo o
mesmo saldo. O lock do ledger e a consideração do mempool garantem uma aceita
e uma rejeitada com:

```text
Saldo insuficiente ou tentativa de duplo gasto detectada.
```

### 5. Concorrência pelo mesmo drone

Execute **Mesmo drone, duas companhias**. As duas chamadas concorrem pelo
`DRONE-03`; apenas uma entra no ledger. A outra recebe `Drone indisponível`.

### 6. Pagamento de escolta

Na tela **Solicitar escolta**, selecione carteira, drone e rota. Mostre no
bloco confirmado `ESCORT_PAYMENT` seguido de `DRONE_DISPATCH`.

Para saldo insuficiente, transfira ou gaste o saldo e repita a solicitação.

### 7. Laudo e confidencialidade

1. Conclua uma missão na tela **Missões e laudos**.
2. Mostre o `MISSION_REPORT_PROOF` no explorer.
3. Use a carteira dona para descriptografar.
4. Troque para outra carteira e repita: o acesso será negado, embora os hashes
   públicos continuem visíveis.

### 8. Adulteração

1. Execute **Adulterar blockchain** no nó selecionado.
2. Execute **Verificar cadeia** e mostre o bloco inconsistente.
3. Execute **Sincronizar com peers** para recuperar a cópia válida.
4. Execute **Adulterar arquivo off-chain**.
5. Na missão, use **Verificar arquivo** e mostre a divergência de hashes.

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
