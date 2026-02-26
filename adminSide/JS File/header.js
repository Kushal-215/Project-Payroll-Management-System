// ── Leave Request Notification Dropdown ─────────────────────────────
function toggleNotifications() {
    const dropdown = document.getElementById("notifDropdown");
    const profileDropdown = document.getElementById("profileDropdown");

    // Close profile if open
    if (profileDropdown) profileDropdown.style.display = "none";

    dropdown.style.display = dropdown.style.display === "block" ? "none" : "block";

    if (dropdown.style.display === "block") {
        loadLeaveRequests();
    }
}

function loadLeaveRequests() {
    fetch("http://localhost:5000/leave_requests")
        .then(res => res.json())
        .then(data => {
            const list = document.getElementById("notifList");
            const badge = document.getElementById("notifBadge");

            const pending = data.filter(r => r.status === "Pending");
            badge.innerText = pending.length;
            badge.style.display = pending.length > 0 ? "flex" : "none";

            if (pending.length === 0) {
                list.innerHTML = `<p class="notif-empty">No pending leave requests</p>`;
                return;
            }

            list.innerHTML = pending.map(r => `
                <div class="notif-item">
                    <p class="notif-name">${r.employee_name}</p>
                    <p class="notif-detail">${r.leave_type} · ${r.start_date} to ${r.end_date}</p>
                    <p class="notif-reason">${r.reason || ""}</p>
                    <div class="notif-actions">
                        <button onclick="respondLeave(${r.id}, 'Approved')">Approve</button>
                        <button onclick="respondLeave(${r.id}, 'Rejected')">Reject</button>
                    </div>
                </div>
            `).join("");
        })
        .catch(() => {
            document.getElementById("notifList").innerHTML =
                `<p class="notif-empty">Could not load requests</p>`;
        });
}

function respondLeave(id, status) {
    fetch(`http://localhost:5000/leave_requests/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status })
    })
    .then(res => res.json())
    .then(() => loadLeaveRequests());
}

// ── Profile Dropdown ─────────────────────────────────────────────────
function toggleProfile() {
    const dropdown = document.getElementById("profileDropdown");
    const notifDropdown = document.getElementById("notifDropdown");

    // Close notifications if open
    if (notifDropdown) notifDropdown.style.display = "none";

    dropdown.style.display = dropdown.style.display === "block" ? "none" : "block";
}

function openEditProfile() {
    document.getElementById("profileDropdown").style.display = "none";
    document.getElementById("editProfilePopup").style.display = "flex";
}

function closeEditProfile() {
    document.getElementById("editProfilePopup").style.display = "none";
}

function saveProfile() {
    const name = document.getElementById("editAdminName").value.trim();
    const password = document.getElementById("editAdminPassword").value.trim();

    if (!name) {
        alert("Name cannot be empty");
        return;
    }

    fetch("http://localhost:5000/update_admin", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, password })
    })
    .then(res => res.json())
    .then(result => {
        alert(result.message);
        closeEditProfile();
        document.querySelector(".welcome-name").innerText = `Welcome Back, ${name}`;
    })
    .catch(() => alert("Failed to update profile"));
}

function logout() {
    if (confirm("Are you sure you want to log out?")) {
        window.location.href = "../public/login.html";
    }
}

// ── Close dropdowns when clicking outside ───────────────────────────
document.addEventListener("click", function(e) {
    const notif = document.getElementById("notifDropdown");
    const profile = document.getElementById("profileDropdown");
    const notifBtn = document.getElementById("notifBtn");
    const profileBtn = document.getElementById("profileBtn");

    if (notif && !notif.contains(e.target) && e.target !== notifBtn) {
        notif.style.display = "none";
    }
    if (profile && !profile.contains(e.target) && e.target !== profileBtn) {
        profile.style.display = "none";
    }
});

// ── Load admin name on page load ─────────────────────────────────────
document.addEventListener("DOMContentLoaded", function() {
    fetch("http://localhost:5000/admin")
        .then(res => res.json())
        .then(data => {
            const el = document.querySelector(".welcome-name");
            if (el) el.innerText = `Welcome Back, ${data.name}`;
        })
        .catch(() => {});

    // Load notification badge count
    fetch("http://localhost:5000/leave_requests")
        .then(res => res.json())
        .then(data => {
            const pending = data.filter(r => r.status === "Pending").length;
            const badge = document.getElementById("notifBadge");
            if (badge) {
                badge.innerText = pending;
                badge.style.display = pending > 0 ? "flex" : "none";
            }
        })
        .catch(() => {});
});
