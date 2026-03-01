// Global variables
let currentUser = null;
let currentPage = 'games';
let currentPaymentData = null;
let paymentCheckInterval = null;
let currentInvoiceMessageId = null;

// Initialize on load
document.addEventListener('DOMContentLoaded', function() {
    console.log('Gacha.js initialized');
    const demoUserId = 7998861975;
    
    loadUserData(demoUserId);
    loadPage('games');
    
    // Setup navigation
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const page = this.dataset.page;
            loadPage(page);
        });
    });
    
    // Setup quick amount buttons
    document.querySelectorAll('.amount-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const amount = this.dataset.amount;
            document.getElementById('depositAmount').value = amount;
        });
    });
});

// Load user data
async function loadUserData(userId) {
    try {
        console.log(`Loading user data for ID: ${userId}`);
        const response = await fetch(`/gacha/api/user/${userId}`);
        const data = await response.json();
        
        if (data.success) {
            currentUser = data.user;
            console.log('User data loaded:', currentUser);
            updateUI();
        } else {
            console.error('Failed to load user:', data.message);
            showError('Gagal memuat data user');
        }
    } catch (error) {
        console.error('Error loading user:', error);
        showError('Gagal terhubung ke server');
    }
}

// Update UI
function updateUI() {
    if (!currentUser) return;
    if (currentPage === 'profile') {
        renderProfilePage();
    }
}

// Load page
function loadPage(page) {
    currentPage = page;
    console.log(`Loading page: ${page}`);
    
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.page === page) {
            btn.classList.add('active');
        }
    });
    
    const mainContent = document.getElementById('mainContent');
    
    switch(page) {
        case 'games':
            mainContent.innerHTML = renderGamesPage();
            break;
        case 'gacha':
            mainContent.innerHTML = renderGachaPage();
            break;
        case 'profile':
            mainContent.innerHTML = renderProfilePage();
            break;
    }
}

// Render Games page
function renderGamesPage() {
    return `
        <div class="page">
            <div class="coming-soon">
                <i class="fas fa-gamepad"></i>
                <h2>Games</h2>
                <p>Fitur Games akan segera hadir!</p>
                <p style="margin-top: 20px; font-size: 14px; color: #999;">Coming Soon</p>
            </div>
        </div>
    `;
}

// Render Gacha page
function renderGachaPage() {
    return `
        <div class="page">
            <div class="gacha-container">
                <div class="gacha-header">
                    <h2>Gacha Username</h2>
                    <p>Dapatkan username random dengan harga menarik!</p>
                </div>
                
                <div class="balance-info">
                    <i class="fas fa-star"></i>
                    <span>Saldo Anda: <strong>${currentUser ? currentUser.balance : 0}</strong> ⭐</span>
                </div>
                
                <div class="gacha-preview">
                    <div class="gacha-preview-box">
                        <div class="preview-username">@username123</div>
                        <div class="preview-price">10 ⭐</div>
                    </div>
                </div>
                
                <button class="btn-primary btn-large" onclick="openGachaModal()">
                    <i class="fas fa-dice"></i> Mulai Gacha
                </button>
                
                <div class="gacha-info">
                    <h4>Informasi:</h4>
                    <ul>
                        <li>Harga bervariasi dari 1 - 200 ⭐</li>
                        <li>Username random dari database</li>
                        <li>Saldo akan otomatis terpotong</li>
                    </ul>
                </div>
            </div>
        </div>
    `;
}

// Render Profile page
function renderProfilePage() {
    if (!currentUser) {
        return '<div class="page"><div class="loading">Loading...</div></div>';
    }
    
    return `
        <div class="page">
            <div class="profile-header">
                <div class="profile-avatar">
                    <i class="fas fa-user-circle"></i>
                </div>
                <div class="profile-info">
                    <h3>${currentUser.full_name || 'User'}</h3>
                    <p>@${currentUser.username || 'username'}</p>
                    <p>ID: ${currentUser.user_id}</p>
                </div>
            </div>
            
            <div class="stats-grid">
                <div class="stat-card">
                    <i class="fas fa-star"></i>
                    <div class="stat-value">${currentUser.balance}</div>
                    <div class="stat-label">Saldo</div>
                </div>
                <div class="stat-card">
                    <i class="fas fa-database"></i>
                    <div class="stat-value">${currentUser.total_deposit || 0}</div>
                    <div class="stat-label">Total Deposit</div>
                </div>
                <div class="stat-card">
                    <i class="fas fa-dice"></i>
                    <div class="stat-value">${currentUser.total_gacha || 0}</div>
                    <div class="stat-label">Total Gacha</div>
                </div>
            </div>
            
            <div class="action-buttons">
                <button class="btn-primary" onclick="openDepositModal()">
                    <i class="fas fa-plus-circle"></i> Deposit
                </button>
                <button class="btn-secondary" onclick="refreshBalance()">
                    <i class="fas fa-sync-alt"></i> Refresh
                </button>
            </div>
            
            <h4 class="recent-title">Riwayat Deposit</h4>
            <div class="transactions-list">
                <div class="transaction-item">
                    <div class="transaction-icon">
                        <i class="fas fa-star"></i>
                    </div>
                    <div class="transaction-details">
                        <div class="transaction-title">Saldo Saat Ini</div>
                        <div class="transaction-date">${new Date().toLocaleDateString()}</div>
                    </div>
                    <div class="transaction-amount positive">${currentUser.balance} ⭐</div>
                </div>
            </div>
        </div>
    `;
}

