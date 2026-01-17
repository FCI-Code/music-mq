import json
import time
import pika
import requests
from messaging import build_connection, configure_channel_for_consume, declare_queue

QUEUE_NAME = "service.catalog"
BASE_URL = "https://musicbrainz.org/ws/2"
HEADERS = {
    "User-Agent": "MusicMQ/1.0 ( educational_project )"
}

def _format_track(track):
    duration_ms = track.get("length")
    duration_sec = int(duration_ms / 1000) if duration_ms else 0
    
    artist_name = "Unknown"
    if track.get("artist-credit"):
        artist_name = track["artist-credit"][0].get("name", "Unknown")
        
    album_name = "Unknown"
    release_date = "Unknown"
    country = "Unknown"
    
    if track.get("releases"):
        release_info = track["releases"][0]
        album_name = release_info.get("title", "Unknown")
        release_date = release_info.get("date", "Unknown")
        country = release_info.get("country", "Unknown")
        
    genre_list = track.get("genres", [])
    genre = genre_list[0].get("name") if genre_list else "Unknown"

    return {
        "id": track.get("id"),
        "title": track.get("title"),
        "artist": artist_name,
        "album": album_name,
        "release_date": release_date,
        "country": country,
        "duration": duration_sec,
        "genre": genre,
        "thumbnail": None
    }

def search_music(query, limit=10):
    try:
        params = {
            "query": query,
            "fmt": "json",
            "limit": limit
        }
        response = requests.get(f"{BASE_URL}/recording", params=params, headers=HEADERS)
        data = response.json()
        recordings = data.get("recordings", [])
        return [_format_track(t) for t in recordings]
    except Exception:
        return []

def list_by_artist(artist):
    try:
        query = f'artist:"{artist}"'
        params = {
            "query": query,
            "fmt": "json",
            "limit": 10
        }
        response = requests.get(f"{BASE_URL}/recording", params=params, headers=HEADERS)
        data = response.json()
        recordings = data.get("recordings", [])
        return [_format_track(t) for t in recordings]
    except Exception:
        return []

def get_music_details(music_id):
    try:
        params = {
            "inc": "artist-credits+releases+genres",
            "fmt": "json"
        }
        response = requests.get(f"{BASE_URL}/recording/{music_id}", params=params, headers=HEADERS)
        if response.status_code == 200:
            data = response.json()
            return _format_track(data)
        return None
    except Exception:
        return None

def handle_request(ch, method, props, body):
    try:
        payload = json.loads(body.decode())
        action = payload.get("action")
        params = payload.get("params", {})
        
        response = {}
        
        if action == "search":
            query = params.get("query", "")
            limit = params.get("limit", 10)
            result = search_music(query, limit)
            response = {"results": result, "count": len(result)}
            
        elif action == "list_by_artist":
            artist = params.get("artist", "")
            result = list_by_artist(artist)
            response = {"results": result, "count": len(result)}
            
        elif action == "get_details":
            music_id = params.get("music_id")
            result = get_music_details(music_id)
            if result:
                response = {"music": result}
            else:
                response = {"error": "Música não encontrada"}
            
        else:
            response = {"error": f"Ação '{action}' não reconhecida"}
        
    except Exception as e:
        response = {"error": str(e)}
    
    ch.basic_publish(
        exchange="",
        routing_key=props.reply_to,
        properties=pika.BasicProperties(correlation_id=props.correlation_id),
        body=json.dumps(response),
    )
    ch.basic_ack(delivery_tag=method.delivery_tag)

def main():
    conn = build_connection()
    ch = configure_channel_for_consume(conn)
    declare_queue(ch, QUEUE_NAME)
    
    ch.basic_consume(queue=QUEUE_NAME, on_message_callback=handle_request)
    
    print(f"[service_catalog] Aguardando requisições na fila '{QUEUE_NAME}'")
    
    try:
        ch.start_consuming()
    except KeyboardInterrupt:
        pass
    finally:
        conn.close()

if __name__ == "__main__":
    main()
