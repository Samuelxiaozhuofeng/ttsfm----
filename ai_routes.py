from flask import Blueprint, request, jsonify, Response, stream_with_context
import json
import requests
import time

from library import Library

# 全局 Library 实例，由 init_ai_routes 注入
library: Library | None = None

ai_bp = Blueprint("ai", __name__)


def build_chat_endpoint(base_url: str) -> str:
    """Normalize the chat completions endpoint for OpenAI-compatible APIs."""
    if not base_url:
        return ""
    normalized = base_url.rstrip("/")
    if normalized.lower().endswith("/chat/completions"):
        return normalized
    return f"{normalized}/chat/completions"


def init_ai_routes(app, library_instance: Library) -> None:
    """
    在主应用中调用，用于注入 Library 实例并注册 Blueprint。

    示例（在 app.py 中）:
        from ai_routes import init_ai_routes
        library = Library()
        init_ai_routes(app, library)
    """
    global library
    library = library_instance
    app.register_blueprint(ai_bp)


@ai_bp.route("/api/ai/settings", methods=["GET"])
def get_ai_settings():
    """Get AI settings (masked api_key for frontend)."""
    try:
        assert library is not None, "Library is not initialized in ai_routes"
        settings = library.get_ai_settings()
        if settings:
            # Don't send the full API key to frontend, only show last 4 chars
            safe_settings = settings.copy()
            if "api_key" in safe_settings and safe_settings["api_key"]:
                key = safe_settings["api_key"]
                safe_settings["api_key_masked"] = (
                    "***" + key[-4:] if len(key) > 4 else "***"
                )
                safe_settings["has_api_key"] = True
                del safe_settings["api_key"]
            else:
                safe_settings["has_api_key"] = False

            return jsonify({"success": True, "settings": safe_settings})
        else:
            return jsonify({"success": True, "settings": None})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@ai_bp.route("/api/ai/settings", methods=["POST"])
def save_ai_settings():
    """Save AI settings."""
    try:
        assert library is not None, "Library is not initialized in ai_routes"
        data = request.get_json()
        api_url = data.get("api_url", "").strip()
        api_key = data.get("api_key", "").strip()
        model = data.get("model", "").strip()

        if not api_url or not model:
            return jsonify({"error": "请填写API地址和模型名称"}), 400

        # If API key is not provided, try to keep existing one
        if not api_key:
            existing_settings = library.get_ai_settings()
            if existing_settings and existing_settings.get("api_key"):
                api_key = existing_settings["api_key"]
            else:
                return jsonify({"error": "请输入API密钥"}), 400

        library.save_ai_settings(api_url, api_key, model)

        return jsonify({"success": True, "message": "AI设置已保存"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@ai_bp.route("/api/ai/test", methods=["POST"])
def test_ai_connection():
    """Test AI API connectivity with provided or saved settings."""
    try:
        assert library is not None, "Library is not initialized in ai_routes"
        data = request.get_json() or {}
        api_url = data.get("api_url", "").strip()
        api_key = data.get("api_key", "").strip()
        model = data.get("model", "").strip()

        # Fallback to saved settings if any field missing
        if not api_url or not api_key or not model:
            saved = library.get_ai_settings() or {}
            api_url = api_url or saved.get("api_url", "").strip()
            api_key = api_key or saved.get("api_key", "").strip()
            model = model or saved.get("model", "").strip()

        if not api_url or not model or not api_key:
            return jsonify({"error": "请先填写完整的AI配置"}), 400

        endpoint = build_chat_endpoint(api_url)
        if not endpoint:
            return jsonify({"error": "AI配置不完整"}), 400
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "你是一个测试助手，用于验证API连通性，请简单回答。",
                },
                {
                    "role": "user",
                    "content": "如果你收到这条信息，请回复：连接正常",
                },
            ],
            "temperature": 0,
        }

        start = time.perf_counter()
        response = requests.post(endpoint, headers=headers, json=payload, timeout=20)
        duration = int((time.perf_counter() - start) * 1000)

        if response.status_code != 200:
            return (
                jsonify({"error": f"AI API测试失败: {response.text}"}),
                500,
            )

        result = response.json()
        assistant_message = result["choices"][0]["message"]["content"]

        return jsonify(
            {
                "success": True,
                "message": "AI连接正常，可以使用",
                "response_preview": assistant_message[:120],
                "duration_ms": duration,
            }
        )
    except requests.exceptions.Timeout:
        return jsonify({"error": "AI连接测试超时"}), 500
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"网络错误: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@ai_bp.route("/api/chat/history/<chapter_id>", methods=["GET"])
def get_chat_history(chapter_id):
    """Get chat history for a chapter."""
    try:
        assert library is not None, "Library is not initialized in ai_routes"
        history = library.get_chat_history(chapter_id)
        return jsonify({"success": True, "history": history})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@ai_bp.route("/api/chat/history/<chapter_id>", methods=["DELETE"])
