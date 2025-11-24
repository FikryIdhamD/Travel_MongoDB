// static/js/main.js
const API = "http://127.0.0.1:8000/api";
let currentUser = null;
let companiesList = [];

function apiUrl(endpoint) {
  const clean = endpoint.replace(/^\/+|\/+$/g, "");
  return `${API}/${clean}/`;
}

async function fetchWithAuth(url, options = {}) {
  if (!currentUser || currentUser.role !== "admin") {
    alert("Akses ditolak. Hanya admin.");
    return null;
  }

  const headers = {
    "Content-Type": "application/json",
    "X-User-ID": currentUser.id,
    "X-User-Role": currentUser.role,
    ...options.headers,
  };

  const res = await fetch(url, { ...options, headers });

  if (!res.ok) {
    let errorMessage = "Gagal request";

    try {
      const errData = await res.json();
      // FastAPI bisa balikin: {detail: "string"} atau {detail: [{msg: "..."}]}
      if (typeof errData.detail === "string") {
        errorMessage = errData.detail;
      } else if (Array.isArray(errData.detail)) {
        errorMessage = errData.detail.map((e) => e.msg || e.message).join("; ");
      } else if (errData.msg) {
        errorMessage = errData.msg;
      }
    } catch (e) {
      errorMessage = (await res.text()) || res.statusText;
    }

    alert("Error: " + errorMessage);
    return null;
  }

  // Sukses → kembalikan JSON
  return res.json();
}

// Fungsi load companies untuk cache (dipanggil sekali di admin)
async function loadCompaniesForAdmin() {
  if (companiesList.length > 0) return;
  const data = await fetchWithAuth(apiUrl("companies"));
  if (data) companiesList = data;
}

// Fungsi show form di modal (untuk create/edit)
function showAdminForm(entity, id = null) {
  const modal = new bootstrap.Modal(document.getElementById("adminModal"));
  const label = document.getElementById("adminModalLabel");
  const body = document.getElementById("adminModalBody");
  const submitBtn = document.getElementById("adminSubmitBtn");

  label.textContent = id
    ? `Edit ${entity.charAt(0).toUpperCase() + entity.slice(1)}`
    : `Tambah ${entity.charAt(0).toUpperCase() + entity.slice(1)}`;
  body.innerHTML = getFormHtml(entity, id);
  submitBtn.onclick = () => handleAdminSubmit(entity, id);

  modal.show();
}

// Generate HTML form berdasarkan entity
function getFormHtml(entity, id) {
  switch (entity) {
    case "user":
      return `
        <div class="mb-3"><label>Nama</label><input class="form-control" id="form-name" required></div>
        <div class="mb-3"><label>Email</label><input type="email" class="form-control" id="form-email" required></div>
        <div class="mb-3"><label>Password (kosongkan jika edit)</label><input type="password" class="form-control" id="form-password"></div>
        <div class="mb-3"><label>Phone</label><input class="form-control" id="form-phone"></div>
        <div class="mb-3"><label>Role</label><select class="form-select" id="form-role"><option>customer</option><option>admin</option></select></div>
      `;
    case "schedule":
      let companyOptions = companiesList
        .map((c) => `<option value="${c.id}">${c.name}</option>`)
        .join("");
      return `
        <div class="mb-3"><label>Perusahaan</label><select class="form-select" id="form-company_id" required>${companyOptions}</select></div>
        <div class="mb-3"><label>Tipe</label><select class="form-select" id="form-type" required><option>bus</option><option>flight</option><option>train</option></select></div>
        <div class="mb-3"><label>Asal</label><input class="form-control" id="form-origin" required></div>
        <div class="mb-3"><label>Tujuan</label><input class="form-control" id="form-destination" required></div>
        <div class="mb-3"><label>Berangkat</label><input type="datetime-local" class="form-control" id="form-departure_date" required></div>
        <div class="mb-3"><label>Sampai</label><input type="datetime-local" class="form-control" id="form-arrival_date"></div>
        <div class="mb-3"><label>Harga</label><input type="number" class="form-control" id="form-price" required></div>
        <div class="mb-3"><label>Kursi Tersedia</label><input type="number" class="form-control" id="form-available_seats" required></div>
      `;
    case "booking":
      // Untuk booking, mungkin perlu select user_id, schedule_id (load dari API jika perlu)
      return `
        <div class="mb-3"><label>User ID</label><input class="form-control" id="form-user_id" required></div>
        <div class="mb-3"><label>Schedule ID</label><input class="form-control" id="form-schedule_id" required></div>
        <div class="mb-3"><label>Nama Penumpang</label><input class="form-control" id="form-passenger_name" required></div>
        <div class="mb-3"><label>Jumlah Penumpang</label><input type="number" class="form-control" id="form-passenger_count" required></div>
      `;
    case "review":
      return `
        <div class="mb-3"><label>Booking ID</label><input class="form-control" id="form-booking_id" required></div>
        <div class="mb-3"><label>Rating (1-5)</label><input type="number" min="1" max="5" class="form-control" id="form-rating" required></div>
        <div class="mb-3"><label>Komentar</label><textarea class="form-control" id="form-comment"></textarea></div>
      `;
    case "company":
      return `
        <div class="mb-3"><label>Nama</label><input class="form-control" id="form-name" required></div>
        <div class="mb-3"><label>Tipe</label><input class="form-control" id="form-type" required></div>
        <div class="mb-3"><label>Deskripsi</label><textarea class="form-control" id="form-description"></textarea></div>
        <div class="mb-3"><label>Email Kontak</label><input type="email" class="form-control" id="form-contact_email"></div>
        <div class="mb-3"><label>Phone</label><input class="form-control" id="form-phone"></div>
      `;
    default:
      return "<p>Entity tidak dikenal</p>";
  }
}