// ============ DEPOSIT FUNCTIONS (DIPERBAIKI) ============
function openDepositModal() {
    document.getElementById('depositModal').classList.add('show');
}

function closeDepositModal() {
    document.getElementById('depositModal').classList.remove('show');
}

async function initDeposit() {
    const amount = document.getElementById('depositAmount').value;
    
    if (!amount || amount < 1) {
        showError('Masukkan jumlah yang valid (minimal 1 ⭐)');
        return;
    }
    
    if (amount > 2500) {
        showError('Maksimal deposit 2500 ⭐');
        return;
    }
    
    closeDepositModal();
    showLoading(true);
    
    try {
        console.log('Initiating deposit:', amount);
        const response = await fetch('/gacha/api/deposit/init', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: currentUser.user_id,
                amount: parseInt(amount)
            })
        });
        
        const data = await response.json();
        console.log('Deposit response:', data);
        
        if (data.success) {
            currentPaymentData = data;
            showPaymentModal(data);
        } else {
            showError('Gagal memproses deposit: ' + data.message);
        }
    } catch (error) {
        console.error('Error in initDeposit:', error);
        showError('Gagal terhubung ke server');
    } finally {
        showLoading(false);
    }
}

// ============ FUNGSI DEPOSIT STARS DENGAN LINK FORMAT BARU ============
function showPaymentModal(depositData) {
  const modal = document.getElementById('paymentModal');
  const paymentInfo = document.getElementById('paymentInfo');
  const paymentLinkContainer = document.getElementById('paymentLinkContainer');
  const paymentDetails = document.getElementById('paymentDetails');
  const payButton = document.getElementById('payButton');

  const expiredTime = new Date(Date.now() + 300000).toLocaleTimeString();

  // Gunakan payment_link dari response (format: https://t.me/$random_string)
  const telegramDeepLink = depositData.payment_link;

  paymentInfo.innerHTML = `
        <div class="payment-info-box">
            <p><strong>Jumlah Deposit:</strong> ${depositData.amount} ⭐</p>
            <p><strong>ID Transaksi:</strong> <span class="transaction-id">${depositData.transaction_id}</span></p>
            <p><strong>Batas Waktu:</strong> ${expiredTime}</p>
        </div>
    `;

  // Tampilkan instruksi
  paymentLinkContainer.innerHTML = `
        <div class="payment-steps" style="background: #f0f3ff; padding: 20px; border-radius: 15px; margin-bottom: 20px;">
            <h4 style="margin-bottom: 15px; color: #333;">📋 Langkah Pembayaran Stars:</h4>
            
            <div style="margin-bottom: 20px;">
                <div style="display: flex; align-items: center; margin-bottom: 15px;">
                    <div style="background: #667eea; color: white; width: 30px; height: 30px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin-right: 15px; font-weight: bold;">1</div>
                    <div style="flex: 1;">Klik tombol <strong>"Bayar ${depositData.amount} ⭐"</strong> di bawah</div>
                </div>
                
                <div style="display: flex; align-items: center; margin-bottom: 15px;">
                    <div style="background: #667eea; color: white; width: 30px; height: 30px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin-right: 15px; font-weight: bold;">2</div>
                    <div style="flex: 1;">Aplikasi Telegram akan terbuka</div>
                </div>
                
                <div style="display: flex; align-items: center; margin-bottom: 15px;">
                    <div style="background: #667eea; color: white; width: 30px; height: 30px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin-right: 15px; font-weight: bold;">3</div>
                    <div style="flex: 1;">Klik tombol <strong>"PAY"</strong> di invoice Telegram</div>
                </div>
                
                <div style="display: flex; align-items: center;">
                    <div style="background: #667eea; color: white; width: 30px; height: 30px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin-right: 15px; font-weight: bold;">4</div>
                    <div style="flex: 1;">Konfirmasi pembayaran dengan Stars Anda</div>
                </div>
            </div>
            
            <div style="background: #e8f0fe; padding: 15px; border-radius: 10px; margin-top: 15px;">
                <p style="margin-bottom: 10px; font-weight: 600;">💰 Total Pembayaran:</p>
                <p style="font-size: 24px; font-weight: bold; color: #667eea;">${depositData.amount} ⭐</p>
            </div>
        </div>
        
        <div class="payment-link-box" style="text-align: center; margin-top: 20px;">
            <p style="margin-bottom: 15px; color: #666;">Klik tombol di bawah untuk membayar dengan Stars:</p>
            
            <a href="${telegramDeepLink}" 
               target="_blank" 
               class="btn-primary btn-large payment-link-btn" 
               style="display: inline-flex; align-items: center; justify-content: center; gap: 10px; padding: 18px 30px; font-size: 18px; text-decoration: none; width: 100%; box-sizing: border-box;"
               onclick="startPaymentCheck('${depositData.payload}')">
                <i class="fab fa-telegram" style="font-size: 24px;"></i>
                Bayar ${depositData.amount} ⭐ dengan Stars
            </a>
            
            <p style="margin-top: 15px; font-size: 13px; color: #888;">
                <i class="fas fa-info-circle"></i> 
                Link pembayaran: <code style="background: #f0f0f0; padding: 3px 6px; border-radius: 4px;">${telegramDeepLink}</code>
            </p>
        </div>
    `;

  paymentDetails.innerHTML = `
        <div class="payment-details-box" style="background: #f8f9fa; border-radius: 10px; padding: 15px; font-size: 13px; margin-top: 20px;">
            <p><strong>🆔 Transaksi:</strong> <code style="background: #e9ecef; padding: 3px 6px; border-radius: 4px;">${depositData.transaction_id}</code></p>
            <p><strong>🤖 Bot:</strong> @${depositData.bot_username}</p>
            <p><strong>📅 Waktu:</strong> ${new Date().toLocaleString()}</p>
            <p><strong>⏱️ Kadaluarsa:</strong> ${expiredTime}</p>
        </div>
    `;

  payButton.style.display = 'inline-block';
  payButton.innerHTML = '<i class="fab fa-telegram"></i> Bayar dengan Stars';
  payButton.onclick = () => {
    window.open(telegramDeepLink, '_blank');
    startPaymentCheck(depositData.payload);
  };

  modal.classList.add('show');
}

