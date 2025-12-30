from fastapi import FastAPI, HTTPException, Depends, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ValidationError
from typing import Optional
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
import pymysql
import json
import hashlib
import uuid
import httpx
from datetime import datetime
import os
import base64
from config import MySQL_CONFIG

app = FastAPI(title="AI Chat Assistant")

# 自定义验证错误处理器
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    print(f"验证错误 - URL: {request.url}")
    print(f"错误详情: {exc.errors()}")
    print(f"请求体: {await request.body()}")
    return await request_validation_exception_handler(request, exc)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")

# Pydantic模型
class UserRegister(BaseModel):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class ChatMessage(BaseModel):
    message: str
    model_id: str
    session_id: Optional[str] = None

class ChatHistory(BaseModel):
    session_id: Optional[str] = None

class ChatHistoryByDateRange(BaseModel):
    start_time: str
    end_time: str

# 管理员相关模型
class ApiProvider(BaseModel):
    name: str
    base_url: str
    api_key: str
    description: Optional[str] = None

class ApiProviderUpdate(BaseModel):
    name: str
    base_url: str
    api_key: Optional[str] = None
    description: Optional[str] = None

class ModelConfig(BaseModel):
    provider_id: int
    model_id: str
    model_name: str
    description: Optional[str] = None
    max_tokens: Optional[int] = 4096
    sort_order: Optional[int] = 0

class UserManagement(BaseModel):
    username: str
    status: int
    is_admin: Optional[int] = 0

# 数据库连接
def get_db_connection():
    return pymysql.connect(**MySQL_CONFIG)

# 工具函数
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed

def get_current_user(request: Request):
    user_id = request.cookies.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="未登录")
    return int(user_id)

def get_admin_user(request: Request):
    user_id = get_current_user(request)
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT is_admin FROM users WHERE id = %s", (user_id,))
            result = cursor.fetchone()
            if not result or result[0] != 1:
                raise HTTPException(status_code=403, detail="需要管理员权限")
            return user_id
    finally:
        conn.close()

# 生成默认头像（SVG格式，显示用户名首字母）
def generate_default_avatar(username: str) -> str:
    # 获取用户名首字母
    initial = username[0].upper() if username else "U"
    
    # 生成随机背景色
    import random
    colors = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7", "#DDA0DD", "#98D8C8", "#F7DC6F"]
    bg_color = colors[hash(username) % len(colors)]
    
    # 创建SVG
    svg = f'''
    <svg width="40" height="40" xmlns="http://www.w3.org/2000/svg">
        <circle cx="20" cy="20" r="20" fill="{bg_color}"/>
        <text x="20" y="26" font-family="Arial, sans-serif" font-size="16" font-weight="bold" 
              text-anchor="middle" fill="white">{initial}</text>
    </svg>
    '''
    
    # 转换为base64
    return base64.b64encode(svg.encode('utf-8')).decode('utf-8')

# 用户注册
@app.post("/api/register")
async def register(user_data: UserRegister):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        username = user_data.username
        password = user_data.password
        
        if not username or not password:
            raise HTTPException(status_code=400, detail="用户名和密码不能为空")
        
        # 检查用户名是否存在
        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="用户名已存在")
        
        # 创建用户
        hashed_password = hash_password(password)
        cursor.execute(
            "INSERT INTO users (username, password) VALUES (%s, %s)",
            (username, hashed_password)
        )
        conn.commit()
        return {"message": "注册成功"}
    finally:
        conn.close()

# 用户登录
@app.post("/api/login")
async def login(user_data: UserLogin):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        username = user_data.username
        password = user_data.password
        
        if not username or not password:
            raise HTTPException(status_code=400, detail="用户名和密码不能为空")
        
        cursor.execute(
            "SELECT id, password FROM users WHERE username = %s",
            (username,)
        )
        result = cursor.fetchone()
        if not result or not verify_password(password, result[1]):
            raise HTTPException(status_code=401, detail="用户名或密码错误")
        
        # 更新最后登录时间
        cursor.execute(
            "UPDATE users SET last_login = NOW() WHERE id = %s",
            (result[0],)
        )
        conn.commit()
        
        response = {"message": "登录成功", "user_id": result[0]}
        return response
    finally:
        conn.close()