// Handle submit form
async function handleAdminSubmit(entity, id = null) {
  const payload = getFormPayload(entity);
  if (!payload) return alert("Isi form dengan benar!");

  let url = "";
  let method = id ? "PUT" : "POST";

  switch (entity) {
    case "user":
      url = id ? `/api/users/${id}` : "/api/users/register_admin";
      break;
    case "company":
      url = id ? `/api/companies/${id}` : "/api/companies";
      break;
    case "schedule":
      url = id ? `/api/schedules/${id}` : "/api/schedules";
      break;
    case "booking":
      if (!id) return alert("Booking tidak bisa ditambah manual");
      url = `/api/bookings/${id}`;
      method = "PUT";
      break;
    case "review":
      url = id ? `/api/reviews/${id}` : "/api/reviews";
      break;
    default:
      return alert("Entity tidak didukung!");
  }

  try {
    const result = await fetchWithAuth(url, {
      method,
      body: JSON.stringify(payload),
      headers: { "Content-Type": "application/json" },
    });

    if (result === null) {
      return; // berhenti, jangan lanjut
    }

    alert(id ? "Berhasil diperbarui!" : "Berhasil ditambahkan!");

    bootstrap.Modal.getInstance(document.getElementById("adminModal")).hide();

    loadAdminData(entity);
  } catch (err) {
    console.error("Unexpected error:", err);
    alert("Terjadi kesalahan tak terduga");
  }
}

// Get payload dari form inputs
function getFormPayload(entity) {
  try {
    switch (entity) {
      case "user":
        const password = document.getElementById("form-password").value;
        return {
          name: document.getElementById("form-name").value,
          email: document.getElementById("form-email").value,
          ...(password && { password }),
          phone: document.getElementById("form-phone").value,
          role: document.getElementById("form-role").value,
        };
      case "schedule":
        return {
          company_id: document.getElementById("form-company_id").value,
          type: document.getElementById("form-type").value,
          origin: document.getElementById("form-origin").value,
          destination: document.getElementById("form-destination").value,
          departure_date: new Date(
            document.getElementById("form-departure_date").value
          ).toISOString(),
          arrival_date: document.getElementById("form-arrival_date").value
            ? new Date(
                document.getElementById("form-arrival_date").value
              ).toISOString()
            : null,
          price: parseInt(document.getElementById("form-price").value),
          available_seats: parseInt(
            document.getElementById("form-available_seats").value
          ),
        };
      case "booking":
        return {
          user_id: document.getElementById("form-user_id").value,
          schedule_id: document.getElementById("form-schedule_id").value,
          passenger_name: document.getElementById("form-passenger_name").value,
          passenger_count: parseInt(
            document.getElementById("form-passenger_count").value
          ),
        };
      case "review":
        return {
          booking_id: document.getElementById("form-booking_id").value,
          rating: parseInt(document.getElementById("form-rating").value),
          comment: document.getElementById("form-comment").value,
        };
      case "company":
        return {
          name: document.getElementById("form-name").value,
          type: document.getElementById("form-type").value,
          description: document.getElementById("form-description").value,
          contact_email: document.getElementById("form-contact_email").value,
          phone: document.getElementById("form-phone").value,
        };
    }
  } catch (e) {
    return null;
  }
}

