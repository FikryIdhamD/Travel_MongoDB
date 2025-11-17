// static/js/main.js
const API = "http://127.0.0.1:8000/api";
let currentUser = null;

function apiUrl(endpoint) {
  const clean = endpoint.replace(/^\/+|\/+$/g, '');
  return `${API}/${clean}/`;
}

document.addEventListener("DOMContentLoaded", () => {
  checkAuth();
  document.getElementById("toggle-auth")?.addEventListener("click", toggleAuth);
  document.getElementById("authForm")?.addEventListener("submit", handleAuth);
  document.getElementById("searchForm")?.addEventListener("submit", searchSchedules);
});

function checkAuth() {
  const stored = localStorage.getItem("user");
  if (stored) {
    currentUser = JSON.parse(stored);
    if (currentUser.id) {
      showMainApp();
      return;
    }
  }
  showAuthForm();
}

function showAuthForm() {
  document.getElementById("auth-form").style.display = "block";
  document.getElementById("main-app").style.display = "none";
}

function showMainApp() {
  document.getElementById("auth-form").style.display = "none";
  document.getElementById("main-app").style.display = "block";
  document.getElementById("auth-section").innerHTML = `
    <div class="text-white">Hi, ${currentUser.name}!</div>
    <button class="btn btn-sm btn-outline-light ms-2" onclick="logout()">Logout</button>
  `;
  loadPopular();
  loadBookingHistory();
}

function logout() {
  localStorage.removeItem("user");
  location.reload();
}

function toggleAuth(e) {
  e.preventDefault();
  const isLogin = document.getElementById("auth-title").textContent === "Login";
  document.getElementById("auth-title").textContent = isLogin ? "Daftar" : "Login";
  document.getElementById("toggle-auth").textContent = isLogin ? "Sudah punya akun? Login" : "Belum punya akun? Daftar";
}

async function handleAuth(e) {
  e.preventDefault();
  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value;
  const isLogin = document.getElementById("auth-title").textContent === "Login";

  const endpoint = isLogin ? "users/login" : "users/register";
  const body = isLogin 
    ? { email, password } 
    : { name: email.split("@")[0], email, password, phone: "" };

  try {
    const res = await fetch(apiUrl(endpoint), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    });

    const data = await res.json();

    if (res.ok && data.user?.id) {
      localStorage.setItem("user", JSON.stringify(data.user));
      checkAuth();
    } else {
      alert(data.detail || "Gagal. Periksa email/password.");
    }
  } catch (err) {
    alert("Koneksi gagal");
  }
}

async function searchSchedules(e) {
  e.preventDefault();
  const params = new URLSearchParams({
    origin: document.getElementById("origin").value,
    destination: document.getElementById("destination").value,
    departure_date: document.getElementById("departure_date").value,
    type: document.getElementById("type").value
  });

  const url = apiUrl("schedules") + (params.toString() ? "?" + params : "");
  const res = await fetch(url);
  const schedules = await res.json();
  renderSchedules(schedules);
}

function renderSchedules(schedules) {
  const container = document.getElementById("results");
  container.innerHTML = schedules.length ? "<h5>Hasil Pencarian</h5>" : "<p class='text-center text-muted'>Tidak ada jadwal.</p>";

  schedules.forEach(s => {
    container.innerHTML += `
      <div class="card mb-3">
        <div class="card-body">
          <h6>${s.type.toUpperCase()} • ${s.operator || 'Unknown'}</h6>
          <p class="mb-1"><strong>${s.origin} → ${s.destination}</strong></p>
          <p class="mb-1">Berangkat: ${new Date(s.departure_date).toLocaleString('id-ID')}</p>
          <p class="mb-1 text-success fw-bold">Rp ${s.price.toLocaleString('id-ID')}</p>
          <p class="mb-2"><small>Tersedia: ${s.available_seats} kursi</small></p>
          <button class="btn btn-primary btn-sm" onclick="bookSchedule('${s.id}')">Pesan</button>
        </div>
      </div>`;
  });
}

async function bookSchedule(scheduleId) {
  if (!currentUser?.id) {
    alert("Login ulang untuk booking.");
    return;
  }

  const passengerName = prompt("Nama Penumpang:");
  if (!passengerName?.trim()) return;

  const countStr = prompt("Jumlah Penumpang:", "1");
  const passengerCount = parseInt(countStr);
  if (isNaN(passengerCount) || passengerCount < 1) {
    alert("Jumlah tidak valid");
    return;
  }

  const payload = {
    user_id: currentUser.id,
    schedule_id: scheduleId,
    passenger_name: passengerName.trim(),
    passenger_count: passengerCount
  };

  console.log("Booking payload:", payload); // DEBUG

  try {
    const res = await fetch(apiUrl("bookings"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    const data = await res.json();

    if (res.ok) {
      alert(`Booking berhasil! Kode: ${data.booking_code}`);
      loadBookingHistory();
    } else {
      alert(data.detail || "Gagal booking");
    }
  } catch (err) {
    alert("Koneksi gagal");
  }
}

async function loadPopular() {
  const res = await fetch(apiUrl("schedules/popular"));
  const popular = await res.json();
  const container = document.getElementById("popular");
  container.innerHTML = "<h5>Jadwal Populer</h5>";
  if (!popular.length) {
    container.innerHTML += "<p class='text-muted'>Belum ada data.</p>";
    return;
  }
  popular.forEach(p => {
    container.innerHTML += `
      <div class="alert alert-info p-2">
        <strong>${p.schedule.origin} → ${p.schedule.destination}</strong> (${p.schedule.type})<br>
        <small>${p.booking_count} booking • Rp ${p.total_revenue.toLocaleString('id-ID')}</small>
      </div>`;
  });
}

async function loadBookingHistory() {
  const res = await fetch(apiUrl("bookings"));
  const bookings = await res.json();
  const container = document.getElementById("booking-history");
  container.innerHTML = "<h5>Riwayat Booking</h5>";
  if (!bookings.length) {
    container.innerHTML += "<p class='text-muted'>Belum ada booking.</p>";
    return;
  }
  bookings.forEach(b => {
    container.innerHTML += `
      <div class="card mb-2">
        <div class="card-body py-2">
          <small><strong>${b.booking_code}</strong> • ${b.passenger_name} (${b.passenger_count}x)</small><br>
          <small>${b.schedule_info.origin} → ${b.schedule_info.destination}</small><br>
          <small class="text-success">Rp ${b.total_price.toLocaleString('id-ID')} • ${b.status}</small>
        </div>
      </div>`;
  });
}