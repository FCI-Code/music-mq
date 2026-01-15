import json
import time
import pika
from messaging import build_connection, configure_channel_for_consume, declare_queue

QUEUE_NAME = "service.catalog"

MUSIC_DATABASE = {
    "m001": {
        "id": "m001",
        "title": "Bohemian Rhapsody",
        "artist": "Queen",
        "album": "A Night at the Opera",
        "duration": 354,
        "genre": "rock"
    },
    "m002": {
        "id": "m002",
        "title": "We Will Rock You",
        "artist": "Queen",
        "album": "News of the World",
        "duration": 122,
        "genre": "rock"
    },
    "m003": {
        "id": "m003",
        "title": "Hotel California",
        "artist": "Eagles",
        "album": "Hotel California",
        "duration": 391,
        "genre": "rock"
    },
    "m004": {
        "id": "m004",
        "title": "Imagine",
        "artist": "John Lennon",
        "album": "Imagine",
        "duration": 183,
        "genre": "pop"
    },
    "m005": {
        "id": "m005",
        "title": "Billie Jean",
        "artist": "Michael Jackson",
        "album": "Thriller",
        "duration": 294,
        "genre": "pop"
    },
    "m006": {
        "id": "m006",
        "title": "Smells Like Teen Spirit",
        "artist": "Nirvana",
        "album": "Nevermind",
        "duration": 301,
        "genre": "rock"
    }
}


def search_music(query: str, limit: int = 10):
    query_lower = query.lower()
    results = []
    
    for music in MUSIC_DATABASE.values():
        if (query_lower in music["title"].lower() or
            query_lower in music["artist"].lower() or
            query_lower in music["album"].lower() or
            query_lower in music["genre"].lower()):
            results.append(music)
        
        if len(results) >= limit:
            break
    
    return results


def list_by_artist(artist: str):
    artist_lower = artist.lower()
    return [m for m in MUSIC_DATABASE.values() 
            if artist_lower in m["artist"].lower()]


def list_by_genre(genre: str):
    genre_lower = genre.lower()
    return [m for m in MUSIC_DATABASE.values() 
            if genre_lower in m["genre"].lower()]


def get_music_details(music_id: str):
    return MUSIC_DATABASE.get(music_id)


def list_all_music(limit: int = 20):
    return list(MUSIC_DATABASE.values())[:limit]


def handle_request(ch, method, props, body):
    try:
        payload = json.loads(body.decode())
        action = payload.get("action")
        params = payload.get("params", {})
        
        print(f"[service_catalog] Processando ação '{action}' com params={params}")
        
        time.sleep(0.3)
        
        if action == "search":
            query = params.get("query", "")
            limit = params.get("limit", 10)
            result = search_music(query, limit)
            response = {"results": result, "count": len(result)}
            
        elif action == "list_by_artist":
            artist = params.get("artist", "")
            result = list_by_artist(artist)
            response = {"results": result, "count": len(result)}
            
        elif action == "list_by_genre":
            genre = params.get("genre", "")
            result = list_by_genre(genre)
            response = {"results": result, "count": len(result)}
            
        elif action == "get_details":
            music_id = params.get("music_id")
            result = get_music_details(music_id)
            if result:
                response = {"music": result}
            else:
                response = {"error": "Música não encontrada"}
                
        elif action == "list_all":
            limit = params.get("limit", 20)
            result = list_all_music(limit)
            response = {"results": result, "count": len(result)}
            
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
    print(f"[service_catalog] Resposta enviada para '{action}'")


def main():
    conn = build_connection()
    ch = configure_channel_for_consume(conn)
    declare_queue(ch, QUEUE_NAME)
    
    ch.basic_consume(queue=QUEUE_NAME, on_message_callback=handle_request)
    
    print(f"[service_catalog] Aguardando requisições na fila '{QUEUE_NAME}'")
    print(f"[service_catalog] Catálogo contém {len(MUSIC_DATABASE)} músicas")
    
    try:
        ch.start_consuming()
    except KeyboardInterrupt:
        print("\n[service_catalog] Encerrando...")
    finally:
        conn.close()


if __name__ == "__main__":
    main()