// Fungsi load data untuk tabel
async function loadAdminData(entity) {
  const data = await fetchWithAuth(apiUrl(entity + "s"));
  if (!data) return;

  const tbody = document.querySelector(`#admin-${entity}s-table tbody`);
  tbody.innerHTML = "";
  data.forEach((item) => {
    tbody.innerHTML += getTableRowHtml(entity, item);
  });
}

// Generate row HTML
function getTableRowHtml(entity, item) {
  if (entity === "companie") entity = "company";
  switch (entity) {
    case "user":
      return `<tr><td>${item.id}</td><td>${item.name}</td><td>${
        item.email
      }</td><td>${item.role}</td><td>${item.phone || "-"}</td><td>
        <button class="btn btn-sm btn-warning" onclick="editAdminItem('user', '${
          item.id
        }')">Edit</button>
        <button class="btn btn-sm btn-danger" onclick="deleteAdminItem('user', '${
          item.id
        }')">Hapus</button>
      </td></tr>`;
    case "schedule":
      return `<tr><td>${item.id}</td><td>${item.type}</td><td>${
        item.origin
      }</td><td>${item.destination}</td><td>${new Date(
        item.departure_date
      ).toLocaleString()}</td><td>Rp ${item.price.toLocaleString()}</td><td>${
        item.available_seats
      }</td><td>${item.company?.name || "-"}</td><td>
        <button class="btn btn-sm btn-warning" onclick="editAdminItem('schedule', '${
          item.id
        }')">Edit</button>
        <button class="btn btn-sm btn-danger" onclick="deleteAdminItem('schedule', '${
          item.id
        }')">Hapus</button>
      </td></tr>`;
    case "booking":
      return `<tr><td>${item._id}</td><td>${item.booking_code}</td><td>${
        item.status
      }</td><td>Rp ${item.total_price.toLocaleString()}</td><td>${
        item.passenger_name
      } (${item.passenger_count})</td><td>${item.schedule_info?.origin} → ${
        item.schedule_info?.destination
      }</td><td>${item.user_info?.name || "-"}</td><td>
        <button class="btn btn-sm btn-warning" onclick="editAdminItem('booking', '${
          item._id
        }')">Edit</button>
        <button class="btn btn-sm btn-danger" onclick="deleteAdminItem('booking', '${
          item._id
        }')">Hapus</button>
      </td></tr>`;
    case "review":
      return `<tr><td>${item.id}</td><td>${item.rating}</td><td>${
        item.comment || "-"
      }</td><td>${item.company_name}</td><td>${
        item.user_name
      }</td><td>${new Date(item.created_at).toLocaleDateString()}</td><td>
        <button class="btn btn-sm btn-warning" onclick="editAdminItem('review', '${
          item.id
        }')">Edit</button>
        <button class="btn btn-sm btn-danger" onclick="deleteAdminItem('review', '${
          item.id
        }')">Hapus</button>
      </td></tr>`;
    case "company":
      return `<tr><td>${item.id}</td><td>${item.name}</td><td>${
        item.type
      }</td><td>${item.description || "-"}</td><td>${
        item.average_rating
      }</td><td>${item.total_reviews}</td><td>
        <button class="btn btn-sm btn-warning" onclick="editAdminItem('companie', '${
          item.id
        }')">Edit</button>
        <button class="btn btn-sm btn-danger" onclick="deleteAdminItem('companie', '${
          item.id
        }')">Hapus</button>
      </td></tr>`;
    default:
      console.warn("Entity tidak dikenali:", entity);
      return `<tr><td colspan="10">Entity ${entity} belum didukung</td></tr>`;
  }
}

// Edit item: Load data ke form
async function editAdminItem(entity, id) {
  const data = await fetchWithAuth(apiUrl(entity + "s/" + id));
  if (!data) return;

  showAdminForm(entity, id);
  // Isi form dengan data (contoh untuk user)
  if (entity === "user") {
    document.getElementById("form-name").value = data.name;
    document.getElementById("form-email").value = data.email;
    document.getElementById("form-phone").value = data.phone || "";
    document.getElementById("form-role").value = data.role;
  }
  // Serupa untuk entity lain (tambah logic isi form)
  // Misal untuk schedule: document.getElementById('form-origin').value = data.origin; dll.
}

// Delete item
async function deleteAdminItem(entity, id) {
  if (!confirm("Yakin hapus?")) return;
  const data = await fetchWithAuth(apiUrl(entity + "s/" + id), {
    method: "DELETE",
  });
  if (data) {
    alert("Hapus sukses");
    loadAdminData(entity);
  }
}

