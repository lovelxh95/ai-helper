const { createApp } = Vue;
const { ElMessage, ElMessageBox } = ElementPlus;
const { Delete, Picture, SwitchButton } = ElementPlusIconsVue;

createApp({
    setup() {
        return {
            Delete,
            Picture,
            SwitchButton
        };
    },
    data() {
        return {
            isLoggedIn: false,
            isLogin: true,
            loginLoading: false,
            loginForm: {
                username: '',
                password: ''
            },
            loginRules: {
                username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
                password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
            },
            models: [],
            providers: {},
            currentModel: '',
            messages: [],
            inputMessage: '',
            isTyping: false,
            sessions: [],
            currentSessionId: null,
            userId: null,
            userInfo: {
                username: '',
                message_count: 0,
                avatar: ''
            },
            dateRange: null,
            dateFilterCollapse: [],
            isDateFiltered: false
        }
    },
    async mounted() {
        // 检查登录状态
        await this.checkLoginStatus();
    },
    methods: {
        getCookie(name) {
            const value = `; ${document.cookie}`;
            const parts = value.split(`; ${name}=`);
            if (parts.length === 2) return parts.pop().split(';').shift();
        },
        setCookie(name, value, days = 7) {
            const expires = new Date(Date.now() + days * 864e5).toUTCString();
            document.cookie = `${name}=${value}; expires=${expires}; path=/`;
        },
        async handleLogin() {
            try {
                await this.$refs.loginFormRef.validate();
                this.loginLoading = true;
                
                const url = this.isLogin ? '/api/login' : '/api/register';
                const response = await fetch(url, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(this.loginForm)
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    if (this.isLogin) {
                        this.setCookie('user_id', data.user_id);
                        this.userId = data.user_id;
                        this.isLoggedIn = true;
                        await this.loadModels();
                        await this.loadSessions();
                        await this.loadUserInfo();
                        ElMessage.success('登录成功');
                    } else {
                        ElMessage.success('注册成功，请登录');
                        this.isLogin = true;
                    }
                } else {
                    ElMessage.error(data.detail || '操作失败');
                }
            } catch (error) {
                ElMessage.error('网络错误');
            } finally {
                this.loginLoading = false;
            }
        },
        async checkLoginStatus() {
            const userId = this.getCookie('user_id');
            if (userId) {
                this.userId = userId;
                // 验证登录状态是否有效
                try {
                    const response = await fetch('/api/models');
                    if (response.status === 401) {
                        this.handleLogout();
                        return;
                    }
                    this.isLoggedIn = true;
                    await this.loadModels();
                    await this.loadSessions();
                    await this.loadUserInfo();
                } catch (error) {
                    this.handleLogout();
                }
            } else {
                this.isLoggedIn = false;
            }
        },
        handleLogout() {
            this.isLoggedIn = false;
            this.userId = null;
            this.currentSessionId = null;
            this.messages = [];
            this.sessions = [];
            this.userInfo = {
                username: '',
                message_count: 0,
                avatar: ''
            };
            // 清除cookie
            document.cookie = 'user_id=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
            ElMessage.warning('登录已过期，请重新登录');
        },
        handleAvatarCommand(command) {
            if (command === 'changeAvatar') {
                this.$refs.avatarInput.click();
            } else if (command === 'logout') {
                this.logout();
            }
        },
        triggerAvatarUpload() {
            this.$refs.avatarInput.click();
        },
        async handleAvatarUpload(event) {
            const file = event.target.files[0];
            if (!file) return;
            
            // 检查文件类型
            if (!file.type.startsWith('image/')) {
                ElMessage.error('请选择图片文件');
                return;
            }
            
            // 检查文件大小（2MB）
            if (file.size > 2 * 1024 * 1024) {
                ElMessage.error('文件大小不能超过2MB');
                return;
            }
            
            try {
                const formData = new FormData();
                formData.append('file', file);
                
                const response = await fetch('/api/user/avatar', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    this.userInfo.avatar = data.avatar;
                    ElMessage.success('头像更新成功');
                } else {
                    ElMessage.error(data.detail || '头像上传失败');
                }
            } catch (error) {
                ElMessage.error('网络错误');
            }
            
            // 清空文件输入
            event.target.value = '';
        },
        async loadModels() {
            try {
                const response = await fetch('/api/models');
                if (response.status === 401) {
                    this.handleLogout();
                    return;
                }
                const data = await response.json();
                this.models = data.models;
                this.providers = data.providers || {};
                this.currentModel = this.models[0];
            } catch (error) {
                ElMessage.error('加载模型失败');
            }
        },
        async loadSessions() {
            try {
                const response = await fetch('/api/chat/history');
                if (response.status === 401) {
                    this.handleLogout();
                    return;
                }
                const data = await response.json();
                this.sessions = data.sessions || [];
            } catch (error) {
                ElMessage.error('加载对话历史失败');
            }
        },
        async loadUserInfo() {
            try {
                const response = await fetch('/api/user/info');
                if (response.status === 401) {
                    this.handleLogout();
                    return;
                }
                const data = await response.json();
                this.userInfo = data;
            } catch (error) {
                ElMessage.error('加载用户信息失败');
            }
        },
        async loadSession(sessionId) {
            try {
                this.currentSessionId = sessionId;
                const response = await fetch(`/api/chat/history?session_id=${sessionId}`);
                if (response.status === 401) {
                    this.handleLogout();
                    return;
                }
                const data = await response.json();
                this.messages = data.conversation || [];
                this.$nextTick(() => {
                    this.scrollToBottom();
                });
            } catch (error) {
                ElMessage.error('加载对话失败');
            }
        },
        startNewChat() {
            this.currentSessionId = null;
            this.messages = [];
        },
        async sendMessage() {
            if (!this.inputMessage.trim() || this.isTyping) return;
            
            const userMessage = {
                role: 'user',
                content: this.inputMessage,
                timestamp: new Date().toISOString()
            };
            
            this.messages.push(userMessage);
            const messageToSend = this.inputMessage;
            this.inputMessage = '';
            this.isTyping = true;
            
            this.$nextTick(() => {
                this.scrollToBottom();
            });
            
            try {
                const response = await fetch('/api/chat/stream', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        message: messageToSend,
                        model_id: this.currentModel,
                        session_id: this.currentSessionId
                    })
                });
                
                if (response.status === 401) {
                    this.handleLogout();
                    this.messages.pop(); // 移除用户消息
                    return;
                }
                
                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let assistantMessage = {
                    role: 'assistant',
                    content: '',
                    timestamp: new Date().toISOString()
                };
                this.messages.push(assistantMessage);
                
                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;
                    
                    const chunk = decoder.decode(value, { stream: true });
                    const lines = chunk.split('\n');
                    
                    for (const line of lines) {
                        if (line.trim() && line.startsWith('data: ')) {
                            try {
                                const data = JSON.parse(line.slice(6));
                                if (data.content) {
                                    assistantMessage.content += data.content;
                                    // 强制Vue更新DOM
                                    this.$forceUpdate();
                                    this.$nextTick(() => {
                                        this.scrollToBottom();
                                    });
                                } else if (data.done) {
                                    this.currentSessionId = data.session_id;
                                    await this.loadSessions();
                                    // 更新消息计数
                                    this.userInfo.message_count++;
                                } else if (data.error) {
                                    ElMessage.error('AI回复出错: ' + data.error);
                                }
                            } catch (e) {
                                console.log('解析数据出错:', line, e);
                            }
                        }
                    }
                }
            } catch (error) {
                ElMessage.error('发送消息失败');
                this.messages.pop(); // 移除失败的消息
            } finally {
                this.isTyping = false;
            }
        },
        scrollToBottom() {
            const container = this.$refs.messagesContainer;
            if (container) {
                container.scrollTop = container.scrollHeight;
            }
        },
        formatTime(timeStr) {
            const date = new Date(timeStr);
            return date.toLocaleString('zh-CN');
        },
        renderMarkdown(content) {
            if (typeof marked !== 'undefined') {
                // 配置marked选项
                marked.setOptions({
                    highlight: function(code, lang) {
                        if (typeof hljs !== 'undefined' && lang && hljs.getLanguage(lang)) {
                            try {
                                return hljs.highlight(code, { language: lang }).value;
                            } catch (err) {}
                        }
                        return code;
                    },
                    breaks: true,
                    gfm: true
                });
                return marked.parse(content);
            }
            return content.replace(/\n/g, '<br>');
        },
        async deleteSession(sessionId) {
            try {
                await ElMessageBox.confirm(
                    '确定要删除这个对话吗？删除后无法恢复。',
                    '确认删除',
                    {
                        confirmButtonText: '删除',
                        cancelButtonText: '取消',
                        type: 'warning',
                        confirmButtonClass: 'el-button--danger'
                    }
                );
                
                const response = await fetch(`/api/chat/session/${sessionId}`, {
                    method: 'DELETE',
                    headers: {
                        'Content-Type': 'application/json',
                        'Cookie': document.cookie
                    }
                });
                
                if (response.status === 401) {
                    this.handleLogout();
                    return;
                }
                
                if (response.ok) {
                    ElMessage.success('对话已删除');
                    // 如果删除的是当前会话，清空消息
                    if (this.currentSessionId === sessionId) {
                        this.messages = [];
                        this.currentSessionId = null;
                    }
                    // 重新加载会话列表
                    await this.loadSessions();
                } else {
                    const error = await response.json();
                    ElMessage.error(error.detail || '删除失败');
                }
            } catch (error) {
                if (error !== 'cancel') {
                    ElMessage.error('删除失败');
                }
            }
        },
        logout() {
            this.isLoggedIn = false;
            this.userId = null;
            this.currentSessionId = null;
            this.messages = [];
            this.sessions = [];
            // 清除cookie
            document.cookie = 'user_id=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
            ElMessage.success('已退出登录');
        },
        clearCookieAndReload() {
            // 清除所有cookie
            document.cookie = 'user_id=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
            // 重新加载页面
            location.reload();
        },
        async searchByDateRange() {
            if (!this.dateRange || this.dateRange.length !== 2) {
                ElMessage.warning('请选择时间范围');
                return;
            }
            
            try {
                const response = await fetch('/api/chat/history/date-range', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Cookie': `user_id=${this.userId}`
                    },
                    body: JSON.stringify({
                        start_time: this.dateRange[0],
                        end_time: this.dateRange[1]
                    })
                });
                
                if (response.ok) {
                    const data = await response.json();
                    this.sessions = data.sessions;
                    this.isDateFiltered = true;
                    
                    if (data.sessions.length === 0) {
                        ElMessage.info('该时间范围内没有找到对话记录');
                    } else {
                        ElMessage.success(`找到 ${data.sessions.length} 条对话记录`);
                    }
                } else {
                    ElMessage.error('搜索失败');
                }
            } catch (error) {
                ElMessage.error('网络错误');
            }
        },
        async clearDateFilter() {
            this.dateRange = null;
            this.isDateFiltered = false;
            this.dateFilterCollapse = [];
            await this.loadSessions();
            ElMessage.success('已清除时间筛选');
        }
    }
}).use(ElementPlus).mount('#app');