function closePaymentModal() {
    document.getElementById('paymentModal').classList.remove('show');
    if (paymentCheckInterval) {
        clearInterval(paymentCheckInterval);
        paymentCheckInterval = null;
    }
    if (currentInvoiceMessageId) {
        currentInvoiceMessageId = null;
    }
    currentPaymentData = null;
    
    // Reset tampilan
    document.getElementById('paymentStatus').style.display = 'none';
    document.getElementById('paymentLinkContainer').style.display = 'block';
    document.getElementById('payButton').style.display = 'inline-block';
}

function startPaymentCheck(payload) {
    const paymentStatus = document.getElementById('paymentStatus');
    const paymentLinkContainer = document.getElementById('paymentLinkContainer');
    const payButton = document.getElementById('payButton');
    const paymentDetails = document.getElementById('paymentDetails');
    
    // Sembunyikan tombol bayar dan link, tampilkan status
    paymentLinkContainer.style.display = 'none';
    payButton.style.display = 'none';
    paymentStatus.style.display = 'block';
    
    // Tampilkan animasi loading
    paymentStatus.innerHTML = `
        <div class="spinner"></div>
        <p style="margin-top: 20px; font-weight: 600;">Menunggu pembayaran Anda...</p>
        <p style="color: #666; font-size: 14px; margin-top: 10px;">Silakan selesaikan pembayaran di aplikasi Telegram</p>
    `;
    
    if (paymentCheckInterval) clearInterval(paymentCheckInterval);
    
    paymentCheckInterval = setInterval(async () => {
        try {
            console.log('Checking payment status for:', payload);
            const response = await fetch(`/gacha/api/deposit/check/${payload}`);
            const data = await response.json();
            
            if (data.success && data.status === 'completed') {
                console.log('Payment completed!');
                clearInterval(paymentCheckInterval);
                paymentCheckInterval = null;
                
                paymentStatus.innerHTML = `
                    <i class="fas fa-check-circle" style="font-size: 64px; color: #10b981; margin-bottom: 20px;"></i>
                    <p style="color: #10b981; font-weight: bold; font-size: 18px;">✓ PEMBAYARAN BERHASIL!</p>
                    <p style="margin-top: 10px;">${data.amount} ⭐ telah ditambahkan ke saldo Anda</p>
                `;
                
                await loadUserData(currentUser.user_id);
                if (currentPage === 'profile') renderProfilePage();
                showSuccess(`Deposit ${data.amount} ⭐ berhasil!`);
                
                // Tutup modal setelah 3 detik
                setTimeout(closePaymentModal, 3000);
            }
        } catch (error) {
            console.error('Error checking payment:', error);
        }
    }, 3000); // Cek setiap 3 detik
    
    // Timeout setelah 5 menit
    setTimeout(() => {
        if (paymentCheckInterval) {
            clearInterval(paymentCheckInterval);
            paymentCheckInterval = null;
            paymentStatus.innerHTML = `
                <i class="fas fa-exclamation-circle" style="font-size: 48px; color: #f59e0b; margin-bottom: 20px;"></i>
                <p style="color: #f59e0b; font-weight: bold;">Waktu pembayaran habis</p>
                <p style="margin-top: 10px; color: #666;">Silakan coba lagi dengan deposit baru</p>
                <button class="btn-primary" onclick="closePaymentModal(); openDepositModal();" style="margin-top: 20px;">
                    <i class="fas fa-redo"></i> Coba Lagi
                </button>
            `;
        }
    }, 300000); // 5 menit
}

