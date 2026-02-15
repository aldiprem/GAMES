const API_URL = 'http://207.180.194.191/api/stats';
const UPDATE_INTERVAL = 5000;

// State
let lastData = null;
let retryCount = 0;
const MAX_RETRIES = 3;

// Elemen DOM
const totalUsersEl = document.getElementById('total-users');
const usersTodayEl = document.getElementById('users-today');
const recentUsersList = document.getElementById('recent-users-list');
const lastUpdatedEl = document.getElementById('last-updated');
const statusIndicator = document.getElementById('status-indicator');
const statusText = document.getElementById('status-text');

// Format tanggal
function formatDate(dateString) {
  const date = new Date(dateString);
  return date.toLocaleString('id-ID', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
}

// Update status koneksi
function updateConnectionStatus(status, message) {
  statusIndicator.className = 'status-indicator ' + status;
  statusText.textContent = message;
}

// Animasi angka
function animateNumber(element, target) {
  const current = parseInt(element.textContent) || 0;
  if (current === target) return;

  const increment = target > current ? 1 : -1;
  const steps = Math.abs(target - current);
  const duration = 1000;
  const interval = Math.max(10, Math.floor(duration / steps));

  let currentNum = current;
  const timer = setInterval(() => {
    currentNum += increment;
    element.textContent = currentNum;

    if (currentNum === target) {
      clearInterval(timer);
    }
  }, interval);
}

// Render tabel user terbaru
function renderRecentUsers(users) {
  if (!users || users.length === 0) {
    recentUsersList.innerHTML = `
            <tr>
                <td colspan="4" class="loading">Belum ada pengguna</td>
            </tr>
        `;
    return;
  }

  let html = '';
  users.forEach(user => {
    const username = user.username ? '@' + user.username : '-';
    const fullname = user.fullname || '-';
    const joinedAt = formatDate(user.joined_at);

    html += `
            <tr>
                <td>${user.user_id}</td>
                <td>${fullname}</td>
                <td>${username}</td>
                <td>${joinedAt}</td>
            </tr>
        `;
  });

  recentUsersList.innerHTML = html;
}

// Ambil data dari API
async function fetchStats() {
  try {
    updateConnectionStatus('checking', 'Menghubungi server...');

    console.log('Mengakses API:', API_URL);

    const response = await fetch(API_URL, {
      method: 'GET',
      mode: 'cors',
      headers: {
        'Accept': 'application/json'
      }
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    console.log('Data diterima:', data);

    if (data.success) {
      // Update total users
      if (!lastData || lastData.total_users !== data.total_users) {
        animateNumber(totalUsersEl, data.total_users);
      } else {
        totalUsersEl.textContent = data.total_users;
      }

      // Update users today
      if (!lastData || lastData.users_today !== data.users_today) {
        animateNumber(usersTodayEl, data.users_today);
      } else {
        usersTodayEl.textContent = data.users_today;
      }

      // Update tabel user terbaru
      renderRecentUsers(data.recent_users);

      // Update last updated
      lastUpdatedEl.textContent = formatDate(data.last_updated);

      // Update status
      updateConnectionStatus('connected', 'Terhubung');

      // Reset retry count
      retryCount = 0;
      lastData = data;
    } else {
      throw new Error(data.error || 'Unknown error');
    }

  } catch (error) {
    console.error('Error fetching stats:', error);

    retryCount++;

    if (retryCount >= MAX_RETRIES) {
      updateConnectionStatus('disconnected', 'Gagal terhubung ke server');
      recentUsersList.innerHTML = `
                <tr>
                    <td colspan="4" class="loading">
                        ⚠️ Gagal terhubung ke server. Coba refresh halaman.
                    </td>
                </tr>
            `;
    } else {
      updateConnectionStatus('checking', `Mencoba lagi... (${retryCount}/${MAX_RETRIES})`);
    }
  }
}

// Inisialisasi
document.addEventListener('DOMContentLoaded', () => {
  // Ambil data pertama kali
  fetchStats();

  // Set interval untuk update berkala
  setInterval(fetchStats, UPDATE_INTERVAL);

  // Tambahkan event listener untuk retry manual
  statusIndicator.addEventListener('click', () => {
    if (statusIndicator.className.includes('disconnected')) {
      retryCount = 0;
      fetchStats();
    }
  });
});
