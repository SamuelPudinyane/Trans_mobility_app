// dashboard_status_poll.js
// Polls the backend for updated dashboard numbers and updates the DOM

function fetchDashboardStats() {
    fetch('/api/dashboard-stats/')
        .then(response => response.json())
        .then(data => {
            document.getElementById('locomotives-under-maintenance').textContent = data.locomotives_under_maintenance;
            document.getElementById('pending-tasks').textContent = data.pending_tasks;
            document.getElementById('completed-today').textContent = data.completed_today;
        });
}

setInterval(fetchDashboardStats, 5000); // Poll every 5 seconds

document.addEventListener('DOMContentLoaded', fetchDashboardStats);