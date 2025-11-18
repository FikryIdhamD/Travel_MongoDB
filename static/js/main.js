// static/js/main.js
const API = "http://127.0.0.1:8000/api";
let currentUser = null;

function apiUrl(endpoint) {
  const clean = endpoint.replace(/^\/+|\/+$/g, '');
  return `${API}/${clean}/`;
}

async function loadCompanies() {
  const res = await fetch(apiUrl("companies"));
  const companies = await res.json();
  const container = document.getElementById("company-list");
  container.innerHTML = "";

  companies.forEach(c => {
    const rating = c.average_rating || 0;
    const stars = "★".repeat(Math.round(rating)) + "☆".repeat(5 - Math.round(rating));
    container.innerHTML += `
      <div class="col-md-4 mb-4">
        <div class="card h-100">
          <div class="card-body">
            <h5 class="card-title">${c.name}</h5>
            <p class="text-muted">${c.type.toUpperCase()} • ${c.total_reviews} ulasan</p>
            <p class="fw-bold fs-4 text-warning">${stars} ${rating}</p>
            <p>${c.description || "Layanan transportasi terpercaya"}</p>
            <button class="btn btn-outline-primary btn-sm" onclick="viewCompanyReviews('${c.id}', '${c.name}')">
              Lihat Ulasan
            </button>
          </div>
        </div>
      </div>`;
  });
}

async function viewCompanyReviews(companyId, companyName) {
  const res = await fetch(apiUrl(`reviews/company/${companyId}`));
  const reviews = await res.json();

  let modalBody = `<h5>Ulasan untuk ${companyName}</h5><hr>`;
  if (reviews.length === 0) {
    modalBody += "<p>Belum ada ulasan.</p>";
  } else {
    reviews.forEach(r => {
      const stars = "★".repeat(r.rating) + "☆".repeat(5 - r.rating);
      modalBody += `
        <div class="border-bottom pb-2 mb-3">
          <strong>${r.user_name}</strong> 
          <span class="text-warning">${stars}</span>
          <small class="text-muted float-end">${new Date(r.created_at).toLocaleDateString('id-ID')}</small>
          <p class="mt-1">${r.comment || "<em>Tanpa komentar</em>"}</p>
        </div>`;
    });
  }

  const modal = new bootstrap.Modal(document.getElementById("reviewModal") || createReviewModal());
  document.getElementById("reviewModalLabel").textContent = "Ulasan Perusahaan";
  document.getElementById("reviewModalBody").innerHTML = modalBody;
  modal.show();
}

function createReviewModal() {
  const modalHtml = `
    <div class="modal fade" id="reviewModal" tabindex="-1">
      <div class="modal-dialog modal-lg">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title" id="reviewModalLabel">Ulasan</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body" id="reviewModalBody"></div>
        </div>
      </div>
    </div>`;
  document.body.insertAdjacentHTML("beforeend", modalHtml);
  return document.getElementById("reviewModal");
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
  loadCompanies();
  const hash = window.location.hash.replace("#", "") || "search";
  document.querySelector(`a[href="#${hash}"]`)?.click();
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
          <h6>${s.type.toUpperCase()} • ${s.company?.name || 'Unknown'}</h6>
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
    const canReview = b.status === "completed" && !b.has_review; // nanti bisa cek dari backend
    container.innerHTML += `
      <div class="card mb-3">
        <div class="card-body">
          <div class="d-flex justify-content-between">
            <div>
              <strong>${b.booking_code}</strong> • ${b.passenger_name} (${b.passenger_count}x)<br>
              <small>${b.schedule_info.origin} → ${b.schedule_info.destination} 
              • ${new Date(b.schedule_info.departure_date).toLocaleDateString('id-ID')}</small><br>
              <span class="badge bg-success">Rp ${b.total_price.toLocaleString('id-ID')}</span>
              <span class="badge ${b.status === 'completed' ? 'bg-success' : 'bg-warning'}">${b.status}</span>
            </div>
            ${b.status === "completed" ? `
              <button class="btn btn-primary btn-sm" onclick="openReviewForm('${b._id}', '${b.schedule_info.company?.name || 'Perusahaan'}')">
                Beri Ulasan
              </button>` : ''}
          </div>
        </div>
      </div>`;
  });
}

function openReviewForm(bookingId, companyName) {
  const modal = new bootstrap.Modal(document.getElementById("reviewModal") || createReviewModal());
  document.getElementById("reviewModalLabel").textContent = `Ulasan untuk ${companyName}`;
  document.getElementById("reviewModalBody").innerHTML = `
    <form id="reviewForm">
      <input type="hidden" id="review_booking_id" value="${bookingId}">
      <div class="mb-3">
        <label>Rating</label><br>
        <div class="star-rating">
          ${[5,4,3,2,1].map(i => `
            <span class="star" style="font-size:2rem;cursor:pointer" onclick="setRating(${i})">☆</span>
          `).join("")}
        </div>
        <input type="hidden" id="selected_rating" value="5">
      </div>
      <div class="mb-3">
        <label>Komentar (opsional)</label>
        <textarea class="form-control" id="review_comment" rows="3"></textarea>
      </div>
      <button type="submit" class="btn btn-success">Kirim Ulasan</button>
    </form>`;

  document.getElementById("reviewForm").onsubmit = async (e) => {
    e.preventDefault();
    const payload = {
      booking_id: bookingId,
      rating: parseInt(document.getElementById("selected_rating").value),
      comment: document.getElementById("review_comment").value.trim() || null
    };

    const res = await fetch(apiUrl("reviews"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (res.ok) {
      alert("Terima kasih atas ulasannya!");
      modal.hide();
      loadBookingHistory();
      loadCompanies();
    } else {
      const err = await res.json();
      alert(err.detail || "Gagal mengirim ulasan");
    }
  };

  modal.show();
}

function setRating(val) {
  document.getElementById("selected_rating").value = val;
  document.querySelectorAll(".star").forEach((s, i) => {
    s.textContent = (i < 5-val) ? "☆" : "★";
  });
}