def clear_chat_history(chapter_id):
    """Clear chat history for a chapter."""
    try:
        assert library is not None, "Library is not initialized in ai_routes"
        library.clear_chat_history(chapter_id)
        return jsonify({"success": True, "message": "聊天记录已清空"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@ai_bp.route("/api/chat/message", methods=["POST"])
def chat_message():
    """
    Send a message to AI and get response.

    支持两种模式：
    - 默认：一次性 JSON 返回（兼容现有前端）
    - 流式：当请求体中包含 {"stream": true} 时，使用 SSE 流式返回
    """
    try:
        assert library is not None, "Library is not initialized in ai_routes"
        data = request.get_json() or {}
        chapter_id = data.get("chapter_id")
        user_message = data.get("message", "").strip()
        stream = bool(data.get("stream", False))

        if not chapter_id or not user_message:
            return jsonify({"error": "缺少必要参数"}), 400

        # Get chapter content
        chapter = library.get_chapter(chapter_id)
        if not chapter:
            return jsonify({"error": "章节不存在"}), 404

        # Get AI settings
        ai_settings = library.get_ai_settings()
        if not ai_settings:
            return jsonify({"error": "请先配置AI设置"}), 400

        # Get chat history
        chat_history = library.get_chat_history(chapter_id)

        # Build messages for AI
        messages = [
            {
                "role": "system",
                "content": (
                    "你是一个阅读助手。用户正在阅读以下文本，请根据文本内容回答用户的问题。\n\n"
                    f"文本内容：\n{chapter['content']}"
                ),
            }
        ]

        # Add previous chat history (limit to last 10 messages to avoid token limits)
        for msg in chat_history[-10:]:
            messages.append({"role": msg["role"], "content": msg["content"]})

        # Add current user message
        messages.append({"role": "user", "content": user_message})

        # Call OpenAI compatible API
        endpoint = build_chat_endpoint(ai_settings.get("api_url", ""))
        if not endpoint:
            return jsonify({"error": "AI配置不完整"}), 400
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {ai_settings['api_key']}",
        }

        # 非流式：保持原有行为，兼容现有前端
        if not stream:
            payload = {
                "model": ai_settings["model"],
                "messages": messages,
                "temperature": 0.7,
            }

            response = requests.post(
                endpoint,
                headers=headers,
                json=payload,
                timeout=30,
            )

            if response.status_code != 200:
                return jsonify({"error": f"AI API错误: {response.text}"}), 500

            result = response.json()
            assistant_message = result["choices"][0]["message"]["content"]

            # Save both messages to chat history
            library.add_chat_message(chapter_id, "user", user_message)
            library.add_chat_message(chapter_id, "assistant", assistant_message)

            return jsonify({"success": True, "message": assistant_message})

        # 流式模式：使用 SSE 返回增量内容
        def event_stream():
            assistant_full = ""

            payload = {
                "model": ai_settings["model"],
                "messages": messages,
                "temperature": 0.7,
                "stream": True,
            }

            try:
                with requests.post(
                    endpoint,
                    headers=headers,
                    json=payload,
                    timeout=60,
                    stream=True,
                ) as resp:
                    if resp.status_code != 200:
                        err_text = f"AI API错误: {resp.text}"
                        yield f"data: {err_text}\n\n"
                        return

                    for line in resp.iter_lines(decode_unicode=True):
                        if not line:
                            continue
                        # OpenAI 兼容流式协议通常以 "data: " 开头
                        if line.startswith("data: "):
                            data_str = line[len("data: ") :].strip()
                        else:
                            data_str = line.strip()

                        if data_str == "[DONE]":
                            break

                        try:
                            chunk = json.loads(data_str)
                        except Exception:
                            # 非 JSON 行，直接透传
                            yield f"data: {data_str}\n\n"
                            continue

                        choices = chunk.get("choices") or []
                        if not choices:
                            continue
                        delta = choices[0].get("delta") or {}
                        content_piece = delta.get("content")
                        if content_piece:
                            assistant_full += content_piece
                            # 将增量内容发给前端
                            yield f"data: {content_piece}\n\n"

            finally:
                # 流结束后，把完整消息写入聊天记录
                if assistant_full:
                    library.add_chat_message(chapter_id, "user", user_message)
                    library.add_chat_message(chapter_id, "assistant", assistant_full)

        return Response(
            stream_with_context(event_stream()),
            mimetype="text/event-stream",
        )

    except requests.exceptions.Timeout:
        return jsonify({"error": "AI请求超时"}), 500
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"网络错误: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500