async function loadCompanies() {
  const res = await fetch(apiUrl("companies"));
  const companies = await res.json();
  const container = document.getElementById("company-list");
  container.innerHTML = "";

  companies.forEach((c) => {
    const rating = c.average_rating || 0;
    const stars =
      "★".repeat(Math.round(rating)) + "☆".repeat(5 - Math.round(rating));
    container.innerHTML += `
      <div class="col-md-4 mb-4">
        <div class="card h-100">
          <div class="card-body">
            <h5 class="card-title">${c.name}</h5>
            <p class="text-muted">${c.type.toUpperCase()} • ${
      c.total_reviews
    } ulasan</p>
            <p class="fw-bold fs-4 text-warning">${stars} ${rating}</p>
            <p>${c.description || "Layanan transportasi terpercaya"}</p>
            <button class="btn btn-outline-primary btn-sm" onclick="viewCompanyReviews('${
              c.id
            }', '${c.name}')">
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
    reviews.forEach((r) => {
      const stars = "★".repeat(r.rating) + "☆".repeat(5 - r.rating);
      modalBody += `
        <div class="border-bottom pb-2 mb-3">
          <strong>${r.user_name}</strong> 
          <span class="text-warning">${stars}</span>
          <small class="text-muted float-end">${new Date(
            r.created_at
          ).toLocaleDateString("id-ID")}</small>
          <p class="mt-1">${r.comment || "<em>Tanpa komentar</em>"}</p>
        </div>`;
    });
  }

  const modal = new bootstrap.Modal(
    document.getElementById("reviewModal") || createReviewModal()
  );
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
  document
    .getElementById("searchForm")
    ?.addEventListener("submit", searchSchedules);

  // Event untuk load data saat sub-tab admin ditampilkan
  document.querySelectorAll("#adminSubTab a").forEach((tab) => {
    tab.addEventListener("shown.bs.tab", async (e) => {
      const entity = e.target.href.split("#admin-")[1].slice(0, -1); // users → user
      await loadCompaniesForAdmin(); // Untuk select
      loadAdminData(entity);
    });
  });
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
  if (currentUser.role === "admin") {
    document.getElementById("admin-tab").style.display = "list-item";
  }
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
  document.getElementById("auth-title").textContent = isLogin
    ? "Daftar"
    : "Login";
  document.getElementById("toggle-auth").textContent = isLogin
    ? "Sudah punya akun? Login"
    : "Belum punya akun? Daftar";
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
      body: JSON.stringify(body),
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
    type: document.getElementById("type").value,
  });

  const url = apiUrl("schedules") + (params.toString() ? "?" + params : "");
  const res = await fetch(url);
  const schedules = await res.json();
  renderSchedules(schedules);
}

function renderSchedules(schedules) {
  const container = document.getElementById("results");
  container.innerHTML = schedules.length
    ? "<h5>Hasil Pencarian</h5>"
    : "<p class='text-center text-muted'>Tidak ada jadwal.</p>";

  schedules.forEach((s) => {
    container.innerHTML += `
      <div class="card mb-3">
        <div class="card-body">
          <h6>${s.type.toUpperCase()} • ${s.company?.name || "Unknown"}</h6>
          <p class="mb-1"><strong>${s.origin} → ${s.destination}</strong></p>
          <p class="mb-1">Berangkat: ${new Date(
            s.departure_date
          ).toLocaleString("id-ID")}</p>
          <p class="mb-1 text-success fw-bold">Rp ${s.price.toLocaleString(
            "id-ID"
          )}</p>
          <p class="mb-2"><small>Tersedia: ${
            s.available_seats
          } kursi</small></p>
          <button class="btn btn-primary btn-sm" onclick="bookSchedule('${
            s.id
          }')">Pesan</button>
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
    passenger_count: passengerCount,
  };

  console.log("Booking payload:", payload); // DEBUG

  try {
    const res = await fetch(apiUrl("bookings"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
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
  popular.forEach((p) => {
    container.innerHTML += `
      <div class="alert alert-info p-2">
        <strong>${p.schedule.origin} → ${p.schedule.destination}</strong> (${
      p.schedule.type
    })<br>
        <small>${p.booking_count} booking • Rp ${p.total_revenue.toLocaleString(
      "id-ID"
    )}</small>
      </div>`;
  });
}

async function loadBookingHistory() {
  // 1. Dapatkan ID pengguna yang sedang login
  const userId = currentUser.id; // Contoh pengambilan dari localStorage

  if (!userId) {
    console.error(
      "User ID tidak ditemukan. Tidak dapat memuat riwayat booking."
    );
    document.getElementById("booking-history").innerHTML =
      "<h5>Riwayat Booking</h5><p class='text-danger'>Harap login untuk melihat riwayat.</p>";
    return;
  }

  const container = document.getElementById("booking-history");
  container.innerHTML = "<h5>Riwayat Booking</h5>";

  try {
    // 2. Ganti URL fetch untuk menggunakan endpoint 'get booking by user' yang baru
    const res = await fetch(apiUrl(`bookings/user/${userId}`));

    if (!res.ok) {
      // Tangani jika server merespons dengan error (misalnya 404 jika ID tidak valid)
      throw new Error(`Gagal memuat booking: ${res.statusText}`);
    }

    const bookings = await res.json();

    if (!bookings.length) {
      container.innerHTML += "<p class='text-muted'>Belum ada booking.</p>";
      return;
    }

    // 3. Iterasi dan tampilkan data
    bookings.forEach((b) => {
      // Cek status untuk menampilkan tombol ulasan (hanya jika completed DAN status_review pending)
      const showReviewButton =
        b.status_review === "pending" && b.status === "completed";

      container.innerHTML += `
        <div class="card mb-3">
          <div class="card-body">
            <div class="d-flex justify-content-between">
              <div>
                <strong>${b.booking_code}</strong> • ${b.passenger_name} (${
        b.passenger_count
      }x)<br>
                <small>${b.schedule_info.origin} → ${
        b.schedule_info.destination
      } 
                • ${new Date(b.schedule_info.departure_date).toLocaleDateString(
                  "id-ID"
                )}</small><br>
                <span class="badge bg-success">Rp ${b.total_price.toLocaleString(
                  "id-ID"
                )}</span>
                <span class="badge ${
                  b.status === "completed"
                    ? "bg-success"
                    : b.status === "cancelled"
                    ? "bg-danger"
                    : "bg-warning"
                }">${b.status.toUpperCase()}</span>
              </div>
              ${
                showReviewButton
                  ? `
                <button class="btn btn-primary btn-sm" onclick="openReviewForm('${
                  b._id
                }', '${b.schedule_info.company?.name || "Perusahaan"}')">
                  Beri Ulasan
                </button>`
                  : ""
              }
            </div>
          </div>
        </div>`;
    });
  } catch (error) {
    console.error("Error loading booking history:", error);
    container.innerHTML += `<p class='text-danger'>Terjadi kesalahan saat mengambil data.</p>`;
  }
}

function openReviewForm(bookingId, companyName) {
  const modal = new bootstrap.Modal(
    document.getElementById("reviewModal") || createReviewModal()
  );
  document.getElementById(
    "reviewModalLabel"
  ).textContent = `Ulasan untuk ${companyName}`;

  document.getElementById("reviewModalBody").innerHTML = `
    <form id="reviewForm">
      <input type="hidden" id="review_booking_id" value="${bookingId}">
      <div class="mb-3">
        <label class="form-label">Rating</label><br>
        <div class="star-rating">
          ${[5, 4, 3, 2, 1]
            .map(
              (i) => `
            <span class="star" style="font-size:2rem;cursor:pointer" onclick="setRating(${i})">☆</span>
          `
            )
            .join("")}
        </div>
        <input type="hidden" id="selected_rating" value="5">
      </div>
      <div class="mb-3">
        <label class="form-label">Komentar (opsional)</label>
        <textarea class="form-control" id="review_comment" rows="3"></textarea>
      </div>
      <div class="text-end">
        <button type="button" class="btn btn-secondary me-2" data-bs-dismiss="modal">Batal</button>
        <button type="submit" class="btn btn-success">Kirim Ulasan</button>
      </div>
    </form>`;

  // Reset rating ke 5 bintang setiap buka modal
  setRating(5);

  // SUBMIT REVIEW → yang paling penting di sini
  document.getElementById("reviewForm").onsubmit = async (e) => {
    e.preventDefault();

    const payload = {
      booking_id: bookingId,
      rating: parseInt(document.getElementById("selected_rating").value),
      comment: document.getElementById("review_comment").value.trim() || null,
    };

    try {
      const res = await fetch(apiUrl("reviews"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (res.ok) {
        alert("Terima kasih atas ulasannya!");
        modal.hide();

        // INI YANG HARUS ADA → refresh data terbaru!
        loadBookingHistory(); // ← tombol akan hilang otomatis
        loadCompanies(); // ← rating perusahaan langsung update
      } else {
        const err = await res.json();
        alert(err.detail || "Gagal mengirim ulasan");
      }
    } catch (err) {
      alert("Koneksi gagal");
    }
  };

  modal.show();
}

function setRating(val) {
  document.getElementById("selected_rating").value = val;
  document.querySelectorAll(".star").forEach((s, i) => {
    s.textContent = i < 5 - val ? "☆" : "★";
  });
}
