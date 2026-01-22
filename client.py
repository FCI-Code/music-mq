import argparse
import json
import uuid
import time
import pika
from messaging import build_connection, RPC_GATEWAY_QUEUE


def call_gateway(service: str, action: str, params: dict, timeout: int = 20) -> dict:
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
    print("\nCATALOGO:")
    print("  catalog search <query> [limit]")
    print("  catalog artist <nome>")
    print("  catalog details <music_id>")
    
    print("\nPLAYLISTS:")
    print("  playlist create <user_id> <nome>")
    print("  playlist list <user_id>")
    print("  playlist get <playlist_id>")
    print("  playlist add <playlist_id> <music_ids...>")
    print("  playlist remove <playlist_id> <music_id>")
    print("  playlist update <playlist_id> <nome> [descrição]")
    print("  playlist delete <playlist_id>")
    
    print("\nUSUARIOS:")
    print("  users play <user_id> <music_id>")
    print("  users history <user_id> [limit]")
    print("  users mostplayed <user_id> [limit]")
    print("  users stats <user_id>")
    print("  users recent [limit]")
    print("  users global [limit]")
    
    print("\nOUTROS:")
    print("  help")
    print("  exit")
    print("\n" + "="*70)
    
    while True:
        try:
            cmd = input("\n> ").strip()
            
            if cmd == "exit":
                print("Encerrando...")
                break
            
            if cmd == "help" or cmd == "":
                continue
            
            parts = cmd.split()
            if len(parts) < 2:
                print("Comando inválido. Digite 'help' para ver os comandos disponíveis.")
                continue
            
            service = parts[0]
            action = parts[1]
            params = {}
            
            if service == "catalog":
                if action == "search":
                    if len(parts) < 3:
                        print("Uso: catalog search <query> [limit]")
                        continue
                    
                    query_parts = parts[2:]
                    limit = 10

                    if query_parts and query_parts[-1].isdigit():
                        limit = int(query_parts[-1])
                        query_parts = query_parts[:-1]
                    
                    params = {
                        "query": " ".join(query_parts),
                        "limit": limit
                    }
                    action = "search"
                
                elif action == "artist":
                    if len(parts) < 3:
                        print("Uso: catalog artist <nome>")
                        continue
                    
                    params = {"artist": " ".join(parts[2:])}
                    action = "list_by_artist"
                
                elif action == "details":
                    if len(parts) < 3:
                        print("Uso: catalog details <music_id>")
                        continue
                    
                    params = {"music_id": parts[2]}
                    action = "get_details"
                
                else:
                    print(f"Ação '{action}' não reconhecida para catalog")
                    continue

            elif service == "playlist":
                if action == "create":
                    if len(parts) < 4:
                        print("Uso: playlist create <user_id> <nome da playlist>")
                        continue
                    
                    user_id = parts[2]
                    name = " ".join(parts[3:])
                    
                    params = {
                        "user_id": user_id,
                        "name": name,
                        "description": ""
                    }
                    action = "create"
                
                elif action == "list":
                    if len(parts) < 3:
                        print("Uso: playlist list <user_id>")
                        continue
                    
                    params = {"user_id": parts[2]}
                    action = "list_user_playlists"
                
                elif action == "get":
                    if len(parts) < 3:
                        print("Uso: playlist get <playlist_id>")
                        continue
                    
                    params = {"playlist_id": parts[2]}
                    action = "get"
                
                elif action == "add":
                    if len(parts) < 4:
                        print("Uso: playlist add <playlist_id> <music_id1> [music_id2] ...")
                        continue
                    
                    playlist_id = parts[2]
                    music_ids = parts[3:]
                    
                    params = {
                        "playlist_id": playlist_id,
                        "music_ids": music_ids
                    }
                    action = "add_music"
                
                elif action == "remove":
                    if len(parts) < 4:
                        print("Uso: playlist remove <playlist_id> <music_id>")
                        continue
                    
                    params = {
                        "playlist_id": parts[2],
                        "music_id": parts[3]
                    }
                    action = "remove_music"
                
                elif action == "update":
                    if len(parts) < 4:
                        print("Uso: playlist update <playlist_id> <novo_nome> [nova_descrição]")
                        continue
                    
                    playlist_id = parts[2]
                    name = parts[3]
                    description = " ".join(parts[4:]) if len(parts) > 4 else None
                    
                    params = {
                        "playlist_id": playlist_id,
                        "name": name
                    }
                    
                    if description:
                        params["description"] = description
                    
                    action = "update"
                
                elif action == "delete":
                    if len(parts) < 3:
                        print("Uso: playlist delete <playlist_id>")
                        continue
                    
                    params = {"playlist_id": parts[2]}
                    action = "delete"
                
                else:
                    print(f"Ação '{action}' não reconhecida para playlist")
                    continue

            elif service == "users":
                if action == "play":
                    if len(parts) < 4:
                        print("Uso: users play <user_id> <music_id>")
                        continue
                    
                    params = {
                        "user_id": parts[2],
                        "music_id": parts[3]
                    }
                    action = "play"
                
                elif action == "history":
                    if len(parts) < 3:
                        print("Uso: users history <user_id> [limit]")
                        continue
                    
                    user_id = parts[2]
                    limit = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 50
                    
                    params = {
                        "user_id": user_id,
                        "limit": limit
                    }
                    action = "get_history"
                
                elif action == "mostplayed":
                    if len(parts) < 3:
                        print("Uso: users mostplayed <user_id> [limit]")
                        continue
                    
                    user_id = parts[2]
                    limit = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 10
                    
                    params = {
                        "user_id": user_id,
                        "limit": limit
                    }
                    action = "most_played"
                
                elif action == "stats":
                    if len(parts) < 3:
                        print("Uso: users stats <user_id>")
                        continue
                    
                    params = {"user_id": parts[2]}
                    action = "get_stats"
                
                elif action == "recent":
                    limit = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 20
                    
                    params = {"limit": limit}
                    action = "recent_plays_all"
                
                elif action == "global":
                    limit = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 10
                    
                    params = {"limit": limit}
                    action = "global_most_played"
                
                else:
                    print(f"Ação '{action}' não reconhecida para users")
                    continue
            
            else:
                print(f"Serviço '{service}' não reconhecido. Use: catalog, playlist ou users")
                continue

            print(f"Processando {service}.{action}...")
            result = call_gateway(service, action, params)

            print("\n" + "="*70)
            print("RESPOSTA:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            print("="*70)
            
        except KeyboardInterrupt:
            print("\n\nEncerrando...")
            break
        except Exception as e:
            print(f"\nErro: {e}")
            import traceback
            traceback.print_exc()


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