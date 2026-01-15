"""
Serviço de Usuários e Histórico de Reprodução
Responsável por: registrar reproduções, histórico, músicas mais tocadas.
"""
import json
import time
from datetime import datetime
from collections import Counter
import pika
from messaging import build_connection, configure_channel_for_consume, declare_queue

QUEUE_NAME = "service.users"

# Base de dados simulada de usuários e histórico
USERS_DATABASE = {}
PLAY_HISTORY = []  # Lista de reproduções


def register_play(user_id: str, music_id: str):
    """Registra uma reprodução de música"""
    play_record = {
        "user_id": user_id,
        "music_id": music_id,
        "played_at": datetime.now().isoformat()
    }
    
    PLAY_HISTORY.append(play_record)
    
    # Inicializa usuário se não existir
    if user_id not in USERS_DATABASE:
        USERS_DATABASE[user_id] = {
            "user_id": user_id,
            "total_plays": 0,
            "created_at": datetime.now().isoformat()
        }
    
    USERS_DATABASE[user_id]["total_plays"] += 1
    
    return play_record


def get_user_history(user_id: str, limit: int = 50):
    """Retorna histórico de reprodução de um usuário"""
    user_history = [
        record for record in PLAY_HISTORY
        if record["user_id"] == user_id
    ]
    
    # Ordena por mais recente
    user_history.sort(key=lambda x: x["played_at"], reverse=True)
    
    return user_history[:limit]


def get_most_played(user_id: str, limit: int = 10):
    """Retorna as músicas mais tocadas por um usuário"""
    user_history = [
        record for record in PLAY_HISTORY
        if record["user_id"] == user_id
    ]
    
    # Conta as músicas
    music_counter = Counter(record["music_id"] for record in user_history)
    most_common = music_counter.most_common(limit)
    
    return [
        {"music_id": music_id, "play_count": count}
        for music_id, count in most_common
    ]


def get_user_stats(user_id: str):
    """Retorna estatísticas de um usuário"""
    user = USERS_DATABASE.get(user_id)
    
    if not user:
        return {"error": "Usuário não encontrado"}
    
    user_plays = [r for r in PLAY_HISTORY if r["user_id"] == user_id]
    unique_songs = len(set(r["music_id"] for r in user_plays))
    
    stats = {
        "user_id": user_id,
        "total_plays": user["total_plays"],
        "unique_songs_played": unique_songs,
        "member_since": user.get("created_at")
    }
    
    return stats


def get_recent_plays_all(limit: int = 20):
    """Retorna reproduções recentes de todos os usuários"""
    recent = PLAY_HISTORY[-limit:] if len(PLAY_HISTORY) > limit else PLAY_HISTORY
    recent.reverse()
    return recent


def get_global_most_played(limit: int = 10):
    """Retorna as músicas mais tocadas globalmente"""
    music_counter = Counter(record["music_id"] for record in PLAY_HISTORY)
    most_common = music_counter.most_common(limit)
    
    return [
        {"music_id": music_id, "play_count": count}
        for music_id, count in most_common
    ]


def handle_request(ch, method, props, body):
    """Processa requisições do gateway"""
    try:
        payload = json.loads(body.decode())
        action = payload.get("action")
        params = payload.get("params", {})
        
        print(f"[service_users] Processando ação '{action}' com params={params}")
        
        # Simula processamento
        time.sleep(0.15)
        
        # Despacha para a função apropriada
        if action == "play":
            user_id = params.get("user_id")
            music_id = params.get("music_id")
            
            if not user_id or not music_id:
                response = {"error": "user_id e music_id são obrigatórios"}
            else:
                result = register_play(user_id, music_id)
                response = {"play_record": result, "success": True}
                
        elif action == "get_history":
            user_id = params.get("user_id")
            limit = params.get("limit", 50)
            result = get_user_history(user_id, limit)
            response = {"history": result, "count": len(result)}
            
        elif action == "most_played":
            user_id = params.get("user_id")
            limit = params.get("limit", 10)
            result = get_most_played(user_id, limit)
            response = {"most_played": result, "count": len(result)}
            
        elif action == "get_stats":
            user_id = params.get("user_id")
            result = get_user_stats(user_id)
            response = {"stats": result}
            
        elif action == "recent_plays_all":
            limit = params.get("limit", 20)
            result = get_recent_plays_all(limit)
            response = {"recent_plays": result, "count": len(result)}
            
        elif action == "global_most_played":
            limit = params.get("limit", 10)
            result = get_global_most_played(limit)
            response = {"global_most_played": result, "count": len(result)}
            
        else:
            response = {"error": f"Ação '{action}' não reconhecida"}
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        response = {"error": str(e)}
    
    # Envia resposta
    ch.basic_publish(
        exchange="",
        routing_key=props.reply_to,
        properties=pika.BasicProperties(correlation_id=props.correlation_id),
        body=json.dumps(response),
    )
    ch.basic_ack(delivery_tag=method.delivery_tag)
    print(f"[service_users] Resposta enviada para '{action}'")


def main():
    conn = build_connection()
    ch = configure_channel_for_consume(conn)
    declare_queue(ch, QUEUE_NAME)
    
    ch.basic_consume(queue=QUEUE_NAME, on_message_callback=handle_request)
    
    print(f"[service_users] Aguardando requisições na fila '{QUEUE_NAME}'")
    
    try:
        ch.start_consuming()
    except KeyboardInterrupt:
        print("\n[service_users] Encerrando...")
    finally:
        conn.close()


if __name__ == "__main__":
    main()