// Global variables
let currentUser = null;
let currentPage = 'dashboard';

// Check auth on load
document.addEventListener('DOMContentLoaded', () => {
    checkAuth();
    setupEventListeners();
});

// Setup event listeners
function setupEventListeners() {
    // Menu clicks
    document.querySelectorAll('.sidebar-menu li').forEach(item => {
        item.addEventListener('click', () => {
            const page = item.dataset.page;
            if (page) {
                switchPage(page);
            }
        });
    });
    
    // Modal close
    document.querySelectorAll('.modal-close, .modal .btn-secondary').forEach(btn => {
        btn.addEventListener('click', () => {
            closeModal();
        });
    });
    
    // Search input debounce
    let searchTimeout;
    document.getElementById('stokSearch')?.addEventListener('input', (e) => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            loadStokData(e.target.value);
        }, 300);
    });
}

// Check authentication with Telegram
async function checkAuth() {
    // Simulasi auth - di real implementation, ini akan cek session
    const userId = prompt('Masukkan Telegram ID Anda:');
    if (userId) {
        // Cek apakah user adalah owner
        const allowedIds = [7998861975]; // Sesuaikan dengan config
        if (allowedIds.includes(parseInt(userId))) {
            currentUser = { id: userId, username: 'owner' };
            loadDashboard();
        } else {
            alert('Anda tidak memiliki akses!');
            document.body.innerHTML = '<h1 style="text-align: center; margin-top: 50px;">Akses Ditolak</h1>';
        }
    }
}

// Switch page
function switchPage(page) {
    currentPage = page;
    
    // Update menu active
    document.querySelectorAll('.sidebar-menu li').forEach(item => {
        if (item.dataset.page === page) {
            item.classList.add('active');
        } else {
            item.classList.remove('active');
        }
    });
    
    // Show page
    document.querySelectorAll('.page').forEach(p => {
        p.classList.remove('active');
    });
    document.getElementById(`${page}Page`).classList.add('active');
    
    // Load page data
    switch(page) {
        case 'dashboard':
            loadDashboard();
            break;
        case 'users':
            loadUsersData();
            break;
        case 'stok':
            loadStokData();
            break;
        case 'bots':
            loadBotsData();
            break;
    }
}

// Load dashboard
async function loadDashboard() {
    try {
        // Load stats
        const [usersRes, stokRes, botsRes] = await Promise.all([
            fetch('/api/users/'),
            fetch('/api/stok/stats'),
            fetch('/api/bots/stats')
        ]);
        
        const users = await usersRes.json();
        const stok = await stokRes.json();
        const bots = await botsRes.json();
        
        // Update stats
        document.getElementById('totalUsers').textContent = users.data?.length || 0;
        document.getElementById('totalStok').textContent = stok.data?.total || 0;
        document.getElementById('availableStok').textContent = stok.data?.available || 0;
        document.getElementById('totalBots').textContent = bots.data?.total || 0;
        
        // Load recent activity
        loadRecentActivity();
    } catch (error) {
        console.error('Error loading dashboard:', error);
    }
}

// Load recent activity
async function loadRecentActivity() {
    try {
        const res = await fetch('/api/users/transactions?limit=10');
        const data = await res.json();
        
        const tbody = document.getElementById('recentActivity');
        tbody.innerHTML = '';
        
        if (data.data && data.data.length > 0) {
            data.data.forEach(tx => {
                tbody.innerHTML += `
                    <tr>
                        <td>${new Date(tx.created_at).toLocaleString()}</td>
                        <td>${tx.user_id}</td>
                        <td>${tx.type}</td>
                        <td>${tx.amount}</td>
                    </tr>
                `;
            });
        } else {
            tbody.innerHTML = '<tr><td colspan="4" style="text-align: center;">No recent activity</td></tr>';
        }
    } catch (error) {
        console.error('Error loading activity:', error);
    }
}

// Load users data
async function loadUsersData() {
    try {
        const res = await fetch('/api/users/');
        const data = await res.json();
        
        const tbody = document.getElementById('usersTableBody');
        tbody.innerHTML = '';
        
        if (data.data && data.data.length > 0) {
            data.data.forEach(user => {
                tbody.innerHTML += `
                    <tr>
                        <td>${user.user_id}</td>
                        <td>@${user.username || '-'}</td>
                        <td>${user.full_name || '-'}</td>
                        <td>${user.balance}</td>
                        <td>${user.total_gacha}</td>
                        <td>${user.total_claim}</td>
                        <td>
                            <span class="badge ${user.is_banned ? 'badge-danger' : 'badge-success'}">
                                ${user.is_banned ? 'Banned' : 'Active'}
                            </span>
                        </td>
                        <td>
                            <div class="action-buttons">
                                <button class="btn btn-primary btn-sm" onclick="editUserBalance(${user.user_id})">
                                    <i class="fas fa-edit"></i>
                                </button>
                                <button class="btn btn-danger btn-sm" onclick="deleteUser(${user.user_id})">
                                    <i class="fas fa-trash"></i>
                                </button>
                            </div>
                        </td>
                    </tr>
                `;
            });
        } else {
            tbody.innerHTML = '<tr><td colspan="8" style="text-align: center;">No users found</td></tr>';
        }
    } catch (error) {
        console.error('Error loading users:', error);
    }
}