# 获取可用模型列表
@app.get("/api/models")
async def get_models():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT mc.model_id, mc.model_name, ap.name as provider_name
                FROM model_configs mc 
                JOIN api_providers ap ON mc.provider_id = ap.id 
                WHERE mc.status = 1 AND ap.status = 1 
                ORDER BY ap.name, mc.sort_order, mc.id
            """)
            models_data = []
            providers = {}
            for row in cursor.fetchall():
                model_id, model_name, provider_name = row
                if provider_name not in providers:
                    providers[provider_name] = []
                providers[provider_name].append({
                    "model_id": model_id,
                    "model_name": model_name
                })
                models_data.append(model_id)  # 保持向后兼容
            
            return {
                "models": models_data,  # 向后兼容的简单列表
                "providers": providers  # 按服务商分组的数据
            }
    finally:
        conn.close()

# 获取用户信息
@app.get("/api/user/info")
async def get_user_info(user_id: int = Depends(get_current_user)):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # 获取用户名和头像
        cursor.execute("SELECT username, avatar FROM users WHERE id = %s", (user_id,))
        user_result = cursor.fetchone()
        if not user_result:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        username, avatar = user_result
        
        # 统计用户发送的消息数量
        cursor.execute(
            "SELECT COUNT(*) FROM ai_chat_messages WHERE session_id IN (SELECT session_id FROM chat_sessions WHERE user_id = %s) AND role = 'user'",
            (user_id,)
        )
        message_count = cursor.fetchone()[0]
        
        # 如果没有头像，生成默认头像（用户名首字母）
        if not avatar:
            avatar = f"data:image/svg+xml;base64,{generate_default_avatar(username)}"
        # 如果头像是旧的base64格式但不是默认头像，也生成新的默认头像
        elif avatar.startswith('data:image/') and 'base64,' in avatar and len(avatar) > 1000:
            avatar = f"data:image/svg+xml;base64,{generate_default_avatar(username)}"
        
        return {
            "username": username,
            "message_count": message_count,
            "avatar": avatar
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

# 上传头像
@app.post("/api/user/avatar")
async def upload_avatar(file: UploadFile = File(...), user_id: int = Depends(get_current_user)):
    # 检查文件类型
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="只支持图片文件")
    
    # 检查文件大小（限制为2MB）
    content = await file.read()
    if len(content) > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="文件大小不能超过2MB")
    
    # 确保img目录存在
    img_dir = "static/img"
    if not os.path.exists(img_dir):
        os.makedirs(img_dir)
    
    # 生成唯一文件名
    file_extension = file.filename.split('.')[-1] if '.' in file.filename else 'jpg'
    filename = f"avatar_{user_id}_{uuid.uuid4().hex[:8]}.{file_extension}"
    file_path = os.path.join(img_dir, filename)
    
    # 保存文件
    with open(file_path, "wb") as f:
        f.write(content)
    
    # 生成访问URL
    avatar_url = f"/static/img/{filename}"
    
    # 更新数据库
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET avatar = %s WHERE id = %s", (avatar_url, user_id))
        conn.commit()
        
        return {"message": "头像上传成功", "avatar": avatar_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

# 发送消息（流式）
@app.post("/api/chat/stream")
async def chat_stream(chat_data: ChatMessage, user_id: int = Depends(get_current_user)):
    async def generate_response():
        try:
            message = chat_data.message
            model_id_selected = chat_data.model_id
            session_id = chat_data.session_id
            
            if not message or not model_id_selected:
                yield f"data: {json.dumps({'error': '消息和模型ID不能为空'})}\n\n"
                return
            
            # 获取或创建会话
            conn = get_db_connection()
            cursor = conn.cursor()
            
            if session_id:
                # 检查会话是否存在
                cursor.execute(
                    "SELECT id FROM chat_sessions WHERE session_id = %s AND user_id = %s",
                    (session_id, user_id)
                )
                if not cursor.fetchone():
                    yield f"data: {json.dumps({'error': '会话不存在'})}\n\n"
                    return
            else:
                # 创建新会话
                session_id = str(uuid.uuid4())
                cursor.execute(
                    "INSERT INTO chat_sessions (session_id, user_id, model_id) VALUES (%s, %s, %s)",
                    (session_id, user_id, model_id_selected)
                )
                conn.commit()
            
            # 获取历史消息
            cursor.execute(
                "SELECT role, content FROM ai_chat_messages WHERE session_id = %s ORDER BY create_time ASC",
                (session_id,)
            )
            messages = []
            for row in cursor.fetchall():
                messages.append({
                    "role": row[0],
                    "content": row[1]
                })
            
            # 添加用户消息到数组
            messages.append({
                "role": "user",
                "content": message
            })
            
            # 保存用户消息到数据库
            cursor.execute(
                "INSERT INTO ai_chat_messages (session_id, user_id, role, content) VALUES (%s, %s, %s, %s)",
                (session_id, user_id, "user", message)
            )
            conn.commit()
            
            # 获取模型对应的API配置
            cursor.execute("""
                SELECT ap.base_url, ap.api_key 
                FROM model_configs mc 
                JOIN api_providers ap ON mc.provider_id = ap.id 
                WHERE mc.model_id = %s AND mc.status = 1 AND ap.status = 1
            """, (model_id_selected,))
            api_config = cursor.fetchone()
            if not api_config:
                yield f"data: {json.dumps({'error': '模型配置不存在或已禁用'})}\n\n"
                return
            
            api_base_url, api_key = api_config
            
            # 调用AI API
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream(
                    "POST",
                    f"{api_base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model_id_selected,
                        "messages": [{"role": msg["role"], "content": msg["content"]} for msg in messages[-10:]],
                        "stream": True
                    }
                ) as response:
                    assistant_message = ""
                    async for line in response.aiter_lines():
                        if line.strip():
                            if line.startswith("data: "):
                                data = line[6:]
                                if data == "[DONE]":
                                    break
                                try:
                                    chunk = json.loads(data)
                                    if "choices" in chunk and len(chunk["choices"]) > 0:
                                        delta = chunk["choices"][0].get("delta", {})
                                        if "content" in delta:
                                            content = delta["content"]
                                            assistant_message += content
                                            yield f"data: {json.dumps({'content': content})}\n\n"
                                except json.JSONDecodeError:
                                    continue
            
            # 保存助手回复到数据库
            cursor.execute(
                "INSERT INTO ai_chat_messages (session_id, user_id, role, content) VALUES (%s, %s, %s, %s)",
                (session_id, user_id, "assistant", assistant_message)
            )
            
            # 更新会话的最后更新时间
            cursor.execute(
                "UPDATE chat_sessions SET update_time = NOW() WHERE session_id = %s",
                (session_id,)
            )
            conn.commit()
            
            yield f"data: {json.dumps({'done': True, 'session_id': session_id})}\n\n"
                
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        finally:
            if 'conn' in locals():
                conn.close()
    
    return StreamingResponse(
        generate_response(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

# 获取对话历史
@app.get("/api/chat/history")
async def get_chat_history(session_id: str = None, user_id: int = Depends(get_current_user)):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        if session_id:
            # 获取指定会话的消息历史
            cursor.execute(
                "SELECT role, content, create_time FROM ai_chat_messages WHERE session_id = %s AND user_id = %s ORDER BY create_time ASC",
                (session_id, user_id)
            )
            messages = []
            for row in cursor.fetchall():
                messages.append({
                    "role": row[0],
                    "content": row[1],
                    "timestamp": row[2].isoformat()
                })
            
            # 获取会话信息
            cursor.execute(
                "SELECT model_id, create_time FROM chat_sessions WHERE session_id = %s AND user_id = %s",
                (session_id, user_id)
            )
            session_info = cursor.fetchone()
            if session_info:
                return {
                    "conversation": messages,
                    "model_id": session_info[0],
                    "create_time": session_info[1].isoformat()
                }
            return {"conversation": []}
        else:
            # 获取所有会话列表
            cursor.execute(
                "SELECT session_id, title, model_id, create_time, update_time FROM chat_sessions WHERE user_id = %s ORDER BY update_time DESC",
                (user_id,)
            )
            sessions = []
            for row in cursor.fetchall():
                # 获取每个会话的第一条消息作为预览
                cursor.execute(
                    "SELECT content FROM ai_chat_messages WHERE session_id = %s AND role = 'user' ORDER BY create_time ASC LIMIT 1",
                    (row[0],)
                )
                first_message = cursor.fetchone()
                preview = first_message[0][:50] + "..." if first_message and len(first_message[0]) > 50 else (first_message[0] if first_message else "新对话")
                
                sessions.append({
                    "session_id": row[0],
                    "title": row[1] or preview,
                    "model_id": row[2],
                    "create_time": row[3].isoformat(),
                    "update_time": row[4].isoformat(),
                    "preview": preview
                })
            return {"sessions": sessions}
    finally:
        conn.close()

# 根据时间范围获取对话历史
@app.post("/api/chat/history/date-range")
async def get_chat_history_by_date_range(date_range: ChatHistoryByDateRange, user_id: int = Depends(get_current_user)):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # 查询指定时间范围内的会话
        cursor.execute("""
            SELECT session_id, title, model_id, create_time, update_time 
            FROM chat_sessions 
            WHERE user_id = %s 
            AND create_time >= %s 
            AND create_time <= %s 
            ORDER BY update_time DESC
        """, (user_id, date_range.start_time, date_range.end_time))
        
        sessions = []
        for row in cursor.fetchall():
            # 获取每个会话的第一条消息作为预览
            cursor.execute(
                "SELECT content FROM ai_chat_messages WHERE session_id = %s AND role = 'user' ORDER BY create_time ASC LIMIT 1",
                (row[0],)
            )
            first_message = cursor.fetchone()
            preview = first_message[0][:50] + "..." if first_message and len(first_message[0]) > 50 else (first_message[0] if first_message else "新对话")
            
            sessions.append({
                "session_id": row[0],
                "title": row[1] or preview,
                "model_id": row[2],
                "create_time": row[3].isoformat(),
                "update_time": row[4].isoformat(),
                "preview": preview
            })
        
        return {"sessions": sessions}
    finally:
        conn.close()

# 删除对话
@app.delete("/api/chat/session/{session_id}")
async def delete_chat_session(session_id: str, user_id: int = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 检查会话是否属于当前用户
        cursor.execute(
            "SELECT id FROM chat_sessions WHERE user_id = %s AND session_id = %s",
            (user_id, session_id)
        )
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="会话不存在或无权限删除")
        
        # 删除会话（由于外键约束，相关消息会自动删除）
        cursor.execute(
            "DELETE FROM chat_sessions WHERE user_id = %s AND session_id = %s",
            (user_id, session_id)
        )
        
        conn.commit()
        return {"message": "对话已删除"}
    
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

# 主页
# ==================== 管理员后台API ====================

# 获取所有API服务商
@app.get("/api/admin/providers")
async def get_providers(admin_id: int = Depends(get_admin_user)):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, name, base_url, description, status, create_time FROM api_providers ORDER BY id")
            providers = []
            for row in cursor.fetchall():
                providers.append({
                    "id": row[0],
                    "name": row[1],
                    "base_url": row[2],
                    "description": row[3],
                    "status": row[4],
                    "create_time": row[5].strftime("%Y-%m-%d %H:%M:%S")
                })
            return {"providers": providers}
    finally:
        conn.close()

# 添加API服务商
@app.post("/api/admin/providers")
async def add_provider(provider: ApiProvider, admin_id: int = Depends(get_admin_user)):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO api_providers (name, base_url, api_key, description) VALUES (%s, %s, %s, %s)",
                (provider.name, provider.base_url, provider.api_key, provider.description)
            )
            conn.commit()
            return {"message": "API服务商添加成功"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=f"添加失败: {str(e)}")
    finally:
        conn.close()

# 更新API服务商
@app.put("/api/admin/providers/{provider_id}")
async def update_provider(provider_id: int, provider: ApiProviderUpdate, admin_id: int = Depends(get_admin_user)):
    print(f"收到更新请求 - provider_id: {provider_id}")
    print(f"数据: name={provider.name}, base_url={provider.base_url}, api_key={provider.api_key}, description={provider.description}")
    
    # 验证必需字段
    if not provider.name or not provider.base_url:
        raise HTTPException(status_code=422, detail="name, base_url 字段不能为空")
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 如果api_key为空，则不更新api_key字段
            if provider.api_key:
                cursor.execute(
                    "UPDATE api_providers SET name=%s, base_url=%s, api_key=%s, description=%s WHERE id=%s",
                    (provider.name, provider.base_url, provider.api_key, provider.description, provider_id)
                )
            else:
                cursor.execute(
                    "UPDATE api_providers SET name=%s, base_url=%s, description=%s WHERE id=%s",
                    (provider.name, provider.base_url, provider.description, provider_id)
                )
            conn.commit()
            return {"message": "API服务商更新成功"}
    except Exception as e:
        conn.rollback()
        print(f"数据库更新错误: {str(e)}")
        raise HTTPException(status_code=400, detail=f"更新失败: {str(e)}")
    finally:
        conn.close()

# 删除API服务商
@app.delete("/api/admin/providers/{provider_id}")
async def delete_provider(provider_id: int, admin_id: int = Depends(get_admin_user)):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM api_providers WHERE id = %s", (provider_id,))
            conn.commit()
            return {"message": "API服务商删除成功"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=f"删除失败: {str(e)}")
    finally:
        conn.close()

# 获取所有模型配置
@app.get("/api/admin/models")
async def get_model_configs(admin_id: int = Depends(get_admin_user)):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT mc.id, mc.model_id, mc.model_name, mc.description, mc.max_tokens, 
                       mc.status, mc.sort_order, ap.name as provider_name, mc.provider_id
                FROM model_configs mc 
                JOIN api_providers ap ON mc.provider_id = ap.id 
                ORDER BY mc.sort_order, mc.id
            """)
            models = []
            for row in cursor.fetchall():
                models.append({
                    "id": row[0],
                    "model_id": row[1],
                    "model_name": row[2],
                    "description": row[3],
                    "max_tokens": row[4],
                    "status": row[5],
                    "sort_order": row[6],
                    "provider_name": row[7],
                    "provider_id": row[8]
                })
            return {"models": models}
    finally:
        conn.close()

