// Konfigurasi
const API_BASE_URL = 'https://logs-meets-charlie-wheels.trycloudflare.com';
let currentUser = null;
let currentPayload = null;
let paymentCheckInterval = null;
let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 3;

// Inisialisasi Telegram Web App
const tg = window.Telegram.WebApp;
tg.expand();
tg.ready();

// Warna tema Telegram
tg.setHeaderColor('#667eea');
tg.setBackgroundColor('#f8f9fa');

// Cek koneksi ke API sebelum melakukan apapun
async function checkApiConnection() {
    try {
        const response = await fetchWithTimeout(`${API_BASE_URL}/api/test`, {
            method: 'GET',
            timeout: 5000
        });
        
        if (response.ok) {
            console.log('✅ API Connection OK');
            return true;
        }
    } catch (error) {
        console.error('❌ API Connection Failed:', error);
        return false;
    }
}

// Fetch dengan timeout
async function fetchWithTimeout(url, options = {}) {
    const { timeout = 10000 } = options;
    
    const controller = new AbortController();
    const id = setTimeout(() => controller.abort(), timeout);
    
    try {
        const response = await fetch(url, {
            ...options,
            signal: controller.signal,
            mode: 'cors',
            credentials: 'omit',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                ...options.headers
            }
        });
        clearTimeout(id);
        return response;
    } catch (error) {
        clearTimeout(id);
        throw error;
    }
}

// Cek apakah user sudah login via Telegram
document.addEventListener('DOMContentLoaded', async function() {
    showLoading(true);
    
    // Cek koneksi API dulu
    const apiConnected = await checkApiConnection();
    if (!apiConnected) {
        showError('Tidak dapat terhubung ke server. Periksa koneksi internet Anda.');
        showLoading(false);
        return;
    }
    
    if (tg.initDataUnsafe && tg.initDataUnsafe.user) {
        await authenticateUser();
    } else {
        document.getElementById('loginBtn').style.display = 'block';
        showError('Silakan login melalui Telegram terlebih dahulu');
        showLoading(false);
    }
});

// Event Listeners
document.getElementById('loginBtn').addEventListener('click', () => {
    tg.openTelegramLink('https://t.me/fTamous_bot');
});

document.getElementById('continueBtn').addEventListener('click', showInvoicePreview);

document.getElementById('backBtn').addEventListener('click', () => {
    document.getElementById('invoicePreview').style.display = 'none';
    document.getElementById('mainContent').style.display = 'block';
    if (paymentCheckInterval) {
        clearInterval(paymentCheckInterval);
        document.getElementById('paymentModal').style.display = 'none';
    }
});

// Quick amount buttons
document.querySelectorAll('.quick-amount').forEach(btn => {
    btn.addEventListener('click', () => {
        document.getElementById('amountInput').value = btn.dataset.amount;
    });
});

// Format number dengan ribuan
function formatNumber(num) {
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ".");
}

