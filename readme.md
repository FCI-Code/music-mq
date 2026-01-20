# Sistema de Streaming Musical Distribuído

Projeto Final - Sistemas Distribuídos 2025-2

## Descrição

Sistema distribuído inspirado em plataformas de streaming de música (Spotify, Deezer, Amazon Music), implementado em Python usando RabbitMQ para comunicação entre processos. O sistema simula funcionalidades básicas como consulta de músicas (integrado com **MusicBrainz API**), gerenciamento de playlists e histórico de reprodução.

## Arquitetura

### Visão Geral

```
Cliente → Gateway (Middleware) → Serviços Distribuídos
                                  ├─ Catálogo Musical (MusicBrainz)
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

#### c) Serviços Distribuídos (`services/`)

Cada serviço representa uma funcionalidade específica do sistema:

**Catálogo Musical (`services/service_catalog.py`)**

- Integração com **MusicBrainz API** para dados reais
- Busca de músicas por título, artista
- Listagem de músicas por artista
- Detalhes completos de músicas

**Playlists (`services/service_playlist.py`)**

- Criação de playlists
- Adição/remoção de músicas
- Listagem de playlists por usuário

**Usuários e Histórico (`services/service_users.py`)**

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

## Estrutura de Arquivos

```
projeto-streaming/
├── client.py              # Cliente do sistema
├── gateway.py             # Gateway/Middleware
├── messaging.py           # Utilitários RabbitMQ
├── requirements.txt       # Dependências Python
├── README.md             # Esta documentação
└── services/              # Microsserviços
    ├── service_catalog.py     # Serviço de catálogo
    ├── service_playlist.py    # Serviço de playlists
    └── service_users.py       # Serviço de usuários
```

## Dependências

- Python 3.10+
- RabbitMQ Server
- Biblioteca `pika` (cliente Python para RabbitMQ)
- Biblioteca `requests` (para API MusicBrainz)

## Instruções de Execução

### 1. Instalar RabbitMQ

**Ubuntu/Debian:**

```bash
sudo apt-get update
sudo apt-get install rabbitmq-server
sudo systemctl start rabbitmq-server
sudo systemctl enable rabbitmq-server
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

Recomendamos abrir 5 terminais diferentes (ou abas).

**Terminal 1 - Gateway:**

```bash
python gateway.py
```

**Terminal 2 - Serviço de Catálogo:**

```bash
python -m services.service_catalog
```

**Terminal 3 - Serviço de Playlists:**

```bash
python -m services.service_playlist
```

**Terminal 4 - Serviço de Usuários:**

```bash
python -m services.service_users
```

**Terminal 5 - Cliente:**

```bash
python client.py --interactive
```

## Exemplos de Saídas

### 1. Busca de Músicas

**Saída (JSON):**

```json
{
  "results": [
    {
      "id": "713a886f-5b48-4386-a24a-7142478f7e21",
      "title": "Bohemian Rhapsody",
      "artist": "Queen",
      "album": "A Night at the Opera",
      "duration": 354,
      "genre": "Rock",
      "thumbnail": null
    }
  ],
  "count": 1
}
```

### 2. Criação de Playlist

**Saída (JSON):**

```json
{
  "playlist_id": "pl_8f3d2a1b",
  "status": "created",
  "name": "Rock Clássico"
}
```

### 3. Adicionar Música à Playlist

**Saída (JSON):**

```json
{
  "status": "success",
  "message": "Music added to playlist",
  "playlist_size": 1
}
```

### 4. Consultar Histórico de Usuário

**Saída (JSON):**

```json
{
  "user_id": "user123",
  "history": [
    {
      "music_id": "713a...",
      "title": "Bohemian Rhapsody",
      "artist": "Queen",
      "timestamp": "2023-10-27T10:30:00"
    }
  ],
  "count": 1
}
```
