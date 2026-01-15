import argparse
import json
import uuid
import time
import pika
from messaging import build_connection, RPC_GATEWAY_QUEUE


def call_gateway(service: str, action: str, params: dict, timeout: int = 20) -> dict:
    """
    Envia uma requisição para o gateway e aguarda resposta.
    
    Args:
        service: Nome do serviço (catalog, playlist, users)
        action: Ação a ser executada (search, create, play, etc)
        params: Parâmetros da requisição
        timeout: Tempo máximo de espera em segundos
    
    Returns:
        Resposta do serviço em formato dict
    """
    conn = build_connection()
    ch = conn.channel()
    
    result = ch.queue_declare(queue='', exclusive=True)
    callback_queue = result.method.queue

    corr_id = str(uuid.uuid4())
    response_container = {"response": None}

    def on_response(_ch, _method, props, body):
        if props.correlation_id == corr_id:
            response_container["response"] = body

    ch.basic_consume(queue=callback_queue, on_message_callback=on_response, auto_ack=True)

    request_body = json.dumps({
        "service": service,
        "action": action,
        "params": params
    })

    ch.basic_publish(
        exchange="",
        routing_key=RPC_GATEWAY_QUEUE,
        properties=pika.BasicProperties(
            reply_to=callback_queue,
            correlation_id=corr_id
        ),
        body=request_body,
    )

    print(f"[client] Enviando: {service}.{action} com params={params}")

    waited = 0
    while response_container["response"] is None and waited < timeout:
        conn.process_data_events(time_limit=1)
        waited += 1

    conn.close()
    
    if response_container["response"] is None:
        return {"error": "timeout esperando resposta"}
    
    try:
        return json.loads(response_container["response"].decode())
    except Exception:
        return {"raw": response_container["response"].decode()}


def demo_catalog():
    print("\n=== DEMONSTRAÇÃO: CATÁLOGO MUSICAL ===")

    result = call_gateway("catalog", "search", {"query": "rock", "limit": 5})
    print(f"Busca por 'rock': {result}")
    time.sleep(0.5)

    result = call_gateway("catalog", "list_by_artist", {"artist": "Queen"})
    print(f"Músicas de Queen: {result}")
    time.sleep(0.5)

    result = call_gateway("catalog", "get_details", {"music_id": "m001"})
    print(f"Detalhes da música: {result}")


def demo_playlist():
    print("\n=== DEMONSTRAÇÃO: PLAYLISTS ===")
    
    result = call_gateway("playlist", "create", {
        "user_id": "user123",
        "name": "Minhas Favoritas",
        "description": "As melhores músicas"
    })
    print(f"Playlist criada: {result}")
    playlist_id = result.get("playlist_id")
    time.sleep(0.5)
    
    result = call_gateway("playlist", "add_music", {
        "playlist_id": playlist_id,
        "music_ids": ["m001", "m002", "m003"]
    })
    print(f"Músicas adicionadas: {result}")
    time.sleep(0.5)
    
    result = call_gateway("playlist", "list_user_playlists", {"user_id": "user123"})
    print(f"Playlists do usuário: {result}")


def demo_users():
    print("\n=== DEMONSTRAÇÃO: USUÁRIOS E HISTÓRICO ===")
    
    result = call_gateway("users", "play", {
        "user_id": "user123",
        "music_id": "m001"
    })
    print(f"Reprodução registrada: {result}")
    time.sleep(0.5)
    
    result = call_gateway("users", "get_history", {
        "user_id": "user123",
        "limit": 10
    })
    print(f"Histórico: {result}")
    time.sleep(0.5)
    
    result = call_gateway("users", "most_played", {
        "user_id": "user123",
        "limit": 5
    })
    print(f"Mais tocadas: {result}")


def interactive_mode():
    print("\n=== MODO INTERATIVO ===")
    print("Comandos disponíveis:")
    print("  catalog search <query>")
    print("  playlist create <user_id> <name>")
    print("  users play <user_id> <music_id>")
    print("  users history <user_id>")
    print("  exit - sair")
    
    while True:
        try:
            cmd = input("\n> ").strip()
            if cmd == "exit":
                break
            
            parts = cmd.split()
            if len(parts) < 2:
                print("Comando inválido")
                continue
            
            service = parts[0]
            action = parts[1]
            params = {}
            
            if service == "catalog" and action == "search":
                params = {"query": " ".join(parts[2:]) if len(parts) > 2 else ""}
            elif service == "playlist" and action == "create":
                params = {
                    "user_id": parts[2] if len(parts) > 2 else "user123",
                    "name": " ".join(parts[3:]) if len(parts) > 3 else "Nova Playlist"
                }
            elif service == "users" and action == "play":
                params = {
                    "user_id": parts[2] if len(parts) > 2 else "user123",
                    "music_id": parts[3] if len(parts) > 3 else "m001"
                }
            elif service == "users" and action == "history":
                params = {"user_id": parts[2] if len(parts) > 2 else "user123"}
            
            result = call_gateway(service, action, params)
            print(f"Resposta: {json.dumps(result, indent=2)}")
            
        except KeyboardInterrupt:
            print("\nSaindo...")
            break
        except Exception as e:
            print(f"Erro: {e}")


def main():
    parser = argparse.ArgumentParser(description="Cliente do Sistema de Streaming Musical")
    parser.add_argument("--demo", choices=["catalog", "playlist", "users", "all"], 
                       help="Executar demonstração de um serviço")
    parser.add_argument("--interactive", "-i", action="store_true",
                       help="Modo interativo")
    parser.add_argument("--service", "-s", type=str,
                       help="Nome do serviço (catalog, playlist, users)")
    parser.add_argument("--action", "-a", type=str,
                       help="Ação a executar")
    parser.add_argument("--params", "-p", type=str,
                       help="Parâmetros em JSON")
    
    args = parser.parse_args()
    
    if args.demo:
        if args.demo == "catalog" or args.demo == "all":
            demo_catalog()
        if args.demo == "playlist" or args.demo == "all":
            demo_playlist()
        if args.demo == "users" or args.demo == "all":
            demo_users()
    elif args.interactive:
        interactive_mode()
    elif args.service and args.action:
        params = json.loads(args.params) if args.params else {}
        result = call_gateway(args.service, args.action, params)
        print(json.dumps(result, indent=2))
    else:
        parser.print_help()
        print("\nExemplos de uso:")
        print("  python client.py --demo all")
        print("  python client.py --interactive")
        print("  python client.py -s catalog -a search -p '{\"query\": \"rock\"}'")


if __name__ == "__main__":
    main()