// ============ GACHA FUNCTIONS ============
function openGachaModal() {
    document.getElementById('gachaModal').classList.add('show');
    getRandomUsername();
}

function closeGachaModal() {
    document.getElementById('gachaModal').classList.remove('show');
    document.getElementById('gachaResult').style.display = 'none';
}

async function getRandomUsername() {
    try {
        const response = await fetch('/gacha/api/gacha/random');
        const data = await response.json();
        
        if (data.success) {
            document.querySelector('.username-display').textContent = '@' + data.username;
            document.querySelector('.price-display').textContent = data.price + ' ⭐';
            document.getElementById('spinButton').dataset.username = data.username;
            document.getElementById('spinButton').dataset.price = data.price;
        }
    } catch (error) {
        console.error('Error getting random username:', error);
    }
}

async function spinGacha() {
    const button = document.getElementById('spinButton');
    const username = button.dataset.username;
    const price = parseInt(button.dataset.price);
    
    if (!username || !price) {
        await getRandomUsername();
        return;
    }
    
    if (currentUser.balance < price) {
        showGachaResult('Saldo tidak mencukupi. Silakan deposit.', 'error');
        return;
    }
    
    try {
        console.log('Purchasing gacha:', {username, price});
        const response = await fetch('/gacha/api/gacha/purchase', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: currentUser.user_id,
                username: username,
                price: price
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showGachaResult(`Selamat! Anda mendapatkan @${username}`, 'success');
            currentUser.balance = data.new_balance;
            currentUser.total_gacha = (currentUser.total_gacha || 0) + 1;
            if (currentPage === 'profile') renderProfilePage();
            await getRandomUsername();
        } else {
            showGachaResult(data.message, 'error');
        }
    } catch (error) {
        console.error('Error purchasing gacha:', error);
        showGachaResult('Terjadi kesalahan', 'error');
    }
}

function showGachaResult(message, type) {
    const result = document.getElementById('gachaResult');
    result.textContent = message;
    result.className = 'gacha-result ' + type;
    result.style.display = 'block';
    setTimeout(() => { result.style.display = 'none'; }, 3000);
}

// ============ UTILITY FUNCTIONS ============
function showLoading(show) {
    // Implement loading indicator if needed
    console.log('Loading:', show);
}

function showSuccess(message) {
    document.getElementById('successMessage').textContent = message;
    document.getElementById('successModal').classList.add('show');
    setTimeout(closeSuccessModal, 3000);
}

function closeSuccessModal() {
    document.getElementById('successModal').classList.remove('show');
}

function showError(message) {
    document.getElementById('errorMessage').textContent = message;
    document.getElementById('errorModal').classList.add('show');
    setTimeout(closeErrorModal, 3000);
}

function closeErrorModal() {
    document.getElementById('errorModal').classList.remove('show');
}

async function refreshBalance() {
    if (currentUser) {
        await loadUserData(currentUser.user_id);
        showSuccess('Saldo diperbarui!');
    }
}

// Export functions to global scope
window.openDepositModal = openDepositModal;
window.closeDepositModal = closeDepositModal;
window.initDeposit = initDeposit;
window.closePaymentModal = closePaymentModal;
window.openGachaModal = openGachaModal;
window.closeGachaModal = closeGachaModal;
window.spinGacha = spinGacha;
window.closeSuccessModal = closeSuccessModal;
window.closeErrorModal = closeErrorModal;
window.refreshBalance = refreshBalance;
window.startPaymentCheck = startPaymentCheck;