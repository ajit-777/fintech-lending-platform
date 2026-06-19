import api from './client';

export const getLoans = (params) => api.get('/admin/loans', { params });
export const getLoan = (id) => api.get(`/admin/loans/${id}`);
export const approveLoan = (id) => api.patch(`/admin/loans/${id}/approve`);
export const rejectLoan = (id, reason) => api.patch(`/admin/loans/${id}/reject`, { reason });
export const disburseLoan = (id, referenceNumber) =>
  api.post(`/admin/loans/${id}/disburse`, { reference_number: referenceNumber });
export const getRepayments = (id) => api.get(`/admin/loans/${id}/repayments`);
export const markRepaymentPaid = (loanId, repaymentId) =>
  api.patch(`/admin/loans/${loanId}/repayments/${repaymentId}/pay`);
export const getPricing = () => api.get('/admin/pricing');
export const updatePricing = (id, data) => api.patch(`/admin/pricing/${id}`, data);

export const getUserKYC = (userId) => api.get(`/admin/users/${userId}/kyc`);
export const overrideKYCStatus = (userId, data) => api.patch(`/admin/users/${userId}/kyc/status`, data);
export const overrideBankAccount = (loanId) => api.patch(`/admin/loans/${loanId}/bank-account/override`);