# 添加模型配置
@app.post("/api/admin/models")
async def add_model_config(model: ModelConfig, admin_id: int = Depends(get_admin_user)):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO model_configs (provider_id, model_id, model_name, description, max_tokens, sort_order) VALUES (%s, %s, %s, %s, %s, %s)",
                (model.provider_id, model.model_id, model.model_name, model.description, model.max_tokens, model.sort_order)
            )
            conn.commit()
            return {"message": "模型配置添加成功"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=f"添加失败: {str(e)}")
    finally:
        conn.close()

# 更新模型配置
@app.put("/api/admin/models/{model_id}")
async def update_model_config(model_id: int, model: ModelConfig, admin_id: int = Depends(get_admin_user)):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE model_configs SET provider_id=%s, model_id=%s, model_name=%s, description=%s, max_tokens=%s, sort_order=%s WHERE id=%s",
                (model.provider_id, model.model_id, model.model_name, model.description, model.max_tokens, model.sort_order, model_id)
            )
            conn.commit()
            return {"message": "模型配置更新成功"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=f"更新失败: {str(e)}")
    finally:
        conn.close()

# 删除模型配置
@app.delete("/api/admin/models/{model_id}")
async def delete_model_config(model_id: int, admin_id: int = Depends(get_admin_user)):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM model_configs WHERE id = %s", (model_id,))
            conn.commit()
            return {"message": "模型配置删除成功"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=f"删除失败: {str(e)}")
    finally:
        conn.close()