// Edit user balance
function editUserBalance(userId) {
    const modal = document.getElementById('balanceModal');
    document.getElementById('balanceUserId').value = userId;
    document.getElementById('balanceAmount').value = '';
    document.getElementById('balanceAction').value = 'add';
    modal.classList.add('active');
}

// Submit balance update
async function submitBalanceUpdate() {
    const userId = document.getElementById('balanceUserId').value;
    const amount = parseInt(document.getElementById('balanceAmount').value);
    const action = document.getElementById('balanceAction').value;
    const description = document.getElementById('balanceDescription').value;
    
    if (!amount && action !== 'reset') {
        alert('Please enter amount');
        return;
    }
    
    try {
        const res = await fetch(`/api/users/${userId}/balance`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ amount, action, description })
        });
        
        const data = await res.json();
        
        if (data.success) {
            alert('Balance updated successfully');
            closeModal();
            loadUsersData();
        } else {
            alert(data.message || 'Failed to update balance');
        }
    } catch (error) {
        console.error('Error updating balance:', error);
        alert('Error updating balance');
    }
}

// Delete user
async function deleteUser(userId) {
    if (!confirm('Are you sure you want to delete this user?')) return;
    
    try {
        const res = await fetch(`/api/users/${userId}`, { method: 'DELETE' });
        const data = await res.json();
        
        if (data.success) {
            alert('User deleted successfully');
            loadUsersData();
        } else {
            alert(data.message || 'Failed to delete user');
        }
    } catch (error) {
        console.error('Error deleting user:', error);
        alert('Error deleting user');
    }
}

// Load stok data
async function loadStokData(search = '') {
    try {
        let url = '/api/stok/';
        if (search) {
            url = `/api/stok/search?q=${encodeURIComponent(search)}`;
        }
        
        const res = await fetch(url);
        const data = await res.json();
        
        const tbody = document.getElementById('stokTableBody');
        tbody.innerHTML = '';
        
        if (data.data && data.data.length > 0) {
            data.data.forEach(item => {
                const statusClass = {
                    'available': 'badge-available',
                    'claimed': 'badge-claimed',
                    'reserved': 'badge-reserved'
                }[item.status] || '';
                
                tbody.innerHTML += `
                    <tr>
                        <td>${item.id}</td>
                        <td>${item.username}</td>
                        <td>
                            <span class="badge ${statusClass}">${item.status}</span>
                        </td>
                        <td>${item.claimed_by || '-'}</td>
                        <td>${item.price || 0}</td>
                        <td>${item.category || '-'}</td>
                        <td>${new Date(item.created_at).toLocaleDateString()}</td>
                        <td>
                            <div class="action-buttons">
                                <button class="btn btn-primary btn-sm" onclick="editStok(${item.id})">
                                    <i class="fas fa-edit"></i>
                                </button>
                                <button class="btn btn-danger btn-sm" onclick="deleteStok(${item.id})">
                                    <i class="fas fa-trash"></i>
                                </button>
                            </div>
                        </td>
                    </tr>
                `;
            });
        } else {
            tbody.innerHTML = '<tr><td colspan="8" style="text-align: center;">No stok found</td></tr>';
        }
    } catch (error) {
        console.error('Error loading stok:', error);
    }
}

// Add stok
function showAddStokModal() {
    const modal = document.getElementById('stokModal');
    document.getElementById('stokForm').reset();
    document.getElementById('stokModalTitle').textContent = 'Add Usernames';
    document.getElementById('stokId').value = '';
    modal.classList.add('active');
}

// Edit stok
function editStok(id) {
    // Fetch stok data and populate form
    fetch(`/api/stok/${id}`)
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                const modal = document.getElementById('stokModal');
                document.getElementById('stokModalTitle').textContent = 'Edit Username';
                document.getElementById('stokId').value = id;
                document.getElementById('stokUsernames').value = data.data.username;
                document.getElementById('stokStatus').value = data.data.status;
                document.getElementById('stokPrice').value = data.data.price;
                document.getElementById('stokCategory').value = data.data.category || '';
                document.getElementById('stokTags').value = data.data.tags || '';
                modal.classList.add('active');
            }
        })
        .catch(error => console.error('Error loading stok:', error));
}

