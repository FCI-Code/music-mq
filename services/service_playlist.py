import json
import time
import uuid
from datetime import datetime
import pika
from messaging import build_connection, configure_channel_for_consume, declare_queue

QUEUE_NAME = "service.playlist"

PLAYLISTS_DATABASE = {}


def create_playlist(user_id: str, name: str, description: str = ""):
    playlist_id = f"pl_{uuid.uuid4().hex[:8]}"
    
    playlist = {
        "id": playlist_id,
        "user_id": user_id,
        "name": name,
        "description": description,
        "music_ids": [],
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    PLAYLISTS_DATABASE[playlist_id] = playlist
    return playlist


def get_playlist(playlist_id: str):
    return PLAYLISTS_DATABASE.get(playlist_id)


def list_user_playlists(user_id: str):
    return [pl for pl in PLAYLISTS_DATABASE.values() 
            if pl["user_id"] == user_id]


def add_music_to_playlist(playlist_id: str, music_ids: list):
    playlist = PLAYLISTS_DATABASE.get(playlist_id)
    
    if not playlist:
        return {"error": "Playlist não encontrada"}
    
    # Evita duplicatas
    for music_id in music_ids:
        if music_id not in playlist["music_ids"]:
            playlist["music_ids"].append(music_id)
    
    playlist["updated_at"] = datetime.now().isoformat()
    return playlist


def remove_music_from_playlist(playlist_id: str, music_id: str):
    playlist = PLAYLISTS_DATABASE.get(playlist_id)
    
    if not playlist:
        return {"error": "Playlist não encontrada"}
    
    if music_id in playlist["music_ids"]:
        playlist["music_ids"].remove(music_id)
        playlist["updated_at"] = datetime.now().isoformat()
    
    return playlist


def delete_playlist(playlist_id: str):
    if playlist_id in PLAYLISTS_DATABASE:
        del PLAYLISTS_DATABASE[playlist_id]
        return {"success": True, "message": "Playlist deletada"}
    return {"error": "Playlist não encontrada"}


def update_playlist(playlist_id: str, name: str = None, description: str = None):
    playlist = PLAYLISTS_DATABASE.get(playlist_id)
    
    if not playlist:
        return {"error": "Playlist não encontrada"}
    
    if name:
        playlist["name"] = name
    if description is not None:
        playlist["description"] = description
    
    playlist["updated_at"] = datetime.now().isoformat()
    return playlist


def handle_request(ch, method, props, body):
    try:
        payload = json.loads(body.decode())
        action = payload.get("action")
        params = payload.get("params", {})
        
        print(f"[service_playlist] Processando ação '{action}' com params={params}")
        
        time.sleep(0.2)
        
        if action == "create":
            user_id = params.get("user_id")
            name = params.get("name")
            description = params.get("description", "")
            
            if not user_id or not name:
                response = {"error": "user_id e name são obrigatórios"}
            else:
                result = create_playlist(user_id, name, description)
                response = {"playlist": result, "playlist_id": result["id"]}
                
        elif action == "get":
            playlist_id = params.get("playlist_id")
            result = get_playlist(playlist_id)
            
            if result:
                response = {"playlist": result}
            else:
                response = {"error": "Playlist não encontrada"}
                
        elif action == "list_user_playlists":
            user_id = params.get("user_id")
            result = list_user_playlists(user_id)
            response = {"playlists": result, "count": len(result)}
            
        elif action == "add_music":
            playlist_id = params.get("playlist_id")
            music_ids = params.get("music_ids", [])
            
            if isinstance(music_ids, str):
                music_ids = [music_ids]
            
            result = add_music_to_playlist(playlist_id, music_ids)
            response = {"playlist": result}
            
        elif action == "remove_music":
            playlist_id = params.get("playlist_id")
            music_id = params.get("music_id")
            result = remove_music_from_playlist(playlist_id, music_id)
            response = {"playlist": result}
            
        elif action == "delete":
            playlist_id = params.get("playlist_id")
            result = delete_playlist(playlist_id)
            response = result
            
        elif action == "update":
            playlist_id = params.get("playlist_id")
            name = params.get("name")
            description = params.get("description")
            result = update_playlist(playlist_id, name, description)
            response = {"playlist": result}
            
        else:
            response = {"error": f"Ação '{action}' não reconhecida"}
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        response = {"error": str(e)}
    
    ch.basic_publish(
        exchange="",
        routing_key=props.reply_to,
        properties=pika.BasicProperties(correlation_id=props.correlation_id),
        body=json.dumps(response),
    )
    ch.basic_ack(delivery_tag=method.delivery_tag)
    print(f"[service_playlist] Resposta enviada para '{action}'")


def main():
    conn = build_connection()
    ch = configure_channel_for_consume(conn)
    declare_queue(ch, QUEUE_NAME)
    
    ch.basic_consume(queue=QUEUE_NAME, on_message_callback=handle_request)
    
    print(f"[service_playlist] Aguardando requisições na fila '{QUEUE_NAME}'")
    
    try:
        ch.start_consuming()
    except KeyboardInterrupt:
        print("\n[service_playlist] Encerrando...")
    finally:
        conn.close()


if __name__ == "__main__":
    main()