# 获取所有用户
@app.get("/api/admin/users")
async def get_users(admin_id: int = Depends(get_admin_user)):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT u.id, u.username, u.status, u.is_admin, u.create_time, u.last_login,
                       COUNT(m.id) as message_count
                FROM users u 
                LEFT JOIN ai_chat_messages m ON u.id = m.user_id 
                GROUP BY u.id 
                ORDER BY u.id
            """)
            users = []
            for row in cursor.fetchall():
                users.append({
                    "id": row[0],
                    "username": row[1],
                    "status": row[2],
                    "is_admin": row[3],
                    "create_time": row[4].strftime("%Y-%m-%d %H:%M:%S"),
                    "last_login": row[5].strftime("%Y-%m-%d %H:%M:%S") if row[5] else None,
                    "message_count": row[6]
                })
            return {"users": users}
    finally:
        conn.close()

# 更新用户状态
@app.put("/api/admin/users/{user_id}")
async def update_user_status(user_id: int, user_data: UserManagement, admin_id: int = Depends(get_admin_user)):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE users SET status=%s, is_admin=%s WHERE id=%s",
                (user_data.status, user_data.is_admin, user_id)
            )
            conn.commit()
            return {"message": "用户状态更新成功"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=f"更新失败: {str(e)}")
    finally:
        conn.close()

# 删除用户
@app.delete("/api/admin/users/{user_id}")
async def delete_user(user_id: int, admin_id: int = Depends(get_admin_user)):
    if user_id == admin_id:
        raise HTTPException(status_code=400, detail="不能删除自己的账户")
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
            conn.commit()
            return {"message": "用户删除成功"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=f"删除失败: {str(e)}")
    finally:
        conn.close()

@app.get("/", response_class=HTMLResponse)
async def read_root():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/admin", response_class=HTMLResponse)
async def read_admin():
    with open("static/admin.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/api/admin/check")
async def check_admin_auth(admin_id: int = Depends(get_admin_user)):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT username FROM users WHERE id = %s", (admin_id,))
            result = cursor.fetchone()
            return {"message": "Admin access granted", "user": result[0] if result else "Unknown"}
    finally:
        conn.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)