async function authenticateUser(retryCount = 0) {
    try {
        const initData = tg.initData;
        console.log('Raw initData:', initData);

        if (!initData) {
            throw new Error('No initData from Telegram');
        }

        // Parse initData menjadi object
        const params = new URLSearchParams(initData);
        const authData = {};

        // Ambil semua parameter
        for (const [key, value] of params) {
            if (key === 'user') {
                try {
                    // Parse dulu jadi object, lalu stringify ulang tanpa spasi
                    const userObj = JSON.parse(value);
                    authData[key] = JSON.stringify(userObj);
                } catch (e) {
                    authData[key] = value;
                }
            } else {
                authData[key] = value;
            }
        }

        console.log('Sending auth data:', authData);

        const response = await fetchWithTimeout(`${API_BASE_URL}/api/auth`, {
            method: 'POST',
            body: JSON.stringify(authData),
            timeout: 10000
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const responseData = await response.json();
        console.log('Auth response:', responseData);

        if (responseData.error) {
            throw new Error(responseData.error);
        }

        currentUser = responseData;
        updateUserInfo();
        document.getElementById('mainContent').style.display = 'block';
        document.getElementById('historySection').style.display = 'block';
        await loadTransactionHistory();
        showSuccess(`Selamat datang, ${currentUser.first_name || currentUser.username}!`);
        
        // Reset reconnect attempts on success
        reconnectAttempts = 0;
        
    } catch (error) {
        console.error('Auth error:', error);
        
        if (error.name === 'AbortError') {
            showError('Koneksi timeout. Periksa koneksi internet Anda.');
        } else if (retryCount < MAX_RECONNECT_ATTEMPTS) {
            // Retry connection
            reconnectAttempts++;
            showError(`Koneksi gagal. Mencoba ulang... (${retryCount + 1}/${MAX_RECONNECT_ATTEMPTS})`);
            setTimeout(() => authenticateUser(retryCount + 1), 2000);
        } else {
            showError('Gagal terhubung ke server. Silakan refresh halaman.');
            document.getElementById('loginBtn').style.display = 'block';
        }
    } finally {
        showLoading(false);
    }
}

// Update tampilan user info
function updateUserInfo() {
    if (currentUser) {
        const userInfo = document.getElementById('userInfo');
        const loginBtn = document.getElementById('loginBtn');

        document.getElementById('userName').textContent = 
            currentUser.first_name || currentUser.username || `User ${currentUser.id}`;
        document.getElementById('userUsername').textContent = 
            currentUser.username ? `@${currentUser.username}` : '';
        document.getElementById('userBalance').textContent = formatNumber(currentUser.balance);

        userInfo.style.display = 'flex';
        loginBtn.style.display = 'none';
    }
}

// Tampilkan preview invoice
function showInvoicePreview() {
    const amount = parseInt(document.getElementById('amountInput').value);

    if (isNaN(amount) || amount < 1 || amount > 2500) {
        showError('Masukkan jumlah yang valid (1-2500)');
        return;
    }

    document.getElementById('invoiceTitle').textContent = `Deposit ${amount} Stars`;
    document.getElementById('invoiceAmount').textContent = `${formatNumber(amount)} ⭐`;
    document.getElementById('invoiceTotal').textContent = `${formatNumber(amount)} ⭐`;
    document.getElementById('payAmount').textContent = formatNumber(amount);

    document.getElementById('mainContent').style.display = 'none';
    document.getElementById('invoicePreview').style.display = 'block';
}

// Proses pembayaran
async function processPayment() {
    const amount = parseInt(document.getElementById('amountInput').value);

    if (!currentUser) {
        showError('Silakan login terlebih dahulu');
        return;
    }

    showLoading(true);

    try {
        const response = await fetchWithTimeout(`${API_BASE_URL}/api/create-deposit`, {
            method: 'POST',
            body: JSON.stringify({
                telegram_id: currentUser.id,
                amount: amount
            }),
            timeout: 15000
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        console.log('Deposit response:', data);

        if (data.success) {
            // Extract payload dari payment link
            const paymentLink = data.payment_link;
            currentPayload = data.payload || paymentLink.split('$')[1] || paymentLink.split('/').pop();

            // Set link pembayaran ke tombol
            document.getElementById('paymentLink').href = paymentLink;

            // Tampilkan modal processing
            document.getElementById('paymentModal').style.display = 'flex';
            document.getElementById('paymentStatus').textContent = 'Menunggu pembayaran...';

            // Buka link pembayaran di tab baru
            window.open(paymentLink, '_blank');

            // Mulai pengecekan status pembayaran
            startPaymentCheck(currentPayload);

            showSuccess('Silakan selesaikan pembayaran di jendela yang terbuka');
        } else {
            showError(data.error || 'Gagal membuat deposit');
        }
    } catch (error) {
        console.error('Payment error:', error);
        if (error.name === 'AbortError') {
            showError('Koneksi timeout. Silakan coba lagi.');
        } else {
            showError('Koneksi error: ' + error.message);
        }
    } finally {
        showLoading(false);
    }
}

// Event listener untuk tombol bayar
document.getElementById('payBtn').addEventListener('click', function(e) {
    e.preventDefault();
    processPayment();
});

// Cek status pembayaran
function startPaymentCheck(payload) {
    if (paymentCheckInterval) {
        clearInterval(paymentCheckInterval);
    }

    let checkCount = 0;
    const maxChecks = 60; // Maksimal 3 menit (60 x 3 detik)

    paymentCheckInterval = setInterval(async () => {
        checkCount++;

        try {
            const response = await fetchWithTimeout(`${API_BASE_URL}/api/check-transaction`, {
                method: 'POST',
                body: JSON.stringify({ payload }),
                timeout: 5000
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            if (data.status === 'completed') {
                clearInterval(paymentCheckInterval);
                document.getElementById('paymentModal').style.display = 'none';

                // Update saldo user
                currentUser.balance += data.amount;
                updateUserInfo();

                // Load ulang riwayat
                await loadTransactionHistory();

                // Kembali ke halaman utama
                document.getElementById('invoicePreview').style.display = 'none';
                document.getElementById('mainContent').style.display = 'block';

                showSuccess(`Deposit ${formatNumber(data.amount)} ⭐ berhasil!`);
                
                // Kirim notifikasi ke Telegram
                tg.HapticFeedback.notificationOccurred('success');
                
                return;
            }

            document.getElementById('paymentStatus').textContent = 
                `Menunggu pembayaran... (${checkCount}/${maxChecks})`;

            if (checkCount >= maxChecks) {
                clearInterval(paymentCheckInterval);
                document.getElementById('paymentModal').style.display = 'none';
                showError('Waktu pembayaran habis. Silakan coba lagi.');
            }

        } catch (error) {
            console.error('Error checking payment:', error);
            // Don't stop interval on error, just continue
        }
    }, 3000); // Cek setiap 3 detik
}

// Batalkan pengecekan pembayaran
function cancelPaymentCheck() {
    if (paymentCheckInterval) {
        clearInterval(paymentCheckInterval);
    }
    document.getElementById('paymentModal').style.display = 'none';
    showError('Pembayaran dibatalkan');
}

// Load riwayat transaksi
async function loadTransactionHistory() {
    if (!currentUser) return;

    try {
        const response = await fetchWithTimeout(`${API_BASE_URL}/api/user/${currentUser.id}`, {
            method: 'GET',
            timeout: 5000
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        const historyList = document.getElementById('historyList');
        historyList.innerHTML = '';

        if (data.transactions && data.transactions.length > 0) {
            data.transactions.forEach(trans => {
                const item = document.createElement('div');
                item.className = 'history-item';
                item.innerHTML = `
                    <div class="history-info">
                        <div class="history-amount">+${formatNumber(trans.amount)} ⭐</div>
                        <div class="history-date">${trans.completed_at || 'Pending'}</div>
                    </div>
                    <div class="history-status">
                        <span class="status-badge success">✅ Selesai</span>
                    </div>
                `;
                historyList.appendChild(item);
            });
        } else {
            historyList.innerHTML = '<p style="text-align: center; color: #999; padding: 20px;">Belum ada transaksi</p>';
        }
    } catch (error) {
        console.error('Error loading history:', error);
        // Don't show error to user for history loading
    }
}

// Utility functions
function showLoading(show) {
    const loadingEl = document.getElementById('loading');
    const mainContent = document.getElementById('mainContent');
    
    if (loadingEl) {
        loadingEl.style.display = show ? 'block' : 'none';
    }
    
    if (mainContent) {
        if (show) {
            mainContent.style.opacity = '0.5';
            mainContent.style.pointerEvents = 'none';
        } else {
            mainContent.style.opacity = '1';
            mainContent.style.pointerEvents = 'auto';
        }
    }
}

function showError(message) {
    document.getElementById('errorMessage').textContent = message;
    document.getElementById('errorModal').style.display = 'flex';
    
    // Haptic feedback untuk error
    try {
        tg.HapticFeedback.notificationOccurred('error');
    } catch (e) {}

    setTimeout(() => {
        document.getElementById('errorModal').style.display = 'none';
    }, 5000);
}

function showSuccess(message) {
    document.getElementById('successMessage').textContent = message;
    document.getElementById('successModal').style.display = 'flex';
    
    // Haptic feedback untuk success
    try {
        tg.HapticFeedback.notificationOccurred('success');
    } catch (e) {}

    setTimeout(() => {
        document.getElementById('successModal').style.display = 'none';
    }, 5000);
}

function closeModal() {
    document.getElementById('errorModal').style.display = 'none';
    document.getElementById('successModal').style.display = 'none';
    document.getElementById('paymentModal').style.display = 'none';
}

// Handle tombol back Telegram
tg.BackButton.onClick(function() {
    if (document.getElementById('invoicePreview').style.display === 'block') {
        document.getElementById('invoicePreview').style.display = 'none';
        document.getElementById('mainContent').style.display = 'block';
        tg.BackButton.hide();
    } else {
        tg.close();
    }
});

// Tampilkan back button jika perlu
function showBackButton() {
    if (document.getElementById('invoicePreview').style.display === 'block') {
        tg.BackButton.show();
    } else {
        tg.BackButton.hide();
    }
}

// Main button Telegram
tg.MainButton.setText('Tutup');
tg.MainButton.onClick(function() {
    tg.close();
});