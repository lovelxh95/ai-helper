const { createApp } = Vue;
const { ElMessage, ElMessageBox } = ElementPlus;

createApp({
    data() {
        return {
            activeTab: 'providers',
            // API服务商数据
            providers: [],
            showProviderDialog: false,
            editingProvider: false,
            providerForm: {
                name: '',
                base_url: '',
                api_key: '',
                description: ''
            },
            // 模型配置数据
            models: [],
            showModelDialog: false,
            editingModel: false,
            modelForm: {
                provider_id: '',
                model_id: '',
                model_name: '',
                max_tokens: 4000,
                sort_order: 0,
                description: ''
            },
            // 用户管理数据
            users: [],
            showUserDialog: false,
            userForm: {
                id: '',
                username: '',
                status: 1,
                is_admin: 0
            }
        };
    },
    mounted() {
        this.checkAuth();
        this.loadProviders();
        this.loadModels();
        this.loadUsers();
    },
    methods: {
        // 检查管理员权限
        async checkAuth() {
            try {
                const response = await fetch('/api/admin/check', {
                    method: 'GET',
                    credentials: 'include'
                });
                if (!response.ok) {
                    ElMessage.error('无管理员权限，即将跳转到登录页');
                    setTimeout(() => {
                        window.location.href = '/';
                    }, 2000);
                }
            } catch (error) {
                ElMessage.error('权限验证失败');
                window.location.href = '/';
            }
        },

        // 退出登录
        logout() {
            ElMessageBox.confirm('确定要退出登录吗？', '提示', {
                confirmButtonText: '确定',
                cancelButtonText: '取消',
                type: 'warning'
            }).then(() => {
                document.cookie = 'session_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
                window.location.href = '/';
            });
        },

        // API服务商管理
        async loadProviders() {
            try {
                const response = await fetch('/api/admin/providers', {
                    credentials: 'include'
                });
                if (response.ok) {
                    const data = await response.json();
                    this.providers = data.providers || [];
                }
            } catch (error) {
                ElMessage.error('加载服务商列表失败');
            }
        },

        editProvider(provider) {
            this.editingProvider = true;
            this.providerForm = {
                id: provider.id,
                name: provider.name,
                base_url: provider.base_url,
                api_key: '', // 编辑时需要重新输入API密钥
                description: provider.description || ''
            };
            this.showProviderDialog = true;
        },

        async saveProvider() {
            try {
                const url = this.editingProvider 
                    ? `/api/admin/providers/${this.providerForm.id}`
                    : '/api/admin/providers';
                const method = this.editingProvider ? 'PUT' : 'POST';
                
                // 创建一个只包含必需字段的数据对象用于发送
                const providerData = {
                    name: this.providerForm.name,
                    base_url: this.providerForm.base_url,
                    api_key: this.providerForm.api_key || '',
                    description: this.providerForm.description || ''
                };
                console.log('发送的数据:', providerData);
                
                const response = await fetch(url, {
                    method: method,
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    credentials: 'include',
                    body: JSON.stringify(providerData)
                });

                if (response.ok) {
                    ElMessage.success(this.editingProvider ? '更新成功' : '添加成功');
                    this.showProviderDialog = false;
                    this.resetProviderForm();
                    this.loadProviders();
                } else {
                    const error = await response.json();
                    ElMessage.error(error.detail || '操作失败');
                }
            } catch (error) {
                ElMessage.error('操作失败');
            }
        },

        async deleteProvider(id) {
            ElMessageBox.confirm('确定要删除这个服务商吗？', '提示', {
                confirmButtonText: '确定',
                cancelButtonText: '取消',
                type: 'warning'
            }).then(async () => {
                try {
                    const response = await fetch(`/api/admin/providers/${id}`, {
                        method: 'DELETE',
                        credentials: 'include'
                    });
                    if (response.ok) {
                        ElMessage.success('删除成功');
                        this.loadProviders();
                    } else {
                        ElMessage.error('删除失败');
                    }
                } catch (error) {
                    ElMessage.error('删除失败');
                }
            });
        },

        resetProviderForm() {
            this.editingProvider = false;
            this.providerForm = {
                name: '',
                base_url: '',
                api_key: '',
                description: ''
            };
        },

        // 模型配置管理
        async loadModels() {
            try {
                const response = await fetch('/api/admin/models', {
                    credentials: 'include'
                });
                if (response.ok) {
                    const data = await response.json();
                    this.models = data.models || [];
                }
            } catch (error) {
                ElMessage.error('加载模型列表失败');
            }
        },

        editModel(model) {
            this.editingModel = true;
            this.modelForm = { ...model };
            this.showModelDialog = true;
        },

        async saveModel() {
            try {
                const url = this.editingModel 
                    ? `/api/admin/models/${this.modelForm.id}`
                    : '/api/admin/models';
                const method = this.editingModel ? 'PUT' : 'POST';
                
                const response = await fetch(url, {
                    method: method,
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    credentials: 'include',
                    body: JSON.stringify(this.modelForm)
                });

                if (response.ok) {
                    ElMessage.success(this.editingModel ? '更新成功' : '添加成功');
                    this.showModelDialog = false;
                    this.resetModelForm();
                    this.loadModels();
                } else {
                    const error = await response.json();
                    ElMessage.error(error.detail || '操作失败');
                }
            } catch (error) {
                ElMessage.error('操作失败');
            }
        },

        async deleteModel(id) {
            ElMessageBox.confirm('确定要删除这个模型吗？', '提示', {
                confirmButtonText: '确定',
                cancelButtonText: '取消',
                type: 'warning'
            }).then(async () => {
                try {
                    const response = await fetch(`/api/admin/models/${id}`, {
                        method: 'DELETE',
                        credentials: 'include'
                    });
                    if (response.ok) {
                        ElMessage.success('删除成功');
                        this.loadModels();
                    } else {
                        ElMessage.error('删除失败');
                    }
                } catch (error) {
                    ElMessage.error('删除失败');
                }
            });
        },

        resetModelForm() {
            this.editingModel = false;
            this.modelForm = {
                provider_id: '',
                model_id: '',
                model_name: '',
                max_tokens: 4000,
                sort_order: 0,
                description: ''
            };
        },

        // 用户管理
        async loadUsers() {
            try {
                const response = await fetch('/api/admin/users', {
                    credentials: 'include'
                });
                if (response.ok) {
                    const data = await response.json();
                    this.users = data.users || [];
                }
            } catch (error) {
                ElMessage.error('加载用户列表失败');
            }
        },

        editUser(user) {
            this.userForm = {
                id: user.id,
                username: user.username,
                status: user.status,
                is_admin: user.is_admin
            };
            this.showUserDialog = true;
        },

        async saveUser() {
            try {
                const response = await fetch(`/api/admin/users/${this.userForm.id}`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    credentials: 'include',
                    body: JSON.stringify({
                        status: this.userForm.status,
                        is_admin: this.userForm.is_admin
                    })
                });

                if (response.ok) {
                    ElMessage.success('更新成功');
                    this.showUserDialog = false;
                    this.loadUsers();
                } else {
                    const error = await response.json();
                    ElMessage.error(error.detail || '更新失败');
                }
            } catch (error) {
                ElMessage.error('更新失败');
            }
        },

        async deleteUser(id) {
            ElMessageBox.confirm('确定要删除这个用户吗？删除后无法恢复！', '提示', {
                confirmButtonText: '确定',
                cancelButtonText: '取消',
                type: 'warning'
            }).then(async () => {
                try {
                    const response = await fetch(`/api/admin/users/${id}`, {
                        method: 'DELETE',
                        credentials: 'include'
                    });
                    if (response.ok) {
                        ElMessage.success('删除成功');
                        this.loadUsers();
                    } else {
                        ElMessage.error('删除失败');
                    }
                } catch (error) {
                    ElMessage.error('删除失败');
                }
            });
        }
    },
    watch: {
        showProviderDialog(val) {
            if (!val) {
                this.resetProviderForm();
            }
        },
        showModelDialog(val) {
            if (!val) {
                this.resetModelForm();
            }
        }
    }
}).use(ElementPlus).mount('#app');