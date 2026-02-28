import axios from 'axios';

const api = axios.create({
    baseURL: '/api/admin',
    headers: {
        'Content-Type': 'application/json',
    },
});

export const dashboardApi = {
    getTodayStats: () => api.get('/stats/today'),
};

export const employeeApi = {
    list: (params) => api.get('/employees', { params }),
    create: (data) => api.post('/employees', data),
    update: (id, data) => api.put(`/employees/${id}`, data),
    delete: (id) => api.delete(`/employees/${id}`),
};

export const rawDataApi = {
    list: (params) => api.get('/raw-data', { params }),
    createManual: (data) => api.post('/raw-data/manual', data),
    void: (id, reason) => api.patch(`/raw-data/${id}/void`, { reason }),
};

export const policyApi = {
    list: () => api.get('/policies'),
    update: (id, data) => api.put(`/policies/${id}`, data),
};

export const reportApi = {
    getDaily: (date) => api.get('/reports/daily', { params: { target_date: date } }),
    getMonthly: (year, month) => api.get('/reports/monthly', { params: { year, month } }),
    getDept: (start, end) => api.get('/reports/department', { params: { start_date: start, end_date: end } }),
};

export default api;
