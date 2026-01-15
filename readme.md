# Sistema de Streaming Musical Distribuído

Projeto Final - Sistemas Distribuídos 2025-2

## Descrição

Sistema distribuído inspirado em plataformas de streaming de música (Spotify, Deezer, Amazon Music), implementado em Python usando RabbitMQ para comunicação entre processos. O sistema simula funcionalidades básicas como consulta de músicas, gerenciamento de playlists e histórico de reprodução.

## Arquitetura

### Visão Geral

```
Cliente → Gateway (Middleware) → Serviços Distribuídos
                                  ├─ Catálogo Musical
                                  ├─ Playlists
                                  └─ Usuários/Histórico
```

### Componentes

#### a) Cliente (`client.py`)

Simula ações de usuários em uma plataforma de streaming:

- Busca de músicas
- Criação e gerenciamento de playlists
- Reprodução de músicas (registro no histórico)
- Consulta de histórico de reprodução

#### b) Gateway (`gateway.py`)

Middleware que atua como ponto único de entrada:

- Recebe requisições dos clientes
- Encaminha para o serviço apropriado
- Coordena a comunicação entre cliente e serviços

#### c) Serviços Distribuídos

Cada serviço representa uma funcionalidade específica do sistema:

**Catálogo Musical (`service_catalog.py`)**

- Busca de músicas por título, artista ou gênero
- Listagem de músicas por artista
- Detalhes completos de músicas

**Playlists (`service_playlist.py`)**

- Criação de playlists
- Adição/remoção de músicas
- Listagem de playlists por usuário

**Usuários e Histórico (`service_users.py`)**

- Registro de reproduções
- Histórico de reprodução por usuário
- Músicas mais tocadas (por usuário e global)
- Estatísticas de uso

#### d) Broker de Mensagens (`messaging.py`)

RabbitMQ, responsável pela comunicação indireta e assíncrona entre os componentes.

## Comunicação

O sistema implementa três tipos de comunicação:

1. **Comunicação Assíncrona**: Cliente não bloqueia aguardando resposta
2. **Invocação Remota (RPC)**: Padrão request-reply via RabbitMQ
3. **Comunicação Indireta**: Via broker de mensagens (RabbitMQ)

### Fluxo de Comunicação

```
1. Cliente envia requisição para fila rpc_gateway
2. Gateway recebe e identifica o serviço alvo
3. Gateway cria fila temporária para resposta
4. Gateway encaminha para fila service.{nome_servico}
5. Serviço processa e responde na fila temporária
6. Gateway repassa resposta para callback_queue do cliente
7. Cliente recebe resposta via correlation_id
```

## Estrutura de Arquivos

```
projeto-streaming/
├── client.py              # Cliente do sistema
├── gateway.py             # Gateway/Middleware
├── messaging.py           # Utilitários RabbitMQ
├── service_catalog.py     # Serviço de catálogo
├── service_playlist.py    # Serviço de playlists
├── service_users.py       # Serviço de usuários
├── requirements.txt       # Dependências Python
└── README.md             # Esta documentação
```

## Dependências

- Python 3.10+
- RabbitMQ Server
- Biblioteca `pika` (cliente Python para RabbitMQ)

## Instruções de Execução

### 1. Instalar RabbitMQ

**Ubuntu/Debian:**

```bash
sudo apt-get update
sudo apt-get install rabbitmq-server
sudo systemctl start rabbitmq-server
sudo systemctl enable rabbitmq-server
```

**MacOS:**

```bash
brew install rabbitmq
brew services start rabbitmq
```

**Windows:**
Baixe e instale de: https://www.rabbitmq.com/download.html

**Docker (alternativa):**

```bash
docker run -d --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3-management
```

### 2. Instalar Dependências Python

```bash
# Criar ambiente virtual (recomendado)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows

# Instalar dependências
pip install -r requirements.txt
```

### 3. Executar os Componentes

**Terminal 1 - Gateway:**

```bash
python gateway.py
```

**Terminal 2 - Serviço de Catálogo:**

