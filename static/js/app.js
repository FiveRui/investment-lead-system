const { createApp, ref, reactive, onMounted, onUnmounted, nextTick } = Vue;

createApp({
    setup() {
        const fileName = ref('');
        const chains = ref([]);
        const config = reactive({
            location_name: '成武',
            location_id: '152',
            nodes: '节点1, 节点2'
        });
        
        const isRunning = ref(false);
        const logs = ref([]);
        const leads = ref([]);
        const stats = reactive({ total_crawled: 0, valid_leads: 0 });
        const rawNews = reactive({
            state: { is_running: false, phase: 'idle' },
            logs: []
        });
        const rawNewsLabel = ref('未启动');
        let statusTimer = null;
        let keyHandler = null;

        // 处理文件上传
        const handleFileUpload = async (event) => {
            const file = event.target.files[0];
            if (!file) return;
            
            fileName.value = file.name;
            const formData = new FormData();
            formData.append('file', file);
            
            try {
                const response = await axios.post('/api/upload_excel', formData, {
                    headers: { 'Content-Type': 'multipart/form-data' }
                });
                if (response.data.status === 'success') {
                    chains.value = response.data.chains;
                    alert(`成功解析 ${chains.value.length} 个产业链！`);
                }
            } catch (error) {
                console.error('上传失败', error);
                alert('上传失败，请检查网络或控制台日志');
            }
        };

        // 保存配置
        const saveConfig = async () => {
            const formData = new FormData();
            formData.append('location_name', config.location_name);
            formData.append('location_id', config.location_id);
            formData.append('nodes', config.nodes);
            
            try {
                const response = await axios.post('/api/config', formData);
                if (response.data.status === 'success') {
                    alert('配置已成功保存！');
                }
            } catch (error) {
                console.error('配置保存失败', error);
            }
        };

        // 启动任务
        const startTask = async () => {
            try {
                const response = await axios.post('/api/start_task');
                if (response.data.status === 'success') {
                    isRunning.value = true;
                    startPolling();
                } else {
                    alert(response.data.message);
                }
            } catch (error) {
                console.error('启动任务失败', error);
            }
        };

        // 停止任务
        const stopTask = async () => {
            try {
                const response = await axios.post('/api/stop_task');
                if (response.data.status === 'success') {
                    alert('正在停止任务，请等待当前循环完成...');
                }
            } catch (error) {
                console.error('停止任务失败', error);
            }
        };

        // 获取状态
        const fetchStatus = async () => {
            try {
                const response = await axios.get('/api/status');
                isRunning.value = response.data.is_running;
                logs.value = response.data.logs;
                stats.total_crawled = response.data.stats.total_crawled;
                stats.valid_leads = response.data.stats.valid_leads;
                
                // 滚动日志到底部
                nextTick(() => {
                    const container = document.getElementById('log-container');
                    if (container) {
                        container.scrollTop = container.scrollHeight;
                    }
                });
                
                if (!isRunning.value && statusTimer) {
                    // 如果任务停止，可以放慢轮询或停止
                }
            } catch (error) {
                console.error('获取状态失败', error);
            }
        };

        const fetchRawNewsStatus = async () => {
            try {
                const response = await axios.get('/api/raw_news/status');
                if (response.data.status !== 'success') return;
                rawNews.state = response.data.state || { is_running: false, phase: 'idle' };
                rawNews.logs = response.data.logs || [];
                const phase = rawNews.state.phase || 'idle';
                if (phase === 'running') rawNewsLabel.value = '运行中';
                else if (phase === 'waiting_login') rawNewsLabel.value = '等待登录';
                else if (phase === 'done') rawNewsLabel.value = '已完成';
                else if (phase === 'stopping') rawNewsLabel.value = '停止中';
                else if (phase === 'error') rawNewsLabel.value = '异常';
                else rawNewsLabel.value = '未启动';
            } catch (e) {
                rawNewsLabel.value = '不可用';
            }
        };

        const startRawNews = async () => {
            try {
                const response = await axios.post('/api/raw_news/start');
                if (response.data.status !== 'success') {
                    alert(response.data.message || '启动失败');
                }
                fetchRawNewsStatus();
            } catch (e) {
                alert('启动失败，请查看控制台');
            }
        };

        const continueRawNews = async () => {
            try {
                const response = await axios.post('/api/raw_news/continue');
                if (response.data.status !== 'success') {
                    alert(response.data.message || '发送失败');
                }
                fetchRawNewsStatus();
            } catch (e) {
                alert('发送失败，请查看控制台');
            }
        };

        const stopRawNews = async () => {
            try {
                const response = await axios.post('/api/raw_news/stop');
                if (response.data.status !== 'success') {
                    alert(response.data.message || '停止失败');
                }
                fetchRawNewsStatus();
            } catch (e) {
                alert('停止失败，请查看控制台');
            }
        };

        // 获取线索
        const fetchLeads = async () => {
            try {
                const response = await axios.get('/api/leads');
                if (response.data.status === 'success') {
                    leads.value = response.data.data;
                }
            } catch (error) {
                console.error('获取线索失败', error);
            }
        };

        const getFirstPlanDocUrl = (lead) => {
            if (!lead) return '';
            const v = lead.investment_plan_docs;
            if (!v) return '';
            if (Array.isArray(v)) {
                const u = v[0] && v[0].url ? String(v[0].url) : '';
                return u || '';
            }
            if (typeof v === 'string') {
                const s = v.trim();
                if (!s || s === '[]') return '';
                try {
                    const arr = JSON.parse(s);
                    if (Array.isArray(arr) && arr.length > 0) {
                        const u = arr[0] && arr[0].url ? String(arr[0].url) : '';
                        return u || '';
                    }
                } catch (e) {
                    return '';
                }
            }
            if (typeof v === 'object') {
                const u = v.url ? String(v.url) : '';
                return u || '';
            }
            return '';
        };

        const exportLeads = (format) => {
            const fmt = (format || 'xlsx').toLowerCase();
            const url = `/api/export_leads?format=${encodeURIComponent(fmt)}`;
            window.location.href = url;
        };

        const startPolling = () => {
            if (statusTimer) clearInterval(statusTimer);
            statusTimer = setInterval(() => {
                fetchStatus();
                fetchLeads();
                fetchRawNewsStatus();
            }, 2000);
        };

        onMounted(() => {
            fetchStatus();
            fetchLeads();
            fetchRawNewsStatus();
            startPolling();

            keyHandler = (e) => {
                if (!e) return;
                const isEnter =
                    e.key === 'Enter' ||
                    e.code === 'Enter' ||
                    e.keyCode === 13 ||
                    e.which === 13;
                if (!isEnter) return;
                const phase = rawNews && rawNews.state ? (rawNews.state.phase || '') : '';
                if (rawNews.state && rawNews.state.is_running && (phase === 'waiting_login' || phase === 'starting')) {
                    try { e.preventDefault(); } catch (_) {}
                    continueRawNews();
                }
            };
            document.addEventListener('keydown', keyHandler, true);
        });

        onUnmounted(() => {
            if (statusTimer) clearInterval(statusTimer);
            if (keyHandler) document.removeEventListener('keydown', keyHandler, true);
        });

        return {
            fileName,
            chains,
            config,
            isRunning,
            logs,
            leads,
            stats,
            rawNews,
            rawNewsLabel,
            handleFileUpload,
            saveConfig,
            startTask,
            stopTask,
            startRawNews,
            continueRawNews,
            stopRawNews,
            fetchLeads,
            getFirstPlanDocUrl,
            exportLeads
        };
    }
}).mount('#app');