// Submit stok form
async function submitStokForm() {
    const id = document.getElementById('stokId').value;
    const usernames = document.getElementById('stokUsernames').value;
    const status = document.getElementById('stokStatus').value;
    const price = document.getElementById('stokPrice').value;
    const category = document.getElementById('stokCategory').value;
    const tags = document.getElementById('stokTags').value;
    
    if (!usernames) {
        alert('Please enter usernames');
        return;
    }
    
    let url = '/api/stok/';
    let method = 'POST';
    let body = { usernames };
    
    if (id) {
        url = `/api/stok/${id}`;
        method = 'PUT';
        body = { status, price, category, tags };
    }
    
    try {
        const res = await fetch(url, {
            method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        
        const data = await res.json();
        
        if (data.success) {
            alert(data.message || 'Success');
            closeModal();
            loadStokData();
        } else {
            alert(data.message || 'Failed');
        }
    } catch (error) {
        console.error('Error submitting form:', error);
        alert('Error submitting form');
    }
}

// Delete stok
async function deleteStok(id) {
    if (!confirm('Are you sure you want to delete this username?')) return;
    
    try {
        const res = await fetch(`/api/stok/${id}`, { method: 'DELETE' });
        const data = await res.json();
        
        if (data.success) {
            alert('Username deleted successfully');
            loadStokData();
        } else {
            alert(data.message || 'Failed to delete');
        }
    } catch (error) {
        console.error('Error deleting stok:', error);
        alert('Error deleting stok');
    }
}

// Load bots data
async function loadBotsData() {
    try {
        const res = await fetch('/api/bots/');
        const data = await res.json();
        
        // Update stats
        if (data.stats) {
            document.getElementById('totalBotsCount').textContent = data.stats.total || 0;
            document.getElementById('mainBotsCount').textContent = data.stats.main || 0;
            document.getElementById('cloneBotsCount').textContent = data.stats.clone || 0;
        }
        
        const tbody = document.getElementById('botsTableBody');
        tbody.innerHTML = '';
        
        if (data.data && data.data.length > 0) {
            data.data.forEach(bot => {
                tbody.innerHTML += `
                    <tr>
                        <td>${bot.id}</td>
                        <td>@${bot.username || 'Unknown'}</td>
                        <td>${bot.bot_id || '-'}</td>
                        <td>${bot.api_id}</td>
                        <td>${bot.bot_token.substring(0, 15)}...</td>
                        <td>
                            <span class="badge ${bot.is_main ? 'badge-main' : 'badge-clone'}">
                                ${bot.is_main ? 'Main' : 'Clone'}
                            </span>
                        </td>
                        <td>
                            <span class="badge ${bot.status === 'active' ? 'badge-success' : 'badge-danger'}">
                                ${bot.status || 'active'}
                            </span>
                        </td>
                        <td>
                            ${!bot.is_main ? `
                                <button class="btn btn-danger btn-sm" onclick="deleteBot('${bot.bot_token}')">
                                    <i class="fas fa-trash"></i>
                                </button>
                            ` : '-'}
                        </td>
                    </tr>
                `;
            });
        } else {
            tbody.innerHTML = '<tr><td colspan="8" style="text-align: center;">No bots found</td></tr>';
        }
    } catch (error) {
        console.error('Error loading bots:', error);
    }
}

// Show add bot modal
function showAddBotModal() {
    const modal = document.getElementById('botModal');
    document.getElementById('botForm').reset();
    modal.classList.add('active');
}

// Submit bot form
async function submitBotForm() {
    const apiId = document.getElementById('botApiId').value;
    const apiHash = document.getElementById('botApiHash').value;
    const botToken = document.getElementById('botToken').value;
    
    if (!apiId || !apiHash || !botToken) {
        alert('Please fill all fields');
        return;
    }
    
    try {
        const res = await fetch('/api/bots/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ api_id: apiId, api_hash: apiHash, bot_token: botToken })
        });
        
        const data = await res.json();
        
        if (data.success) {
            alert('Bot added successfully');
            closeModal();
            loadBotsData();
        } else {
            alert(data.message || 'Failed to add bot');
        }
    } catch (error) {
        console.error('Error adding bot:', error);
        alert('Error adding bot');
    }
}

// Delete bot
async function deleteBot(botToken) {
    if (!confirm('Are you sure you want to delete this bot?')) return;
    
    try {
        const res = await fetch(`/api/bots/${encodeURIComponent(botToken)}`, {
            method: 'DELETE'
        });
        
        const data = await res.json();
        
        if (data.success) {
            alert('Bot deleted successfully');
            loadBotsData();
        } else {
            alert(data.message || 'Failed to delete bot');
        }
    } catch (error) {
        console.error('Error deleting bot:', error);
        alert('Error deleting bot');
    }
}

// Restart bots
async function restartBots() {
    if (!confirm('Restart all bots? This may take a moment.')) return;
    
    try {
        const res = await fetch('/api/bots/restart', { method: 'POST' });
        const data = await res.json();
        
        if (data.success) {
            alert('Restart signal sent');
        } else {
            alert(data.message || 'Failed to restart');
        }
    } catch (error) {
        console.error('Error restarting bots:', error);
        alert('Error restarting bots');
    }
}

// Close modal
function closeModal() {
    document.querySelectorAll('.modal').forEach(modal => {
        modal.classList.remove('active');
    });
}
