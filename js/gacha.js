// Konfigurasi
const API_BASE_URL = 'https://fragrances-dir-enforcement-put.trycloudflare.com';
let currentUser = null;
let currentPayload = null;
let paymentCheckInterval = null;

// Inisialisasi Telegram Web App
const tg = window.Telegram.WebApp;
tg.expand();

// Cek apakah user sudah login via Telegram
if (tg.initDataUnsafe && tg.initDataUnsafe.user) {
  const user = tg.initDataUnsafe.user;
  authenticateUser(user);
} else {
  document.getElementById('loginBtn').style.display = 'block';
}

// Event Listeners
document.getElementById('loginBtn').addEventListener('click', () => {
  tg.openTelegramLink('https://t.me/YourBotUsername'); // Ganti dengan username bot Anda
});

document.getElementById('continueBtn').addEventListener('click', showInvoicePreview);

document.getElementById('payBtn').addEventListener('click', processPayment);

document.getElementById('backBtn').addEventListener('click', () => {
  document.getElementById('invoicePreview').style.display = 'none';
  document.getElementById('mainContent').style.display = 'block';
});

// Quick amount buttons
document.querySelectorAll('.quick-amount').forEach(btn => {
  btn.addEventListener('click', () => {
    document.getElementById('amountInput').value = btn.dataset.amount;
  });
});

async function authenticateUser(telegramUser) {
  showLoading(true);

  try {
    const initData = tg.initData;
    console.log('Raw initData:', initData);

    // Parse initData menjadi object
    const params = new URLSearchParams(initData);
    const authData = {};
    for (const [key, value] of params) {
      authData[key] = value;
    }

    // Gabungkan dengan user data (HAPUS DUPLIKASI!)
    const requestData = {
      ...authData,
      // Jangan tambahkan user data terpisah karena sudah ada di authData.user
    };

    console.log('Sending data:', requestData);

    const response = await fetch(`${API_BASE_URL}/api/auth`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json', // Kembali ke JSON
      },
      body: JSON.stringify(requestData)
    });

    const responseData = await response.json();
    console.log('Response:', responseData);

    if (response.ok) {
      currentUser = responseData;
      updateUserInfo();
      document.getElementById('mainContent').style.display = 'block';
      document.getElementById('historySection').style.display = 'block';
      loadTransactionHistory();
    } else {
      showError('Gagal autentikasi: ' + (responseData.error || 'Unknown error'));
    }
  } catch (error) {
    showError('Koneksi error: ' + error.message);
    console.error('Auth error:', error);
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
    document.getElementById('userBalance').textContent = `${currentUser.balance} ⭐`;

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
  document.getElementById('invoiceAmount').textContent = `${amount} ⭐`;
  document.getElementById('invoiceTotal').textContent = `${amount} ⭐`;
  document.getElementById('payAmount').textContent = amount;

  // Buat border struktur invoice
  const borderEl = document.getElementById('invoiceBorder');
  borderEl.innerHTML = '';

  for (let i = 0; i < 3; i++) {
    const row = document.createElement('div');
    row.style.display = 'flex';
    row.style.justifyContent = 'space-between';
    row.style.marginBottom = '10px';
    row.style.padding = '5px';
    row.style.background = 'white';
    row.style.borderRadius = '5px';

    row.innerHTML = `
            <span>Item ${i+1}</span>
            <span>${amount/3} ⭐</span>
        `;
    borderEl.appendChild(row);
  }

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
    const response = await fetch(`${API_BASE_URL}/api/create-deposit`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        telegram_id: currentUser.id,
        amount: amount
      })
    });

    const data = await response.json();

    if (data.success) {
      // Simpan payload untuk pengecekan
      currentPayload = data.payment_link.split('$')[1];

      // Buka link pembayaran
      window.open(data.payment_link, '_blank');

      // Mulai pengecekan status pembayaran
      startPaymentCheck(currentPayload);

      showSuccess('Silakan selesaikan pembayaran di jendela yang terbuka');
    } else {
      showError(data.error || 'Gagal membuat deposit');
    }
  } catch (error) {
    showError('Koneksi error');
    console.error(error);
  } finally {
    showLoading(false);
  }
}

// Cek status pembayaran
function startPaymentCheck(payload) {
  if (paymentCheckInterval) {
    clearInterval(paymentCheckInterval);
  }

  paymentCheckInterval = setInterval(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/check-transaction`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ payload })
      });

      const data = await response.json();

      if (data.status === 'completed') {
        clearInterval(paymentCheckInterval);

        // Update saldo user
        currentUser.balance += data.amount;
        updateUserInfo();

        // Load ulang riwayat
        loadTransactionHistory();

        // Kembali ke halaman utama
        document.getElementById('invoicePreview').style.display = 'none';
        document.getElementById('mainContent').style.display = 'block';

        showSuccess(`Deposit ${data.amount} ⭐ berhasil!`);
      }
    } catch (error) {
      console.error('Error checking payment:', error);
    }
  }, 3000); // Cek setiap 3 detik
}

// Load riwayat transaksi
async function loadTransactionHistory() {
  if (!currentUser) return;

  try {
    const response = await fetch(`${API_BASE_URL}/api/user/${currentUser.id}`);
    const data = await response.json();

    const historyList = document.getElementById('historyList');
    historyList.innerHTML = '';

    if (data.transactions && data.transactions.length > 0) {
      data.transactions.forEach(trans => {
        const item = document.createElement('div');
        item.className = 'history-item';
        item.innerHTML = `
                    <div>
                        <div class="history-amount">+${trans.amount} ⭐</div>
                        <div class="history-date">${trans.completed_at}</div>
                    </div>
                    <div>✅</div>
                `;
        historyList.appendChild(item);
      });
    } else {
      historyList.innerHTML = '<p style="text-align: center; color: #999;">Belum ada transaksi</p>';
    }
  } catch (error) {
    console.error('Error loading history:', error);
  }
}

// Utility functions
function showLoading(show) {
  document.getElementById('loading').style.display = show ? 'block' : 'none';
  if (show) {
    document.getElementById('mainContent').style.opacity = '0.5';
    document.getElementById('mainContent').style.pointerEvents = 'none';
  } else {
    document.getElementById('mainContent').style.opacity = '1';
    document.getElementById('mainContent').style.pointerEvents = 'auto';
  }
}

function showError(message) {
  document.getElementById('errorMessage').textContent = message;
  document.getElementById('errorModal').style.display = 'flex';

  setTimeout(() => {
    document.getElementById('errorModal').style.display = 'none';
  }, 5000);
}

function showSuccess(message) {
  document.getElementById('successMessage').textContent = message;
  document.getElementById('successModal').style.display = 'flex';

  setTimeout(() => {
    document.getElementById('successModal').style.display = 'none';
  }, 5000);
}

function closeModal() {
  document.getElementById('errorModal').style.display = 'none';
  document.getElementById('successModal').style.display = 'none';
}