```bash
python service_catalog.py
```

**Terminal 3 - Serviço de Playlists:**

```bash
python service_playlist.py
```

**Terminal 4 - Serviço de Usuários:**

```bash
python service_users.py
```

**Terminal 5 - Cliente:**

```bash
# Demonstração completa
python client.py --demo all

# Demonstração específica
python client.py --demo catalog
python client.py --demo playlist
python client.py --demo users

# Modo interativo
python client.py --interactive

# Comando específico
python client.py -s catalog -a search -p '{"query": "rock"}'
```

## Exemplos de Uso

### Buscar Músicas

```bash
python client.py -s catalog -a search -p '{"query": "rock", "limit": 5}'
```

### Criar Playlist

```bash
python client.py -s playlist -a create -p '{"user_id": "user123", "name": "Minhas Favoritas"}'
```

### Reproduzir Música

```bash
python client.py -s users -a play -p '{"user_id": "user123", "music_id": "m001"}'
```

### Ver Histórico

```bash
python client.py -s users -a get_history -p '{"user_id": "user123", "limit": 10}'
```

## Fluxo do Sistema

### Exemplo: Buscar Músicas

1. Cliente envia: `{"service": "catalog", "action": "search", "params": {"query": "rock"}}`
2. Gateway recebe na fila `rpc_gateway`
3. Gateway encaminha para `service.catalog`
4. Serviço Catalog processa busca no banco de dados simulado
5. Serviço responde com lista de músicas
6. Gateway repassa resposta ao cliente
7. Cliente exibe resultados

### Exemplo: Criar Playlist e Adicionar Músicas

1. Cliente cria playlist via serviço `playlist`
2. Recebe `playlist_id` na resposta
3. Cliente adiciona músicas usando o `playlist_id`
4. Serviço atualiza banco de dados da playlist
5. Retorna playlist atualizada

## Conceitos de Sistemas Distribuídos Aplicados

### 1. Comunicação Indireta

- Uso de RabbitMQ como broker de mensagens
- Desacoplamento entre cliente e serviços

### 2. RPC (Remote Procedure Call)

- Pattern request-reply implementado
- Uso de `correlation_id` para matching de respostas
- Filas exclusivas temporárias para callbacks

### 3. Middleware

- Gateway atua como intermediário
- Centraliza lógica de roteamento
- Facilita evolução do sistema

### 4. Serviços Distribuídos

- Cada serviço em processo separado
- Especialização por domínio (catálogo, playlist, usuários)
- Escalabilidade horizontal possível

### 5. Comunicação Assíncrona

- Cliente não bloqueia durante processamento
- Uso de threads para paralelização
- Timeouts para evitar espera infinita

## Características Técnicas

- **Linguagem**: Python 3.10+
- **Broker**: RabbitMQ
- **Pattern**: RPC sobre Message Queue
- **Concorrência**: Threading para requests paralelas
- **Persistência**: Em memória (simulado)
- **Timeout**: 15s no gateway, 20s no cliente

## Possíveis Melhorias Futuras

- Persistência real (PostgreSQL, MongoDB)
- Autenticação e autorização
- Cache distribuído (Redis)
- Monitoramento e logs centralizados
- Load balancing de serviços
- Service discovery
- Circuit breaker pattern
- Implementação de filas de trabalho assíncronas

## Critérios de Avaliação Atendidos

✅ Desenvolvido em dupla  
✅ Hospedado em repositório Git com README  
✅ Implementado em Python com RabbitMQ  
✅ Arquitetura baseada em serviços distribuídos  
✅ Gateway como middleware único  
✅ Comunicação assíncrona demonstrada  
✅ Invocação remota (RPC) implementada  
✅ Comunicação indireta via broker  
✅ Módulos e arquivos organizados  
✅ Uso consciente dos conceitos de Sistemas Distribuídos

## Autores

[Seu Nome]  
[Nome do Colega]

Universidade Federal do Ceará  
Sistemas Distribuídos - 2025-2

## Licença

Este projeto foi desenvolvido para fins educacionais.
